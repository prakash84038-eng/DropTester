import os

# Determine the absolute path to the project's root directory.
# This assumes constants.py is in a 'src' folder at the project root.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------- Constants ----------
# You can replace 'logo.png' with different files (e.g., 'login_logo.png', 'header_logo.png') 
# in the 'assets' directory to use unique logos for each section.
LOGIN_LOGO_FILE = os.path.join(BASE_DIR, "assets/login_logo.png")
HEADER_LOGO_FILE = os.path.join(BASE_DIR, "assets/header_logo.png")
REPORT_LOGO_FILE = os.path.join(BASE_DIR, "assets/report_logo.png")

APP_ICON_FILE = os.path.join(BASE_DIR, "app_icon.png")
LOGIN_FILE = "login.json"
DIR_FILE = "directory.json"
TESTING_PERSONS_FILE = "testing_persons.json"
VIDEO_SETTINGS_FILE = "video_settings.json"

BOTTLE_COUNT = 6
MAX_RECORD_SECONDS = 15