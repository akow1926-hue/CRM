import os
import sys
import json
import sqlite3
import threading
from datetime import datetime
from config import settings

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

_db_lock = threading.Lock()


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def normalize_id(val) -> str:
    if val is None or val == "":
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.startswith("TG-") or s.startswith("tg-"):
        s = s[3:]
    return s


def init_db():
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'Активен',
                telegram_id TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                date TEXT,
                client TEXT,
                phone TEXT,
                address TEXT,
                district TEXT,
                language TEXT,
                sizes TEXT,
                area TEXT DEFAULT '0',
                total_price TEXT DEFAULT '0',
                paid_amount TEXT DEFAULT '0',
                payment_type TEXT DEFAULT '-',
                status TEXT DEFAULT 'Ожидает забора',
                courier TEXT DEFAULT '',
                dispatcher TEXT DEFAULT '',
                location TEXT DEFAULT '-',
                debt_reason TEXT DEFAULT '-',
                created_at TEXT,
                updated_at TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                telegram_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_active_at TEXT NOT NULL,
                ip_address TEXT DEFAULT ''
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT DEFAULT 'order',
                target_id TEXT DEFAULT '',
                details_json TEXT DEFAULT '{}',
                ip_address TEXT DEFAULT ''
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sms_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                phone TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'sent',
                response TEXT DEFAULT ''
            );
        """)

        conn.commit()

        # Migrate Users
        cursor.execute("SELECT COUNT(*) FROM users;")
        if cursor.fetchone()[0] == 0 and os.path.exists(settings.BACKUP_USERS_FILE):
            try:
                from core import security
                with open(settings.BACKUP_USERS_FILE, "r", encoding="utf-8") as f:
                    users_data = json.load(f)
                    now_str = datetime.now().isoformat()
                    for u in users_data:
                        un = str(u.get("Username") or u.get("username") or "").strip()
                        pw = str(u.get("Password") or u.get("password") or "").strip()
                        rl = str(u.get("Role") or u.get("role") or "").strip()
                        st = str(u.get("Status") or u.get("status") or "Активен").strip()
                        tg = str(u.get("TelegramID") or u.get("telegram_id") or "").strip()
                        if un and pw:
                            if not pw.startswith("pbkdf2:"):
                                pw = security.hash_password(pw)
                            cursor.execute("""
                                INSERT OR IGNORE INTO users (username, password, role, status, telegram_id, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?);
                            """, (un, pw, rl, st, tg, now_str, now_str))
                conn.commit()
            except Exception as e:
                print(f"[DB Migration Error Users] {e}")

        # Migrate Orders
        cursor.execute("SELECT COUNT(*) FROM orders;")
        if cursor.fetchone()[0] == 0 and os.path.exists(settings.BACKUP_ORDERS_FILE):
            try:
                with open(settings.BACKUP_ORDERS_FILE, "r", encoding="utf-8") as f:
                    orders_data = json.load(f)
                    now_str = datetime.now().isoformat()
                    for o in orders_data:
                        oid = normalize_id(o.get("ID"))
                        if oid:
                            cursor.execute("""
                                INSERT OR IGNORE INTO orders (
                                    id, date, client, phone, address, district, language,
                                    sizes, area, total_price, paid_amount, payment_type,
                                    status, courier, dispatcher, location, debt_reason,
                                    created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """, (
                                oid,
                                str(o.get("Дата", "")),
                                str(o.get("Клиент", "")),
                                str(o.get("Телефон", "")),
                                str(o.get("Адрес", "")),
                                str(o.get("Район", "")),
                                str(o.get("Язык", "")),
                                str(o.get("Размеры", "")),
                                str(o.get("Площадь", "0")),
                                str(o.get("Сумма", "0")),
                                str(o.get("Оплачено", "0")),
                                str(o.get("Тип оплаты", "-")),
                                str(o.get("Статус", "Ожидает забора")),
                                str(o.get("Курьер", "")),
                                str(o.get("Диспетчер", "")),
                                str(o.get("Локация", "-")),
                                str(o.get("Причина", "-")),
                                now_str,
                                now_str
                            ))
                conn.commit()
            except Exception as e:
                print(f"[DB Migration Error Orders] {e}")

        conn.close()

init_db()
