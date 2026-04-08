import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QMenu, QInputDialog, QSystemTrayIcon, QHBoxLayout, QPushButton, QFrame)
from PyQt6.QtCore import QTimer, QTime, Qt, QPoint
from PyQt6.QtGui import QFont, QAction, QIcon


def resource_path(relative_path):
    nuitka_root = os.environ.get("NUITKA_PACKAGE_HOME")
    if nuitka_root:
        return os.path.join(nuitka_root, relative_path)
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    if hasattr(sys, "frozen") or "__compiled__" in globals():
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


class ChronoGlass(QWidget):
    def __init__(self):
        super().__init__()
        self.mode = 0
        self.is_running = False
        self.default_seconds = 1200
        self.remaining_seconds = self.default_seconds
        self.elapsed_seconds = 0
        self.drag_position = QPoint()

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
        self.mode_btn.clicked.connect(lambda: self.switch_mode((self.mode + 1) % 3))
        top_bar.addWidget(self.mode_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(32, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.clicked.connect(QApplication.instance().quit)
        top_bar.addWidget(self.close_btn)

        frame_layout.addLayout(top_bar)

        self.label = QLabel()
        self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        frame_layout.addWidget(self.label)

        self.setMinimumWidth(400)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

        self.refresh_display()
        self.show()

    def create_tray(self):
        """创建带直接导航功能的托盘菜单"""
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(self.tray_icon_path))

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2e3440;
                color: #d8dee9;
                border: 1px solid #4c566a;
                font-family: 'Microsoft YaHei';
            }
            QMenu::item {
                padding: 8px 30px;
            }
            QMenu::item:selected {
                background-color: #434c5e;
                color: #88c0d0;
            }
            QMenu::separator {
                height: 1px;
                background: #4c566a;
                margin: 5px 15px;
            }
        """)

        # --- 模式直达区 ---
        m0_act = QAction("🕒 系统时钟", self)
        m0_act.triggered.connect(lambda: self.switch_mode(0))

        m1_act = QAction("⏳ 倒计时模式", self)
        m1_act.triggered.connect(lambda: self.switch_mode(1))

        m2_act = QAction("⏱️ 秒表计时", self)
        m2_act.triggered.connect(lambda: self.switch_mode(2))

        # --- 功能控制区 ---
        reset_act = QAction("🔄 重置当前计时", self)
        reset_act.triggered.connect(self.reset_timer)

        quit_act = QAction("❌ 彻底退出程序", self)
        quit_act.triggered.connect(QApplication.instance().quit)

        # 组合菜单
        menu.addAction(m0_act)
        menu.addAction(m1_act)
        menu.addAction(m2_act)
        menu.addSeparator()
        menu.addAction(reset_act)
        menu.addSeparator()
        menu.addAction(quit_act)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip("ChronoGlass")
        self.tray.show()

    def update_style(self, color, mode_text):
        self.main_frame.setStyleSheet(
            f"QFrame#MainFrame {{ background-color: rgba(46, 52, 64, 235); border: 2px solid {color}; border-radius: 20px; }}")
        self.mode_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.mode_label.setText(mode_text)

        self.mode_btn.setStyleSheet(f"""
            QPushButton {{
                color: {color}; background: rgba(216, 222, 233, 15);
                border: none; border-bottom: 2px solid {color};
                font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(216, 222, 233, 30); color: #eceff4; border-bottom: 3px solid #eceff4; }}
        """)

        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                color: #bf616a; background: rgba(191, 97, 106, 15);
                border: none; border-bottom: 2px solid #bf616a;
                font-size: 18px; font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(191, 97, 106, 40); color: #d8dee9; border-bottom: 3px solid #d8dee9; }}
        """)
        self.label.setStyleSheet(f"color: {color}; background: transparent; padding-bottom: 15px;")

    def mouseDoubleClickEvent(self, event):
        if self.mode == 1 and event.button() == Qt.MouseButton.LeftButton:
            self.set_custom_time()

    def wheelEvent(self, event):
        if self.mode == 1:
            step = 60 if event.angleDelta().y() > 0 else -60
            if self.default_seconds + step >= 60:
                self.default_seconds += step
                self.remaining_seconds = self.default_seconds
                self.refresh_display()

    def contextMenuEvent(self, event):
        """主窗口右键也调用托盘菜单"""
        self.tray.contextMenu().exec(event.globalPos())

    def set_custom_time(self):
        val, ok = QInputDialog.getInt(self, "设定", "输入倒计时分钟数:",
                                      value=self.default_seconds // 60, min=1, max=1440)
        if ok:
            self.default_seconds = val * 60
            self.remaining_seconds = self.default_seconds
            self.is_running = False
            self.refresh_display()

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
        self.refresh_display()

    def refresh_display(self):
        if self.mode == 0:
            self.label.setText(QTime.currentTime().toString("HH:mm:ss"))
            self.update_style("#88c0d0", "系统时钟")
        elif self.mode == 1:
            self.label.setText(self.format_time(self.remaining_seconds))
            if self.remaining_seconds == 0:
                self.update_style("#bf616a", "时间到！")
            elif self.is_running:
                self.update_style("#ebcb8b", "倒计时进行中")
            else:
                self.update_style("#a3be8c", "倒计时已暂停")
        elif self.mode == 2:
            self.label.setText(self.format_time(self.elapsed_seconds))
            if self.is_running:
                self.update_style("#b48ead", "正在计时")
            else:
                self.update_style("#d8dee9", "计时已暂停")

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
        self.is_running = False
        self.refresh_display()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    clock = ChronoGlass()
    sys.exit(app.exec())