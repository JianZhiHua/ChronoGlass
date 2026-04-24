import datetime
import html
import os
import re
import sys
import urllib.parse
import winsound
from enum import IntEnum

try:
    from lunar_python import Lunar, Solar

    HAS_LUNAR = True
except ImportError:
    Lunar = None
    Solar = None
    HAS_LUNAR = False

from PyQt6.QtCore import QPoint, QTime, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon, QImageReader, QMovie, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkProxyFactory, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .common import AMBITION_TIME_FORMAT, resource_path
from .dialogs import AlarmSettingsDialog, AlarmTriggerDialog, AmbitionEditDialog
from .state import (
    load_alarms,
    load_config,
    log_error,
    normalize_ambition_config,
    save_alarms,
    save_config,
)
from .theme import (
    AMBITION_CARD_STYLE,
    CYAN,
    DIALOG_STYLE,
    GREEN,
    MAGENTA,
    MENU_STYLE,
    ORANGE,
    PURPLE,
    RED,
    TEXT,
    YELLOW,
    main_frame_style,
    mode_label_style,
    top_button_style,
)


class AppMode(IntEnum):
    CLOCK = 0
    AMBITION = 1
    COUNTDOWN = 2
    STOPWATCH = 3
    ALARM = 4


class ChronoGlass(QWidget):
    weather_updated = pyqtSignal(str)
    WINDOW_WIDTH = 450
    WINDOW_HEIGHT = 245
    WEATHER_TIMEOUT_MS = 12000

    def __init__(self):
        super().__init__()
        self.mode = AppMode.CLOCK
        self.is_running = False
        self.default_seconds = 1200
        self.remaining_seconds = self.default_seconds
        self.elapsed_seconds = 0
        self.drag_position = QPoint()

        self.alarms = load_alarms()
        self.config = load_config()
        self.location = self.config.get("location", "")
        self.ambition_config = normalize_ambition_config(self.config.get("ambition"))
        self.weather_info = ""
        self.weather_fetch_inflight = False
        QNetworkProxyFactory.setUseSystemConfiguration(True)
        self.weather_manager = QNetworkAccessManager(self)
        self.weather_reply = None
        self.cached_clock_info_date = None
        self.cached_clock_info_html = ""
        self.ambition_movie = None
        self.loaded_ambition_image_path = None

        self.weather_updated.connect(self.on_weather_updated)

        self.icon_path = resource_path("tray_icon.png")
        self.tray_icon_path = resource_path("tray_icon.png")

        self.init_ui()
        self.create_tray()

        if self.location:
            self.fetch_weather()

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.fetch_weather)
        self.weather_timer.start(1800000)

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(self.icon_path))
        self.setMinimumSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("MainFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.main_frame)

        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(18, 12, 16, 0)
        top_bar.setSpacing(8)

        self.mode_label = QLabel()
        self.mode_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        top_bar.addWidget(self.mode_label)
        top_bar.addStretch()

        self.mode_btn = QPushButton("⇆")
        self.mode_btn.setFixedSize(34, 30)
        self.mode_btn.setFont(QFont("Segoe UI Symbol", 15, QFont.Weight.Bold))
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mode_btn.setStyleSheet(top_button_style(GREEN))
        self.mode_btn.clicked.connect(lambda: self.switch_mode((self.mode + 1) % len(AppMode)))
        top_bar.addWidget(self.mode_btn)

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(34, 30)
        self.min_btn.setFont(QFont("Segoe UI Symbol", 15, QFont.Weight.Bold))
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.min_btn.setStyleSheet(top_button_style(CYAN))
        self.min_btn.clicked.connect(self.hide)
        top_bar.addWidget(self.min_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(34, 30)
        self.close_btn.setFont(QFont("Segoe UI Symbol", 15, QFont.Weight.Bold))
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.clicked.connect(QApplication.instance().quit)
        top_bar.addWidget(self.close_btn)

        frame_layout.addLayout(top_bar)

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: transparent; border: none;")
        self.content_stack.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.text_page = self.build_text_page()
        self.ambition_page = self.build_ambition_page()
        self.content_stack.addWidget(self.text_page)
        self.content_stack.addWidget(self.ambition_page)
        frame_layout.addWidget(self.content_stack, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

        self.refresh_display()
        self.show()

    def build_text_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 0, 18, 14)
        layout.setSpacing(0)
        layout.addStretch()

        self.label = QLabel()
        self.label.setMinimumHeight(178)
        self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.label)

        layout.addStretch()
        return page

    def build_ambition_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 8, 18, 18)
        layout.setSpacing(0)

        self.ambition_card = QFrame()
        self.ambition_card.setObjectName("AmbitionCard")
        self.ambition_card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.ambition_card.setStyleSheet(AMBITION_CARD_STYLE)
        layout.addWidget(self.ambition_card)

        card_layout = QHBoxLayout(self.ambition_card)
        card_layout.setContentsMargins(22, 8, 18, 12)
        card_layout.setSpacing(16)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)

        self.ambition_text_container = QWidget()
        self.ambition_text_container.setFixedSize(220, 72)

        text_layout = QVBoxLayout(self.ambition_text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        self.ambition_title_label = QLabel()
        self.ambition_title_label.setObjectName("AmbitionTitle")
        self.ambition_title_label.setWordWrap(True)
        self.ambition_title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(self.ambition_title_label)

        self.ambition_subtitle_label = QLabel()
        self.ambition_subtitle_label.setObjectName("AmbitionSubtitle")
        self.ambition_subtitle_label.setWordWrap(True)
        self.ambition_subtitle_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(self.ambition_subtitle_label)

        self.ambition_countdown_label = QLabel()
        self.ambition_countdown_label.setObjectName("AmbitionCountdown")
        self.ambition_countdown_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(self.ambition_countdown_label)

        text_layout.addStretch()

        left_layout.addWidget(
            self.ambition_text_container,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )

        self.ambition_festival_label = QLabel()
        self.ambition_festival_label.setObjectName("AmbitionFestival")
        self.ambition_festival_label.setWordWrap(True)
        self.ambition_festival_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ambition_festival_label.setFixedWidth(82)
        self.ambition_festival_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        left_layout.addWidget(self.ambition_festival_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        left_layout.addStretch()

        card_layout.addLayout(left_layout, 3)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addStretch()

        self.ambition_image_label = QLabel("上传图片后显示在这里\n支持 GIF")
        self.ambition_image_label.setObjectName("AmbitionImage")
        self.ambition_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ambition_image_label.setFixedSize(120, 120)
        self.ambition_image_label.setWordWrap(True)
        self.ambition_image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        right_layout.addWidget(self.ambition_image_label)

        right_layout.addStretch()
        card_layout.addLayout(right_layout, 2)

        return page

    def create_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(self.tray_icon_path))

        menu = QMenu()
        menu.setStyleSheet(MENU_STYLE)

        m0_act = QAction("🕒 系统时钟", self)
        m0_act.triggered.connect(lambda: self.switch_mode(AppMode.CLOCK))
        m1_act = QAction("🎯 生活的小确幸", self)
        m1_act.triggered.connect(lambda: self.switch_mode(AppMode.AMBITION))
        m2_act = QAction("⏳ 倒计时模式", self)
        m2_act.triggered.connect(lambda: self.switch_mode(AppMode.COUNTDOWN))
        m3_act = QAction("⏱️ 秒表计时", self)
        m3_act.triggered.connect(lambda: self.switch_mode(AppMode.STOPWATCH))
        m4_act = QAction("⏰ 闹钟", self)
        m4_act.triggered.connect(lambda: self.switch_mode(AppMode.ALARM))
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
        menu.addAction(m4_act)
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
        self.main_frame.setStyleSheet(main_frame_style(color))
        self.mode_label.setStyleSheet(mode_label_style(color))
        self.mode_label.setText(mode_text)
        self.close_btn.setStyleSheet(top_button_style(RED))
        self.label.setStyleSheet(f"color: {color}; background: transparent; padding-bottom: 4px;")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == AppMode.COUNTDOWN:
                self.set_custom_time()
            elif self.mode == AppMode.CLOCK:
                location, ok = QInputDialog.getText(self, "设定", "输入所在地获取天气(如: 北京):", text=self.location)
                if ok:
                    self.location = location.strip()
                    self.save_current_config()
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
        if self.mode == AppMode.AMBITION:
            self.open_ambition_editor()
            event.accept()
            return
        self.tray.contextMenu().exec(event.globalPos())

    def set_custom_time(self):
        value, ok = QInputDialog.getInt(
            self,
            "设定",
            "输入倒计时分钟数:",
            value=self.default_seconds // 60,
            min=1,
            max=1440,
        )
        if ok:
            self.default_seconds = value * 60
            self.remaining_seconds = self.default_seconds
            self.is_running = False
            self.refresh_display()

    def open_alarm_settings(self):
        dlg = AlarmSettingsDialog(self.alarms, self)
        dlg.exec()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and self.mode in (AppMode.COUNTDOWN, AppMode.STOPWATCH):
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

    def save_current_config(self):
        self.config["location"] = self.location
        self.config["ambition"] = normalize_ambition_config(self.ambition_config)
        save_config(self.config)

    def open_ambition_editor(self):
        dlg = AmbitionEditDialog(self.ambition_config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            previous_config = dict(self.ambition_config)
            self.ambition_config = dlg.get_values()
            self.loaded_ambition_image_path = None
            self.save_current_config()
            try:
                self.refresh_display()
            except Exception as exc:
                log_error("目标图片刷新失败", exc)
                self.ambition_config = previous_config
                self.loaded_ambition_image_path = None
                self.save_current_config()
                self.refresh_display()
                QMessageBox.warning(self, "图片加载失败", "选中的文件无法预览，请换一张图片再试。")

    def get_ambition_target_time(self):
        target_time = QTime.fromString(self.ambition_config.get("target_time", ""), AMBITION_TIME_FORMAT)
        if target_time.isValid():
            return target_time
        return QTime.currentTime().addSecs(3600)

    def format_ambition_countdown(self, seconds):
        total_seconds = max(abs(seconds), 0)
        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, secs = divmod(rem, 60)
        if days > 0:
            return f"{days}天 {hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_ambition_image_path(self, completed=False):
        image_key = "completed_image_path" if completed else "image_path"
        image_path = self.ambition_config.get(image_key, "").strip()
        if completed and not image_path:
            image_path = self.ambition_config.get("image_path", "").strip()
        if image_path:
            image_path = os.path.abspath(image_path)
        return image_path

    def update_ambition_image(self, completed=False, force=False):
        image_path = self.get_ambition_image_path(completed)
        if not force and image_path == self.loaded_ambition_image_path:
            return

        if self.ambition_movie is not None:
            self.ambition_movie.stop()
            self.ambition_movie = None

        self.loaded_ambition_image_path = image_path
        self.ambition_image_label.clear()
        self.ambition_image_label.setText("上传图片后显示在这里\n支持 GIF")

        if not image_path:
            return
        if not os.path.exists(image_path):
            self.ambition_image_label.setText("图片不存在\n右键重新上传")
            return

        if image_path.lower().endswith(".gif"):
            movie = QMovie(image_path)
            if movie.isValid():
                movie.setScaledSize(self.ambition_image_label.size())
                self.ambition_movie = movie
                self.ambition_image_label.setMovie(movie)
                movie.start()
                return
        reader = QImageReader(image_path)
        reader.setAutoTransform(True)
        if not reader.canRead():
            self.ambition_image_label.setText("图片格式不受支持")
            log_error(f"图片加载失败: {image_path}")
            return

        image = reader.read()
        if image.isNull():
            self.ambition_image_label.setText("图片加载失败")
            log_error(f"图片读取失败: {image_path}")
            return

        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            self.ambition_image_label.setText("图片转换失败")
            log_error(f"图片转换失败: {image_path}")
            return

        scaled = pixmap.scaled(
            self.ambition_image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.ambition_image_label.setPixmap(scaled)

    def fetch_weather(self):
        if not self.location:
            return

        if self.weather_fetch_inflight:
            return

        self.weather_fetch_inflight = True
        url = f"https://wttr.in/{urllib.parse.quote(self.location)}?format=%c+%t&m"
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(self.WEATHER_TIMEOUT_MS)
        request.setRawHeader(b"User-Agent", b"curl/8.0.1")
        request.setRawHeader(b"Accept", b"text/plain")
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )

        self.weather_reply = self.weather_manager.get(request)
        self.weather_reply.finished.connect(self.on_weather_request_finished)

    def extract_weather_text(self, result):
        match = re.search(r'<div class="term-container">\s*(.*?)\s*</div>', result, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return re.sub(r"<[^>]+>", "", match.group(1))

    def normalize_weather_result(self, result):
        normalized = result.strip()
        if "<html" in normalized.lower():
            normalized = self.extract_weather_text(normalized)
        normalized = html.unescape(re.sub(r"\s+", " ", normalized)).strip()
        if not normalized:
            return "网络异常"
        if "unknown location" in normalized.lower() or normalized.lower() == "unknown":
            return "未找到该地点"
        if len(normalized) > 20 or "<" in normalized:
            return "网络异常"
        return normalized

    def on_weather_request_finished(self):
        reply = self.sender()
        if not isinstance(reply, QNetworkReply):
            return

        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                result = bytes(reply.readAll()).decode("utf-8", errors="replace").strip()
                self.weather_updated.emit(self.normalize_weather_result(result))
                return

            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            status_text = str(status) if status is not None else "-"
            error = reply.error()
            url = reply.url().toString()
            detail = reply.errorString()
            log_error(f"天气请求失败: url={url} status={status_text} error={error.name} detail={detail}")
            if error == QNetworkReply.NetworkError.TimeoutError:
                self.weather_updated.emit("请求超时")
            else:
                self.weather_updated.emit("网络异常")
        finally:
            self.weather_fetch_inflight = False
            if reply is self.weather_reply:
                self.weather_reply = None
            reply.deleteLater()

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

    def update_ambition_display(self):
        target_time = self.get_ambition_target_time()
        seconds = QTime.currentTime().secsTo(target_time)
        title = self.ambition_config.get("title", "生活的小确幸").strip() or "生活的小确幸"
        subtitle = self.ambition_config.get("subtitle", "").strip()
        is_completed = seconds <= 0

        if not is_completed:
            self.ambition_title_label.setText(title)
            self.ambition_subtitle_label.clear()
            self.ambition_subtitle_label.setVisible(False)
            self.ambition_subtitle_label.setStyleSheet("")
            self.ambition_countdown_label.setVisible(True)
            self.ambition_countdown_label.setText(self.format_ambition_countdown(seconds))
            self.ambition_countdown_label.setStyleSheet(
                f"color: {YELLOW}; font-family: 'Consolas'; font-size: 48px; font-weight: bold;"
            )
        else:
            self.ambition_title_label.setText("恭喜")
            self.ambition_subtitle_label.setText(subtitle or "00:00:00")
            self.ambition_subtitle_label.setVisible(True)
            self.ambition_subtitle_label.setStyleSheet(
                f"color: {GREEN}; font-family: 'Consolas'; font-size: 34px; font-weight: bold;"
            )
            self.ambition_countdown_label.clear()
            self.ambition_countdown_label.setVisible(False)

        if HAS_LUNAR:
            festival_name, festival_days = self.get_next_festival_info(datetime.date.today())
            festival_display = self.truncate_display_text(festival_name, 4)
            if festival_days is None:
                badge_text = f"{festival_display}\n待定"
            elif festival_days <= 0:
                badge_text = f"{festival_display}\n今天"
            else:
                badge_text = f"{festival_display}\n{festival_days}天"
            self.ambition_festival_label.setText(badge_text)
        else:
            self.ambition_festival_label.setText("节日\n待启用")

        self.update_ambition_image(is_completed)

    def get_clock_info_html(self, now):
        today = now.date()
        if self.cached_clock_info_date == today and self.cached_clock_info_html:
            return self.cached_clock_info_html

        date_str = now.strftime("%Y年%m月%d日")
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        week_str = weekdays[now.weekday()]

        location_text = html.escape(self.location)
        weather_text = html.escape(self.weather_info)
        weather_str = (
            f" &nbsp;|&nbsp; {location_text} {weather_text}".rstrip()
            if self.location
            else " &nbsp;|&nbsp; 双击添加天气"
        )
        line1_str = f"{date_str} {week_str}{weather_str}"

        if HAS_LUNAR:
            lunar = Lunar.fromDate(now)
            jieqi_name, jieqi_days = self.get_next_jieqi_info(lunar, today)
            lunar_date_str = html.escape(f"农历{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}")
            jieqi_display = html.escape(jieqi_name)
            yi = html.escape(" ".join(lunar.getDayYi()[:4]) or "无")
            ji = html.escape(" ".join(lunar.getDayJi()[:4]) or "无")
            line2_str = f"{lunar_date_str} &nbsp;|&nbsp; 最近节气: {jieqi_display}({self.format_days_until(jieqi_days)})"
            line3_str = f"宜: {yi} &nbsp;|&nbsp; 忌: {ji}"
            info_str = "<br>".join([line1_str, line2_str, line3_str])
        else:
            info_str = (
                f"{line1_str}<br><span style='font-size: 9pt;'>"
                "(如需显示农历黄历，请在终端运行 pip install lunar-python)</span>"
            )

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
                    except RuntimeError as exc:
                        log_error("倒计时提示音播放失败", exc)
            elif self.mode == AppMode.STOPWATCH:
                self.elapsed_seconds += 1

        if self.alarms:
            today = datetime.date.today().isoformat()
            trigger_happened = False
            for index, alarm in enumerate(self.alarms):
                if self.should_trigger_alarm(alarm, today):
                    trigger_happened = True
                    alarm["last_trigger_date"] = today
                    if alarm.get("repeat", "once") == "once":
                        alarm["enabled"] = False

                    try:
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                    except RuntimeError as exc:
                        log_error("闹钟提示音播放失败", exc)

                    self.show_trigger_dialog(index)
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
            self.content_stack.setCurrentWidget(self.text_page)
            time_str = QTime.currentTime().toString("HH:mm:ss")
            now = datetime.datetime.now()
            info_str = self.get_clock_info_html(now)
            html_text = (
                f"""<span style="font-family: Consolas; font-size: 50pt; font-weight: bold;">{time_str}</span><br>"""
                f"""<span style="font-family: 'Microsoft YaHei'; font-size: 10pt; font-weight: normal; line-height: 1.18;">{info_str}</span>"""
            )
            self.label.setText(html_text)
            self.update_style(CYAN, "系统时钟")

        elif self.mode == AppMode.AMBITION:
            self.content_stack.setCurrentWidget(self.ambition_page)
            self.update_ambition_display()
            self.update_style(PURPLE, "生活的小确幸")

        elif self.mode == AppMode.COUNTDOWN:
            self.content_stack.setCurrentWidget(self.text_page)
            self.label.setText(self.format_time(self.remaining_seconds))
            self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
            if self.remaining_seconds == 0:
                self.update_style(RED, "时间到！")
            elif self.is_running:
                self.update_style(YELLOW, "倒计时进行中")
            else:
                self.update_style(GREEN, "倒计时已暂停")

        elif self.mode == AppMode.STOPWATCH:
            self.content_stack.setCurrentWidget(self.text_page)
            self.label.setText(self.format_time(self.elapsed_seconds))
            self.label.setFont(QFont("Consolas", 52, QFont.Weight.Bold))
            if self.is_running:
                self.update_style(MAGENTA, "正在计时")
            else:
                self.update_style(TEXT, "计时已暂停")

        elif self.mode == AppMode.ALARM:
            self.content_stack.setCurrentWidget(self.text_page)
            self.label.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
            count = len(self.alarms)
            enabled_count = sum(1 for alarm in self.alarms if alarm["enabled"])
            self.label.setText(f"您现在设定了 {count} 个闹钟\n(已启用 {enabled_count} 个)")
            self.update_style(ORANGE, "闹钟管理")

    def format_time(self, seconds):
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours > 0 else f"{minutes:02d}:{secs:02d}"

    def switch_mode(self, mode_idx):
        self.mode = AppMode(mode_idx)
        self.is_running = False
        self.refresh_display()

    def reset_timer(self):
        if self.mode == AppMode.COUNTDOWN:
            self.remaining_seconds = self.default_seconds
        elif self.mode == AppMode.STOPWATCH:
            self.elapsed_seconds = 0
        self.is_running = False
        self.refresh_display()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DIALOG_STYLE)
    app.setQuitOnLastWindowClosed(False)
    window = ChronoGlass()
    return app.exec()
