import os
import sys
import json
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "telegram_config.json")
BACKUP_ORDERS_FILE = os.path.join(BASE_DIR, "backup_orders.json")
BACKUP_USERS_FILE = os.path.join(BASE_DIR, "backup_users.json")
SMS_HISTORY_FILE = os.path.join(BASE_DIR, "sms_history.json")
DB_FILE = os.path.join(BASE_DIR, "crm.db")

# Security settings
JWT_SECRET = os.environ.get("JWT_SECRET") or "cosmo-crm-super-secret-jwt-key-2026-secure-prod"
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:8080,https://crm-cosmo.streamlit.app").split(",") if o.strip()]
PORT = int(os.environ.get("PORT", 8080))

def load_telegram_config() -> dict:
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[Settings Config Error] {e}")

    c_token = os.environ.get("COURIER_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("courier_bot_token") or cfg.get("bot_token")
    d_token = os.environ.get("DISPATCHER_BOT_TOKEN") or cfg.get("dispatcher_bot_token")

    if c_token:
        cfg["courier_bot_token"] = c_token
        cfg["bot_token"] = c_token
    if d_token:
        cfg["dispatcher_bot_token"] = d_token

    return cfg

def save_telegram_config(new_cfg: dict) -> bool:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(new_cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Settings Save Config Error] {e}")
        return False
