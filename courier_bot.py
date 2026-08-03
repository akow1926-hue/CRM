import os
import sys
import json
import re
import asyncio
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    MenuButtonWebApp,
    Message,
    CallbackQuery,
    BufferedInputFile
)

import orders_db
import receipt_generator

# utf-8 for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()

CONFIG_FILE = "telegram_config.json"
BACKUP_FILE = "backup_orders.json"
USERS_BACKUP_FILE = "backup_users.json"
SESSIONS_FILE = "telegram_sessions.json"

def load_json_file(filename: str, default: dict | list) -> dict | list:
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[JSON Error] Ошибка чтения {filename}: {e}")
    return default

def get_courier_webapp_url() -> str:
    cfg = load_json_file(CONFIG_FILE, {})
    if isinstance(cfg, dict) and cfg.get("courier_webapp_url"):
        url = str(cfg.get("courier_webapp_url")).strip()
        if url and "trycloudflare" not in url and "loca.lt" not in url:
            if "mode=" not in url:
                url = url.replace("/webapp", "").rstrip("/") + "/?mode=courier"
            return url

    render_url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("WEBAPP_URL") or os.environ.get("COURIER_WEBAPP_URL")
    if render_url and "trycloudflare" not in render_url:
        url = render_url.replace("/webapp", "").rstrip("/")
        return url + "/?mode=courier"

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            sec_url = st.secrets.get("courier_webapp_url") or st.secrets.get("WEBAPP_URL") or st.secrets.get("telegram", {}).get("courier_webapp_url")
            if sec_url and "trycloudflare" not in str(sec_url):
                url = str(sec_url).replace("/webapp", "").rstrip("/")
                return url + "/?mode=courier"
    except Exception:
        pass

    return "https://crm-cosmo.streamlit.app/?mode=courier"

COURIER_WEBAPP_URL = get_courier_webapp_url()

def save_json_file(filename: str, data: dict | list) -> bool:
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[JSON Error] Ошибка записи {filename}: {e}")
        return False

def authenticate_courier(login: str, password: str) -> Optional[dict]:
    users = load_json_file(USERS_BACKUP_FILE, [])
    if isinstance(users, list):
        l_clean = str(login).strip().lower()
        p_clean = str(password).strip()
        for u in users:
            u_name = str(u.get("Username") or u.get("username") or u.get("Login") or u.get("login") or "").strip()
            u_pass = str(u.get("Password") or u.get("password") or u.get("Pass") or u.get("pass") or "").strip()
            u_status = str(u.get("Status") or u.get("status") or "Активен").strip()
            u_role = str(u.get("Role") or u.get("role") or "").strip()

            if u_name.lower() == l_clean and u_pass == p_clean and u_status != "Заблокирован":
                if is_courier_role(u_role) or "admin" in u_role.lower() or "админ" in u_role.lower():
                    return {"username": u_name, "role": u_role}
    return None

def is_courier_role(role: str) -> bool:
    r = str(role).lower()
    return any(k in r for k in ["courier", "курьер", "доставщик", "yuboruvchi", "kuryer", "admin", "админ", "диспетчер", "dispatcher"])

def get_next_order_id() -> int:
    orders = orders_db.get_orders()
    max_id = 5218
    if isinstance(orders, list):
        for o in orders:
            try:
                val = int(float(orders_db.normalize_id(o.get("ID", 0))))
                if val > max_id:
                    max_id = val
            except Exception:
                pass
    return max_id + 1

def format_phone(raw_phone: str) -> str:
    digits = ''.join(filter(str.isdigit, raw_phone))
    if len(digits) >= 9:
        last9 = digits[-9:]
        return f"+998 {last9[:2]} {last9[2:5]} {last9[5:7]} {last9[7:]}"
    return raw_phone

def get_yandex_nav_url(address: str, district: str, location_str: str = "") -> str:
    if location_str and ("39." in location_str or "40." in location_str):
        try:
            coords = re.findall(r"\d+\.\d+", location_str)
            if len(coords) >= 2:
                lat, lng = coords[0], coords[1]
                return f"https://yandex.ru/maps/?rtext=~{lat},{lng}&rtt=auto"
        except Exception:
            pass
    full_addr = f"Самарканд {district} {address}".strip()
    encoded = urllib.parse.quote(full_addr)
    return f"https://yandex.ru/maps/?text={encoded}"

