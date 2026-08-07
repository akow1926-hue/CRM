import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Dict, Any

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "crm.log")

# Setup root logger
logger = logging.getLogger("CosmoCRM")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # File handler with rotation (max 5 MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def log_info(msg: str):
    logger.info(msg)


def log_warning(msg: str):
    logger.warning(msg)


def log_error(msg: str, exc: Optional[Exception] = None):
    if exc:
        logger.error(f"{msg}: {exc}", exc_info=True)
    else:
        logger.error(msg)


def log_audit(username: str, role: str, action: str, target_type: str = "order", target_id: str = "", details: Optional[Dict[str, Any]] = None, ip_address: str = ""):
    """
    Logs user audit events both to the log file and to the SQLite database.
    """
    details_str = str(details) if details else ""
    log_msg = f"[AUDIT] User='{username}' Role='{role}' Action='{action}' TargetType='{target_type}' TargetID='{target_id}' IP='{ip_address}' Details='{details_str}'"
    logger.info(log_msg)

    # Save to SQLite audit_logs table via db module if imported
    try:
        import db
        db.add_audit_log(
            username=username,
            role=role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address
        )
    except Exception as e:
        logger.warning(f"Could not persist audit log to DB: {e}")
