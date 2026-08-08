import os
import sys
import json
from datetime import datetime
import db

def normalize_id(val) -> str:
    return db.normalize_id(val)

def load_orders_from_file() -> list:
    return db.get_orders()

def save_orders_to_file(orders: list) -> bool:
    for o in orders:
        db.add_order(o)
    return True

def get_orders() -> list:
    return db.get_orders()

def get_order_by_id(order_id):
    return db.get_order_by_id(order_id)

def update_order(order_id: str | int, updates: dict) -> bool:
    return db.update_order(order_id, updates)

def add_order(order_data: dict) -> bool:
    return db.add_order(order_data)

def delete_order(order_id) -> bool:
    return db.delete_order(order_id)
