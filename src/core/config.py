import os
import json

APP_NAME = "TelegramHooker"
APP_VERSION = "1.0.0"
AUTHOR = "@ASEQX12"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".telegram_hooker")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SESSIONS_DIR = os.path.join(CONFIG_DIR, "sessions")

DEFAULT_CONFIG = {
    "api_id": "",
    "api_hash": "",
    "phone": "",
    "last_target": "",
}

def ensure_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(SESSIONS_DIR, exist_ok=True)

def load_config():
    ensure_dirs()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def get_sessions():
    ensure_dirs()
    return [f.replace(".json", "") for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
