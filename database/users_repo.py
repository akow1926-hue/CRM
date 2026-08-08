import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from database.db import _db_lock, get_worksheet_safe, add_audit_log

_users_cache: List[Dict[str, Any]] = [
    {
        "id": 1,
        "Username": "admin",
        "Password": "admin123",
        "Role": "Администратор",
        "Status": "Активен",
        "TelegramID": "",
        "Phone": "+998 90 123 45 67",
        "Name": "Администратор"
    }
]
_sessions_cache: Dict[str, Dict[str, Any]] = {}
_last_fetch_time = 0
CACHE_TTL = 30


def sync_to_json_files():
    # Deprecated backup sync - no longer using local files
    pass


def _row_to_user_dict(r: Dict[str, Any], idx: int = 1) -> Dict[str, Any]:
    return {
        "id": r.get("ID") or idx,
        "Username": str(r.get("Username") or r.get("username") or "").strip(),
        "Password": str(r.get("Password") or r.get("password") or "").strip(),
        "Role": str(r.get("Role") or r.get("role") or "Курьер").strip(),
        "Status": str(r.get("Status") or r.get("status") or "Активен").strip(),
        "TelegramID": str(r.get("TelegramID") or r.get("telegram_id") or "").strip(),
        "Phone": str(r.get("Phone") or r.get("phone") or "").strip(),
        "Name": str(r.get("Name") or r.get("name") or r.get("Username") or "").strip()
    }


def get_users(force_refresh: bool = False) -> List[Dict[str, Any]]:
    global _users_cache, _last_fetch_time
    now = datetime.now().timestamp()

    with _db_lock:
        if not force_refresh and _users_cache and (now - _last_fetch_time < CACHE_TTL):
            return list(_users_cache)

    try:
        # Check 'Сотрудники' or 'Пользователи'
        ws = get_worksheet_safe("Сотрудники") or get_worksheet_safe("Пользователи")
        if ws:
            records = ws.get_all_records()
            if records:
                users = []
                for i, r in enumerate(records, start=1):
                    u = _row_to_user_dict(r, i)
                    if u["Username"]:
                        users.append(u)

                if users:
                    with _db_lock:
                        _users_cache = users
                        _last_fetch_time = now
                    return list(users)
    except Exception as e:
        print(f"[Google Sheets get_users Error] {e}")

    with _db_lock:
        return list(_users_cache)


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    if not username:
        return None
    u_clean = username.strip().lower()

    users = get_users()
    for u in users:
        if u["Username"].strip().lower() == u_clean:
            return dict(u)
    return None


def get_user_by_telegram_id(telegram_id: Any) -> Optional[Dict[str, Any]]:
    tg_clean = str(telegram_id).strip()
    if not tg_clean:
        return None

    users = get_users()
    for u in users:
        if str(u.get("TelegramID", "")).strip() == tg_clean:
            return dict(u)
    return None


def add_user(username: str, password: str, role: str, status: str = "Активен", telegram_id: str = "") -> bool:
    from core import security
    u_clean = username.strip()
    if not u_clean or not password:
        return False

    hashed_pw = security.hash_password(password) if not password.startswith("pbkdf2:") else password
    new_user = {
        "id": len(_users_cache) + 1,
        "Username": u_clean,
        "Password": hashed_pw,
        "Role": role,
        "Status": status,
        "TelegramID": str(telegram_id),
        "Phone": "",
        "Name": u_clean
    }

    with _db_lock:
        _users_cache = [u for u in _users_cache if u["Username"].lower() != u_clean.lower()]
        _users_cache.append(new_user)

    def _async_add_sheet():
        try:
            ws = get_worksheet_safe("Сотрудники") or get_worksheet_safe("Пользователи")
            if ws:
                ws.append_row([
                    new_user["id"],
                    new_user["Username"],
                    new_user["Password"],
                    new_user["Role"],
                    new_user["Status"],
                    new_user["TelegramID"],
                    new_user["Phone"],
                    new_user["Name"]
                ])
        except Exception as e:
            print(f"[Google Sheets add_user Error] {e}")

    threading.Thread(target=_async_add_sheet, daemon=True).start()
    return True


def update_user_password(username: str, new_password_hash: str) -> bool:
    u_clean = username.strip().lower()
    with _db_lock:
        for u in _users_cache:
            if u["Username"].lower() == u_clean:
                u["Password"] = new_password_hash
                break

    def _async_update():
        try:
            ws = get_worksheet_safe("Сотрудники") or get_worksheet_safe("Пользователи")
            if ws:
                col_users = ws.col_values(2)  # Username column
                for i, uname in enumerate(col_users[1:], start=2):
                    if uname.strip().lower() == u_clean:
                        ws.update_cell(i, 3, new_password_hash)  # Password column
                        break
        except Exception as e:
            print(f"[Google Sheets update_password Error] {e}")

    threading.Thread(target=_async_update, daemon=True).start()
    return True


def bind_telegram_id(username: str, telegram_id: Any) -> bool:
    u_clean = username.strip().lower()
    tg_str = str(telegram_id).strip()

    with _db_lock:
        for u in _users_cache:
            if u["Username"].lower() == u_clean:
                u["TelegramID"] = tg_str
                break

    def _async_update():
        try:
            ws = get_worksheet_safe("Сотрудники") or get_worksheet_safe("Пользователи")
            if ws:
                col_users = ws.col_values(2)
                for i, uname in enumerate(col_users[1:], start=2):
                    if uname.strip().lower() == u_clean:
                        ws.update_cell(i, 6, tg_str)
                        break
        except Exception as e:
            print(f"[Google Sheets bind_telegram Error] {e}")

    threading.Thread(target=_async_update, daemon=True).start()
    return True


def create_session(token: str, user_id: Any, username: str, role: str, telegram_id: str = "", ip_address: str = "", expires_hours: int = 168) -> bool:
    expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
    now_str = datetime.now().isoformat()
    with _db_lock:
        _sessions_cache[token] = {
            "token": token,
            "user_id": user_id,
            "username": username,
            "role": role,
            "telegram_id": telegram_id,
            "created_at": now_str,
            "expires_at": expires_at,
            "last_active_at": now_str,
            "ip_address": ip_address
        }
    return True


def get_session(token: str) -> Optional[Dict[str, Any]]:
    with _db_lock:
        sess = _sessions_cache.get(token)
        if sess:
            if sess.get("expires_at") > datetime.now().isoformat():
                sess["last_active_at"] = datetime.now().isoformat()
                return dict(sess)
            else:
                del _sessions_cache[token]
    return None


def delete_session(token: str) -> bool:
    with _db_lock:
        if token in _sessions_cache:
            del _sessions_cache[token]
            return True
    return False


def cleanup_expired_sessions():
    now_str = datetime.now().isoformat()
    with _db_lock:
        expired = [t for t, s in _sessions_cache.items() if s.get("expires_at", "") < now_str]
        for t in expired:
            del _sessions_cache[t]
