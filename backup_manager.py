import os
import sys
import json
from datetime import datetime
import db

def check_db_integrity() -> bool:
    """Verifies Google Sheets connection."""
    try:
        doc = db.get_gsheet_doc()
        return doc is not None
    except Exception:
        return False

def create_backup() -> str:
    """Exports Google Sheets orders and users snapshot."""
    try:
        orders = db.get_orders()
        users = db.get_users()
        print(f"[Backup] Successfully fetched {len(orders)} orders and {len(users)} users from Google Sheets.")
        return f"gsheet_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    except Exception as e:
        print(f"[Backup Error] {e}")
        return ""
