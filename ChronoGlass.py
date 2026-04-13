import sys
import os
import json
import winsound
import datetime
import traceback
import urllib.request
import urllib.parse
import threading
from enum import IntEnum

try:
    from lunar_python import Lunar, Solar

    HAS_LUNAR = True
except ImportError:
    HAS_LUNAR = False

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QMenu, QInputDialog, QSystemTrayIcon, QHBoxLayout, QPushButton, QFrame,
                             QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QSpinBox, QLineEdit, QFormLayout, QComboBox)
from PyQt6.QtCore import QTimer, QTime, Qt, QPoint, QDateTime, pyqtSignal, QPropertyAnimation, pyqtProperty, \
    QEasingCurve
from PyQt6.QtGui import QFont, QAction, QIcon, QPainter, QColor, QBrush


STATE_FILE_NAME = "chronoglass_state.json"
LEGACY_ALARMS_FILE_NAME = "alarms.json"
LEGACY_CONFIG_FILE_NAME = "config.json"
STATE_LOCK = threading.RLock()


def resource_path(relative_path):
    nuitka_root = os.environ.get("NUITKA_PACKAGE_HOME")
    if nuitka_root:
        return os.path.join(nuitka_root, relative_path)
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    if hasattr(sys, "frozen") or "__compiled__" in globals():
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


# --- 本地持久化工具函数 ---
def get_data_file_path(filename=STATE_FILE_NAME):
    """获取数据文件的存储路径（强制保存在真正的 exe 同级目录）"""
    if getattr(sys, 'frozen', False) or "__compiled__" in globals():
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


def log_error(message, exc=None):
    try:
        log_path = get_data_file_path('chronoglass.log')
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        detail = f"[{now}] {message}\n"
        if exc is not None:
            detail += "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(detail)
            f.write("\n")
    except Exception:
        return


def atomic_write_json(file_path, data):
    tmp_path = f"{file_path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, file_path)


def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_alarm(record):
    alarm = dict(record)
    time_value = alarm.get("time", "00:00:00")
    if isinstance(time_value, QTime):
        alarm["time"] = time_value if time_value.isValid() else QTime(0, 0)
    else:
        parsed_time = QTime.fromString(str(time_value), "HH:mm:ss")
        alarm["time"] = parsed_time if parsed_time.isValid() else QTime(0, 0)

    alarm.setdefault("name", "新闹钟")
    alarm.setdefault("enabled", True)
    alarm.setdefault("repeat", "once")
    alarm.setdefault("last_trigger_date", "")
    if alarm["repeat"] not in ("once", "daily"):
        alarm["repeat"] = "once"
    return alarm


def serialize_alarm(alarm):
    repeat = alarm.get("repeat", "once")
    if repeat not in ("once", "daily"):
        repeat = "once"

    time_value = alarm.get("time", QTime(0, 0))
    if isinstance(time_value, QTime):
        time_str = time_value.toString("HH:mm:ss")
    else:
        time_str = str(time_value)
        if not QTime.fromString(time_str, "HH:mm:ss").isValid():
            time_str = "00:00:00"

    return {
        "time": time_str,
        "name": alarm.get("name", "新闹钟"),
        "enabled": alarm.get("enabled", True),
        "repeat": repeat,
        "last_trigger_date": alarm.get("last_trigger_date", "")
    }


def deserialize_alarm(record):
    return normalize_alarm({
        "time": record.get("time", "00:00:00"),
        "name": record.get("name", "新闹钟"),
        "enabled": record.get("enabled", True),
        "repeat": record.get("repeat", "once"),
        "last_trigger_date": record.get("last_trigger_date", "")
    })


def default_state():
    return {
        "version": 1,
        "config": {},
        "alarms": []
    }


def normalize_state(record):
    state = default_state()
    if not isinstance(record, dict):
        return state

    version = record.get("version")
    if isinstance(version, int):
        state["version"] = version

    config = record.get("config")
    if isinstance(config, dict):
        state["config"] = dict(config)

    alarms = record.get("alarms")
    if isinstance(alarms, list):
        state["alarms"] = [deserialize_alarm(alarm) for alarm in alarms if isinstance(alarm, dict)]

    return state


def serialize_state(state):
    normalized = normalize_state(state)
    return {
        "version": normalized["version"],
        "config": normalized["config"],
        "alarms": [serialize_alarm(alarm) for alarm in normalized["alarms"]]
    }


