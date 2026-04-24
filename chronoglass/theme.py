BG_DEEP = "#060814"
BG_MAIN = "#0a1020"
BG_PANEL = "#10182b"
BG_PANEL_ALT = "#151f35"
BORDER = "#263b63"
BORDER_SOFT = "rgba(0, 229, 255, 45)"
TEXT = "#eaf7ff"
TEXT_MUTED = "#8ba6c7"
CYAN = "#00e5ff"
MAGENTA = "#ff2bd6"
PURPLE = "#8a5cff"
GREEN = "#39ff88"
YELLOW = "#f9f871"
ORANGE = "#ff9f1c"
RED = "#ff3b6a"


def main_frame_style(accent):
    return f"""
        QFrame#MainFrame {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 rgba(6, 8, 20, 248),
                stop: 0.45 rgba(10, 16, 32, 244),
                stop: 1 rgba(18, 11, 38, 248)
            );
            border: 2px solid {accent};
            border-radius: 22px;
        }}
    """


def mode_label_style(accent):
    return f"""
        color: {accent};
        background: rgba(0, 229, 255, 18);
        border-left: 3px solid {accent};
        border-right: 1px solid rgba(255, 43, 214, 70);
        border-radius: 9px;
        padding: 4px 10px;
        letter-spacing: 1px;
    """


def top_button_style(accent):
    return f"""
        QPushButton {{
            color: {accent};
            background: rgba(0, 229, 255, 16);
            border: 1px solid rgba(0, 229, 255, 58);
            border-radius: 10px;
            padding: 0px;
            font-family: 'Segoe UI Symbol', 'Segoe UI', 'Microsoft YaHei';
            font-size: 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: rgba(255, 43, 214, 34);
            border: 1px solid {accent};
            color: #ffffff;
        }}
        QPushButton:pressed {{
            background: rgba(6, 8, 20, 190);
            border: 1px solid #ff2bd6;
        }}
    """


MENU_STYLE = """
QMenu {
    background-color: #0a1020;
    color: #eaf7ff;
    border: 1px solid #00e5ff;
    border-radius: 10px;
    padding: 6px;
    font-family: 'Microsoft YaHei';
}
QMenu::item {
    padding: 8px 30px 8px 14px;
    border-radius: 7px;
}
QMenu::item:selected {
    background-color: rgba(255, 43, 214, 42);
    color: #00e5ff;
}
QMenu::separator {
    height: 1px;
    background: rgba(0, 229, 255, 85);
    margin: 6px 10px;
}
"""


AMBITION_CARD_STYLE = """
QFrame#AmbitionCard {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 rgba(0, 229, 255, 62),
        stop: 0.42 rgba(10, 16, 32, 236),
        stop: 1 rgba(255, 43, 214, 70)
    );
    border: 1px solid rgba(0, 229, 255, 105);
    border-radius: 20px;
}
QLabel#AmbitionTitle {
    color: #eaf7ff;
    font-family: 'Microsoft YaHei';
    font-size: 15px;
    font-weight: bold;
}
QLabel#AmbitionSubtitle {
    color: rgba(234, 247, 255, 0.82);
    font-family: 'Microsoft YaHei';
    font-size: 11pt;
}
QLabel#AmbitionCountdown {
    color: #f9f871;
    font-family: 'Consolas';
    font-size: 36px;
    font-weight: bold;
}
QLabel#AmbitionFestival {
    color: #eaf7ff;
    font-family: 'Microsoft YaHei';
    font-size: 10pt;
    font-weight: bold;
    background: rgba(6, 8, 20, 132);
    border: 1px solid rgba(255, 43, 214, 95);
    border-radius: 15px;
    padding: 10px 12px;
}
QLabel#AmbitionImage {
    background: rgba(6, 8, 20, 145);
    border: 1px solid rgba(0, 229, 255, 95);
    border-radius: 18px;
    color: rgba(234, 247, 255, 0.78);
    font-family: 'Microsoft YaHei';
    font-size: 10pt;
}
"""


