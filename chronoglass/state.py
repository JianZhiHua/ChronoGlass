import datetime
import json
import os
import threading
import traceback

from PyQt6.QtCore import QDateTime, QTime

from .common import (
    AMBITION_LEGACY_DATETIME_FORMAT,
    AMBITION_TIME_FORMAT,
    LEGACY_ALARMS_FILE_NAME,
    LEGACY_CONFIG_FILE_NAME,
    STATE_FILE_NAME,
    get_data_file_path,
)


STATE_LOCK = threading.RLock()


def log_error(message, exc=None):
    try:
        log_path = get_data_file_path("chronoglass.log")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        detail = f"[{now}] {message}\n"
        if exc is not None:
            detail += "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with open(log_path, "a", encoding="utf-8") as file:
            file.write(detail)
            file.write("\n")
    except Exception:
        return


def atomic_write_json(file_path, data):
    tmp_path = f"{file_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(tmp_path, file_path)


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


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
        "last_trigger_date": alarm.get("last_trigger_date", ""),
    }


def deserialize_alarm(record):
    return normalize_alarm(
        {
            "time": record.get("time", "00:00:00"),
            "name": record.get("name", "新闹钟"),
            "enabled": record.get("enabled", True),
            "repeat": record.get("repeat", "once"),
            "last_trigger_date": record.get("last_trigger_date", ""),
        }
    )


def default_ambition_config():
    target_time = QTime.currentTime().addSecs(3600)
    return {
        "title": "搬砖",
        "subtitle": "",
        "target_time": target_time.toString(AMBITION_TIME_FORMAT),
        "image_path": "",
        "completed_image_path": "",
    }


def normalize_ambition_config(record):
    ambition = default_ambition_config()
    if not isinstance(record, dict):
        return ambition

    title = record.get("title")
    if isinstance(title, str) and title.strip():
        title_text = title.strip()
        ambition["title"] = "搬砖" if title_text == "生活的小确幸" else title_text

    subtitle = record.get("subtitle")
    if isinstance(subtitle, str):
        ambition["subtitle"] = subtitle.strip()

    target_time = record.get("target_time")
    if isinstance(target_time, str):
        raw_target_time = target_time.strip()
        parsed_time = QTime.fromString(raw_target_time, AMBITION_TIME_FORMAT)
        if parsed_time.isValid():
            ambition["target_time"] = parsed_time.toString(AMBITION_TIME_FORMAT)
        else:
            parsed_dt = QDateTime.fromString(raw_target_time, AMBITION_LEGACY_DATETIME_FORMAT)
            if parsed_dt.isValid():
                ambition["target_time"] = parsed_dt.time().toString(AMBITION_TIME_FORMAT)

    image_path = record.get("image_path")
    if isinstance(image_path, str):
        ambition["image_path"] = image_path.strip()

    completed_image_path = record.get("completed_image_path")
    if isinstance(completed_image_path, str):
        ambition["completed_image_path"] = completed_image_path.strip()

    return ambition


def normalize_config(record):
    config = dict(record) if isinstance(record, dict) else {}
    location = config.get("location", "")
    config["location"] = location.strip() if isinstance(location, str) else ""
    config["ambition"] = normalize_ambition_config(config.get("ambition"))
    return config


def default_state():
    return {
        "version": 1,
        "config": normalize_config({}),
        "alarms": [],
    }


def normalize_state(record):
    state = default_state()
    if not isinstance(record, dict):
        return state

    version = record.get("version")
    if isinstance(version, int):
        state["version"] = version

    state["config"] = normalize_config(record.get("config"))

    alarms = record.get("alarms")
    if isinstance(alarms, list):
        state["alarms"] = [deserialize_alarm(alarm) for alarm in alarms if isinstance(alarm, dict)]

    return state


def serialize_state(state):
    normalized = normalize_state(state)
    return {
        "version": normalized["version"],
        "config": normalized["config"],
        "alarms": [serialize_alarm(alarm) for alarm in normalized["alarms"]],
    }


def load_legacy_state():
    state = default_state()

    alarms_path = get_data_file_path(LEGACY_ALARMS_FILE_NAME)
    if os.path.exists(alarms_path):
        try:
            data = read_json_file(alarms_path)
            if isinstance(data, list):
                state["alarms"] = [deserialize_alarm(alarm) for alarm in data if isinstance(alarm, dict)]
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            log_error("读取旧版 alarms.json 失败", exc)

    config_path = get_data_file_path(LEGACY_CONFIG_FILE_NAME)
    if os.path.exists(config_path):
        try:
            data = read_json_file(config_path)
            if isinstance(data, dict):
                state["config"] = dict(data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            log_error("读取旧版 config.json 失败", exc)

    return state


def load_state():
    file_path = get_data_file_path(STATE_FILE_NAME)
    with STATE_LOCK:
        if os.path.exists(file_path):
            try:
                return normalize_state(read_json_file(file_path))
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                log_error(f"读取 {STATE_FILE_NAME} 失败", exc)

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
    except Exception as exc:
        print(f"状态保存失败: {exc}")
        log_error(f"写入 {STATE_FILE_NAME} 失败", exc)


def load_alarms():
    return load_state()["alarms"]


def save_alarms(alarms):
    state = load_state()
    state["alarms"] = list(alarms)
    save_state(state)


def load_config():
    return normalize_config(load_state()["config"])


def save_config(config):
    state = load_state()
    state["config"] = normalize_config(config)
    save_state(state)


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
