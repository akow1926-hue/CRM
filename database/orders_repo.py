import json
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from database.db import _db_lock, normalize_id, get_worksheet_safe, add_audit_log

_orders_cache: List[Dict[str, Any]] = []
_last_fetch_time = 0
CACHE_TTL = 15  # seconds cache for instant response with auto-refresh


def sync_to_json_files():
    # Deprecated backup sync - no longer using local files
    pass


def _row_to_order_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    raw_id = r.get("ID Заказа") or r.get("ID") or r.get("id") or ""
    return {
        "ID": normalize_id(raw_id),
        "Дата": str(r.get("Дата") or r.get("date") or ""),
        "Клиент": str(r.get("Клиент") or r.get("client") or ""),
        "Телефон": str(r.get("Телефон") or r.get("phone") or ""),
        "Адрес": str(r.get("Адрес") or r.get("address") or ""),
        "Район": str(r.get("Район") or r.get("district") or ""),
        "Язык": str(r.get("Язык") or r.get("language") or "ru"),
        "Размеры": str(r.get("Размеры") or r.get("sizes") or ""),
        "Площадь": str(r.get("Площадь (м²)") or r.get("Площадь") or r.get("area") or "0"),
        "Сумма": str(r.get("Сумма (сум)") or r.get("Сумма") or r.get("total_price") or "0"),
        "Оплачено": str(r.get("Оплачено (сум)") or r.get("Оплачено") or r.get("paid_amount") or "0"),
        "Тип оплаты": str(r.get("Тип оплаты") or r.get("payment_type") or "-"),
        "Статус": str(r.get("Статус") or r.get("status") or "Ожидает забора"),
        "Курьер": str(r.get("Курьер") or r.get("courier") or ""),
        "Диспетчер": str(r.get("Диспетчер") or r.get("dispatcher") or ""),
        "Локация": str(r.get("Локация") or r.get("location") or "-"),
        "Причина": str(r.get("Причина") or r.get("debt_reason") or "-")
    }


def _order_dict_to_row(o: Dict[str, Any]) -> List[Any]:
    return [
        str(o.get("ID", "")),
        str(o.get("Дата", datetime.now().strftime("%d.%m.%Y, %H:%M:%S"))),
        str(o.get("Клиент", "")),
        str(o.get("Телефон", "")),
        str(o.get("Адрес", "")),
        str(o.get("Размеры", "")),
        str(o.get("Площадь", "0")),
        str(o.get("Сумма", "0")),
        str(o.get("Статус", "Ожидает забора")),
        str(o.get("Курьер", "")),
        str(o.get("Диспетчер", "")),
        str(o.get("Район", "")),
        str(o.get("Оплачено", "0")),
        str(o.get("Тип оплаты", "-")),
        str(o.get("Статус оплаты", "unpaid" if str(o.get("Оплачено", "0")) in ["0", ""] else "paid")),
        str(o.get("Кол-во предметов", "1")),
        str(o.get("Комментарий", "")),
        str(o.get("Язык", "ru")),
        str(o.get("Локация", "-")),
        str(o.get("Причина", "-"))
    ]


def get_orders(force_refresh: bool = False) -> List[Dict[str, Any]]:
    global _orders_cache, _last_fetch_time
    now = datetime.now().timestamp()

    with _db_lock:
        if not force_refresh and _orders_cache and (now - _last_fetch_time < CACHE_TTL):
            return list(_orders_cache)

    try:
        ws = get_worksheet_safe("Заказы")
        if ws:
            records = ws.get_all_records()
            orders = []
            for r in records:
                order_item = _row_to_order_dict(r)
                if order_item["ID"]:
                    orders.append(order_item)

            with _db_lock:
                _orders_cache = orders
                _last_fetch_time = now
            return list(orders)
    except Exception as e:
        print(f"[Google Sheets get_orders Error] {e}")

    with _db_lock:
        return list(_orders_cache)