DIALOG_STYLE = """
QDialog {
    background-color: #0a1020;
    color: #eaf7ff;
}
QLabel {
    color: #eaf7ff;
    font-family: 'Microsoft YaHei';
}
QLineEdit, QComboBox {
    background-color: #10182b;
    color: #eaf7ff;
    border: 1px solid #263b63;
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: #ff2bd6;
    font-family: 'Microsoft YaHei';
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #00e5ff;
    background-color: #151f35;
}
QPushButton {
    background-color: #10182b;
    color: #eaf7ff;
    border: 1px solid #263b63;
    border-radius: 8px;
    padding: 7px 16px;
    font-family: 'Microsoft YaHei';
    font-weight: bold;
}
QPushButton:hover {
    background-color: rgba(255, 43, 214, 38);
    border: 1px solid #00e5ff;
}
QPushButton:pressed {
    background-color: #060814;
    border: 1px solid #ff2bd6;
}
"""


PRIMARY_BUTTON_STYLE = """
QPushButton {
    background-color: #00e5ff;
    color: #060814;
    border: none;
    border-radius: 8px;
    padding: 7px 18px;
    font-family: 'Microsoft YaHei';
    font-weight: bold;
}
QPushButton:hover { background-color: #7af3ff; }
QPushButton:pressed { background-color: #00aeca; }
"""


SECONDARY_BUTTON_STYLE = """
QPushButton {
    background-color: #10182b;
    color: #eaf7ff;
    border: 1px solid #263b63;
    border-radius: 8px;
    padding: 7px 18px;
    font-family: 'Microsoft YaHei';
    font-weight: bold;
}
QPushButton:hover {
    background-color: rgba(255, 43, 214, 35);
    border: 1px solid #00e5ff;
    color: #ffffff;
}
QPushButton:pressed { background-color: #060814; border: 1px solid #ff2bd6; }
"""


TABLE_STYLE = """
QTableWidget {
    background-color: #080d1a;
    alternate-background-color: #10182b;
    color: #eaf7ff;
    border: 1px solid #263b63;
    font-family: 'Consolas', 'Microsoft YaHei';
    font-size: 13px;
    border-radius: 10px;
    gridline-color: transparent;
}
QHeaderView::section {
    background-color: #10182b;
    color: #00e5ff;
    padding: 9px 8px;
    border: none;
    border-bottom: 1px solid rgba(0, 229, 255, 105);
    border-right: 1px solid #263b63;
    font-family: 'Microsoft YaHei';
    font-weight: bold;
}
QTableWidget::item {
    border-bottom: 1px solid rgba(38, 59, 99, 90);
    padding: 6px;
}
QTableWidget::item:selected {
    background-color: rgba(255, 43, 214, 58);
    color: #ffffff;
}
"""


TRIGGER_DIALOG_STYLE = """
QDialog {
    background-color: #0a1020;
    border: 2px solid #ff3b6a;
    border-radius: 18px;
}
"""


def trigger_button_style(color):
    return f"""
        QPushButton {{
            background-color: {color};
            color: #060814;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: bold;
            font-family: 'Microsoft YaHei';
        }}
        QPushButton:hover {{
            background-color: #eaf7ff;
            color: #060814;
        }}
        QPushButton:pressed {{
            background-color: #10182b;
            color: #eaf7ff;
            border: 1px solid #ff2bd6;
        }}
    """


HINT_LABEL_STYLE = """
color: #00e5ff;
background: rgba(0, 229, 255, 22);
border: 1px solid rgba(0, 229, 255, 65);
border-radius: 8px;
padding: 8px 10px;
"""


SPINBOX_STYLE = """
QSpinBox {
    background-color: #10182b;
    border: 1px solid #263b63;
    border-right: none;
    border-top-left-radius: 7px;
    border-bottom-left-radius: 7px;
    padding: 5px;
    color: #eaf7ff;
    selection-background-color: #ff2bd6;
}
QSpinBox:focus {
    border: 1px solid #00e5ff;
    border-right: none;
}
"""


SPIN_BUTTON_STYLE = """
QPushButton {
    background-color: #10182b;
    border: 1px solid #263b63;
    color: #eaf7ff;
    font-family: 'Consolas', 'Microsoft YaHei';
    font-weight: bold;
    font-size: 14px;
    padding: 0px;
}
QPushButton:hover {
    background-color: rgba(0, 229, 255, 28);
    color: #00e5ff;
    border: 1px solid #00e5ff;
}
QPushButton:pressed {
    background-color: #060814;
    color: #ff2bd6;
}
"""
