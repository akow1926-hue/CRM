import os
import sys
import json
from datetime import datetime
from database import db, orders_repo, users_repo

def check_db_integrity() -> bool:
    try:
        doc = db.get_gsheet_doc()
        return doc is not None
    except Exception:
        return False

def create_backup() -> str:
    try:
        orders = orders_repo.get_orders()
        users = users_repo.get_users()
        return f"gsheet_backup_{len(orders)}_orders"
    except Exception:
        return ""
