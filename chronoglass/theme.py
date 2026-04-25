BG_DEEP = "#eef6ef"
BG_MAIN = "#f2f8f3"
BG_PANEL = "#f7fbf6"
BG_PANEL_ALT = "#e6f2ea"
BORDER = "#bddbc9"
BORDER_SOFT = "rgba(127, 203, 172, 90)"
TEXT = "#34433f"
TEXT_MUTED = "#6f8a82"
CYAN = "#3fb7ad"
MAGENTA = "#ee86ad"
PURPLE = "#9485d4"
GREEN = "#5fbd82"
YELLOW = "#d2a847"
ORANGE = "#e89a55"
RED = "#df6f7b"


def main_frame_style(accent):
    return f"""
        QFrame#MainFrame {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 rgba(247, 251, 246, 246),
                stop: 0.48 rgba(238, 246, 239, 244),
                stop: 1 rgba(231, 241, 238, 246)
            );
            border: 2px solid {accent};
            border-radius: 22px;
        }}
    """


def mode_label_style(accent):
    return f"""
        color: {accent};
        background: rgba(255, 255, 255, 170);
        border-left: 3px solid {accent};
        border-right: 1px solid rgba(201, 232, 214, 130);
        border-radius: 9px;
        padding: 4px 10px;
        letter-spacing: 1px;
    """


def top_button_style(accent):
    return f"""
        QPushButton {{
            color: {accent};
            background: rgba(255, 255, 255, 165);
            border: 1px solid rgba(127, 203, 172, 120);
            border-radius: 10px;
            padding: 0px;
            font-family: 'Segoe UI Symbol', 'Segoe UI', 'Microsoft YaHei';
            font-size: 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: rgba(237, 248, 242, 230);
            border: 1px solid {accent};
            color: {accent};
        }}
        QPushButton:pressed {{
            background: rgba(224, 244, 234, 230);
            border: 1px solid {accent};
        }}
    """


MENU_STYLE = """
QMenu {
    background-color: #f7fbf6;
    color: #34433f;
    border: 1px solid #c9e8d6;
    border-radius: 10px;
    padding: 6px;
    font-family: 'Microsoft YaHei';
}
QMenu::item {
    padding: 8px 30px 8px 14px;
    border-radius: 7px;
}
QMenu::item:selected {
    background-color: #e6f2ea;
    color: #3fb7ad;
}
QMenu::separator {
    height: 1px;
    background: #dcefe5;
    margin: 6px 10px;
}
"""


def ambition_page_style(accent):
    return f"""
        QFrame#AmbitionCard {{
            background: transparent;
            border: none;
        }}
        QWidget#AmbitionTextBlock {{
            background: transparent;
        }}
        QLabel#AmbitionTitle {{
            color: {TEXT};
            background: transparent;
            font-family: 'Microsoft YaHei';
            font-size: 15px;
            font-weight: bold;
        }}
        QLabel#AmbitionSubtitle {{
            color: {TEXT_MUTED};
            background: transparent;
            font-family: 'Microsoft YaHei';
            font-size: 12pt;
        }}
        QLabel#AmbitionCountdown {{
            color: {accent};
            background: transparent;
            font-family: 'Consolas';
            font-size: 46px;
            font-weight: bold;
        }}
        QLabel#AmbitionFestival,
        QLabel#AmbitionJieqi {{
            color: {accent};
            background: rgba(255, 255, 255, 170);
            border: 1px solid rgba(127, 203, 172, 120);
            border-left: 3px solid {accent};
            border-radius: 10px;
            padding: 7px 10px;
            font-family: 'Microsoft YaHei';
            font-size: 10pt;
            font-weight: bold;
        }}
        QLabel#AmbitionImage {{
            color: {TEXT_MUTED};
            background: rgba(255, 255, 255, 155);
            border: 1px solid rgba(127, 203, 172, 120);
            border-radius: 14px;
            font-family: 'Microsoft YaHei';
            font-size: 10pt;
        }}
    """


