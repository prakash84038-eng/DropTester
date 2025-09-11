import os
import json
import hashlib
from . import constants

# ---------- Analysis Configuration ----------
ANALYSIS_CONFIG_FILE = "analysis_config.json"
BACKUP_CONFIG_FILE = "analysis_config.json.bak"

def load_analysis_config() -> dict:
    """Loads analysis thresholds. Restores from backup or creates a default config if needed."""
    defaults = {
        "deformation_threshold": 0.15,
        "spill_min_area": 400,
        "shatter_contour_increase_ratio": 2.0,
        "shatter_min_contour_count": 5
    }
    
    if not os.path.exists(ANALYSIS_CONFIG_FILE):
        # If main file is missing, try to restore from backup
        if os.path.exists(BACKUP_CONFIG_FILE):
            try:
                with open(BACKUP_CONFIG_FILE, "r") as f:
                    config = json.load(f)
                save_analysis_config(config)  # This restores the main file
                print("Restored analysis config from backup.")
                return config
            except Exception as e:
                print(f"Could not restore from backup: {e}")
        
        # If no main file and no backup, create a new default config
        save_analysis_config(defaults)
        return defaults

    try:
        with open(ANALYSIS_CONFIG_FILE, "r") as f:
            config = json.load(f)
        # Ensure all keys are present, add if missing
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        return config
    except Exception:
        return defaults

def save_analysis_config(config: dict) -> None:
    """Saves the analysis thresholds to the config file and a backup file."""
    try:
        # Save the main configuration file
        with open(ANALYSIS_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        # Save the backup file
        with open(BACKUP_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving analysis config: {e}")

# ---------- Utility functions ----------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def save_login_data(username: str, password: str) -> None:
    data = {"username": username, "password_hash": hash_password(password)}
    try:
        with open(constants.LOGIN_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving login data: {e}")

def load_login_data() -> dict:
    if os.path.exists(constants.LOGIN_FILE):
        try:
            with open(constants.LOGIN_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Default credentials
    data = {"username": "admin", "password_hash": hash_password("1234")}
    save_login_data(data["username"], "1234")
    return data

def save_directory(path: str) -> None:
    try:
        with open(constants.DIR_FILE, "w") as f:
            json.dump({"directory": path}, f, indent=2)
    except Exception as e:
        print(f"Error saving directory: {e}")

def load_directory() -> str:
    if os.path.exists(constants.DIR_FILE):
        try:
            with open(constants.DIR_FILE, "r") as f:
                data = json.load(f)
            if "directory" in data and os.path.exists(data["directory"]):
                return data["directory"]
        except Exception:
            pass
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop) and os.access(desktop, os.R_OK | os.W_OK):
            return desktop
    except Exception:
        pass
    return os.getcwd()

def load_testing_persons():
    try:
        with open(constants.TESTING_PERSONS_FILE, "r") as f:
            data = json.load(f)
        persons = data.get("testing_persons", [])
        return persons if persons else ["Default User"]
    except Exception:
        return ["Default User"]

def save_testing_persons(persons):
    try:
        with open(constants.TESTING_PERSONS_FILE, "w") as f:
            json.dump({"testing_persons": persons}, f, indent=2)
    except Exception as e:
        print(f"Error saving testing persons: {e}")

# ---------- Video settings ----------
def load_video_settings():
    try:
        with open(constants.VIDEO_SETTINGS_FILE, "r") as f:
            data = json.load(f)
        w = int(data.get("width", 640))
        h = int(data.get("height", 480))
        return w, h
    except Exception:
        return 640, 480

def save_video_settings(width: int, height: int):
    try:
        # Merge with any existing advanced settings
        data = {}
        if os.path.exists(constants.VIDEO_SETTINGS_FILE):
            try:
                with open(constants.VIDEO_SETTINGS_FILE, "r") as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
        data.update({"width": int(width), "height": int(height)})
        with open(constants.VIDEO_SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving video settings: {e}")

# ---------- Advanced video settings ----------
def load_advanced_video_settings():
    """Returns dict with keys: force_directshow(bool), disable_preview_on_record(bool), target_fps(str|int)."""
    defaults = {
        "force_directshow": True,
        "disable_preview_on_record": False,
        "target_fps": "auto",  # or an int like 15, 20, 24, 25, 30
    }
    try:
        with open(constants.VIDEO_SETTINGS_FILE, "r") as f:
            data = json.load(f) or {}
        for k, v in defaults.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return defaults.copy()

def save_advanced_video_settings(force_directshow: bool, disable_preview_on_record: bool, target_fps):
    try:
        data = {}
        if os.path.exists(constants.VIDEO_SETTINGS_FILE):
            try:
                with open(constants.VIDEO_SETTINGS_FILE, "r") as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
        data.update({
            "force_directshow": bool(force_directshow),
            "disable_preview_on_record": bool(disable_preview_on_record),
            "target_fps": target_fps if (isinstance(target_fps, int) or target_fps == "auto") else "auto",
        })
        with open(constants.VIDEO_SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving advanced video settings: {e}")