def get_courier_login_keyboard() -> ReplyKeyboardMarkup:
    kb = []
    url = get_courier_webapp_url()
    if url.startswith("https://"):
        kb.append([KeyboardButton(text="📱 Открыть WebApp Курьера", web_app=WebAppInfo(url=url))])
    kb.append([KeyboardButton(text="🔑 Войти по логину и паролю")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_courier_main_keyboard() -> ReplyKeyboardMarkup:
    kb = []
    url = get_courier_webapp_url()
    if url.startswith("https://"):
        kb.append([KeyboardButton(text="📱 Открыть WebApp Курьера", web_app=WebAppInfo(url=url))])
    
    kb.append([KeyboardButton(text="📥 Забор ковров"), KeyboardButton(text="🚚 Доставка ковров")])
    kb.append([KeyboardButton(text="➕ Новый заказ"), KeyboardButton(text="📋 Мои заказы")])
    kb.append([KeyboardButton(text="🔍 Поиск заказа"), KeyboardButton(text="🚪 Выйти из аккаунта (/logout)")])
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
    norm_id = orders_db.normalize_id(order_id)

    parsed = parse_coords(location_str, district)
    if parsed:
        lat, lng, _ = parsed
        navi_url = f"yandexnavi://build_route_on_map?lat_to={lat}&lon_to={lng}"
        ymaps_url = f"https://yandex.ru/maps/?rtext=~{lat},{lng}&rtt=auto"
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
        buttons.append([
            InlineKeyboardButton(text="🧭 Я.Навигатор", url=navi_url),
            InlineKeyboardButton(text="🗺️ Я.Карты", url=ymaps_url),
            InlineKeyboardButton(text="📍 Google Maps", url=gmaps_url)
        ])
    else:
        full_addr = f"Самарканд {district} {address}".strip()
        encoded = urllib.parse.quote(full_addr)
        ymaps_url = f"https://yandex.ru/maps/?text={encoded}"
        buttons.append([InlineKeyboardButton(text="🗺️ Открыть адрес в Я.Картах", url=ymaps_url)])

    if "забор" in st_clean or "ожид" in st_clean or "нов" in st_clean:
        buttons.append([
            InlineKeyboardButton(text="🚗 Забрать в цех", callback_data=f"cour_st_shop_{norm_id}"),
            InlineKeyboardButton(text="📍 Зафиксировать GPS", callback_data=f"cour_loc_{norm_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="🧺 Указать детали/кол-во", callback_data=f"cour_items_{norm_id}")
        ])
    elif "готов" in st_clean or "достав" in st_clean:
        buttons.append([
            InlineKeyboardButton(text="🧭 Маршрут до клиента", callback_data=f"cour_route_{norm_id}"),
            InlineKeyboardButton(text="🧾 Выдать чек", callback_data=f"cour_receipt_{norm_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="💵 Доставлено (Наличные)", callback_data=f"cour_pay_cash_{norm_id}"),
            InlineKeyboardButton(text="💳 Доставлено (Карта/Click)", callback_data=f"cour_pay_card_{norm_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="📦 Изменить статус", callback_data=f"cour_edit_st_{norm_id}")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Callback hook for notify dispatcher
notify_dispatcher_func = None

def set_notify_dispatcher_hook(fn):
    global notify_dispatcher_func
    notify_dispatcher_func = fn

async def clean_previous_messages(bot: Bot, chat_id: int | str, delete_incoming_id: int = None):
    """Стирает старые сообщения бота в чате для поддержания чистоты и аккуратности"""
    chat_id_str = str(chat_id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id_str, {})
    old_msg_ids = sess.get("last_msg_ids", [])

    if delete_incoming_id:
        try:
            await bot.delete_message(chat_id, delete_incoming_id)
        except Exception:
            pass

    for mid in list(old_msg_ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    sess["last_msg_ids"] = []
    sessions[chat_id_str] = sess
    save_json_file(SESSIONS_FILE, sessions)

def register_sent_message_id(chat_id: int | str, msg_id: int):
    chat_id_str = str(chat_id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id_str, {})
    old = sess.get("last_msg_ids", [])
    if not isinstance(old, list):
        old = []
    if msg_id not in old:
        old.append(msg_id)
    sess["last_msg_ids"] = old[-20:]
    sessions[chat_id_str] = sess
    save_json_file(SESSIONS_FILE, sessions)

async def send_clean_message(bot: Bot, chat_id: int | str, text: str, reply_markup=None, parse_mode="Markdown", delete_incoming_id: int = None, keep_old: bool = False) -> Message:
    if not keep_old:
        await clean_previous_messages(bot, chat_id, delete_incoming_id=delete_incoming_id)
    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    register_sent_message_id(chat_id, sent.message_id)
    return sent

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    chat_id = str(message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    sess.pop("state", None)
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)

    cour_url = get_courier_webapp_url()
    try:
        if cour_url.startswith("https://"):
            await bot.set_chat_menu_button(
                chat_id=message.chat.id,
                menu_button=MenuButtonWebApp(text="📱 WebApp Курьера", web_app=WebAppInfo(url=cour_url))
            )
    except Exception as e:
        print(f"[Courier MenuButton Warning] {e}")

    username = sess.get("cour_username") or (sess.get("username") if is_courier_role(sess.get("role", "")) else None)
    role = sess.get("cour_role") or (sess.get("role") if is_courier_role(sess.get("role", "")) else None)

    # Save courier chat_id mapping in config
    cfg = load_json_file(CONFIG_FILE, {})
    courier_chats = cfg.get("courier_chats", {})
    if username:
        courier_chats[username.lower()] = chat_id
        cfg["courier_chats"] = courier_chats
        save_json_file(CONFIG_FILE, cfg)

    if username and role and is_courier_role(role):
        welcome_text = (
            f"🚚 **Cosmo CRM — Бот Курьера**\n\n"
            f"👤 **Вы авторизованы как:** `{username}` ({role})\n\n"
            f"🌐 **WebApp Курьера:** {cour_url}"
        )
        await send_clean_message(bot, message.chat.id, welcome_text, reply_markup=get_courier_main_keyboard(), delete_incoming_id=message.message_id)
    else:
        auth_msg = (
            "🔒 **Cosmo CRM — Бот Курьера**\n\n"
            f"🌐 **WebApp Курьера:** {cour_url}\n\n"
            "Пожалуйста, авторизуйтесь. Введите `логин пароль` через пробел или нажмите кнопку **🔑 Войти по логину и паролю**."
        )
        await send_clean_message(bot, message.chat.id, auth_msg, reply_markup=get_courier_login_keyboard(), delete_incoming_id=message.message_id)

@router.message(Command("logout"))
async def cmd_logout(message: Message, bot: Bot):
    chat_id = str(message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    if chat_id in sessions:
        u_name = sessions[chat_id].get("cour_username") or sessions[chat_id].get("username")
        sessions[chat_id].pop("cour_username", None)
        sessions[chat_id].pop("cour_role", None)
        sessions.pop(chat_id, None)
        save_json_file(SESSIONS_FILE, sessions)
        if u_name:
            cfg = load_json_file(CONFIG_FILE, {})
            c_chats = cfg.get("courier_chats", {})
            c_chats.pop(u_name.lower(), None)
            cfg["courier_chats"] = c_chats
            save_json_file(CONFIG_FILE, cfg)

    await send_clean_message(bot, message.chat.id, "🚪 **Вы вышли из системы Курьера.**\n\n🔑 Введите `логин пароль` через пробел или нажмите **Войти по логину и паролю** для нового входа:", reply_markup=get_courier_login_keyboard(), delete_incoming_id=message.message_id)

@router.message(Command("login"))
async def cmd_login(message: Message, bot: Bot):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await send_clean_message(bot, message.chat.id, "⚠️ Формат входа: `/login логин пароль`", delete_incoming_id=message.message_id)
        return

    login_in, pass_in = args[1], args[2]
    auth_data = authenticate_courier(login_in, pass_in)

    if auth_data:
        chat_id = str(message.chat.id)
        sessions = load_json_file(SESSIONS_FILE, {})
        sess = sessions.get(chat_id, {})
        sess["cour_username"] = auth_data["username"]
        sess["cour_role"] = auth_data["role"]
        sess["login_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        cfg = load_json_file(CONFIG_FILE, {})
        courier_chats = cfg.get("courier_chats", {})
        courier_chats[auth_data["username"].lower()] = chat_id
        cfg["courier_chats"] = courier_chats
        save_json_file(CONFIG_FILE, cfg)

        cour_url = get_courier_webapp_url()
        if cour_url.startswith("https://"):
            try:
                await bot.set_chat_menu_button(
                    chat_id=message.chat.id,
                    menu_button=MenuButtonWebApp(text="📱 WebApp Курьера", web_app=WebAppInfo(url=cour_url))
                )
            except Exception:
                pass

        await send_clean_message(
            bot,
            message.chat.id,
            f"✅ **Успешная авторизация!**\nПриветствуем, курьер `{auth_data['username']}`!\n\n🌐 **WebApp:** {cour_url}",
            reply_markup=get_courier_main_keyboard(),
            delete_incoming_id=message.message_id
        )
    else:
        await send_clean_message(bot, message.chat.id, "❌ Ошибка входа: у вас нет прав Курьера или неверный логин/пароль!", reply_markup=get_courier_login_keyboard(), delete_incoming_id=message.message_id)

@router.message(F.text)
async def handle_courier_messages(message: Message, bot: Bot):
    text = message.text.strip()
    chat_id = str(message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    username = sess.get("cour_username") or (sess.get("username") if is_courier_role(sess.get("role", "")) else None)
    role = sess.get("cour_role") or (sess.get("role") if is_courier_role(sess.get("role", "")) else None)
    state = sess.get("state", "")
    cour_url = get_courier_webapp_url()

    if not username or not is_courier_role(role):
        if text == "🔑 Войти по логину и паролю":
            sess["state"] = "awaiting_login"
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)
            await send_clean_message(bot, message.chat.id, "👤 Введите ваш **логин** курьера:", delete_incoming_id=message.message_id)
            return

        if state == "awaiting_login":
            sess["temp_login"] = text
            sess["state"] = "awaiting_password"
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)
            await send_clean_message(bot, message.chat.id, "🔑 Введите ваш **пароль**:", delete_incoming_id=message.message_id)
            return

        if state == "awaiting_password":
            l_val = sess.get("temp_login", "")
            p_val = text
            auth_data = authenticate_courier(l_val, p_val)
            sess.pop("temp_login", None)
            sess.pop("state", None)

            if auth_data:
                sess["cour_username"] = auth_data["username"]
                sess["cour_role"] = auth_data["role"]
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)

                cfg = load_json_file(CONFIG_FILE, {})
                courier_chats = cfg.get("courier_chats", {})
                courier_chats[auth_data["username"].lower()] = chat_id
                cfg["courier_chats"] = courier_chats
                save_json_file(CONFIG_FILE, cfg)

                await send_clean_message(
                    bot,
                    message.chat.id,
                    f"✅ **Успешный вход!**\nС возвращением, курьер `{auth_data['username']}`!\n\n🌐 **WebApp:** {cour_url}",
                    reply_markup=get_courier_main_keyboard(),
                    delete_incoming_id=message.message_id
                )
            else:
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)
                await send_clean_message(bot, message.chat.id, "❌ Неверный логин или пароль!", reply_markup=get_courier_login_keyboard(), delete_incoming_id=message.message_id)
            return

        words = text.split()
        if len(words) == 2 and not text.startswith("/"):
            auth_data = authenticate_courier(words[0], words[1])
            if auth_data:
                sess["cour_username"] = auth_data["username"]
                sess["cour_role"] = auth_data["role"]
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)

                cfg = load_json_file(CONFIG_FILE, {})
                courier_chats = cfg.get("courier_chats", {})
                courier_chats[auth_data["username"].lower()] = chat_id
                cfg["courier_chats"] = courier_chats
                save_json_file(CONFIG_FILE, cfg)

                await send_clean_message(
                    bot,
                    message.chat.id,
                    f"✅ **Успешный вход!**\nКурьер: `{auth_data['username']}`\n\n🌐 **WebApp:** {cour_url}",
                    reply_markup=get_courier_main_keyboard(),
                    delete_incoming_id=message.message_id
                )
                return

        await send_clean_message(bot, message.chat.id, f"🔒 Пожалуйста, войдите в систему курьера. Введите `логин пароль`.", reply_markup=get_courier_login_keyboard(), delete_incoming_id=message.message_id)
        return

    if text in ["🚪 Выйти из аккаунта (/logout)", "/logout", "Выйти"]:
        await cmd_logout(message, bot)
        return

    if text in ["📥 Забор ковров", "Забор"]:
        orders = orders_db.get_orders()
        pickup_orders = [
            o for o in orders
            if any(w in str(o.get("Статус", "")).lower() for w in ["забор", "ожид", "нов"])
            and not any(w in str(o.get("Статус", "")).lower() for w in ["цех", "цеху", "цехе", "мойк", "готов", "выполн"])
        ]
        if not pickup_orders:
            await send_clean_message(bot, message.chat.id, "📭 На данный момент нет новых заявок на забор ковров.", delete_incoming_id=message.message_id)
            return

        await clean_previous_messages(bot, message.chat.id, delete_incoming_id=message.message_id)
        h_msg = await bot.send_message(message.chat.id, f"📥 <b>Заявки на забор ({len(pickup_orders)} шт.):</b>", parse_mode="HTML")
        register_sent_message_id(message.chat.id, h_msg.message_id)

        for o in pickup_orders[:10]:
            o_id = orders_db.normalize_id(o.get("ID"))
            c_name = html.escape(str(o.get('Клиент', '-')))
            p_phone = format_phone(str(o.get('Телефон', '-')))
            c_dist = html.escape(str(o.get('Район', 'Самарканд')))
            c_addr = html.escape(str(o.get('Адрес', '-')))
            c_items = html.escape(str(o.get('Размеры', '-')))

            card = (
                f"📥 <b>ЗАБОР №{o_id}</b>\n\n"
                f"👤 <b>Клиент:</b> {c_name}\n"
                f"📞 <b>Тел:</b> <code>{p_phone}</code>\n"
                f"🏠 <b>Адрес:</b> {c_dist}, {c_addr}\n"
                f"🧺 <b>Детали:</b> {c_items}"
            )
            actions_kb = get_order_inline_actions(o_id, o.get("Статус", "Забор"), o.get("Адрес", ""), o.get("Район", ""), o.get("Локация", ""))
            try:
                c_msg = await bot.send_message(message.chat.id, card, reply_markup=actions_kb, parse_mode="HTML")
                register_sent_message_id(message.chat.id, c_msg.message_id)
            except Exception as ex:
                print(f"[Pickup Card Error] {ex}")
                try:
                    c_msg = await bot.send_message(message.chat.id, card, reply_markup=actions_kb)
                    register_sent_message_id(message.chat.id, c_msg.message_id)
                except Exception:
                    pass
        return

    if text in ["🚚 Доставка ковров", "Доставка"]:
        orders = orders_db.get_orders()
        delivery_orders = [o for o in orders if any(w in str(o.get("Статус", "")).lower() for w in ["готов", "достав"])]
        if not delivery_orders:
            await send_clean_message(bot, message.chat.id, "📭 Нет готовых заказов на доставку.", delete_incoming_id=message.message_id)
            return

        await clean_previous_messages(bot, message.chat.id, delete_incoming_id=message.message_id)
        h_msg = await bot.send_message(message.chat.id, f"🚚 <b>Заказы на доставку ({len(delivery_orders)} шт.):</b>", parse_mode="HTML")
        register_sent_message_id(message.chat.id, h_msg.message_id)

        for o in delivery_orders[:10]:
            o_id = orders_db.normalize_id(o.get("ID"))
            c_name = html.escape(str(o.get('Клиент', '-')))
            p_phone = format_phone(str(o.get('Телефон', '-')))
            c_dist = html.escape(str(o.get('Район', 'Самарканд')))
            c_addr = html.escape(str(o.get('Адрес', '-')))
            c_items = html.escape(str(o.get('Размеры', '-')))
            c_sum = str(o.get('Сумма', '0'))

            card = (
                f"🚚 <b>ДОСТАВКА №{o_id}</b>\n\n"
                f"👤 <b>Клиент:</b> {c_name}\n"
                f"📞 <b>Тел:</b> <code>{p_phone}</code>\n"
                f"🏠 <b>Адрес:</b> {c_dist}, {c_addr}\n"
                f"🧺 <b>Содержимое:</b> {c_items}\n"
                f"💰 <b>К оплате:</b> <code>{c_sum} сум</code>"
            )
            actions_kb = get_order_inline_actions(o_id, o.get("Статус", "Готов"), o.get("Адрес", ""), o.get("Район", ""), o.get("Локация", ""))
            try:
                c_msg = await bot.send_message(message.chat.id, card, reply_markup=actions_kb, parse_mode="HTML")
                register_sent_message_id(message.chat.id, c_msg.message_id)
            except Exception as ex:
                print(f"[Delivery Card Error] {ex}")
                try:
                    c_msg = await bot.send_message(message.chat.id, card, reply_markup=actions_kb)
                    register_sent_message_id(message.chat.id, c_msg.message_id)
                except Exception:
                    pass
        return

    if text in ["📏 Замерить ковер", "Замерить"]:
        await send_clean_message(bot, message.chat.id, "📏 **Замер ковров выполняется мастером цеха в системе CRM.**", delete_incoming_id=message.message_id)
        return

    if text == "📋 Мои заказы":
        orders = orders_db.get_orders()
        my_list = [o for o in orders if username.lower() in str(o.get("Курьер", "")).lower()]
        if not my_list:
            await send_clean_message(bot, message.chat.id, "📭 У вас пока нет закрепленных заказов.", delete_incoming_id=message.message_id)
            return

        msg = f"📋 **Все заказы курьера {username} ({len(my_list)} шт.):**\n\n"
        for o in my_list[:8]:
            msg += f"🔹 **Заказ №{orders_db.normalize_id(o.get('ID'))}** | {o.get('Клиент')}\n🏠 {o.get('Район')}, {o.get('Адрес')}\n📊 Статус: **{o.get('Статус')}**\n\n"
        await send_clean_message(bot, message.chat.id, msg, delete_incoming_id=message.message_id)
        return

    if text == "🔍 Поиск заказа":
        sess["state"] = "search_order"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await send_clean_message(bot, message.chat.id, "🔍 Введите **номер заказа** (например `5218`) или **телефон**:", delete_incoming_id=message.message_id)
        return

    if state == "search_order":
        sess.pop("state", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        q = text.lower().strip()
        orders = orders_db.get_orders()
        found = [o for o in orders if q in str(o.get("ID", "")).lower() or q in str(o.get("Телефон", "")).lower() or q in str(o.get("Клиент", "")).lower()]

        if not found:
            await send_clean_message(bot, message.chat.id, f"❌ Заказ '{text}' не найден.", delete_incoming_id=message.message_id)
            return

        await clean_previous_messages(bot, message.chat.id, delete_incoming_id=message.message_id)
        for o in found[:5]:
            o_id = orders_db.normalize_id(o.get("ID"))
            card = (
                f"🔎 **Заказ №{o_id}**\n"
                f"👤 **Клиент:** {o.get('Клиент')}\n"
                f"📞 **Тел:** `{format_phone(str(o.get('Телефон')))}`\n"
                f"🏠 **Адрес:** {o.get('Район')}, {o.get('Адрес')}\n"
                f"📊 **Статус:** {o.get('Статус')}"
            )
            c_msg = await bot.send_message(message.chat.id, card, reply_markup=get_order_inline_actions(o_id, o.get("Статус"), o.get("Адрес", ""), o.get("Район", ""), o.get("Локация", "")), parse_mode="Markdown")
            register_sent_message_id(message.chat.id, c_msg.message_id)
        return

    if text == "➕ Новый заказ":
        sess["state"] = "create_order_step1"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await send_clean_message(bot, message.chat.id, "➕ **Новый заказ (1/4):** Введите **Имя клиента**:", delete_incoming_id=message.message_id)
        return

    if state == "create_order_step1":
        sess["new_client"] = text
        sess["state"] = "create_order_step2"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await send_clean_message(bot, message.chat.id, "Шаг 2/4: Введите **Телефон клиента**:", delete_incoming_id=message.message_id)
        return

    if state == "create_order_step2":
        sess["new_phone"] = format_phone(text)
        sess["state"] = "create_order_step3"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await send_clean_message(bot, message.chat.id, "Шаг 3/4: Введите **Район и Адрес**:", delete_incoming_id=message.message_id)
        return

    if state == "create_order_step3":
        sess["new_address"] = text
        sess["state"] = "create_order_step4"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await send_clean_message(bot, message.chat.id, "Шаг 4/4: Введите **детали / количество ковров**:", delete_incoming_id=message.message_id)
        return

    if state == "create_order_step4":
        items_desc = text
        client = sess.get("new_client", "Клиент")
        phone = sess.get("new_phone", "")
        addr = sess.get("new_address", "")

        new_id = get_next_order_id()
        now_str = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

        new_order = {
            "ID": str(new_id),
            "Дата": now_str,
            "Клиент": client,
            "Телефон": phone,
            "Адрес": addr,
            "Размеры": items_desc,
            "Площадь": "0",
            "Сумма": "0",
            "Статус": "Ожидает забора",
            "Курьер": username,
            "Диспетчер": f"Курьер {username}",
            "Район": "Самарканд",
            "Язык": "Русский язык",
            "Локация": "",
            "Оплачено": "0",
            "Тип оплаты": "Наличные",
            "Причина": "Создано курьером через Бот"
        }

        orders_db.add_order(new_order)

        sess.pop("state", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        await send_clean_message(bot, message.chat.id, f"🎉 **Заказ №{new_id} создан!**\n👤 Клиент: {client}\n📞 Тел: {phone}\n🏠 Адрес: {addr}", reply_markup=get_courier_main_keyboard(), delete_incoming_id=message.message_id)

        # Notify dispatcher
        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"📥 **Новый заказ №{new_id}** от курьера **{username}**!\n👤 Клиент: {client}\n📞 Тел: {phone}\n🏠 Адрес: {addr}"))
        return

    if state == "cour_editing_items":
        oid = sess.get("items_oid", "")
        sess.pop("state", None)
        sess.pop("items_oid", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        orders_db.update_order(oid, {"Размеры": text})

        await send_clean_message(
            bot,
            message.chat.id,
            f"✅ **Детали забора для Заказа №{oid} сохранены!**\n🧺 **Содержимое:** `{text}`",
            reply_markup=get_courier_main_keyboard(),
            delete_incoming_id=message.message_id
        )

        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(
                f"🧺 **Курьер {username} указал детали забора для Заказа №{oid}!**\nДетали: {text}"
            ))
        return

    if text == "📏 Замерить ковер":
        sess["state"] = "calc_step1"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await send_clean_message(bot, message.chat.id, "📏 **Замер:** Введите **№ заказа** (например: `5218`):", delete_incoming_id=message.message_id)
        return

    if state == "calc_step1":
        sess["calc_oid"] = text.strip()
        sess["state"] = "calc_step2"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await send_clean_message(bot, message.chat.id, f"📐 Заказ №{text}: Введите **Ширину** и **Длину** через пробел (например: `2.5 3.0`):", delete_incoming_id=message.message_id)
        return

    if state == "calc_step2":
        try:
            parts = text.replace(",", ".").split()
            w = float(parts[0])
            l = float(parts[1])
            area = round(w * l, 2)
            price_per_sq = 20000
            total = int(area * price_per_sq)

            oid = sess.get("calc_oid", "")
            orders_db.update_order(oid, {
                "Площадь": str(area),
                "Сумма": str(total),
                "Размеры": f"{w}m x {l}m ({area} кв.м)"
            })

            sess.pop("state", None)
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            await send_clean_message(bot, message.chat.id, f"✅ **Замер сохранен (№{oid})!**\n📏 Размер: `{w}x{l} м` ({area} м²)\n💰 Сумма: `{total:,} сум`", reply_markup=get_courier_main_keyboard(), delete_incoming_id=message.message_id)

            if notify_dispatcher_func:
                asyncio.create_task(notify_dispatcher_func(f"📏 **Курьер {username} замерил заказ №{oid}:**\nРазмер: {w}x{l} м ({area} кв.м)\nСумма: {total:,} сум"))
        except Exception:
            await send_clean_message(bot, message.chat.id, "⚠️ Введите два числа через пробел (например: `2.5 3.0`).", delete_incoming_id=message.message_id)
        return

    await send_clean_message(bot, message.chat.id, f"👇 Меню курьера ниже:\n\n🌐 **WebApp:** {COURIER_WEBAPP_URL}", reply_markup=get_courier_main_keyboard(), delete_incoming_id=message.message_id)

@router.callback_query(F.data.startswith("cour_claim_"))
async def cb_cour_claim(callback: CallbackQuery):
    order_id = orders_db.normalize_id(callback.data.replace("cour_claim_", "").strip())
    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    username = sess.get("cour_username") or sess.get("username", "Курьер")

    orders = orders_db.get_orders()
    target_order = None
    for o in orders:
        if orders_db.normalize_id(o.get("ID")) == order_id:
            target_order = o
            break

    if not target_order:
        await callback.answer("❌ Заказ не найден в базе!", show_alert=True)
        return

    current_courier = str(target_order.get("Курьер", "")).strip()

    if current_courier and current_courier not in ["Не назначен", "None", "", "Курьер"] and current_courier.lower() != username.lower():
        await callback.answer(f"⚠️ Заказ №{order_id} уже забронирован курьером {current_courier}!", show_alert=True)
        return

    orders_db.update_order(order_id, {"Курьер": username, "Статус": "Принят курьером"})

    await callback.answer(f"🎉 Вы успешно приняли заказ №{order_id}!", show_alert=True)

    actions_kb = get_order_inline_actions(order_id, "Принят курьером", target_order.get("Адрес", ""), target_order.get("Район", ""), target_order.get("Локация", ""))
    
    card_text = (
        f"✅ **Заказ №{order_id} забронирован за вами ({username})!**\n\n"
        f"👤 **Клиент:** {target_order.get('Клиент')}\n"
        f"📞 **Тел:** `{target_order.get('Телефон')}`\n"
        f"🏠 **Адрес:** {target_order.get('Район')}, {target_order.get('Адрес')}\n"
        f"💬 **Комментарий:** {target_order.get('Размеры') or target_order.get('Примечание') or '-'}"
    )
    try:
        await callback.message.edit_text(card_text, reply_markup=actions_kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(card_text, reply_markup=actions_kb, parse_mode="Markdown")

    if notify_dispatcher_func:
        asyncio.create_task(notify_dispatcher_func(f"🚚 **Курьер {username} первым принял заказ №{order_id}!**"))

@router.callback_query(F.data.startswith("cour_st_"))
async def cb_change_status(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    parts = callback.data.split("_")
    if len(parts) < 4:
        return

    st_type = parts[2]
    order_id = orders_db.normalize_id(parts[3])
    new_status = "В цеху" if st_type == "shop" else "В обработке"

    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    username = sessions.get(chat_id, {}).get("username", "Курьер")

    orders_db.update_order(order_id, {"Статус": new_status, "Курьер": username})

    await send_clean_message(bot, callback.message.chat.id, f"✅ **Заказ №{order_id} обновлен на: {new_status}!** ({username})", reply_markup=get_courier_main_keyboard(), parse_mode="Markdown")

    if notify_dispatcher_func:
        asyncio.create_task(notify_dispatcher_func(f"🚗 **Курьер {username} забрал заказ №{order_id} (В цеху)!**"))

@router.callback_query(F.data.startswith("cour_pay_"))
async def cb_pay_done(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    parts = callback.data.split("_")
    if len(parts) < 4:
        return

    pay_type_code = parts[2]
    order_id = orders_db.normalize_id(parts[3])
    pay_type_name = "Наличные" if pay_type_code == "cash" else "Карта/Click"

    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    username = sessions.get(chat_id, {}).get("username", "Курьер")

    orders = orders_db.get_orders()
    sum_val = "0"
    for o in orders:
        if orders_db.normalize_id(o.get("ID")) == order_id:
            sum_val = str(o.get("Сумма", "0"))
            break

    orders_db.update_order(order_id, {
        "Статус": "Выполнен",
        "Тип оплаты": pay_type_name,
        "Оплачено": sum_val,
        "Курьер": username
    })

    await send_clean_message(bot, callback.message.chat.id, f"🎉 **Заказ №{order_id} выполнен!**\n💰 Оплата: `{sum_val} сум` ({pay_type_name})", reply_markup=get_courier_main_keyboard(), parse_mode="Markdown")

    if notify_dispatcher_func:
        asyncio.create_task(notify_dispatcher_func(f"💵 **Курьер {username} доставил заказ №{order_id}!**\nСумма: {sum_val} сум ({pay_type_name})"))

@router.callback_query(F.data.startswith("cour_route_"))
async def cb_cour_route(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    order_id = orders_db.normalize_id(callback.data.replace("cour_route_", "").strip())
    orders = orders_db.get_orders()
    target_order = None
    for o in orders:
        if orders_db.normalize_id(o.get("ID")) == order_id:
            target_order = o
            break

    if not target_order:
        await callback.message.answer("❌ Заказ не найден!")
        return

    loc = target_order.get("Локация", "")
    address = target_order.get("Адрес", "")
    district = target_order.get("Район", "")

    parsed = parse_coords(loc, district)
    if parsed:
        lat, lng, _ = parsed
        navi_url = f"yandexnavi://build_route_on_map?lat_to={lat}&lon_to={lng}"
        ymaps_url = f"https://yandex.ru/maps/?rtext=~{lat},{lng}&rtt=auto"
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧭 Яндекс.Навигатор", url=navi_url), InlineKeyboardButton(text="🗺️ Яндекс.Карты", url=ymaps_url)],
            [InlineKeyboardButton(text="📍 Google Maps", url=gmaps_url)]
        ])
        msg_text = (
            f"🧭 **Маршрут доставки до клиента (Заказ №{order_id}):**\n\n"
            f"👤 **Клиент:** {target_order.get('Клиент')}\n"
            f"📞 **Тел:** `{format_phone(str(target_order.get('Телефон')))}`\n"
            f"🏠 **Адрес:** {district}, {address}\n"
            f"📍 **GPS Координаты:** `{lat}, {lng}`\n\n"
            f"👇 Выберите навигатор для авто-прокладки маршрута:"
        )
    else:
        full_addr = f"Самарканд {district} {address}".strip()
        encoded = urllib.parse.quote(full_addr)
        navi_url = f"yandexnavi://map?text={encoded}"
        ymaps_url = f"https://yandex.ru/maps/?text={encoded}&rtt=auto"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧭 Яндекс.Навигатор", url=navi_url), InlineKeyboardButton(text="🗺️ Яндекс.Карты", url=ymaps_url)]
        ])
        msg_text = (
            f"🗺️ **Поиск адреса / маршрута клиента (Заказ №{order_id}):**\n\n"
            f"👤 **Клиент:** {target_order.get('Клиент')}\n"
            f"📞 **Тел:** `{format_phone(str(target_order.get('Телефон')))}`\n"
            f"🏠 **Адрес:** {district}, {address}\n\n"
            f"💡 *Точные GPS координаты не сохранены. Маршрут строится по адресу.*"
        )

    await clean_previous_messages(bot, callback.message.chat.id)
    sent = await bot.send_message(callback.message.chat.id, msg_text, reply_markup=kb, parse_mode="Markdown")
    register_sent_message_id(callback.message.chat.id, sent.message_id)

@router.callback_query(F.data.startswith("cour_receipt_"))
async def cb_cour_receipt(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    order_id = orders_db.normalize_id(callback.data.replace("cour_receipt_", "").strip())
    orders = orders_db.get_orders()
    target_order = None
    for o in orders:
        if orders_db.normalize_id(o.get("ID")) == order_id:
            target_order = o
            break

    if not target_order:
        await callback.message.answer("❌ Заказ не найден!")
        return

    await clean_previous_messages(bot, callback.message.chat.id)

    receipt_text = receipt_generator.generate_receipt_text(target_order)
    receipt_html = receipt_generator.generate_receipt_html(target_order)
    
    receipt_bytes = receipt_html.encode('utf-8')
    input_file = BufferedInputFile(receipt_bytes, filename=f"Receipt_Order_{order_id}.html")

    sent = await bot.send_document(
        chat_id=callback.message.chat.id,
        document=input_file,
        caption=receipt_text,
        parse_mode="Markdown"
    )
    register_sent_message_id(callback.message.chat.id, sent.message_id)

@router.callback_query(F.data.startswith("cour_calc_"))
async def cb_start_calc(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    order_id = orders_db.normalize_id(callback.data.replace("cour_calc_", "").strip())
    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    sess["calc_oid"] = order_id
    sess["state"] = "calc_step2"
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)

    await send_clean_message(bot, callback.message.chat.id, f"📏 Замер для №{order_id}: Введите Ширину и Длину через пробел (например: `2.5 3.0`):")

@router.callback_query(F.data.startswith("cour_items_"))
async def cb_edit_items_prompt(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    order_id = orders_db.normalize_id(callback.data.replace("cour_items_", "").strip())
    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    sess["state"] = "cour_editing_items"
    sess["items_oid"] = order_id
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)

    await send_clean_message(
        bot,
        callback.message.chat.id,
        f"🧺 **Указание деталей/предметов для Заказа №{order_id}:**\n\n"
        f"Введите в ответном сообщении количество и типы вещей (например: `3 ковра, 2 курпачи, 4 подушки`):",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("cour_loc_"))
async def cb_request_loc(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    order_id = orders_db.normalize_id(callback.data.replace("cour_loc_", "").strip())
    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    sess["pending_loc_order"] = order_id
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)

    loc_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"📍 Поделиться геопозицией Заказа №{order_id}", request_location=True)],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await send_clean_message(
        bot,
        callback.message.chat.id,
        f"📍 **Фиксация GPS координаты для Заказа №{order_id}:**\n\n"
        f"Пожалуйста, нажмите кнопку **«📍 Поделиться геопозицией Заказа №{order_id}»** ниже или отправьте локацию в чат (📎 Скрепка -> Локация).\n\n"
        f"Бот привяжет точные GPS координаты к заказу!",
        reply_markup=loc_kb,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("cour_edit_st_"))
async def cb_edit_st_menu(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    order_id = callback.data.replace("cour_edit_st_", "").strip()
    buttons = [
        [InlineKeyboardButton(text="🚗 Забрать в цех", callback_data=f"cour_st_shop_{order_id}")],
        [InlineKeyboardButton(text="💵 Доставлено (Наличные)", callback_data=f"cour_pay_cash_{order_id}")],
        [InlineKeyboardButton(text="💳 Доставлено (Карта/Click)", callback_data=f"cour_pay_card_{order_id}")]
    ]
    await send_clean_message(bot, callback.message.chat.id, f"📦 Выберите новый статус для заказа **№{order_id}**:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


# --- AIOHTTP REST API HANDLERS FOR WEBAPP ---

from aiohttp import web

async def handle_webapp_index(request):
    mode = request.query.get("mode", "").lower()
    if mode == "dispatcher" or "dispatcher" in request.path:
        if os.path.exists("dispatcher_webapp.html"):
            return web.FileResponse("dispatcher_webapp.html")
    if os.path.exists("courier_webapp.html"):
        return web.FileResponse("courier_webapp.html")
    return web.Response(text="<h1>WebApp file not found</h1>", content_type="text/html", status=404)

async def handle_api_login(request):
    try:
        data = await request.json()
        login = str(data.get("login", "")).strip()
        password = str(data.get("password", "")).strip()

        auth = authenticate_courier(login, password)
        if not auth:
            # Try dispatcher authentication if courier fails
            from dispatcher_bot import authenticate_dispatcher
            auth = authenticate_dispatcher(login, password)

        if auth:
            return web.json_response({"ok": True, "user": auth})
        return web.json_response({"ok": False, "error": "Неверный логин или пароль"}, status=400)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_api_orders(request):
    orders = orders_db.get_orders()
    return web.json_response(orders)

async def handle_api_update_status(request):
    try:
        data = await request.json()
        order_id = orders_db.normalize_id(data.get("orderId"))
        new_status = data.get("status")
        pay_type = data.get("payType", "Наличные")
        courier = data.get("courier", "Курьер")

        updates = {"Статус": new_status, "Курьер": courier}
        if new_status == "Выполнен":
            updates["Тип оплаты"] = pay_type
            orders = orders_db.get_orders()
            for o in orders:
                if orders_db.normalize_id(o.get("ID")) == order_id:
                    updates["Оплачено"] = str(o.get("Сумма", "0"))
                    break

        orders_db.update_order(order_id, updates)

        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"📲 **Обновление в WebApp!**\nЗаказ №{order_id} переведен в статус **{new_status}** ({courier})"))

        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_api_create_order(request):
    try:
        data = await request.json()
        client = data.get("client", "Клиент")
        phone = data.get("phone", "")
        address = data.get("address", "")
        district = data.get("district", "Самарканд")
        items = data.get("items", "Забор ковров")
        courier = data.get("courier", "Не назначен")
        dispatcher = data.get("dispatcher", "Диспетчер")
        language = data.get("language", "Русский язык")
        priority = data.get("priority", "Обычный")
        pickup_time = data.get("pickupTime", "В любое время")
        extra_note = data.get("extraNote", "")
        delivery_date = data.get("deliveryDate", "")
        delivery_time = data.get("deliveryTime", "")

        new_id = get_next_order_id()
        now_str = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

        full_details = f"Забор: {pickup_time} | {items}"
        if "СРОЧН" in str(priority).upper():
            full_details = f"🔥 СРОЧНО ({delivery_date} {delivery_time})! {full_details}"
        if extra_note:
            full_details += f" | Ориентир: {extra_note}"

        new_order = {
            "ID": str(new_id),
            "Дата": now_str,
            "Клиент": client,
            "Телефон": phone,
            "Адрес": address,
            "Размеры": full_details,
            "Площадь": "0",
            "Сумма": "0",
            "Статус": "Ожидает забора",
            "Курьер": courier,
            "Диспетчер": dispatcher,
            "Район": district,
            "Язык": language,
            "Локация": "",
            "Оплачено": "0",
            "Тип оплаты": "-",
            "Причина": "Создано через WebApp"
        }

        orders_db.add_order(new_order)

        if notify_courier_func:
            msg_text = (
                f"📥 **Новый заказ №{new_id}!**\n\n"
                f"👤 **Клиент:** {client}\n"
                f"📞 **Тел:** `{phone}`\n"
                f"🏠 **Адрес:** {district}, {address}\n"
                f"💬 **Комментарий:** {items}"
            )
            claim_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"📥 Принять заказ №{new_id}", callback_data=f"cour_claim_{new_id}")]
            ])
            target_cour = courier if (courier and courier not in ["Не назначен", "all"]) else "all"
            asyncio.create_task(notify_courier_func(msg_text, target_courier=target_cour, reply_markup=claim_kb))

        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"🆕 **Создан новый заказ №{new_id}!** (Клиент: {client}, Адрес: {district}, {address})"))

        return web.json_response({"ok": True, "orderId": new_id})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_api_notify_couriers(request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        sender = data.get("sender", "Диспетчер")
        target_cour = data.get("courier", "all")
        if notify_courier_func and text:
            msg = f"📢 **Сообщение от Диспетчера ({sender}):**\n\n{text}"
            asyncio.create_task(notify_courier_func(msg, target_courier=target_cour))
            return web.json_response({"ok": True})
        return web.json_response({"ok": False, "error": "Пустое сообщение или нет функции уведомлений"}, status=400)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_api_measure(request):
    try:
        data = await request.json()
        order_id = orders_db.normalize_id(data.get("orderId"))
        w = float(data.get("width", 0))
        l = float(data.get("length", 0))
        price = float(data.get("price", 20000))

        area = round(w * l, 2)
        total = int(area * price)

        orders_db.update_order(order_id, {
            "Площадь": str(area),
            "Сумма": str(total),
            "Размеры": f"Ковёр: {w}m x {l}m ({area} кв.м)"
        })

        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"📏 **Замер из WebApp (Заказ №{order_id}):**\nРазмер: {w}x{l} м ({area} кв.м)\nСумма: {total:,} сум"))

        return web.json_response({"ok": True, "area": area, "total": total})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_api_update_location(request):
    try:
        data = await request.json()
        order_id = orders_db.normalize_id(data.get("orderId", ""))
        lat = data.get("lat")
        lng = data.get("lng")
        loc_str = f"{lat}, {lng}" if (lat and lng) else str(data.get("location", "")).strip()

        found = orders_db.update_order(order_id, {"Локация": loc_str})

        if found:
            if notify_dispatcher_func:
                asyncio.create_task(notify_dispatcher_func(f"📍 **GPS локация заказа №{order_id} обновлена из WebApp!** ({loc_str})"))
            return web.json_response({"ok": True, "location": loc_str})
        return web.json_response({"ok": False, "error": f"Заказ №{order_id} не найден"}, status=404)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

