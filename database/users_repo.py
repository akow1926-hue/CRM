import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from database.db import get_db_connection, _db_lock
from config import settings


def sync_to_json_files():
    try:
        users = get_users()
        with open(settings.BACKUP_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[JSON Sync Users Error] {e}")


def get_users() -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id ASC;")
        rows = cursor.fetchall()
        conn.close()

    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "Username": r["username"],
            "Password": r["password"],
            "Role": r["role"],
            "Status": r["status"] or "Активен",
            "TelegramID": r["telegram_id"] or ""
        })
    return res


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    if not username:
        return None
    u_clean = username.strip().lower()

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = ?;", (u_clean,))
        r = cursor.fetchone()
        conn.close()

    if not r:
        return None

    return {
        "id": r["id"],
        "Username": r["username"],
        "Password": r["password"],
        "Role": r["role"],
        "Status": r["status"] or "Активен",
        "TelegramID": r["telegram_id"] or ""
    }


def get_user_by_telegram_id(telegram_id: Any) -> Optional[Dict[str, Any]]:
    tg_clean = str(telegram_id).strip()
    if not tg_clean:
        return None

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?;", (tg_clean,))
        r = cursor.fetchone()
        conn.close()

    if not r:
        return None

    return {
        "id": r["id"],
        "Username": r["username"],
        "Password": r["password"],
        "Role": r["role"],
        "Status": r["status"] or "Активен",
        "TelegramID": r["telegram_id"] or ""
    }


def add_user(username: str, password: str, role: str, status: str = "Активен", telegram_id: str = "") -> bool:
    from core import security
    u_clean = username.strip()
    if not u_clean or not password:
        return False

    hashed_pw = security.hash_password(password) if not password.startswith("pbkdf2:") else password
    now_str = datetime.now().isoformat()

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, password, role, status, telegram_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (u_clean, hashed_pw, role, status, str(telegram_id).strip(), now_str, now_str))
            conn.commit()
            conn.close()
            sync_to_json_files()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False


def update_user_password(username: str, new_hashed_password: str) -> bool:
    u_clean = username.strip().lower()
    now_str = datetime.now().isoformat()
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET password = ?, updated_at = ? WHERE LOWER(username) = ?;
        """, (new_hashed_password, now_str, u_clean))
        conn.commit()
        conn.close()
    sync_to_json_files()
    return True


def bind_telegram_id(username: str, telegram_id: Any) -> bool:
    u_clean = username.strip().lower()
    tg_str = str(telegram_id).strip()
    now_str = datetime.now().isoformat()
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET telegram_id = ?, updated_at = ? WHERE LOWER(username) = ?;
        """, (tg_str, now_str, u_clean))
        conn.commit()
        conn.close()
    sync_to_json_files()
    return True


# Sessions & Audit Logs
def create_session(token: str, username: str, role: str, telegram_id: str = "", ip_address: str = "", ttl_hours: int = 24) -> bool:
    now = datetime.now()
    exp = now + timedelta(hours=ttl_hours)

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (token, username, role, telegram_id, created_at, expires_at, last_active_at, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (token, username, role, str(telegram_id), now.isoformat(), exp.isoformat(), now.isoformat(), ip_address))
        conn.commit()
        conn.close()
    return True


def get_session(token: str) -> Optional[Dict[str, Any]]:
    cleanup_expired_sessions()
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE token = ?;", (token,))
        r = cursor.fetchone()

        if r:
            now_str = datetime.now().isoformat()
            cursor.execute("UPDATE sessions SET last_active_at = ? WHERE token = ?;", (now_str, token))
            conn.commit()
            conn.close()
            return {
                "token": r["token"],
                "username": r["username"],
                "role": r["role"],
                "telegram_id": r["telegram_id"],
                "created_at": r["created_at"],
                "expires_at": r["expires_at"],
                "last_active_at": r["last_active_at"],
                "ip_address": r["ip_address"]
            }
        conn.close()
    return None


def delete_session(token: str) -> bool:
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?;", (token,))
        conn.commit()
        conn.close()
    return True


def cleanup_expired_sessions():
    now_str = datetime.now().isoformat()
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE expires_at < ?;", (now_str,))
        conn.commit()
        conn.close()


def add_audit_log(username: str, role: str, action: str, target_type: str = "order", target_id: str = "", details: Optional[Dict[str, Any]] = None, ip_address: str = ""):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details_json = json.dumps(details or {}, ensure_ascii=False)

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, username, role, action, target_type, target_id, details_json, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (now_str, username, role, action, target_type, target_id, details_json, ip_address))
        conn.commit()
        conn.close()
