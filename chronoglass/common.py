import os
import sys


STATE_FILE_NAME = "chronoglass_state.json"
LEGACY_ALARMS_FILE_NAME = "alarms.json"
LEGACY_CONFIG_FILE_NAME = "config.json"
AMBITION_TIME_FORMAT = "HH:mm:ss"
AMBITION_LEGACY_DATETIME_FORMAT = "yyyy-MM-dd HH:mm:ss"

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    if hasattr(sys, "frozen") or "__compiled__" in globals():
        return os.path.join(os.path.dirname(sys.executable), relative_path)

    nuitka_root = os.environ.get("NUITKA_PACKAGE_HOME")
    if nuitka_root:
        return os.path.join(nuitka_root, relative_path)

    return os.path.join(PROJECT_DIR, relative_path)


def get_data_file_path(filename=STATE_FILE_NAME):
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        base_path = PROJECT_DIR
    return os.path.join(base_path, filename)
