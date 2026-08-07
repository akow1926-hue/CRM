from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)
from config import settings

def get_dispatcher_webapp_url() -> str:
    cfg = settings.load_telegram_config()
    if isinstance(cfg, dict) and cfg.get("dispatcher_webapp_url"):
        url = str(cfg.get("dispatcher_webapp_url")).strip()
        if url and "trycloudflare" not in url and "loca.lt" not in url:
            if "mode=" not in url:
                url = url.rstrip("/") + "/?mode=dispatcher"
            return url
    return "https://crm-cosmo.streamlit.app/?mode=dispatcher"


def get_dispatcher_login_keyboard() -> ReplyKeyboardMarkup:
    kb = []
    url = get_dispatcher_webapp_url()
    if url.startswith("https://"):
        kb.append([KeyboardButton(text="🖥️ Открыть CRM Диспетчера", web_app=WebAppInfo(url=url))])
    kb.append([KeyboardButton(text="🔑 Войти по логину и паролю")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_dispatcher_main_keyboard() -> ReplyKeyboardMarkup:
    kb = []
    url = get_dispatcher_webapp_url()
    if url.startswith("https://"):
        kb.append([KeyboardButton(text="🖥️ Открыть CRM Диспетчера", web_app=WebAppInfo(url=url))])
    
    kb.append([KeyboardButton(text="➕ Создать заказ"), KeyboardButton(text="📋 Все заказы")])
    kb.append([KeyboardButton(text="🚚 Назначить курьера"), KeyboardButton(text="🔍 Поиск заказа")])
    kb.append([KeyboardButton(text="🚪 Выйти из аккаунта (/logout)")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