def get_order_by_id(order_id: Any) -> Optional[Dict[str, Any]]:
    target_id = normalize_id(order_id)
    if not target_id:
        return None

    orders = get_orders()
    for o in orders:
        if normalize_id(o.get("ID")) == target_id:
            return dict(o)

    # Secondary lookup if not in cache
    try:
        ws = get_worksheet_safe("Заказы")
        if ws:
            cell = ws.find(target_id, in_column=1)
            if cell:
                headers = ws.row_values(1)
                row_vals = ws.row_values(cell.row)
                row_dict = dict(zip(headers, row_vals))
                return _row_to_order_dict(row_dict)
    except Exception:
        pass

    return None


def add_order(order_data: Dict[str, Any]) -> bool:
    global _orders_cache
    target_id = normalize_id(order_data.get("ID"))

    orders = get_orders()
    if not target_id:
        max_id = 5500
        for o in orders:
            try:
                v = int(normalize_id(o.get("ID")))
                if v > max_id:
                    max_id = v
            except Exception:
                pass
        target_id = str(max_id + 1)
        order_data["ID"] = target_id

    clean_order = _row_to_order_dict(order_data)
    clean_order["ID"] = target_id

    # Immediate cache update
    with _db_lock:
        _orders_cache = [o for o in _orders_cache if normalize_id(o.get("ID")) != target_id]
        _orders_cache.insert(0, clean_order)

    def _async_add_sheet():
        try:
            ws = get_worksheet_safe("Заказы")
            if ws:
                row_vals = _order_dict_to_row(clean_order)
                ws.append_row(row_vals)
                add_audit_log("Система", "Администратор", f"Создан заказ #{target_id}", f"Клиент: {clean_order.get('Клиент')}")
        except Exception as e:
            print(f"[Google Sheets add_order Error] {e}")

    threading.Thread(target=_async_add_sheet, daemon=True).start()
    return True


def update_order(order_id: Any, updates: Dict[str, Any]) -> bool:
    global _orders_cache
    target_id = normalize_id(order_id)
    if not target_id:
        return False

    with _db_lock:
        found = False
        for idx, o in enumerate(_orders_cache):
            if normalize_id(o.get("ID")) == target_id:
                for k, v in updates.items():
                    o[k] = v
                found = True
                break

    def _async_update_sheet():
        try:
            ws = get_worksheet_safe("Заказы")
            if ws:
                cell = ws.find(str(target_id), in_column=1)
                row_idx = None
                if cell:
                    row_idx = cell.row
                else:
                    col1 = ws.col_values(1)
                    for i, val in enumerate(col1[1:], start=2):
                        if normalize_id(val) == target_id:
                            row_idx = i
                            break

                if row_idx is not None:
                    headers = [h.strip() for h in ws.row_values(1)]
                    for col_name, val in updates.items():
                        # Try exact match and alias match
                        matched_idx = None
                        if col_name in headers:
                            matched_idx = headers.index(col_name) + 1
                        else:
                            alias_map = {
                                "Сумма": "Сумма (сум)",
                                "Площадь": "Площадь (м²)",
                                "Оплачено": "Оплачено (сум)",
                                "ID": "ID Заказа"
                            }
                            target_header = alias_map.get(col_name)
                            if target_header and target_header in headers:
                                matched_idx = headers.index(target_header) + 1

                        if matched_idx is not None:
                            ws.update_cell(row_idx, matched_idx, str(val) if val is not None else "")
        except Exception as e:
            print(f"[Google Sheets update_order Error] {e}")

    threading.Thread(target=_async_update_sheet, daemon=True).start()
    return True


def delete_order(order_id: Any) -> bool:
    global _orders_cache
    target_id = normalize_id(order_id)
    if not target_id:
        return False

    with _db_lock:
        _orders_cache = [o for o in _orders_cache if normalize_id(o.get("ID")) != target_id]

    def _async_delete_sheet():
        try:
            ws = get_worksheet_safe("Заказы")
            if ws:
                cell = ws.find(str(target_id), in_column=1)
                if cell:
                    ws.delete_rows(cell.row)
        except Exception as e:
            print(f"[Google Sheets delete_order Error] {e}")

    threading.Thread(target=_async_delete_sheet, daemon=True).start()
    return True
