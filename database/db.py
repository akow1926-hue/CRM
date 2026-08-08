import os
import sys
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.path.join(BASE_DIR, "key.json")
GSHEET_CONFIG_FILE = os.path.join(BASE_DIR, "gsheet_config.json")
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1zYbTgS1aQc-1aeP0EeAo-KeohbTAyGYumJLQQxmBZRk/edit"

_db_lock = threading.RLock()
_gs_client = None
_gs_doc = None
_last_doc_time = 0

# In-memory storage cache for ultra-fast instant UI responsiveness
_cache_orders: List[Dict[str, Any]] = []
_cache_users: List[Dict[str, Any]] = []
_cache_sessions: Dict[str, Dict[str, Any]] = {}
_cache_audit_logs: List[Dict[str, Any]] = []
_last_orders_fetch = 0
_last_users_fetch = 0


def normalize_id(val) -> str:
    if val is None or val == "":
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.startswith("TG-") or s.startswith("tg-"):
        s = s[3:]
    return s


def get_gsheet_url() -> str:
    if os.path.exists(GSHEET_CONFIG_FILE):
        try:
            with open(GSHEET_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("gsheet_url"):
                    return data.get("gsheet_url").strip()
        except Exception:
            pass
    return DEFAULT_GSHEET_URL


def get_gsheet_doc():
    global _gs_client, _gs_doc, _last_doc_time
    now = datetime.now().timestamp()
    if _gs_doc is not None and (now - _last_doc_time < 300):
        return _gs_doc

    if not os.path.exists(KEY_FILE):
        return None

    try:
        import gspread
        _gs_client = gspread.service_account(filename=KEY_FILE)
        url = get_gsheet_url()
        _gs_doc = _gs_client.open_by_url(url)
        _last_doc_time = now
        return _gs_doc
    except Exception as e:
        print(f"[Google Sheets Connect Warning] {e}")
        return None


def get_worksheet_safe(name: str):
    doc = get_gsheet_doc()
    if not doc:
        return None
    try:
        return doc.worksheet(name)
    except Exception:
        # Fallback search by title
        try:
            for s in doc.worksheets():
                if s.title.lower() == name.lower():
                    return s
        except Exception:
            pass
    return None


def init_db():
    """Initializes Google Sheets worksheets and loads primary memory cache."""
    print("[Google Sheets Database Engine] Initializing Google Sheets as primary DB...")
    doc = get_gsheet_doc()
    if doc:
        try:
            titles = [s.title for s in doc.worksheets()]
            print(f"[Google Sheets DB] Connected to: '{doc.title}'. Active sheets: {titles}")
        except Exception as e:
            print(f"[Google Sheets Init Warning] {e}")


def add_audit_log(username: str, role: str, action: str, details: str = "", ip_address: str = ""):
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    entry = {
        "timestamp": now_str,
        "username": username,
        "role": role,
        "action": action,
        "details": details,
        "ip_address": ip_address
    }
    with _db_lock:
        _cache_audit_logs.insert(0, entry)
        if len(_cache_audit_logs) > 1000:
            _cache_audit_logs.pop()

    # Async log to Google Sheets in background thread
    def _async_write():
        try:
            ws = get_worksheet_safe("Журнал Действий")
            if ws:
                ws.append_row([now_str, username, role, action, details, ip_address])
        except Exception:
            pass

    threading.Thread(target=_async_write, daemon=True).start()


def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    with _db_lock:
        if _cache_audit_logs:
            return _cache_audit_logs[:limit]
    try:
        ws = get_worksheet_safe("Журнал Действий")
        if ws:
            rows = ws.get_all_records()
            if rows:
                return rows[-limit:][::-1]
    except Exception:
        pass
    return []
