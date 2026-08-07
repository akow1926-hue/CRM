import os
import sys
from bots.dispatcher.handlers import router, set_notify_courier_hook
from bots.dispatcher.keyboards import (
    get_dispatcher_login_keyboard,
    get_dispatcher_main_keyboard,
    get_dispatcher_webapp_url
)
from core import auth

def authenticate_dispatcher(login: str, password: str):
    ok, user, _ = auth.authenticate_user(login, password)
    if ok and user:
        r = str(user.get("Role", "")).lower()
        if any(k in r for k in ["dispatcher", "диспетчер", "admin", "админ"]):
            return {"username": user["Username"], "role": user["Role"], "telegram_id": user.get("TelegramID", "")}
    return None
