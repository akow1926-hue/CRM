import os
import sys
import zipfile
import sqlite3
import time
from datetime import datetime, timedelta
import logger

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
DB_PATH = os.path.join(BASE_DIR, "crm.db")

os.makedirs(BACKUP_DIR, exist_ok=True)


def check_db_integrity() -> bool:
    """Verifies SQLite database integrity using PRAGMA quick_check."""
    if not os.path.exists(DB_PATH):
        return True
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("PRAGMA quick_check;")
        res = cursor.fetchone()
        conn.close()
        if res and res[0] == "ok":
            return True
        logger.log_error(f"БД повреждена: {res}")
        return False
    except Exception as e:
        logger.log_error("Ошибка при проверке целостности БД", e)
        return False


def create_backup() -> str:
    """
    Creates a timestamped zip archive containing crm.db and backup JSON files.
    Cleans up backups older than retention_days (default 30).
    Returns path to created backup archive.
    """
    if not check_db_integrity():
        logger.log_error("Отмена бэкапа: проверка целостности БД не пройдена.")
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"crm_backup_{timestamp}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_name)

    files_to_backup = ["crm.db", "backup_orders.json", "backup_users.json", "sms_history.json", "telegram_config.json"]

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for fname in files_to_backup:
                fpath = os.path.join(BASE_DIR, fname)
                if os.path.exists(fpath):
                    zipf.write(fpath, arcname=fname)

        logger.log_info(f"Резервная копия успешно создана: {zip_name}")
        cleanup_old_backups(retention_days=30)
        return zip_path
    except Exception as e:
        logger.log_error("Ошибка создания бэкапа", e)
        return ""


def cleanup_old_backups(retention_days: int = 30):
    """Removes backup files older than retention_days."""
    now = time.time()
    cutoff = now - (retention_days * 86400)
    for fname in os.listdir(BACKUP_DIR):
        if fname.startswith("crm_backup_") and fname.endswith(".zip"):
            fpath = os.path.join(BACKUP_DIR, fname)
            if os.path.getmtime(fpath) < cutoff:
                try:
                    os.remove(fpath)
                    logger.log_info(f"Удалён старый бэкап: {fname}")
                except Exception as e:
                    logger.log_error(f"Не удалось удалить старый бэкап {fname}", e)


if __name__ == "__main__":
    create_backup()
