import re
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)
from config import settings

def get_courier_webapp_url() -> str:
    cfg = settings.load_telegram_config()
    if isinstance(cfg, dict) and cfg.get("courier_webapp_url"):
        url = str(cfg.get("courier_webapp_url")).strip()
        if url and "trycloudflare" not in url and "loca.lt" not in url:
            if "mode=" not in url:
                url = url.replace("/webapp", "").rstrip("/") + "/?mode=courier"
            return url
    return "https://crm-cosmo.streamlit.app/?mode=courier"


def get_courier_login_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🔑 Войти по логину и паролю")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_courier_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📥 Забор ковров"), KeyboardButton(text="📦 Готовые заказы")],
        [KeyboardButton(text="🚚 На доставку"), KeyboardButton(text="📋 Мои заказы")],
        [KeyboardButton(text="📍 Отправить моё GPS местоположение", request_location=True)],
        [KeyboardButton(text="🔍 Поиск заказа"), KeyboardButton(text="🚪 Выйти из аккаунта (/logout)")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def parse_coords(location_str: str, district: str = "") -> tuple | None:
    if location_str and isinstance(location_str, str):
        numbers = re.findall(r"[0-9]+\.[0-9]+", location_str)
        if len(numbers) >= 2:
            n1, n2 = float(numbers[0]), float(numbers[1])
            if 30.0 <= n1 <= 45.0 and 60.0 <= n2 <= 75.0:
                return n1, n2, True
            elif 60.0 <= n1 <= 75.0 and 30.0 <= n2 <= 45.0:
                return n2, n1, True
    return None


def get_order_inline_actions(order_id: str | int, status: str, address: str, district: str, location_str: str = "") -> InlineKeyboardMarkup:
    st_clean = str(status).lower()
    buttons = []
    norm_id = str(order_id)

    parsed = parse_coords(location_str, district)
    if parsed:
        lat, lng, _ = parsed
        navi_url = f"https://yandex.ru/navi/?rtext=~{lat},{lng}"
        ymaps_url = f"https://yandex.ru/maps/?rtext=~{lat},{lng}&rtt=auto"
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
        buttons.append([
            InlineKeyboardButton(text="🧭 Я.Навигатор", url=navi_url),
            InlineKeyboardButton(text="🗺️ Я.Карты", url=ymaps_url),
            InlineKeyboardButton(text="📍 Google Maps", url=gmaps_url)
        ])

    if "забор" in st_clean or "ожид" in st_clean:
        buttons.append([InlineKeyboardButton(text="🚗 Взять на забор", callback_data=f"cour_claim_{norm_id}")])
        buttons.append([InlineKeyboardButton(text="📍 Привязать GPS", callback_data=f"cour_loc_{norm_id}")])
    elif "цех" in st_clean or "мойка" in st_clean:
        buttons.append([InlineKeyboardButton(text="📏 Указать замеры", callback_data=f"cour_measure_{norm_id}")])
        buttons.append([InlineKeyboardButton(text="📦 Готов к доставке", callback_data=f"cour_ready_{norm_id}")])
    elif "доставк" in st_clean or "готов" in st_clean:
        buttons.append([InlineKeyboardButton(text="✅ Завершить заказ", callback_data=f"cour_finish_{norm_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
