import os
import sys
import json
import re
from datetime import datetime

CONFIG_FILE = "telegram_config.json"
BACKUP_FILE = "backup_orders.json"
GSHEET_CONFIG_FILE = "gsheet_config.json"
KEY_FILE = "key.json"

def normalize_id(val) -> str:
    if val is None or val == "":
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.startswith("TG-") or s.startswith("tg-"):
        s = s[3:]
    return s

def load_orders_from_file() -> list:
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for o in data:
                        if isinstance(o, dict) and "ID" in o:
                            o["ID"] = normalize_id(o["ID"])
                    return data
        except Exception as e:
            print(f"[JSON Load Error] {e}")
    return []

def save_orders_to_file(orders: list) -> bool:
    try:
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[JSON Save Error] {e}")
        return False

def connect_gsheet():
    if not os.path.exists(KEY_FILE):
        return None, None
    try:
        import gspread
        client = gspread.service_account(filename=KEY_FILE)
        gsheet_url = "https://docs.google.com/spreadsheets/d/1zYbTgS1aQc-1aeP0EeAo-KeohbTAyGYumJLQQxmBZRk/edit"
        if os.path.exists(GSHEET_CONFIG_FILE):
            try:
                with open(GSHEET_CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if cfg.get("gsheet_url"):
                        gsheet_url = cfg.get("gsheet_url").strip()
            except Exception:
                pass
        db = client.open_by_url(gsheet_url)
        sheet = db.sheet1
        return db, sheet
    except Exception as e:
        print(f"[GSheet Connect Error] {e}")
        return None, None

def get_orders() -> list:
    """Returns clean orders, syncing from Google Sheets if available"""
    db, sheet = connect_gsheet()
    if sheet is not None:
        try:
            records = sheet.get_all_records()
            if records and isinstance(records, list):
                clean_records = []
                for r in records:
                    r_dict = dict(r)
                    if "ID" in r_dict:
                        r_dict["ID"] = normalize_id(r_dict["ID"])
                    clean_records.append(r_dict)
                save_orders_to_file(clean_records)
                return clean_records
        except Exception as e:
            print(f"[GSheet Fetch Warning] {e}")
    return load_orders_from_file()

def update_order(order_id: str | int, updates: dict) -> bool:
    """Updates order in backup_orders.json AND in Google Sheets"""
    target_id = normalize_id(order_id)
    orders = load_orders_from_file()
    found = False

    for o in orders:
        if normalize_id(o.get("ID")) == target_id:
            for k, v in updates.items():
                o[k] = v
            found = True
            break

    if found:
        save_orders_to_file(orders)

    # Sync update to Google Sheets
    db, sheet = connect_gsheet()
    if sheet is not None:
        try:
            row = None
            try:
                cell = sheet.find(str(target_id), in_column=1)
                if cell:
                    row = cell.row
            except Exception:
                pass

            if row is None:
                try:
                    col1_values = sheet.col_values(1)
                    for idx, cell_val in enumerate(col1_values[1:], start=2):
                        if normalize_id(cell_val) == target_id:
                            row = idx
                            break
                except Exception:
                    pass

            if row is not None:
                headers = [str(h).strip() for h in sheet.row_values(1)]
                for col_name, val in updates.items():
                    if col_name in headers:
                        col_idx = headers.index(col_name) + 1
                        sheet.update_cell(row, col_idx, str(val) if val is not None else "")
        except Exception as e:
            print(f"[GSheet Update Warning] {e}")

    return found

def add_order(order_data: dict) -> bool:
    """Adds a new order to backup_orders.json AND Google Sheets"""
    orders = load_orders_from_file()
    new_id = order_data.get("ID")
    if not new_id:
        max_id = 5218
        for o in orders:
            try:
                v = int(normalize_id(o.get("ID")))
                if v > max_id:
                    max_id = v
            except Exception:
                pass
        new_id = str(max_id + 1)
    order_data["ID"] = normalize_id(new_id)

    orders.insert(0, order_data)
    save_orders_to_file(orders)

    db, sheet = connect_gsheet()
    if sheet is not None:
        try:
            sheet.append_row([
                order_data.get("ID", ""),
                order_data.get("Дата", datetime.now().strftime("%d.%m.%Y, %H:%M:%S")),
                order_data.get("Клиент", ""),
                order_data.get("Телефон", ""),
                order_data.get("Адрес", ""),
                order_data.get("Размеры", ""),
                order_data.get("Площадь", "0"),
                order_data.get("Сумма", "0"),
                order_data.get("Статус", "Ожидает забора"),
                order_data.get("Курьер", ""),
                order_data.get("Диспетчер", ""),
                order_data.get("Район", ""),
                order_data.get("Язык", ""),
                order_data.get("Локация", "-"),
                order_data.get("Оплачено", "0"),
                order_data.get("Тип оплаты", "-"),
                order_data.get("Причина", "-")
            ])
        except Exception as e:
            print(f"[GSheet Add Order Warning] {e}")

    return True
