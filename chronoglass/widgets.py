from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


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


class CustomSpinBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.spin = QSpinBox()
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin.setFixedSize(55, 30)
        self.spin.setStyleSheet(
            """
            QSpinBox {
                background-color: #3b4252; border: 1px solid #4c566a; border-right: none;
                border-top-left-radius: 4px; border-bottom-left-radius: 4px;
                padding: 5px; color: #eceff4;
            }
            """
        )

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

    def value(self):
        return self.spin.value()

    def setValue(self, value):
        self.spin.setValue(value)

    def setRange(self, min_val, max_val):
        self.spin.setRange(min_val, max_val)