DIALOG_STYLE = """
QDialog {
    background-color: #f9fefb;
    color: #34433f;
}
QLabel {
    color: #34433f;
    font-family: 'Microsoft YaHei';
}
QLineEdit, QComboBox {
    background-color: #f7fbf6;
    color: #34433f;
    border: 1px solid #c9e8d6;
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: #d3ebdc;
    selection-color: #34433f;
    font-family: 'Microsoft YaHei';
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3fb7ad;
    background-color: #f7fbf6;
}
QComboBox QAbstractItemView {
    background-color: #f7fbf6;
    color: #34433f;
    border: 1px solid #c9e8d6;
    selection-background-color: #e6f2ea;
}
QPushButton {
    background-color: #f7fbf6;
    color: #34433f;
    border: 1px solid #c9e8d6;
    border-radius: 8px;
    padding: 7px 16px;
    font-family: 'Microsoft YaHei';
    font-weight: bold;
}
QPushButton:hover {
    background-color: #e6f2ea;
    border: 1px solid #3fb7ad;
}
QPushButton:pressed {
    background-color: #d8ebdf;
    border: 1px solid #5fbd82;
}
"""


PRIMARY_BUTTON_STYLE = """
QPushButton {
    background-color: #78d6a1;
    color: #f7fbf6;
    border: none;
    border-radius: 8px;
    padding: 7px 18px;
    font-family: 'Microsoft YaHei';
    font-weight: bold;
}
QPushButton:hover { background-color: #8ee1b1; }
QPushButton:pressed { background-color: #5fbd82; }
"""


SECONDARY_BUTTON_STYLE = """
QPushButton {
    background-color: #f7fbf6;
    color: #34433f;
    border: 1px solid #c9e8d6;
    border-radius: 8px;
    padding: 7px 18px;
    font-family: 'Microsoft YaHei';
    font-weight: bold;
}
QPushButton:hover {
    background-color: #e6f2ea;
    border: 1px solid #3fb7ad;
    color: #2f8f86;
}
QPushButton:pressed { background-color: #d8ebdf; border: 1px solid #5fbd82; }
"""


TABLE_STYLE = """
QTableWidget {
    background-color: #f7fbf6;
    alternate-background-color: #edf6ef;
    color: #34433f;
    border: 1px solid #c9e8d6;
    font-family: 'Consolas', 'Microsoft YaHei';
    font-size: 13px;
    border-radius: 10px;
    gridline-color: transparent;
}
QHeaderView::section {
    background-color: #e6f2ea;
    color: #3fb7ad;
    padding: 9px 8px;
    border: none;
    border-bottom: 1px solid #c9e8d6;
    border-right: 1px solid #dcefe5;
    font-family: 'Microsoft YaHei';
    font-weight: bold;
}
QTableWidget::item {
    border-bottom: 1px solid #e2f0e8;
    padding: 6px;
}
QTableWidget::item:selected {
    background-color: #d3ebdc;
    color: #34433f;
}
"""


TRIGGER_DIALOG_STYLE = """
QDialog {
    background-color: #fff8f8;
    border: 2px solid #df6f7b;
    border-radius: 18px;
}
"""


def trigger_button_style(color):
    return f"""
        QPushButton {{
            background-color: {color};
            color: #f7fbf6;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: bold;
            font-family: 'Microsoft YaHei';
        }}
        QPushButton:hover {{
            background-color: #f7fbf6;
            color: {color};
            border: 1px solid {color};
        }}
        QPushButton:pressed {{
            background-color: #eef6ef;
            color: {color};
            border: 1px solid {color};
        }}
    """


HINT_LABEL_STYLE = """
color: #2f8f86;
background: #e6f2ea;
border: 1px solid #c9e8d6;
border-radius: 8px;
padding: 8px 10px;
"""


SPINBOX_STYLE = """
QSpinBox {
    background-color: #f7fbf6;
    border: 1px solid #c9e8d6;
    border-right: none;
    border-top-left-radius: 7px;
    border-bottom-left-radius: 7px;
    padding: 5px;
    color: #34433f;
    selection-background-color: #d3ebdc;
    selection-color: #34433f;
}
QSpinBox:focus {
    border: 1px solid #3fb7ad;
    border-right: none;
}
"""


SPIN_BUTTON_STYLE = """
QPushButton {
    background-color: #f7fbf6;
    border: 1px solid #c9e8d6;
    color: #5fbd82;
    font-family: 'Consolas', 'Microsoft YaHei';
    font-weight: bold;
    font-size: 14px;
    padding: 0px;
}
QPushButton:hover {
    background-color: #e6f2ea;
    color: #3fb7ad;
    border: 1px solid #3fb7ad;
}
QPushButton:pressed {
    background-color: #d8ebdf;
    color: #2f8f86;
}
"""
