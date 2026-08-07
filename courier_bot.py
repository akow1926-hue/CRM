import os
import sys
from bots.courier.handlers import router, set_notify_dispatcher_hook
from bots.courier.keyboards import (
    get_courier_login_keyboard,
    get_courier_main_keyboard,
    get_courier_webapp_url
)
from webapp.api import (
    handle_webapp_index,
    handle_api_login,
    handle_api_orders,
    handle_api_update_status,
    handle_api_create_order,
    handle_api_update_location
)
from core import auth

def authenticate_courier(login: str, password: str):
    ok, user, _ = auth.authenticate_user(login, password)
    if ok and user:
        r = str(user.get("Role", "")).lower()
        if any(k in r for k in ["courier", "курьер", "доставщик", "admin", "админ"]):
            return {"username": user["Username"], "role": user["Role"], "telegram_id": user.get("TelegramID", "")}
    return None
