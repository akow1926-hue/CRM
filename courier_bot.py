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
    CallbackQuery
)

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
    orders = load_json_file(BACKUP_FILE, [])
    max_id = 5218
    if isinstance(orders, list):
        for o in orders:
            try:
                val = int(float(str(o.get("ID", 0)).replace("TG-", "")))
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
    kb.append([KeyboardButton(text="➕ Новый заказ"), KeyboardButton(text="📏 Замерить ковер")])
    kb.append([KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="🔍 Поиск заказа")])
    kb.append([KeyboardButton(text="🚪 Выйти из аккаунта (/logout)")])
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

    buttons.append([
        InlineKeyboardButton(text="📍 Зафиксировать GPS геопозицию", callback_data=f"cour_loc_{order_id}")
    ])

    if "забор" in st_clean or "ожид" in st_clean or "нов" in st_clean:
        buttons.append([
            InlineKeyboardButton(text="🚗 Забрал ковры (В цех)", callback_data=f"cour_st_shop_{order_id}"),
            InlineKeyboardButton(text="📏 Замерить", callback_data=f"cour_calc_{order_id}")
        ])
    elif "готов" in st_clean or "достав" in st_clean:
        buttons.append([
            InlineKeyboardButton(text="💵 Доставлено (Наличные)", callback_data=f"cour_pay_cash_{order_id}"),
            InlineKeyboardButton(text="💳 Доставлено (Карта/Click)", callback_data=f"cour_pay_card_{order_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="📦 Изменить статус", callback_data=f"cour_edit_st_{order_id}"),
            InlineKeyboardButton(text="📏 Замерить", callback_data=f"cour_calc_{order_id}")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Callback hook for notify dispatcher
notify_dispatcher_func = None

def set_notify_dispatcher_hook(fn):
    global notify_dispatcher_func
    notify_dispatcher_func = fn

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
        await message.answer(welcome_text, reply_markup=get_courier_main_keyboard(), parse_mode="Markdown")
    else:
        auth_msg = (
            "🔒 **Cosmo CRM — Бот Курьера**\n\n"
            f"🌐 **WebApp Курьера:** {cour_url}\n\n"
            "Пожалуйста, авторизуйтесь. Введите `логин пароль` через пробел или нажмите кнопку **🔑 Войти по логину и паролю**."
        )
        await message.answer(auth_msg, reply_markup=get_courier_login_keyboard(), parse_mode="Markdown")

@router.message(Command("logout"))
async def cmd_logout(message: Message):
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

    await message.answer("🚪 **Вы вышли из системы Курьера.**\n\n🔑 Введите `логин пароль` через пробел или нажмите **Войти по логину и паролю** для нового входа:", reply_markup=get_courier_login_keyboard(), parse_mode="Markdown")

@router.message(Command("login"))
async def cmd_login(message: Message, bot: Bot):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("⚠️ Формат входа: `/login логин пароль`", parse_mode="Markdown")
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

        await message.answer(
            f"✅ **Успешная авторизация!**\nПриветствуем, курьер `{auth_data['username']}`!\n\n🌐 **WebApp:** {cour_url}",
            reply_markup=get_courier_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Ошибка входа: у вас нет прав Курьера или неверный логин/пароль!")

@router.message(F.text)
async def handle_courier_messages(message: Message):
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
            await message.answer("👤 Введите ваш **логин** курьера:")
            return

        if state == "awaiting_login":
            sess["temp_login"] = text
            sess["state"] = "awaiting_password"
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)
            await message.answer("🔑 Введите ваш **пароль**:")
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

                await message.answer(
                    f"✅ **Успешный вход!**\nС возвращением, курьер `{auth_data['username']}`!\n\n🌐 **WebApp:** {cour_url}",
                    reply_markup=get_courier_main_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)
                await message.answer("❌ Неверный логин или пароль!", reply_markup=get_courier_login_keyboard())
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

                await message.answer(
                    f"✅ **Успешный вход!**\nКурьер: `{auth_data['username']}`\n\n🌐 **WebApp:** {cour_url}",
                    reply_markup=get_courier_main_keyboard(),
                    parse_mode="Markdown"
                )
                return

        await message.answer(f"🔒 Пожалуйста, войдите в систему курьера. Введите `логин пароль`.", reply_markup=get_courier_login_keyboard())
        return

    if text in ["🚪 Выйти из аккаунта (/logout)", "/logout", "Выйти"]:
        await cmd_logout(message)
        return

    if text in ["📥 Забор ковров", "Забор"]:
        orders = load_json_file(BACKUP_FILE, [])
        pickup_orders = [o for o in orders if any(w in str(o.get("Статус", "")).lower() for w in ["забор", "ожид", "нов"])]
        if not pickup_orders:
            await message.answer("📭 На данный момент нет новых заявок на забор ковров.")
            return

        await message.answer(f"📥 **Заявки на забор ({len(pickup_orders)} шт.):**", parse_mode="Markdown")
        for o in pickup_orders[:8]:
            o_id = o.get("ID")
            card = (
                f"📥 **ЗАБОР №{o_id}**\n"
                f"👤 **Клиент:** {o.get('Клиент')}\n"
                f"📞 **Тел:** `{format_phone(str(o.get('Телефон')))}`\n"
                f"🏠 **Адрес:** {o.get('Район')}, {o.get('Адрес')}\n"
                f"🧺 **Детали:** {o.get('Размеры')}"
            )
            await message.answer(card, reply_markup=get_order_inline_actions(o_id, o.get("Статус"), o.get("Адрес", ""), o.get("Район", "")), parse_mode="Markdown")
        return

    if text in ["🚚 Доставка ковров", "Доставка"]:
        orders = load_json_file(BACKUP_FILE, [])
        delivery_orders = [o for o in orders if any(w in str(o.get("Статус", "")).lower() for w in ["готов", "достав"])]
        if not delivery_orders:
            await message.answer("📭 Нет готовых заказов на доставку.")
            return

        await message.answer(f"🚚 **Заказы на доставку ({len(delivery_orders)} шт.):**", parse_mode="Markdown")
        for o in delivery_orders[:8]:
            o_id = o.get("ID")
            card = (
                f"🚚 **ДОСТАВКА №{o_id}**\n"
                f"👤 **Клиент:** {o.get('Клиент')}\n"
                f"📞 **Тел:** `{format_phone(str(o.get('Телефон')))}`\n"
                f"🏠 **Адрес:** {o.get('Район')}, {o.get('Адрес')}\n"
                f"💰 **К оплате:** `{o.get('Сумма')}` сум"
            )
            await message.answer(card, reply_markup=get_order_inline_actions(o_id, o.get("Статус"), o.get("Адрес", ""), o.get("Район", "")), parse_mode="Markdown")
        return

    if text == "📋 Мои заказы":
        orders = load_json_file(BACKUP_FILE, [])
        my_list = [o for o in orders if username.lower() in str(o.get("Курьер", "")).lower()]
        if not my_list:
            await message.answer("📭 У вас пока нет закрепленных заказов.")
            return

        msg = f"📋 **Все заказы курьера {username} ({len(my_list)} шт.):**\n\n"
        for o in my_list[:8]:
            msg += f"🔹 **Заказ №{o.get('ID')}** | {o.get('Клиент')}\n🏠 {o.get('Район')}, {o.get('Адрес')}\n📊 Статус: **{o.get('Статус')}**\n\n"
        await message.answer(msg, parse_mode="Markdown")
        return

    if text == "🔍 Поиск заказа":
        sess["state"] = "search_order"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("🔍 Введите **номер заказа** (например `5218`) или **телефон**:")
        return

    if state == "search_order":
        sess.pop("state", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        q = text.lower().strip()
        orders = load_json_file(BACKUP_FILE, [])
        found = [o for o in orders if q in str(o.get("ID", "")).lower() or q in str(o.get("Телефон", "")).lower() or q in str(o.get("Клиент", "")).lower()]

        if not found:
            await message.answer(f"❌ Заказ '{text}' не найден.")
            return

        for o in found[:5]:
            o_id = o.get("ID")
            card = (
                f"🔎 **Заказ №{o_id}**\n"
                f"👤 **Клиент:** {o.get('Клиент')}\n"
                f"📞 **Тел:** `{format_phone(str(o.get('Телефон')))}`\n"
                f"🏠 **Адрес:** {o.get('Район')}, {o.get('Адрес')}\n"
                f"📊 **Статус:** {o.get('Статус')}"
            )
            await message.answer(card, reply_markup=get_order_inline_actions(o_id, o.get("Статус"), o.get("Адрес", ""), o.get("Район", "")), parse_mode="Markdown")
        return

    if text == "➕ Новый заказ":
        sess["state"] = "create_order_step1"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("➕ **Новый заказ (1/4):** Введите **Имя клиента**:")
        return

    if state == "create_order_step1":
        sess["new_client"] = text
        sess["state"] = "create_order_step2"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("Шаг 2/4: Введите **Телефон клиента**:")
        return

    if state == "create_order_step2":
        sess["new_phone"] = format_phone(text)
        sess["state"] = "create_order_step3"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("Шаг 3/4: Введите **Район и Адрес**:")
        return

    if state == "create_order_step3":
        sess["new_address"] = text
        sess["state"] = "create_order_step4"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("Шаг 4/4: Введите **детали / количество ковров**:")
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

        orders = load_json_file(BACKUP_FILE, [])
        orders.insert(0, new_order)
        save_json_file(BACKUP_FILE, orders)

        sess.pop("state", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        await message.answer(f"🎉 **Заказ №{new_id} создан!**\n👤 Клиент: {client}\n📞 Тел: {phone}\n🏠 Адрес: {addr}", reply_markup=get_courier_main_keyboard(), parse_mode="Markdown")

        # Notify dispatcher
        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"📥 **Новый заказ №{new_id}** от курьера **{username}**!\n👤 Клиент: {client}\n📞 Тел: {phone}\n🏠 Адрес: {addr}"))
        return

    if text == "📏 Замерить ковер":
        sess["state"] = "calc_step1"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("📏 **Замер:** Введите **№ заказа** (например: `5218`):")
        return

    if state == "calc_step1":
        sess["calc_oid"] = text.strip()
        sess["state"] = "calc_step2"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer(f"📐 Заказ №{text}: Введите **Ширину** и **Длину** через пробел (например: `2.5 3.0`):")
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
            orders = load_json_file(BACKUP_FILE, [])
            for o in orders:
                if str(o.get("ID")) == str(oid):
                    o["Площадь"] = str(area)
                    o["Сумма"] = str(total)
                    o["Размеры"] = f"{w}m x {l}m ({area} кв.м)"
                    break

            save_json_file(BACKUP_FILE, orders)
            sess.pop("state", None)
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            await message.answer(f"✅ **Замер сохранен (№{oid})!**\n📏 Размер: `{w}x{l} м` ({area} м²)\n💰 Сумма: `{total:,} сум`", reply_markup=get_courier_main_keyboard(), parse_mode="Markdown")

            if notify_dispatcher_func:
                asyncio.create_task(notify_dispatcher_func(f"📏 **Курьер {username} замерил заказ №{oid}:**\nРазмер: {w}x{l} м ({area} кв.м)\nСумма: {total:,} сум"))
        except Exception:
            await message.answer("⚠️ Введите два числа через пробел (например: `2.5 3.0`).")
        return

    await message.answer(f"👇 Меню курьера ниже:\n\n🌐 **WebApp:** {COURIER_WEBAPP_URL}", reply_markup=get_courier_main_keyboard())

@router.callback_query(F.data.startswith("cour_st_"))
async def cb_change_status(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    if len(parts) < 4:
        return

    st_type = parts[2]
    order_id = parts[3]
    new_status = "В цеху" if st_type == "shop" else "В обработке"

    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    username = sessions.get(chat_id, {}).get("username", "Курьер")

    orders = load_json_file(BACKUP_FILE, [])
    for o in orders:
        if str(o.get("ID")) == str(order_id):
            o["Статус"] = new_status
            o["Курьер"] = username
            break

    save_json_file(BACKUP_FILE, orders)
    await callback.message.answer(f"✅ Заказ №{order_id} обновлен на: **{new_status}** ({username})", parse_mode="Markdown")

    if notify_dispatcher_func:
        asyncio.create_task(notify_dispatcher_func(f"🚗 **Курьер {username} забрал заказ №{order_id} (В цеху)!**"))

@router.callback_query(F.data.startswith("cour_pay_"))
async def cb_pay_done(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    if len(parts) < 4:
        return

    pay_type_code = parts[2]
    order_id = parts[3]
    pay_type_name = "Наличные" if pay_type_code == "cash" else "Карта/Click"

    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    username = sessions.get(chat_id, {}).get("username", "Курьер")

    orders = load_json_file(BACKUP_FILE, [])
    sum_val = "0"
    for o in orders:
        if str(o.get("ID")) == str(order_id):
            o["Статус"] = "Выполнен"
            o["Тип оплаты"] = pay_type_name
            sum_val = str(o.get("Сумма", "0"))
            o["Оплачено"] = sum_val
            o["Курьер"] = username
            break

    save_json_file(BACKUP_FILE, orders)
    await callback.message.answer(f"🎉 **Заказ №{order_id} выполнен!** Оплата: {sum_val} сум ({pay_type_name})", parse_mode="Markdown")

    if notify_dispatcher_func:
        asyncio.create_task(notify_dispatcher_func(f"💵 **Курьер {username} доставил заказ №{order_id}!**\nСумма: {sum_val} сум ({pay_type_name})"))

@router.callback_query(F.data.startswith("cour_calc_"))
async def cb_start_calc(callback: CallbackQuery):
    await callback.answer()
    order_id = callback.data.replace("cour_calc_", "").strip()
    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    sess["calc_oid"] = order_id
    sess["state"] = "calc_step2"
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)

    await callback.message.answer(f"📏 Замер для №{order_id}: Введите Ширину и Длину через пробел (например: `2.5 3.0`):")


# --- AIOHTTP REST API HANDLERS FOR WEBAPP ---
from aiohttp import web

async def handle_webapp_index(request):
    return web.FileResponse("courier_webapp.html")

async def handle_api_login(request):
    try:
        data = await request.json()
        login = str(data.get("login", "")).strip()
        password = str(data.get("password", "")).strip()

        auth = authenticate_courier(login, password)
        if auth:
            return web.json_response({"ok": True, "user": auth})
        return web.json_response({"ok": False, "error": "Неверный логин или пароль"}, status=400)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_api_orders(request):
    orders = load_json_file(BACKUP_FILE, [])
    return web.json_response(orders)

async def handle_api_update_status(request):
    try:
        data = await request.json()
        order_id = str(data.get("orderId"))
        new_status = data.get("status")
        pay_type = data.get("payType", "Наличные")
        courier = data.get("courier", "Курьер")

        orders = load_json_file(BACKUP_FILE, [])
        for o in orders:
            if str(o.get("ID")) == order_id:
                o["Статус"] = new_status
                o["Курьер"] = courier
                if new_status == "Выполнен":
                    o["Тип оплаты"] = pay_type
                    o["Оплачено"] = str(o.get("Сумма", "0"))
                break

        save_json_file(BACKUP_FILE, orders)

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
        items = data.get("items", "")
        courier = data.get("courier", "Курьер")

        new_id = get_next_order_id()
        now_str = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

        new_order = {
            "ID": str(new_id),
            "Дата": now_str,
            "Клиент": client,
            "Телефон": phone,
            "Адрес": address,
            "Размеры": items,
            "Площадь": "0",
            "Сумма": "0",
            "Статус": "Ожидает забора",
            "Курьер": courier,
            "Диспетчер": f"Курьер {courier}",
            "Район": "Самарканд",
            "Язык": "Русский язык",
            "Локация": "",
            "Оплачено": "0",
            "Тип оплаты": "Наличные",
            "Причина": "Создано через WebApp"
        }

        orders = load_json_file(BACKUP_FILE, [])
        orders.insert(0, new_order)
        save_json_file(BACKUP_FILE, orders)

        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"📲 **Новый заказ №{new_id} из WebApp!**\nКлиент: {client}\nТел: {phone}\nАдрес: {address}"))

        return web.json_response({"ok": True, "orderId": new_id})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_api_measure(request):
    try:
        data = await request.json()
        order_id = str(data.get("orderId"))
        w = float(data.get("width", 0))
        l = float(data.get("length", 0))
        price = float(data.get("price", 20000))

        area = round(w * l, 2)
        total = int(area * price)

        orders = load_json_file(BACKUP_FILE, [])
        for o in orders:
            if str(o.get("ID")) == order_id:
                o["Площадь"] = str(area)
                o["Сумма"] = str(total)
                o["Размеры"] = f"Ковёр: {w}m x {l}m ({area} кв.м)"
                break

        save_json_file(BACKUP_FILE, orders)

        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"📏 **Замер из WebApp (Заказ №{order_id}):**\nРазмер: {w}x{l} м ({area} кв.м)\nСумма: {total:,} сум"))

        return web.json_response({"ok": True, "area": area, "total": total})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_api_update_location(request):
    try:
        data = await request.json()
        order_id = str(data.get("orderId", ""))
        lat = data.get("lat")
        lng = data.get("lng")
        loc_str = f"{lat}, {lng}" if (lat and lng) else str(data.get("location", "")).strip()

        orders = load_json_file(BACKUP_FILE, [])
        found = False
        for o in orders:
            if str(o.get("ID")) == order_id:
                o["Локация"] = loc_str
                found = True
                break

        if found:
            save_json_file(BACKUP_FILE, orders)
            if notify_dispatcher_func:
                asyncio.create_task(notify_dispatcher_func(f"📍 **GPS локация заказа №{order_id} обновлена из WebApp!** ({loc_str})"))
            return web.json_response({"ok": True, "location": loc_str})
        return web.json_response({"ok": False, "error": f"Заказ №{order_id} не найден"}, status=404)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)