def load_legacy_state():
    state = default_state()

    alarms_path = get_data_file_path(LEGACY_ALARMS_FILE_NAME)
    if os.path.exists(alarms_path):
        try:
            data = read_json_file(alarms_path)
            if isinstance(data, list):
                state["alarms"] = [deserialize_alarm(alarm) for alarm in data if isinstance(alarm, dict)]
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
            log_error("读取旧版 alarms.json 失败", e)

    config_path = get_data_file_path(LEGACY_CONFIG_FILE_NAME)
    if os.path.exists(config_path):
        try:
            data = read_json_file(config_path)
            if isinstance(data, dict):
                state["config"] = dict(data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
            log_error("读取旧版 config.json 失败", e)

    return state


def load_state():
    file_path = get_data_file_path(STATE_FILE_NAME)
    with STATE_LOCK:
        if os.path.exists(file_path):
            try:
                return normalize_state(read_json_file(file_path))
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
                log_error(f"读取 {STATE_FILE_NAME} 失败", e)

        state = load_legacy_state()
        if state["alarms"] or state["config"]:
            save_state(state)
        return state


def save_state(state):
    file_path = get_data_file_path(STATE_FILE_NAME)
    try:
        payload = serialize_state(state)
        with STATE_LOCK:
            atomic_write_json(file_path, payload)
    except Exception as e:
        print(f"状态保存失败: {e}")
        log_error(f"写入 {STATE_FILE_NAME} 失败", e)


def load_alarms():
    return load_state()["alarms"]


def save_alarms(alarms):
    state = load_state()
    state["alarms"] = list(alarms)
    save_state(state)


def load_config():
    """读取程序通用配置（如地理位置）"""
    return load_state()["config"]


def save_config(config):
    """保存程序通用配置"""
    state = load_state()
    state["config"] = dict(config)
    save_state(state)


# --- 自定义原生平滑开关控件 ---
class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._position = 20 if checked else 2

    @pyqtProperty(int)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def setChecked(self, checked):
        self._checked = checked
        self._position = 20 if checked else 2
        self.update()

    def isChecked(self):
        return self._checked

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.start_animation()
            self.toggled.emit(self._checked)

    def start_animation(self):
        self.anim = QPropertyAnimation(self, b"position")
        self.anim.setDuration(150)
        self.anim.setStartValue(self._position)
        self.anim.setEndValue(20 if self._checked else 2)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        bg_color = QColor("#88c0d0") if self._checked else QColor("#4c566a")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, rect.width(), rect.height(), 11, 11)
        painter.setBrush(QBrush(QColor("#eceff4")))
        painter.drawEllipse(self._position, 2, 18, 18)
        painter.end()


from PyQt6.QtWidgets import QAbstractSpinBox