@router.message(F.text == "❌ Отмена")
async def cancel_location_request(message: Message):
    chat_id = str(message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    sess.pop("pending_loc_order", None)
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)
    await message.answer("❌ Фиксация GPS отменена.", reply_markup=get_courier_main_keyboard())

@router.message(F.location)
async def handle_user_location(message: Message, bot: Bot):
    chat_id = str(message.chat.id)
    lat = message.location.latitude
    lng = message.location.longitude
    loc_str = f"{lat}, {lng}"

    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    username = sess.get("cour_username") or sess.get("username", "")

    orders = orders_db.get_orders()
    active_order = None

    pending_order_id = sess.get("pending_loc_order")
    if pending_order_id:
        for o in orders:
            if orders_db.normalize_id(o.get("ID")) == orders_db.normalize_id(pending_order_id):
                active_order = o
                break

    if not active_order and username:
        for o in orders:
            st_clean = str(o.get("Статус", "")).lower()
            if username.lower() in str(o.get("Курьер", "")).lower() and ("забор" in st_clean or "ожид" in st_clean or "в цех" in st_clean or "готов" in st_clean):
                active_order = o
                break

    if not active_order and orders:
        active_order = orders[0]

    if active_order:
        o_id = orders_db.normalize_id(active_order.get("ID"))
        orders_db.update_order(o_id, {"Локация": loc_str})
        sess.pop("pending_loc_order", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        navi_url = f"yandexnavi://build_route_on_map?lat_to={lat}&lon_to={lng}"
        ymaps_url = f"https://yandex.ru/maps/?rtext=~{lat},{lng}&rtt=auto"
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"

        reply_txt = (
            f"🎉 **Геолокация успешно привязана к Заказу №{o_id}!**\n\n"
            f"👤 **Клиент:** {active_order.get('Клиент', '-')}\n"
            f"📞 **Тел:** `{format_phone(str(active_order.get('Телефон', '-')))}`\n"
            f"🏠 **Адрес:** {active_order.get('Район', '')}, {active_order.get('Адрес', '')}\n"
            f"📍 **GPS Координаты:** `{loc_str}`\n"
            f"🧺 **Детали/Предметы:** {active_order.get('Размеры', 'Не указано')}\n"
            f"📊 **Статус:** {active_order.get('Статус', '-')}\n\n"
            f"🧭 [Яндекс.Навигатор]({navi_url}) | 🗺️ [Яндекс.Карты]({ymaps_url}) | 📍 [Google Maps]({gmaps_url})"
        )

        buttons = [
            [InlineKeyboardButton(text="🚗 Забрать в цех", callback_data=f"cour_st_shop_{o_id}")],
            [InlineKeyboardButton(text="📍 Изменить геолокацию", callback_data=f"cour_loc_{o_id}")],
            [InlineKeyboardButton(text="🧺 Указать детали/предметы", callback_data=f"cour_items_{o_id}")]
        ]

        await message.answer(reply_txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        await message.answer("👇 Меню курьера:", reply_markup=get_courier_main_keyboard())

        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"📍 **Курьер {username} зафиксировал GPS клиента для Заказа №{o_id}!** ({loc_str})"))
    else:
        await message.answer(f"📍 **Ваши координаты получены:** `{loc_str}`\n⚠️ Нет активного заказа для привязки.", reply_markup=get_courier_main_keyboard(), parse_mode="Markdown")
