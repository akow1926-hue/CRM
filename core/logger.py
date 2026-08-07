import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from config import settings

LOG_DIR = os.path.join(settings.BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "crm.log")

logger = logging.getLogger("CosmoCRM")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

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
    details_str = str(details) if details else ""
    log_msg = f"[AUDIT] User='{username}' Role='{role}' Action='{action}' TargetType='{target_type}' TargetID='{target_id}' IP='{ip_address}' Details='{details_str}'"
    logger.info(log_msg)

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
    except Exception:
        pass
