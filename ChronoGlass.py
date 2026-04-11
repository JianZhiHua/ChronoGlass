import sys
import os
import json
import winsound
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QMenu, QInputDialog, QSystemTrayIcon, QHBoxLayout, QPushButton, QFrame,
                             QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QSpinBox, QLineEdit, QFormLayout, QComboBox)
from PyQt6.QtCore import QTimer, QTime, Qt, QPoint, QDateTime, pyqtSignal, QPropertyAnimation, pyqtProperty, \
    QEasingCurve
from PyQt6.QtGui import QFont, QAction, QIcon, QPainter, QColor, QBrush, QPen


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
def get_data_file_path():
    """获取闹钟数据文件的存储路径（在程序所在同级目录）"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, 'alarms.json')


def load_alarms():
    file_path = get_data_file_path()
    alarms = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for d in data:
                    t = QTime.fromString(d.get("time", "00:00:00"), "HH:mm:ss")
                    if not t.isValid(): t = QTime(0, 0)
                    alarms.append({
                        "time": t,
                        "name": d.get("name", "新闹钟"),
                        "enabled": d.get("enabled", True),
                        "triggered": d.get("triggered", False)
                    })
        except Exception:
            pass
    return alarms


def save_alarms(alarms):
    file_path = get_data_file_path()
    try:
        data = []
        for a in alarms:
            data.append({
                "time": a["time"].toString("HH:mm:ss"),
                "name": a["name"],
                "enabled": a["enabled"],
                "triggered": a["triggered"]
            })
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# --- 自定义原生平滑开关控件 (解决状态栏按钮渲染问题) ---
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

        # 背景颜色：暗夜主题的活跃蓝(#88c0d0) 和 失效灰(#4c566a)
        bg_color = QColor("#88c0d0") if self._checked else QColor("#4c566a")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, rect.width(), rect.height(), 11, 11)

        # 圆形滑块
        painter.setBrush(QBrush(QColor("#eceff4")))  # 白色滑块
        painter.drawEllipse(self._position, 2, 18, 18)
        painter.end()


def alarm_remaining_text(alarm):
    """计算闹钟剩余时间文本"""
    if not alarm["enabled"]:
        return "已停用"
    if alarm.get("triggered", False):
        return "已过期"

    now = QTime.currentTime()
    target = alarm["time"]

    now_sec = now.hour() * 3600 + now.minute() * 60 + now.second()
    target_sec = target.hour() * 3600 + target.minute() * 60 + target.second()

    diff = target_sec - now_sec
    if diff < 0:
        diff += 24 * 3600

    hours, rem = divmod(diff, 3600)
    minutes, seconds = divmod(rem, 60)

    if hours > 0:
        return f"{hours}小时"
    elif minutes > 0:
        return f"{minutes}分钟"
    else:
        return "即将触发"


class AlarmEditDialog(QDialog):
    """单个闹钟编辑对话框 — 在一个页面内完成时分秒和名称的输入"""

    def __init__(self, hour=0, minute=0, second=0, name="新闹钟", title="添加闹钟", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(350, 220)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("QDialog { background-color: #2e3440; color: #d8dee9; }")
        up_img = resource_path("add.png").replace("\\", "/")
        down_img = resource_path("sub.png").replace("\\", "/")
        spinbox_style = f"""
                    QSpinBox {{ 
                        background-color: #3b4252; 
                        border: 1px solid #4c566a; 
                        border-radius: 4px; 
                        padding: 5px; 
                        color: #eceff4; 
                    }}

                    /* --- 1. 控制按钮背景区域和宽度 --- */
                    QSpinBox::up-button {{
                        width: 25px;
                        background-color:#5888e6;
                        border-left: 1px solid #4c566a;
                        border-top-right-radius: 4px;
                    }}
                    QSpinBox::down-button {{
                        width: 25px;
                        background-color:#5888e6;
                        border-left: 1px solid #4c566a;
                        border-bottom-right-radius: 4px;
                    }}
                    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                        background-color: #434c5e;
                    }}

                    /* --- 2. 控制内部的自定义图标 --- */
                    QSpinBox::up-arrow {{
                        image: url("{up_img}");
                        width: 12px;  /* 控制图标的显示宽度 */
                        height: 12px; /* 控制图标的显示高度 */
                    }}
                    QSpinBox::down-arrow {{
                        image: url("{down_img}");
                        width: 12px;
                        height: 12px;
                    }}

                    /* 禁用状态下可以隐藏箭头或换一张灰暗的图 */
                    QSpinBox::up-arrow:disabled, QSpinBox::down-arrow:disabled {{
                        image: none; 
                    }}
                """

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 10)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(0, 23)
        self.spin_h.setFixedSize(80, 30)
        self.spin_h.setValue(hour)
        self.spin_h.setStyleSheet(spinbox_style)

        self.spin_m = QSpinBox()
        self.spin_m.setRange(0, 59)
        self.spin_m.setFixedSize(80, 30)
        self.spin_m.setValue(minute)
        self.spin_m.setStyleSheet(spinbox_style)

        self.spin_s = QSpinBox()
        self.spin_s.setRange(0, 59)
        self.spin_s.setFixedSize(80, 30)
        self.spin_s.setValue(second)
        self.spin_s.setStyleSheet(spinbox_style)

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


class AlarmSettingsDialog(QDialog):
    """闹钟设置界面 (暗黑主题)"""

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

        # 按钮区
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

        # 闹钟列表表格 (暗夜主题风格配置)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["时间", "闹钟标签", "剩余", "状态"])

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

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

        # 底部按钮
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
        for i, alarm in enumerate(self.alarms):
            time_str = alarm["time"].toString("HH:mm:ss")
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, time_item)

            name_item = QTableWidgetItem(alarm["name"])
            self.table.setItem(i, 1, name_item)

            remaining = alarm_remaining_text(alarm)
            rem_item = QTableWidgetItem(remaining)
            rem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 过期标红
            if alarm.get("triggered", False):
                rem_item.setForeground(QColor("#bf616a"))
            self.table.setItem(i, 2, rem_item)

            # 使用自定义原生 Switch 控件
            chk = ToggleSwitch(checked=alarm["enabled"])
            chk.toggled.connect(lambda checked, idx=i: self.toggle_alarm(idx, checked))

            cell_widget = QWidget()
            chk_layout = QHBoxLayout(cell_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 3, cell_widget)

            if alarm.get("triggered", False):
                cell_widget.setVisible(False)

    def update_remaining_times(self):
        for i, alarm in enumerate(self.alarms):
            rem_item = self.table.item(i, 2)
            if rem_item:
                rem_item.setText(alarm_remaining_text(alarm))
                if alarm.get("triggered", False):
                    rem_item.setForeground(QColor("#bf616a"))
                else:
                    rem_item.setForeground(QColor("#eceff4"))

            cell_widget = self.table.cellWidget(i, 3)
            if cell_widget:
                cell_widget.setVisible(not alarm.get("triggered", False))

    def add_alarm(self):
        now = QTime.currentTime()
        dlg = AlarmEditDialog(now.hour(), now.minute(), 0, "新闹钟", "添加闹钟", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.alarms.append({
                "time": dlg.get_time(),
                "name": dlg.get_name(),
                "enabled": True,
                "triggered": False,
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
            alarm["name"], "修改闹钟", self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            alarm["time"] = dlg.get_time()
            alarm["name"] = dlg.get_name()
            alarm["triggered"] = False
            save_alarms(self.alarms)
            self.refresh_table()

    def toggle_alarm(self, index, enabled):
        self.alarms[index]["enabled"] = enabled
        self.alarms[index]["triggered"] = False
        save_alarms(self.alarms)
        self.update_remaining_times()

    def closeEvent(self, event):
        if self.parent():
            self.parent().refresh_display()
        super().closeEvent(event)


class AlarmTriggerDialog(QDialog):
    """闹钟触发时的置顶模态提醒框"""

    def __init__(self, alarm, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.action = "done"
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Dialog)
        self.setFixedSize(450, 260)
        self.setStyleSheet("QDialog { background-color: #2e3440; border: 2px solid #bf616a; border-radius: 12px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 20)

        top_layout = QHBoxLayout()
        top_layout.addStretch()
        close_btn = QPushButton("✖")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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


class ChronoGlass(QWidget):
    def __init__(self):
        super().__init__()
        self.mode = 0
        self.is_running = False
        self.default_seconds = 1200
        self.remaining_seconds = self.default_seconds
        self.elapsed_seconds = 0
        self.drag_position = QPoint()

        # 启动时读取本地配置
        self.alarms = load_alarms()

        self.icon_path = resource_path("tray_icon.png")
        self.tray_icon_path = resource_path("tray_icon.png")

        self.initUI()
        self.create_tray()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(self.icon_path))

        # 核心：设置窗口初始和最小尺寸，保证模式切换时窗口大小不闪烁抖动
        self.setMinimumSize(450, 180)

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

        # 1. 原有的模式切换按钮
        self.mode_btn = QPushButton("⇆")
        self.mode_btn.setFixedSize(32, 28)
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mode_btn.clicked.connect(lambda: self.switch_mode((self.mode + 1) % 4))
        top_bar.addWidget(self.mode_btn)

        # 2. 新增的最小化按钮
        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(32, 28)
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.min_btn.clicked.connect(self.hide)  # 点击隐藏窗口（即最小化到托盘）
        top_bar.addWidget(self.min_btn)

        # 3. 原有的关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(32, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.clicked.connect(QApplication.instance().quit)
        top_bar.addWidget(self.close_btn)

        frame_layout.addLayout(top_bar)

        self.label = QLabel()
        # 强制 Label 占据固定高度，解决字体变小时容器缩水的问题
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
        m0_act.triggered.connect(lambda: self.switch_mode(0))
        m1_act = QAction("⏳ 倒计时模式", self)
        m1_act.triggered.connect(lambda: self.switch_mode(1))
        m2_act = QAction("⏱️ 秒表计时", self)
        m2_act.triggered.connect(lambda: self.switch_mode(2))
        m3_act = QAction("⏰ 闹钟", self)
        m3_act.triggered.connect(lambda: self.switch_mode(3))
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

        # 绑定托盘图标的点击事件
        self.tray.activated.connect(self.tray_icon_activated)

        self.tray.show()

    def tray_icon_activated(self, reason):
        """处理托盘图标点击事件"""
        # 如果是左键单击
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isHidden():
                self.show()
                self.activateWindow()  # 确保窗口显示在最上层
            else:
                self.hide()

    def update_style(self, color, mode_text):
        self.main_frame.setStyleSheet(
            f"QFrame#MainFrame {{ background-color: rgba(46, 52, 64, 235); border: 2px solid {color}; border-radius: 20px; }}")
        self.mode_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.mode_label.setText(mode_text)

        # 统一设置模式切换按钮和最小化按钮的风格
        btn_style = f"""
            QPushButton {{ color: {color}; background: rgba(216, 222, 233, 15); border: none; border-bottom: 2px solid {color}; font-size: 16px; font-weight: bold; }}
            QPushButton:hover {{ background: rgba(216, 222, 233, 30); color: #eceff4; border-bottom: 3px solid #eceff4; }}
        """
        self.mode_btn.setStyleSheet(btn_style)
        self.min_btn.setStyleSheet(btn_style)

        self.close_btn.setStyleSheet(f"""
            QPushButton {{ color: #bf616a; background: rgba(191, 97, 106, 15); border: none; border-bottom: 2px solid #bf616a; font-size: 18px; font-weight: bold; }}
            QPushButton:hover {{ background: rgba(191, 97, 106, 40); color: #d8dee9; border-bottom: 3px solid #d8dee9; }}
        """)
        self.label.setStyleSheet(f"color: {color}; background: transparent; padding-bottom: 15px;")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == 1:
                self.set_custom_time()
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if self.mode == 1:
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
        if event.key() == Qt.Key.Key_Space and self.mode != 0:
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

    def tick(self):
        if self.is_running:
            if self.mode == 1:
                if self.remaining_seconds > 0:
                    self.remaining_seconds -= 1
                else:
                    self.is_running = False
            elif self.mode == 2:
                self.elapsed_seconds += 1

        if self.alarms:
            now = QTime.currentTime()
            trigger_happened = False
            for i, alarm in enumerate(self.alarms):
                if alarm["enabled"] and not alarm["triggered"]:
                    if now.hour() == alarm["time"].hour() and now.minute() == alarm["time"].minute() and now.second() == \
                            alarm["time"].second():
                        alarm["triggered"] = True
                        trigger_happened = True
                        try:
                            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                        except Exception:
                            pass
                        self.show_trigger_dialog(i)
                        break
            if trigger_happened:
                save_alarms(self.alarms)  # 触发后自动存档

        self.refresh_display()

    def show_trigger_dialog(self, index):
        alarm = self.alarms[index]
        dlg = AlarmTriggerDialog(alarm, self)
        dlg.exec()

        if dlg.action == "snooze":
            new_time = QTime.currentTime().addSecs(5 * 60)
            alarm["time"] = new_time
            alarm["triggered"] = False
            save_alarms(self.alarms)
        elif dlg.action == "edit":
            self.open_alarm_settings()
        elif dlg.action == "done":
            pass

        self.refresh_display()

    def refresh_display(self):
        if self.mode == 0:
            self.label.setText(QTime.currentTime().toString("HH:mm:ss"))
            self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
            self.update_style("#88c0d0", "系统时钟")
        elif self.mode == 1:
            self.label.setText(self.format_time(self.remaining_seconds))
            self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
            if self.remaining_seconds == 0:
                self.update_style("#bf616a", "时间到！")
            elif self.is_running:
                self.update_style("#ebcb8b", "倒计时进行中")
            else:
                self.update_style("#a3be8c", "倒计时已暂停")
        elif self.mode == 2:
            self.label.setText(self.format_time(self.elapsed_seconds))
            self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
            if self.is_running:
                self.update_style("#b48ead", "正在计时")
            else:
                self.update_style("#d8dee9", "计时已暂停")
        elif self.mode == 3:
            self.label.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
            count = len(self.alarms)
            enabled_count = sum(1 for a in self.alarms if a["enabled"])
            # 去除底部的右键呼出提示
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
        if self.mode == 1:
            self.remaining_seconds = self.default_seconds
        elif self.mode == 2:
            self.elapsed_seconds = 0
        elif self.mode == 3:
            for alarm in self.alarms:
                alarm["triggered"] = False
            save_alarms(self.alarms)
        self.is_running = False
        self.refresh_display()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 【关键机制】这行代码确保即使用户关闭了所有可见窗口（比如最小化到托盘），程序也不会立刻退出
    app.setQuitOnLastWindowClosed(False)

    clock = ChronoGlass()
    sys.exit(app.exec())