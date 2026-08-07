import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from database.db import get_db_connection, _db_lock, normalize_id
from config import settings


def sync_to_json_files():
    try:
        orders = get_orders()
        with open(settings.BACKUP_ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[JSON Sync Orders Error] {e}")


def get_orders() -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY rowid DESC;")
        rows = cursor.fetchall()
        conn.close()

    result = []
    for r in rows:
        result.append({
            "ID": normalize_id(r["id"]),
            "Дата": r["date"] or "",
            "Клиент": r["client"] or "",
            "Телефон": r["phone"] or "",
            "Адрес": r["address"] or "",
            "Район": r["district"] or "",
            "Язык": r["language"] or "",
            "Размеры": r["sizes"] or "",
            "Площадь": r["area"] or "0",
            "Сумма": r["total_price"] or "0",
            "Оплачено": r["paid_amount"] or "0",
            "Тип оплаты": r["payment_type"] or "-",
            "Статус": r["status"] or "Ожидает забора",
            "Курьер": r["courier"] or "",
            "Диспетчер": r["dispatcher"] or "",
            "Локация": r["location"] or "-",
            "Причина": r["debt_reason"] or "-"
        })
    return result


def get_order_by_id(order_id: Any) -> Optional[Dict[str, Any]]:
    target_id = normalize_id(order_id)
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?;", (target_id,))
        r = cursor.fetchone()
        conn.close()

    if not r:
        return None

    return {
        "ID": normalize_id(r["id"]),
        "Дата": r["date"] or "",
        "Клиент": r["client"] or "",
        "Телефон": r["phone"] or "",
        "Адрес": r["address"] or "",
        "Район": r["district"] or "",
        "Язык": r["language"] or "",
        "Размеры": r["sizes"] or "",
        "Площадь": r["area"] or "0",
        "Сумма": r["total_price"] or "0",
        "Оплачено": r["paid_amount"] or "0",
        "Тип оплаты": r["payment_type"] or "-",
        "Статус": r["status"] or "Ожидает забора",
        "Курьер": r["courier"] or "",
        "Диспетчер": r["dispatcher"] or "",
        "Локация": r["location"] or "-",
        "Причина": r["debt_reason"] or "-"
    }


def add_order(order_data: Dict[str, Any]) -> bool:
    target_id = normalize_id(order_data.get("ID"))
    if not target_id:
        orders = get_orders()
        max_id = 5218
        for o in orders:
            try:
                v = int(normalize_id(o.get("ID")))
                if v > max_id:
                    max_id = v
            except Exception:
                pass
        target_id = str(max_id + 1)

    order_data["ID"] = target_id
    now_str = datetime.now().isoformat()

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO orders (
                id, date, client, phone, address, district, language,
                sizes, area, total_price, paid_amount, payment_type,
                status, courier, dispatcher, location, debt_reason,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            target_id,
            str(order_data.get("Дата", datetime.now().strftime("%d.%m.%Y, %H:%M:%S"))),
            str(order_data.get("Клиент", "")),
            str(order_data.get("Телефон", "")),
            str(order_data.get("Адрес", "")),
            str(order_data.get("Район", "")),
            str(order_data.get("Язык", "")),
            str(order_data.get("Размеры", "")),
            str(order_data.get("Площадь", "0")),
            str(order_data.get("Сумма", "0")),
            str(order_data.get("Оплачено", "0")),
            str(order_data.get("Тип оплаты", "-")),
            str(order_data.get("Статус", "Ожидает забора")),
            str(order_data.get("Курьер", "")),
            str(order_data.get("Диспетчер", "")),
            str(order_data.get("Локация", "-")),
            str(order_data.get("Причина", "-")),
            now_str,
            now_str
        ))
        conn.commit()
        conn.close()

    sync_to_json_files()
    return True


def update_order(order_id: Any, updates: Dict[str, Any]) -> bool:
    target_id = normalize_id(order_id)
    existing = get_order_by_id(target_id)
    if not existing:
        return False

    mapping = {
        "Дата": "date", "Клиент": "client", "Телефон": "phone", "Адрес": "address",
        "Район": "district", "Язык": "language", "Размеры": "sizes", "Площадь": "area",
        "Сумма": "total_price", "Оплачено": "paid_amount", "Тип оплаты": "payment_type",
        "Статус": "status", "Курьер": "courier", "Диспетчер": "dispatcher",
        "Локация": "location", "Причина": "debt_reason"
    }

    set_clauses = []
    params = []
    for key, val in updates.items():
        col = mapping.get(key) or key.lower()
        set_clauses.append(f"{col} = ?")
        params.append(str(val) if val is not None else "")

    set_clauses.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(target_id)

    sql = f"UPDATE orders SET {', '.join(set_clauses)} WHERE id = ?;"

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        conn.close()

    sync_to_json_files()
    return True