class CustomSpinBox(QWidget):
    """纯代码拼装的上下带 + - 文本的输入框，免疫一切打包丢图问题"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.spin = QSpinBox()
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin.setFixedSize(55, 30)
        self.spin.setStyleSheet("""
            QSpinBox {
                background-color: #3b4252; border: 1px solid #4c566a; border-right: none;
                border-top-left-radius: 4px; border-bottom-left-radius: 4px;
                padding: 5px; color: #eceff4;
            }
        """)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(0)

        btn_style = """
            QPushButton {
                background-color: #3b4252; border: 1px solid #4c566a; color: #eceff4;
                font-family: 'Consolas', 'Microsoft YaHei'; font-weight: bold; font-size: 14px; padding: 0px;
            }
            QPushButton:hover { background-color: #434c5e; }
            QPushButton:pressed { background-color: #2e3440; }
        """

        self.btn_up = QPushButton("+")
        self.btn_up.setFixedSize(25, 15)
        self.btn_up.setStyleSheet(btn_style + "border-top-right-radius: 4px; border-bottom: none;")
        self.btn_up.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_up.clicked.connect(self.spin.stepUp)

        self.btn_down = QPushButton("-")
        self.btn_down.setFixedSize(25, 15)
        self.btn_down.setStyleSheet(btn_style + "border-bottom-right-radius: 4px;")
        self.btn_down.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_down.clicked.connect(self.spin.stepDown)

        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)

        layout.addWidget(self.spin)
        layout.addLayout(btn_layout)

    def value(self): return self.spin.value()

    def setValue(self, v): self.spin.setValue(v)

    def setRange(self, min_val, max_val): self.spin.setRange(min_val, max_val)


def alarm_remaining_text(alarm):
    today = datetime.date.today().isoformat()
    last_trigger_date = alarm.get("last_trigger_date", "")
    repeat = alarm.get("repeat", "once")

    if repeat == "once" and last_trigger_date == today:
        return "已触发"
    if not alarm["enabled"]:
        return "已停用"

    now = QTime.currentTime()
    target = alarm["time"]
    now_sec = now.hour() * 3600 + now.minute() * 60 + now.second()
    target_sec = target.hour() * 3600 + target.minute() * 60 + target.second()
    diff = target_sec - now_sec

    if repeat == "once":
        if diff < 0:
            return "已过期"
    else:
        if last_trigger_date == today and diff <= 0:
            diff += 24 * 3600
        elif diff < 0:
            diff += 24 * 3600

    hours, rem = divmod(diff, 3600)
    minutes, seconds = divmod(rem, 60)

    if hours > 0:
        if minutes > 0:
            return f"{hours}小时{minutes}分钟"
        if seconds > 0:
            return f"{hours}小时{seconds}秒"
        return f"{hours}小时"

    if minutes > 0:
        if seconds > 0:
            return f"{minutes}分{seconds}秒"
        return f"{minutes}分钟"

    if seconds > 0:
        return f"{seconds}秒"

    return "即将触发"


class AlarmEditDialog(QDialog):
    def __init__(self, hour=0, minute=0, second=0, name="新闹钟", repeat="once", title="添加闹钟", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(350, 220)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("QDialog { background-color: #2e3440; color: #d8dee9; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 10)

        self.spin_h = CustomSpinBox()
        self.spin_h.setRange(0, 23)
        self.spin_h.setValue(hour)

        self.spin_m = CustomSpinBox()
        self.spin_m.setRange(0, 59)
        self.spin_m.setValue(minute)

        self.spin_s = CustomSpinBox()
        self.spin_s.setRange(0, 59)
        self.spin_s.setValue(second)

        time_layout = QHBoxLayout()
        time_layout.addWidget(self.spin_h)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(self.spin_m)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(self.spin_s)
        form.addRow("时间", time_layout)

        self.name_edit = QLineEdit()
        self.name_edit.setText(name)
        self.name_edit.setStyleSheet(
            "QLineEdit { background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; padding: 5px; color: #eceff4; }")
        form.addRow("标签", self.name_edit)

        self.repeat_combo = QComboBox()
        self.repeat_combo.addItem("一次性", "once")
        self.repeat_combo.addItem("每天", "daily")
        idx = self.repeat_combo.findData(repeat)
        self.repeat_combo.setCurrentIndex(0 if idx < 0 else idx)
        self.repeat_combo.setStyleSheet(
            "QComboBox { background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; padding: 5px; color: #eceff4; }")
        form.addRow("重复", self.repeat_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #3b4252; border: 1px solid #4c566a; border-radius: 6px; padding: 6px 18px; color: #d8dee9; } QPushButton:hover { background-color: #4c566a; }")
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("确定")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #88c0d0; color: #2e3440; border-radius: 6px; padding: 6px 18px; font-weight: bold; } QPushButton:hover { background-color: #8fbcbb; }")
        ok_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        self.name_edit.selectAll()
        self.name_edit.setFocus()

    def get_time(self):
        return QTime(self.spin_h.value(), self.spin_m.value(), self.spin_s.value())

    def get_name(self):
        return self.name_edit.text().strip() or "新闹钟"

    def get_repeat(self):
        return self.repeat_combo.currentData()


class AlarmSettingsDialog(QDialog):
    def __init__(self, alarms, parent=None):
        super().__init__(parent)
        self.alarms = alarms
        self.initUI()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_remaining_times)
        self.refresh_timer.start(10000)

    def initUI(self):
        self.setWindowTitle("闹钟设置")
        self.setMinimumSize(540, 420)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #2e3440; color: #d8dee9;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加闹钟")
        del_btn = QPushButton("➖ 删除选中")
        edit_btn = QPushButton("✏️ 修改选中")

        for btn in [add_btn, del_btn, edit_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { background-color: #3b4252; border: 1px solid #4c566a; border-radius: 6px; padding: 6px 12px; color: #eceff4; font-weight: bold; }
                QPushButton:hover { background-color: #434c5e; border: 1px solid #88c0d0; }
            """)
            btn_layout.addWidget(btn)

        add_btn.clicked.connect(self.add_alarm)
        del_btn.clicked.connect(self.delete_alarm)
        edit_btn.clicked.connect(self.edit_alarm)
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["时间", "闹钟标签", "重复", "剩余", "状态"])

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2e3440; color: #eceff4; border: 1px solid #4c566a;
                font-family: 'Consolas', 'Microsoft YaHei'; font-size: 13px; border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #3b4252; color: #88c0d0; padding: 8px; border: none;
                border-bottom: 2px solid #4c566a; border-right: 1px solid #434c5e;
                font-family: 'Microsoft YaHei'; font-weight: bold;
            }
            QTableWidget::item { border-bottom: 1px solid #3b4252; padding: 4px; }
            QTableWidget::item:selected { background-color: #4c566a; color: #eceff4; }
        """)

        self.refresh_table()
        layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = QPushButton("完成并关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: #88c0d0; color: #2e3440; border-radius: 6px; padding: 8px 24px; font-weight: bold; }
            QPushButton:hover { background-color: #8fbcbb; }
        """)
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)

    def refresh_table(self):
        self.table.setRowCount(len(self.alarms))
        now = QTime.currentTime()

        for i, alarm in enumerate(self.alarms):
            time_str = alarm["time"].toString("HH:mm:ss")
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, time_item)

            name_item = QTableWidgetItem(alarm["name"])
            self.table.setItem(i, 1, name_item)

            repeat_text = "每天" if alarm.get("repeat", "once") == "daily" else "一次性"
            repeat_item = QTableWidgetItem(repeat_text)
            repeat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, repeat_item)

            remaining = alarm_remaining_text(alarm)
            rem_item = QTableWidgetItem(remaining)
            rem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            is_expired = alarm.get("repeat", "once") == "once" and remaining in ("已过期", "已触发")
            if is_expired:
                rem_item.setForeground(QColor("#bf616a"))
            self.table.setItem(i, 3, rem_item)

            chk = ToggleSwitch(checked=alarm["enabled"])
            chk.toggled.connect(lambda checked, idx=i: self.toggle_alarm(idx, checked))

            cell_widget = QWidget()
            chk_layout = QHBoxLayout(cell_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 4, cell_widget)

            if is_expired:
                cell_widget.setVisible(False)

    def update_remaining_times(self):
        now = QTime.currentTime()
        for i, alarm in enumerate(self.alarms):
            rem_item = self.table.item(i, 3)
            rem_text = alarm_remaining_text(alarm)
            is_expired = alarm.get("repeat", "once") == "once" and rem_text in ("已过期", "已触发")

            if rem_item:
                rem_item.setText(rem_text)
                if is_expired:
                    rem_item.setForeground(QColor("#bf616a"))
                else:
                    rem_item.setForeground(QColor("#eceff4"))

            cell_widget = self.table.cellWidget(i, 4)
            if cell_widget:
                cell_widget.setVisible(not is_expired)

    def add_alarm(self):
        now = QTime.currentTime()
        dlg = AlarmEditDialog(now.hour(), now.minute(), 0, "新闹钟", "once", "添加闹钟", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.alarms.append({
                "time": dlg.get_time(),
                "name": dlg.get_name(),
                "enabled": True,
                "repeat": dlg.get_repeat(),
                "last_trigger_date": ""
            })
            save_alarms(self.alarms)
            self.refresh_table()

    def delete_alarm(self):
        row = self.table.currentRow()
        if row >= 0:
            self.alarms.pop(row)
            save_alarms(self.alarms)
            self.refresh_table()

    def edit_alarm(self):
        row = self.table.currentRow()
        if row < 0: return
        alarm = self.alarms[row]
        dlg = AlarmEditDialog(
            alarm["time"].hour(), alarm["time"].minute(), alarm["time"].second(),
            alarm["name"], alarm.get("repeat", "once"), "修改闹钟", self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            alarm["time"] = dlg.get_time()
            alarm["name"] = dlg.get_name()
            alarm["repeat"] = dlg.get_repeat()
            alarm["last_trigger_date"] = ""
            save_alarms(self.alarms)
            self.refresh_table()

    def toggle_alarm(self, index, enabled):
        self.alarms[index]["enabled"] = enabled
        save_alarms(self.alarms)
        self.update_remaining_times()

    def closeEvent(self, event):
        if self.parent():
            self.parent().refresh_display()
        super().closeEvent(event)


class AlarmTriggerDialog(QDialog):
    def __init__(self, alarm, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.action = "done"
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(450, 260)
        self.setStyleSheet("QDialog { background-color: #2e3440; border: 2px solid #bf616a; border-radius: 12px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 20)

        top_layout = QHBoxLayout()
        top_layout.addStretch()
        close_btn = QPushButton("✖")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn.setAutoDefault(False)
        close_btn.setDefault(False)
        close_btn.setStyleSheet(
            "QPushButton { border: none; color: #4c566a; font-weight: bold; font-size: 16px; } QPushButton:hover { color: #bf616a; }")
        close_btn.clicked.connect(self.do_done)
        top_layout.addWidget(close_btn)
        layout.addLayout(top_layout)

        icon_label = QLabel("⏰")
        icon_label.setFont(QFont("Segoe UI Emoji", 45))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        time_str = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        time_label = QLabel(time_str)
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label.setFont(QFont("Consolas", 11))
        time_label.setStyleSheet("color: #88c0d0;")
        layout.addWidget(time_label)

        name_label = QLabel(self.alarm["name"])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #eceff4; margin-top: 5px; margin-bottom: 20px;")
        layout.addWidget(name_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        snooze_btn = QPushButton("延时5分钟")
        edit_btn = QPushButton("修改设置")
        done_btn = QPushButton("完成")

        for btn, color, hcolor in [(snooze_btn, "#81a1c1", "#5e81ac"), (edit_btn, "#ebcb8b", "#d08770"),
                                   (done_btn, "#bf616a", "#a3be8c")]:
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setStyleSheet(
                f"background-color: {color}; color: #2e3440; border-radius: 6px; font-size: 15px; font-weight: bold;")
            btn_layout.addWidget(btn)

        snooze_btn.clicked.connect(self.do_snooze)
        edit_btn.clicked.connect(self.do_edit)
        done_btn.clicked.connect(self.do_done)

        layout.addLayout(btn_layout)

    def do_snooze(self): self.action = "snooze"; self.accept()

    def do_edit(self): self.action = "edit"; self.accept()

    def do_done(self): self.action = "done"; self.accept()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.activate_dialog)

    def activate_dialog(self):
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            event.accept()
            return
        super().keyPressEvent(event)


class AppMode(IntEnum):
    CLOCK = 0
    COUNTDOWN = 1
    STOPWATCH = 2
    ALARM = 3


class ChronoGlass(QWidget):
    # 【核心改动：天气更新信号】
    weather_updated = pyqtSignal(str)
    WINDOW_WIDTH = 450
    WINDOW_HEIGHT = 210

    def __init__(self):
        super().__init__()
        self.mode = AppMode.CLOCK
        self.is_running = False
        self.default_seconds = 1200
        self.remaining_seconds = self.default_seconds
        self.elapsed_seconds = 0
        self.drag_position = QPoint()

        self.alarms = load_alarms()

        # 【核心改动：读取配置信息】
        self.config = load_config()
        self.location = self.config.get("location", "")
        self.weather_info = ""
        self.weather_fetch_inflight = False
        self.weather_lock = threading.Lock()
        self.cached_clock_info_date = None
        self.cached_clock_info_html = ""

        # 绑定天气更新槽函数
        self.weather_updated.connect(self.on_weather_updated)

        self.icon_path = resource_path("tray_icon.png")
        self.tray_icon_path = resource_path("tray_icon.png")

        self.initUI()
        self.create_tray()

        # 如果已有位置，启动时获取一次天气
        if self.location:
            self.fetch_weather()

        # 【核心改动：每半小时自动更新天气】
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.fetch_weather)
        self.weather_timer.start(1800000)  # 30分钟 = 30 * 60 * 1000 毫秒

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(self.icon_path))

        # 【核心改动 2：调用全局变量控制窗口尺寸】
        self.setMinimumSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("MainFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.main_frame)

        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(20, 15, 15, 0)

        self.mode_label = QLabel()
        self.mode_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        top_bar.addWidget(self.mode_label)

        top_bar.addStretch()

        self.mode_btn = QPushButton("⇆")
        self.mode_btn.setFixedSize(32, 28)
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mode_btn.setStyleSheet("""
            QPushButton { color: #a3be8c; background: rgba(216, 222, 233, 15); border: none; border-bottom: 2px solid #a3be8c; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background: rgba(216, 222, 233, 30); color: #eceff4; border-bottom: 3px solid #eceff4; }
        """)
        self.mode_btn.clicked.connect(lambda: self.switch_mode((self.mode + 1) % len(AppMode)))
        top_bar.addWidget(self.mode_btn)

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(32, 28)
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.min_btn.setStyleSheet("""
            QPushButton { color: #88c0d0; background: rgba(216, 222, 233, 15); border: none; border-bottom: 2px solid #88c0d0; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background: rgba(216, 222, 233, 30); color: #eceff4; border-bottom: 3px solid #eceff4; }
        """)
        self.min_btn.clicked.connect(self.hide)
        top_bar.addWidget(self.min_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(32, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.clicked.connect(QApplication.instance().quit)
        top_bar.addWidget(self.close_btn)

        frame_layout.addLayout(top_bar)

        self.label = QLabel()
        self.label.setMinimumHeight(100)
        self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        frame_layout.addWidget(self.label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

        self.refresh_display()
        self.show()

    def create_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(self.tray_icon_path))

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #2e3440; color: #d8dee9; border: 1px solid #4c566a; font-family: 'Microsoft YaHei'; }
            QMenu::item { padding: 8px 30px; }
            QMenu::item:selected { background-color: #434c5e; color: #88c0d0; }
            QMenu::separator { height: 1px; background: #4c566a; margin: 5px 15px; }
        """)

        m0_act = QAction("🕒 系统时钟", self)
        m0_act.triggered.connect(lambda: self.switch_mode(AppMode.CLOCK))
        m1_act = QAction("⏳ 倒计时模式", self)
        m1_act.triggered.connect(lambda: self.switch_mode(AppMode.COUNTDOWN))
        m2_act = QAction("⏱️ 秒表计时", self)
        m2_act.triggered.connect(lambda: self.switch_mode(AppMode.STOPWATCH))
        m3_act = QAction("⏰ 闹钟", self)
        m3_act.triggered.connect(lambda: self.switch_mode(AppMode.ALARM))
        reset_act = QAction("🔄 重置当前计时", self)
        reset_act.triggered.connect(self.reset_timer)
        settings_act = QAction("⚙️ 闹钟设置", self)
        settings_act.triggered.connect(self.open_alarm_settings)
        quit_act = QAction("❌ 彻底退出程序", self)
        quit_act.triggered.connect(QApplication.instance().quit)

        menu.addAction(m0_act)
        menu.addAction(m1_act)
        menu.addAction(m2_act)
        menu.addAction(m3_act)
        menu.addSeparator()
        menu.addAction(reset_act)
        menu.addAction(settings_act)
        menu.addSeparator()
        menu.addAction(quit_act)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip("ChronoGlass")
        self.tray.activated.connect(self.tray_icon_activated)
        self.tray.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isHidden():
                self.show()
                self.activateWindow()
            else:
                self.hide()

    def update_style(self, color, mode_text):
        self.main_frame.setStyleSheet(
            f"QFrame#MainFrame {{ background-color: rgba(46, 52, 64, 235); border: 2px solid {color}; border-radius: 20px; }}")
        self.mode_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.mode_label.setText(mode_text)

        self.close_btn.setStyleSheet(f"""
            QPushButton {{ color: #bf616a; background: rgba(191, 97, 106, 15); border: none; border-bottom: 2px solid #bf616a; font-size: 18px; font-weight: bold; }}
            QPushButton:hover {{ background: rgba(191, 97, 106, 40); color: #d8dee9; border-bottom: 3px solid #d8dee9; }}
        """)
        self.label.setStyleSheet(f"color: {color}; background: transparent; padding-bottom: 15px;")

    # 【核心改动：在时钟页面双击即可设置位置，并写入统一状态文件】
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == AppMode.COUNTDOWN:
                self.set_custom_time()
            elif self.mode == AppMode.CLOCK:
                loc, ok = QInputDialog.getText(self, "设定", "输入所在地获取天气(如: 北京):", text=self.location)
                if ok:
                    self.location = loc.strip()
                    self.config["location"] = self.location
                    save_config(self.config)
                    self.cached_clock_info_date = None
                    if self.location:
                        self.weather_info = "获取中..."
                        self.fetch_weather()
                    else:
                        self.weather_info = ""
                    self.refresh_display()

        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if self.mode == AppMode.COUNTDOWN:
            step = 60 if event.angleDelta().y() > 0 else -60
            if self.default_seconds + step >= 60:
                self.default_seconds += step
                self.remaining_seconds = self.default_seconds
                self.refresh_display()
        super().wheelEvent(event)

    def contextMenuEvent(self, event):
        self.tray.contextMenu().exec(event.globalPos())

    def set_custom_time(self):
        val, ok = QInputDialog.getInt(self, "设定", "输入倒计时分钟数:", value=self.default_seconds // 60, min=1,
                                      max=1440)
        if ok:
            self.default_seconds = val * 60
            self.remaining_seconds = self.default_seconds
            self.is_running = False
            self.refresh_display()

    def open_alarm_settings(self):
        dlg = AlarmSettingsDialog(self.alarms, self)
        dlg.exec()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and self.mode != AppMode.CLOCK:
            self.is_running = not self.is_running
            self.refresh_display()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    # 【核心改动：在独立线程请求天气，防卡死】
    def fetch_weather(self):
        if not self.location:
            return

        with self.weather_lock:
            if self.weather_fetch_inflight:
                return
            self.weather_fetch_inflight = True

        def _fetch():
            try:
                url = f"https://wttr.in/{urllib.parse.quote(self.location)}?format=%c+%t&m"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    res = response.read().decode('utf-8').strip()
                    # 防止因为地点找不到被返回整个 HTML 页面
                    if len(res) > 20 or "<html" in res.lower() or "unknown" in res.lower():
                        res = "未找到该地"
                    self.weather_updated.emit(res)
            except Exception as e:
                log_error("天气请求失败", e)
                self.weather_updated.emit("网络异常")
            finally:
                with self.weather_lock:
                    self.weather_fetch_inflight = False

        # 将耗时任务放入子线程中
        threading.Thread(target=_fetch, daemon=True).start()

    # 【核心改动：槽函数，当子线程获取完毕后刷新UI】
    def on_weather_updated(self, weather_text):
        self.weather_info = weather_text
        self.cached_clock_info_date = None
        self.refresh_display()

    def should_trigger_alarm(self, alarm, today):
        if not alarm.get("enabled", True):
            return False

        if alarm.get("last_trigger_date", "") == today:
            return False

        now = QTime.currentTime()
        target = alarm["time"]
        now_sec = now.hour() * 3600 + now.minute() * 60 + now.second()
        target_sec = target.hour() * 3600 + target.minute() * 60 + target.second()
        diff = now_sec - target_sec

        return 0 <= diff <= 1

    def format_days_until(self, days):
        if days is None:
            return "暂无"
        if days <= 0:
            return "今天"
        return f"还有{days}天"

    def truncate_display_text(self, text, max_chars=8):
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars]}..."

    def get_next_festival_info(self, today):
        for offset in range(0, 367):
            target_date = today + datetime.timedelta(days=offset)
            solar = Solar.fromYmd(target_date.year, target_date.month, target_date.day)
            lunar = solar.getLunar()

            official = list(solar.getFestivals()) + list(lunar.getFestivals())
            if official:
                return "、".join(official[:2]), offset

        return "暂无", None

    def get_next_jieqi_info(self, lunar, today):
        current_jieqi = lunar.getCurrentJieQi()
        if current_jieqi:
            return str(current_jieqi), 0

        jieqi = lunar.getNextJieQi()
        if jieqi is None:
            return "暂无", None

        solar = jieqi.getSolar()
        target_date = datetime.date(solar.getYear(), solar.getMonth(), solar.getDay())
        offset = (target_date - today).days
        return jieqi.getName(), max(offset, 0)

    def get_clock_info_html(self, now):
        today = now.date()
        if self.cached_clock_info_date == today and self.cached_clock_info_html:
            return self.cached_clock_info_html

        date_str = now.strftime("%Y年%m月%d日")
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        week_str = weekdays[now.weekday()]

        weather_str = f" &nbsp;|&nbsp; {self.location} {self.weather_info}" if self.location else " &nbsp;|&nbsp; 双击添加天气"
        line1_str = f"{date_str} {week_str}{weather_str}"

        if HAS_LUNAR:
            lunar = Lunar.fromDate(now)
            festival_name, festival_days = self.get_next_festival_info(today)
            jieqi_name, jieqi_days = self.get_next_jieqi_info(lunar, today)
            lunar_date_str = f"农历{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
            yi = " ".join(lunar.getDayYi()[:2]) or "无"
            ji = " ".join(lunar.getDayJi()[:2]) or "无"
            festival_display = self.truncate_display_text(festival_name)

            line2_str = (
                f"下个节日: {festival_display}({self.format_days_until(festival_days)})"
                f" &nbsp;|&nbsp; 最近节气: {jieqi_name}({self.format_days_until(jieqi_days)})"
            )
            line3_str = f"{lunar_date_str} &nbsp;|&nbsp; 宜: {yi} &nbsp;|&nbsp; 忌: {ji}"
            info_str = f"{line1_str}<br>{line2_str}<br>{line3_str}"
        else:
            info_str = f"{line1_str}<br><span style='font-size: 9pt;'>(如需显示农历黄历，请在终端运行 pip install lunar-python)</span>"

        self.cached_clock_info_date = today
        self.cached_clock_info_html = info_str
        return info_str

    def tick(self):
        if self.is_running:
            if self.mode == AppMode.COUNTDOWN:
                if self.remaining_seconds > 0:
                    self.remaining_seconds -= 1
                else:
                    self.is_running = False
                    try:
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    except RuntimeError as e:
                        log_error("倒计时提示音播放失败", e)
            elif self.mode == AppMode.STOPWATCH:
                self.elapsed_seconds += 1

        if self.alarms:
            today = datetime.date.today().isoformat()
            trigger_happened = False
            for i, alarm in enumerate(self.alarms):
                if self.should_trigger_alarm(alarm, today):
                    trigger_happened = True
                    alarm["last_trigger_date"] = today
                    if alarm.get("repeat", "once") == "once":
                        alarm["enabled"] = False

                    try:
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                    except RuntimeError as e:
                        log_error("闹钟提示音播放失败", e)

                    self.show_trigger_dialog(i)
                    break

            if trigger_happened:
                save_alarms(self.alarms)

        self.refresh_display()

    def show_trigger_dialog(self, index):
        alarm = self.alarms[index]
        dlg = AlarmTriggerDialog(alarm, self)
        dlg.exec()

        if dlg.action == "snooze":
            new_time = QTime.currentTime().addSecs(5 * 60)
            alarm["time"] = new_time
            alarm["enabled"] = True
            alarm["last_trigger_date"] = ""
            save_alarms(self.alarms)
        elif dlg.action == "edit":
            self.open_alarm_settings()
        elif dlg.action == "done":
            if alarm.get("repeat", "once") == "once":
                alarm["enabled"] = False
            save_alarms(self.alarms)

        self.refresh_display()

    def refresh_display(self):
        if self.mode == AppMode.CLOCK:
            time_str = QTime.currentTime().toString("HH:mm:ss")
            now = datetime.datetime.now()
            info_str = self.get_clock_info_html(now)

            # 加上 line-height: 1.4 让三行文字看起来不会太拥挤
            html = f"""<span style="font-family: Consolas; font-size: 52pt; font-weight: bold;">{time_str}</span><br>
         <span style="font-family: 'Microsoft YaHei'; font-size: 11pt; font-weight: normal; line-height: 1.4;">{info_str}</span>"""
            self.label.setText(html)
            self.update_style("#88c0d0", "系统时钟")

        elif self.mode == AppMode.COUNTDOWN:
            self.label.setText(self.format_time(self.remaining_seconds))
            self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
            if self.remaining_seconds == 0:
                self.update_style("#bf616a", "时间到！")
            elif self.is_running:
                self.update_style("#ebcb8b", "倒计时进行中")
            else:
                self.update_style("#a3be8c", "倒计时已暂停")

        elif self.mode == AppMode.STOPWATCH:
            self.label.setText(self.format_time(self.elapsed_seconds))
            self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
            if self.is_running:
                self.update_style("#b48ead", "正在计时")
            else:
                self.update_style("#d8dee9", "计时已暂停")

        elif self.mode == AppMode.ALARM:
            self.label.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
            count = len(self.alarms)
            enabled_count = sum(1 for a in self.alarms if a["enabled"])
            self.label.setText(f"您现在设定了 {count} 个闹钟\n(已启用 {enabled_count} 个)")
            self.update_style("#d08770", "闹钟管理")

    def format_time(self, seconds):
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    def switch_mode(self, mode_idx):
        self.mode = mode_idx
        self.is_running = False
        self.refresh_display()

    def reset_timer(self):
        if self.mode == AppMode.COUNTDOWN:
            self.remaining_seconds = self.default_seconds
        elif self.mode == AppMode.STOPWATCH:
            self.elapsed_seconds = 0
        self.is_running = False
        self.refresh_display()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    clock = ChronoGlass()
    sys.exit(app.exec())
