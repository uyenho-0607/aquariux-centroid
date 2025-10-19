from pathlib import Path

# Framework Paths
ROOTDIR = Path(__file__).parent.parent.parent
CONFIG_DIR = ROOTDIR / "config"
VIDEO_DIR = ROOTDIR / ".videos"
SRC_DIR = ROOTDIR / "src"
DATA_DIR = SRC_DIR / "data"

# Timeouts (in seconds)
EXPLICIT_WAIT = 5
IMPLICIT_WAIT = 0
PAGE_LOAD_WAIT = 30
SHORT_WAIT = 2
QUICK_WAIT = 0.5

CHECK_ICON = "✔"
FAILED_ICON = "✘"
CHECK_ICON_COLOR = "✅"
FAILED_ICON_COLOR = "❌"
WARNING_ICON = "❗"
SEND_ICON = "➡️"
RECEIVE_ICON = "⬅️"

WEB_APP_DEVICE = "iPhone 14 Pro Max"

MULTI_OMS = ["lirunex"]
PLATFORMS = ["web", "android", "ios", "web_app"]
CHART_TIME = 2