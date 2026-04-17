import os

from PyQt6.QtCore import QDateTime, QTime, QTimer, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .common import AMBITION_TIME_FORMAT
from .state import alarm_remaining_text, normalize_ambition_config, save_alarms
from .widgets import CustomSpinBox, ToggleSwitch


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
            "QLineEdit { background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; padding: 5px; color: #eceff4; }"
        )
        form.addRow("标签", self.name_edit)

        self.repeat_combo = QComboBox()
        self.repeat_combo.addItem("一次性", "once")
        self.repeat_combo.addItem("每天", "daily")
        idx = self.repeat_combo.findData(repeat)
        self.repeat_combo.setCurrentIndex(0 if idx < 0 else idx)
        self.repeat_combo.setStyleSheet(
            "QComboBox { background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; padding: 5px; color: #eceff4; }"
        )
        form.addRow("重复", self.repeat_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #3b4252; border: 1px solid #4c566a; border-radius: 6px; padding: 6px 18px; color: #d8dee9; } QPushButton:hover { background-color: #4c566a; }"
        )
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("确定")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #88c0d0; color: #2e3440; border-radius: 6px; padding: 6px 18px; font-weight: bold; } QPushButton:hover { background-color: #8fbcbb; }"
        )
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
        self.init_ui()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_remaining_times)
        self.refresh_timer.start(10000)

    def init_ui(self):
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

        for btn in (add_btn, del_btn, edit_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                """
                QPushButton { background-color: #3b4252; border: 1px solid #4c566a; border-radius: 6px; padding: 6px 12px; color: #eceff4; font-weight: bold; }
                QPushButton:hover { background-color: #434c5e; border: 1px solid #88c0d0; }
                """
            )
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
        self.table.setStyleSheet(
            """
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
            """
        )

        self.refresh_table()
        layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = QPushButton("完成并关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            """
            QPushButton { background-color: #88c0d0; color: #2e3440; border-radius: 6px; padding: 8px 24px; font-weight: bold; }
            QPushButton:hover { background-color: #8fbcbb; }
            """
        )
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)

    def refresh_table(self):
        self.table.setRowCount(len(self.alarms))

        for index, alarm in enumerate(self.alarms):
            time_str = alarm["time"].toString("HH:mm:ss")
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(index, 0, time_item)

            name_item = QTableWidgetItem(alarm["name"])
            self.table.setItem(index, 1, name_item)

            repeat_text = "每天" if alarm.get("repeat", "once") == "daily" else "一次性"
            repeat_item = QTableWidgetItem(repeat_text)
            repeat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(index, 2, repeat_item)

            remaining = alarm_remaining_text(alarm)
            rem_item = QTableWidgetItem(remaining)
            rem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            is_expired = alarm.get("repeat", "once") == "once" and remaining in ("已过期", "已触发")
            if is_expired:
                rem_item.setForeground(QColor("#bf616a"))
            self.table.setItem(index, 3, rem_item)

            chk = ToggleSwitch(checked=alarm["enabled"])
            chk.toggled.connect(lambda checked, idx=index: self.toggle_alarm(idx, checked))

            cell_widget = QWidget()
            chk_layout = QHBoxLayout(cell_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(index, 4, cell_widget)

            if is_expired:
                cell_widget.setVisible(False)

    def update_remaining_times(self):
        for index, alarm in enumerate(self.alarms):
            rem_item = self.table.item(index, 3)
            rem_text = alarm_remaining_text(alarm)
            is_expired = alarm.get("repeat", "once") == "once" and rem_text in ("已过期", "已触发")

            if rem_item:
                rem_item.setText(rem_text)
                rem_item.setForeground(QColor("#bf616a" if is_expired else "#eceff4"))

            cell_widget = self.table.cellWidget(index, 4)
            if cell_widget:
                cell_widget.setVisible(not is_expired)

    def add_alarm(self):
        now = QTime.currentTime()
        dlg = AlarmEditDialog(now.hour(), now.minute(), 0, "新闹钟", "once", "添加闹钟", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.alarms.append(
                {
                    "time": dlg.get_time(),
                    "name": dlg.get_name(),
                    "enabled": True,
                    "repeat": dlg.get_repeat(),
                    "last_trigger_date": "",
                }
            )
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
        if row < 0:
            return

        alarm = self.alarms[row]
        dlg = AlarmEditDialog(
            alarm["time"].hour(),
            alarm["time"].minute(),
            alarm["time"].second(),
            alarm["name"],
            alarm.get("repeat", "once"),
            "修改闹钟",
            self,
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
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
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
            "QPushButton { border: none; color: #4c566a; font-weight: bold; font-size: 16px; } QPushButton:hover { color: #bf616a; }"
        )
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

        for btn, color in ((snooze_btn, "#81a1c1"), (edit_btn, "#ebcb8b"), (done_btn, "#bf616a")):
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setStyleSheet(
                f"background-color: {color}; color: #2e3440; border-radius: 6px; font-size: 15px; font-weight: bold;"
            )
            btn_layout.addWidget(btn)

        snooze_btn.clicked.connect(self.do_snooze)
        edit_btn.clicked.connect(self.do_edit)
        done_btn.clicked.connect(self.do_done)

        layout.addLayout(btn_layout)

    def do_snooze(self):
        self.action = "snooze"
        self.accept()

    def do_edit(self):
        self.action = "edit"
        self.accept()

    def do_done(self):
        self.action = "done"
        self.accept()

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


class AmbitionEditDialog(QDialog):
    def __init__(self, ambition_config, parent=None):
        super().__init__(parent)
        self.ambition_config = normalize_ambition_config(ambition_config)
        self.setWindowTitle("修改倒计时")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setStyleSheet(
            """
            QDialog { background-color: #2e3440; color: #d8dee9; }
            QLabel { color: #d8dee9; font-family: 'Microsoft YaHei'; }
            QLineEdit {
                background-color: #3b4252;
                color: #eceff4;
                border: 1px solid #4c566a;
                border-radius: 6px;
                padding: 8px 10px;
                font-family: 'Microsoft YaHei';
            }
            QPushButton {
                background-color: #5e81ac;
                color: #eceff4;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
            }
            QPushButton:hover { background-color: #81a1c1; }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setSpacing(12)

        self.title_edit = QLineEdit(self.ambition_config["title"])
        self.title_edit.setPlaceholderText("输入倒计时标题")
        form.addRow("标题", self.title_edit)

        target_time = QTime.fromString(self.ambition_config["target_time"], AMBITION_TIME_FORMAT)
        if not target_time.isValid():
            target_time = QTime.currentTime().addSecs(3600)

        self.spin_h = CustomSpinBox()
        self.spin_h.setRange(0, 23)
        self.spin_h.setValue(target_time.hour())

        self.spin_m = CustomSpinBox()
        self.spin_m.setRange(0, 59)
        self.spin_m.setValue(target_time.minute())

        self.spin_s = CustomSpinBox()
        self.spin_s.setRange(0, 59)
        self.spin_s.setValue(target_time.second())

        time_layout = QHBoxLayout()
        time_layout.addWidget(self.spin_h)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(self.spin_m)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(self.spin_s)
        form.addRow("时间(24小时制)", time_layout)

        image_row = QHBoxLayout()
        image_row.setSpacing(8)

        self.pending_image_edit = QLineEdit(self.ambition_config["image_path"])
        self.pending_image_edit.setReadOnly(True)
        self.pending_image_edit.setPlaceholderText("支持 PNG / JPG / WEBP / GIF")
        image_row.addWidget(self.pending_image_edit, 1)

        browse_btn = QPushButton("上传图片")
        browse_btn.clicked.connect(self.select_image)
        image_row.addWidget(browse_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4c566a;
                color: #eceff4;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
            }
            QPushButton:hover { background-color: #616e88; }
            """
        )
        clear_btn.clicked.connect(self.pending_image_edit.clear)
        image_row.addWidget(clear_btn)

        image_widget = QWidget()
        image_widget.setLayout(image_row)
        form.addRow("倒计时图片", image_widget)

        completed_image_row = QHBoxLayout()
        completed_image_row.setSpacing(8)

        self.completed_image_edit = QLineEdit(self.ambition_config["completed_image_path"])
        self.completed_image_edit.setReadOnly(True)
        self.completed_image_edit.setPlaceholderText("支持 PNG / JPG / WEBP / GIF")
        completed_image_row.addWidget(self.completed_image_edit, 1)

        completed_browse_btn = QPushButton("上传图片")
        completed_browse_btn.clicked.connect(self.select_completed_image)
        completed_image_row.addWidget(completed_browse_btn)

        completed_clear_btn = QPushButton("清空")
        completed_clear_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4c566a;
                color: #eceff4;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
            }
            QPushButton:hover { background-color: #616e88; }
            """
        )
        completed_clear_btn.clicked.connect(self.completed_image_edit.clear)
        completed_image_row.addWidget(completed_clear_btn)

        completed_image_widget = QWidget()
        completed_image_widget.setLayout(completed_image_row)
        form.addRow("完成后图片", completed_image_widget)

        layout.addLayout(form)

        hint_label = QLabel(
            "倒计时中显示标题和第一张图；结束后标题位显示“恭喜”，大文本位显示原标题，并优先显示第二张图。若未设置第二张图，则继续显示第一张图。时间按 HH:mm:ss 保存。"
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #81a1c1;")
        layout.addWidget(hint_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4c566a;
                color: #eceff4;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
            }
            QPushButton:hover { background-color: #616e88; }
            """
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #a3be8c;
                color: #2e3440;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
            }
            QPushButton:hover { background-color: #b8d29f; }
            """
        )
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def select_image(self):
        self.select_image_for(self.pending_image_edit)

    def select_completed_image(self):
        self.select_image_for(self.completed_image_edit)

    def select_image_for(self, target_edit):
        current_path = target_edit.text().strip()

        dialog = QFileDialog(self, "选择图片")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        # 打包后禁用原生文件对话框，避免部分系统环境下选完文件直接崩溃。
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        if current_path and os.path.exists(current_path):
            dialog.setDirectory(os.path.dirname(current_path))
            dialog.selectFile(current_path)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_files = dialog.selectedFiles()
            if selected_files:
                target_edit.setText(selected_files[0])

    def get_values(self):
        return normalize_ambition_config(
            {
                "title": self.title_edit.text().strip() or "新的倒计时",
                "target_time": QTime(
                    self.spin_h.value(),
                    self.spin_m.value(),
                    self.spin_s.value(),
                ).toString(AMBITION_TIME_FORMAT),
                "image_path": self.pending_image_edit.text().strip(),
                "completed_image_path": self.completed_image_edit.text().strip(),
            }
        )
