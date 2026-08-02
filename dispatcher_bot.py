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

def get_dispatcher_webapp_url() -> str:
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        return render_url.rstrip("/")
    cfg = load_json_file(CONFIG_FILE, {})
    if isinstance(cfg, dict) and cfg.get("dispatcher_webapp_url"):
        return cfg.get("dispatcher_webapp_url")
    return os.environ.get("DISPATCHER_WEBAPP_URL", "https://all-camels-dispatcher.loca.lt")

DISPATCHER_WEBAPP_URL = get_dispatcher_webapp_url()

def save_json_file(filename: str, data: dict | list) -> bool:
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[JSON Error] Ошибка записи {filename}: {e}")
        return False

def authenticate_dispatcher(login: str, password: str) -> Optional[dict]:
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
                if is_dispatcher_role(u_role):
                    return {"username": u_name, "role": u_role}
    return None

def is_dispatcher_role(role: str) -> bool:
    r = str(role).lower()
    return any(k in r for k in ["dispatcher", "диспетчер", "dispetcher", "admin", "админ", "администратор"])

def get_couriers_list() -> List[str]:
    users = load_json_file(USERS_BACKUP_FILE, [])
    couriers = []
    if isinstance(users, list):
        for u in users:
            u_role = str(u.get("Role") or u.get("role") or "").strip().lower()
            u_name = str(u.get("Username") or u.get("username") or "").strip()
            if any(k in u_role for k in ["courier", "курьер", "доставщик", "yuboruvchi", "kuryer"]):
                if u_name and u_name not in couriers:
                    couriers.append(u_name)
    return couriers or ["akobir", "firuz"]

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
    
    kb.append([KeyboardButton(text="➕ Новый заказ"), KeyboardButton(text="📋 Список заказов")])
    kb.append([KeyboardButton(text="🚚 Назначить курьера"), KeyboardButton(text="🔍 Поиск заказа")])
    kb.append([KeyboardButton(text="📊 Статистика"), KeyboardButton(text="💬 Написать курьеру")])
    kb.append([KeyboardButton(text="🚪 Выйти из аккаунта (/logout)")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Hook to send notification to courier bot
notify_courier_func = None

def set_notify_courier_hook(fn):
    global notify_courier_func
    notify_courier_func = fn

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    chat_id = str(message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    sess.pop("state", None)
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)

    disp_url = get_dispatcher_webapp_url()
    try:
        if disp_url.startswith("https://"):
            await bot.set_chat_menu_button(
                chat_id=message.chat.id,
                menu_button=MenuButtonWebApp(text="🖥️ CRM Диспетчера", web_app=WebAppInfo(url=disp_url))
            )
    except Exception as e:
        print(f"[Dispatcher MenuButton Warning] {e}")

    username = sess.get("disp_username") or (sess.get("username") if is_dispatcher_role(sess.get("role", "")) else None)
    role = sess.get("disp_role") or (sess.get("role") if is_dispatcher_role(sess.get("role", "")) else None)

    # Store dispatcher chat ID in config
    cfg = load_json_file(CONFIG_FILE, {})
    disp_chats = cfg.get("dispatcher_chats", {})
    if username:
        disp_chats[username.lower()] = chat_id
        cfg["dispatcher_chats"] = disp_chats
        save_json_file(CONFIG_FILE, cfg)

    if username and role and is_dispatcher_role(role):
        welcome_text = (
            f"🎧 **Cosmo CRM — Бот Диспетчера**\n\n"
            f"👤 **Вы авторизованы как:** `{username}` ({role})\n\n"
            f"🌐 **Панель CRM Диспетчера:** {disp_url}"
        )
        await message.answer(welcome_text, reply_markup=get_dispatcher_main_keyboard(), parse_mode="Markdown")
    else:
        auth_msg = (
            "🔒 **Cosmo CRM — Бот Диспетчера**\n\n"
            f"🌐 **Панель CRM Диспетчера:** {disp_url}\n\n"
            "Пожалуйста, авторизуйтесь. Введите `логин пароль` через пробел (например: `bobur bobur`) или нажмите **🔑 Войти по логину и паролю**."
        )
        await message.answer(auth_msg, reply_markup=get_dispatcher_login_keyboard(), parse_mode="Markdown")

@router.message(Command("logout"))
async def cmd_logout(message: Message):
    chat_id = str(message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    if chat_id in sessions:
        u_name = sessions[chat_id].get("disp_username") or sessions[chat_id].get("username")
        sessions[chat_id].pop("disp_username", None)
        sessions[chat_id].pop("disp_role", None)
        sessions.pop(chat_id, None)
        save_json_file(SESSIONS_FILE, sessions)
        if u_name:
            cfg = load_json_file(CONFIG_FILE, {})
            d_chats = cfg.get("dispatcher_chats", {})
            d_chats.pop(u_name.lower(), None)
            cfg["dispatcher_chats"] = d_chats
            save_json_file(CONFIG_FILE, cfg)

    await message.answer("🚪 **Вы вышли из системы Диспетчера.**\n\n🔑 Введите `логин пароль` через пробел или нажмите **Войти по логину и паролю** для нового входа:", reply_markup=get_dispatcher_login_keyboard(), parse_mode="Markdown")

@router.message(Command("login"))
async def cmd_login(message: Message, bot: Bot):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("⚠️ Формат входа: `/login логин пароль`\nПример: `/login bobur bobur`", parse_mode="Markdown")
        return

    login_in, pass_in = args[1], args[2]
    auth_data = authenticate_dispatcher(login_in, pass_in)

    if auth_data:
        chat_id = str(message.chat.id)
        sessions = load_json_file(SESSIONS_FILE, {})
        sess = sessions.get(chat_id, {})
        sess["disp_username"] = auth_data["username"]
        sess["disp_role"] = auth_data["role"]
        sess["login_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        cfg = load_json_file(CONFIG_FILE, {})
        disp_chats = cfg.get("dispatcher_chats", {})
        disp_chats[auth_data["username"].lower()] = chat_id
        cfg["dispatcher_chats"] = disp_chats
        save_json_file(CONFIG_FILE, cfg)

        disp_url = get_dispatcher_webapp_url()
        if disp_url.startswith("https://"):
            try:
                await bot.set_chat_menu_button(
                    chat_id=message.chat.id,
                    menu_button=MenuButtonWebApp(text="🖥️ CRM Диспетчера", web_app=WebAppInfo(url=disp_url))
                )
            except Exception:
                pass

        await message.answer(
            f"✅ **Успешный вход!**\nДиспетчер: `{auth_data['username']}`\n\n🌐 **CRM WebApp:** {disp_url}",
            reply_markup=get_dispatcher_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Ошибка входа: у вас нет прав Диспетчера или неверный логин/пароль!")

@router.message(F.text)
async def handle_dispatcher_messages(message: Message):
    text = message.text.strip()
    chat_id = str(message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    username = sess.get("disp_username") or (sess.get("username") if is_dispatcher_role(sess.get("role", "")) else None)
    role = sess.get("disp_role") or (sess.get("role") if is_dispatcher_role(sess.get("role", "")) else None)
    state = sess.get("state", "")
    disp_url = get_dispatcher_webapp_url()

    if not username or not is_dispatcher_role(role):
        if text == "🔑 Войти по логину и паролю":
            sess["state"] = "awaiting_login"
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)
            await message.answer("👤 Введите ваш **логин** Диспетчера / Админа:")
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
            auth_data = authenticate_dispatcher(l_val, p_val)
            sess.pop("temp_login", None)
            sess.pop("state", None)

            if auth_data:
                sess["disp_username"] = auth_data["username"]
                sess["disp_role"] = auth_data["role"]
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)

                cfg = load_json_file(CONFIG_FILE, {})
                disp_chats = cfg.get("dispatcher_chats", {})
                disp_chats[auth_data["username"].lower()] = chat_id
                cfg["dispatcher_chats"] = disp_chats
                save_json_file(CONFIG_FILE, cfg)

                await message.answer(
                    f"✅ **Успешная авторизация!**\nПриветствуем, `{auth_data['username']}`!\n\n🌐 **CRM WebApp:** {disp_url}",
                    reply_markup=get_dispatcher_main_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)
                await message.answer("❌ Неверный логин или пароль Диспетчера!", reply_markup=get_dispatcher_login_keyboard())
            return

        words = text.split()
        if len(words) == 2 and not text.startswith("/"):
            auth_data = authenticate_dispatcher(words[0], words[1])
            if auth_data:
                sess["disp_username"] = auth_data["username"]
                sess["disp_role"] = auth_data["role"]
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)

                cfg = load_json_file(CONFIG_FILE, {})
                disp_chats = cfg.get("dispatcher_chats", {})
                disp_chats[auth_data["username"].lower()] = chat_id
                cfg["dispatcher_chats"] = disp_chats
                save_json_file(CONFIG_FILE, cfg)

                await message.answer(
                    f"✅ **Успешный вход!**\nПользователь: `{auth_data['username']}`\n\n🌐 **CRM WebApp:** {disp_url}",
                    reply_markup=get_dispatcher_main_keyboard(),
                    parse_mode="Markdown"
                )
                return

        await message.answer("🔒 Войдите под аккаунтом Диспетчера. Введите `логин пароль`.", reply_markup=get_dispatcher_login_keyboard())
        return

    if text in ["🚪 Выйти из аккаунта (/logout)", "/logout", "Выйти"]:
        await cmd_logout(message)
        return

    if text in ["📊 Статистика", "Статистика"]:
        orders = load_json_file(BACKUP_FILE, [])
        new_cnt = len([o for o in orders if "забор" in str(o.get("Статус", "")).lower() or "ожид" in str(o.get("Статус", "")).lower()])
        shop_cnt = len([o for o in orders if "цех" in str(o.get("Статус", "")).lower()])
        ready_cnt = len([o for o in orders if "готов" in str(o.get("Статус", "")).lower()])
        done_cnt = len([o for o in orders if "выполн" in str(o.get("Статус", "")).lower()])
        
        total_income = sum([int(float(o.get("Сумма", 0))) for o in orders if "выполн" in str(o.get("Статус", "")).lower()])

        stat_msg = (
            f"📊 **Статистика заказов CRM:**\n\n"
            f"📥 **Ожидают забора:** `{new_cnt}`\n"
            f"🧺 **В цеху (стирка/сушка):** `{shop_cnt}`\n"
            f"📦 **Готовы к доставке:** `{ready_cnt}`\n"
            f"✅ **Выполнено:** `{done_cnt}`\n\n"
            f"💰 **Общий доход (выполненные):** `{total_income:,} сум`"
        )
        await message.answer(stat_msg, parse_mode="Markdown")
        return

    if text == "📋 Список заказов":
        buttons = [
            [InlineKeyboardButton(text="📥 На заборе", callback_data="disp_list_pickup"), InlineKeyboardButton(text="🧺 В цеху", callback_data="disp_list_shop")],
            [InlineKeyboardButton(text="📦 Готовые", callback_data="disp_list_ready"), InlineKeyboardButton(text="✅ Выполненные", callback_data="disp_list_done")]
        ]
        await message.answer("📋 **Выберите категорию заказов:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    if text == "➕ Новый заказ":
        sess["state"] = "disp_create_step1"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("➕ **Оформление нового заказа (1/4):**\nВведите **Имя клиента**:")
        return

    if state == "disp_create_step1":
        sess["disp_client"] = text
        sess["state"] = "disp_create_step2"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("Шаг 2/4: Введите **Телефон клиента** (например `901234567`):")
        return

    if state == "disp_create_step2":
        sess["disp_phone"] = format_phone(text)
        sess["state"] = "disp_create_step3"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("Шаг 3/4: Введите **Район и Адрес**:")
        return

    if state == "disp_create_step3":
        sess["disp_address"] = text
        sess["state"] = "disp_create_step4"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        couriers = get_couriers_list()
        buttons = []
        for c in couriers:
            buttons.append([InlineKeyboardButton(text=f"🚚 {c}", callback_data=f"disp_sel_cour_{c}")])

        await message.answer("Шаг 4/4: **Выберите курьера** для назначения на заказ:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    if text == "🚚 Назначить курьера":
        sess["state"] = "disp_assign_step1"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("🚚 Введите **№ заказа** для назначения курьера (например `5218`):")
        return

    if state == "disp_assign_step1":
        oid = text.strip()
        sess["assign_oid"] = oid
        sess.pop("state", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        couriers = get_couriers_list()
        buttons = []
        for c in couriers:
            buttons.append([InlineKeyboardButton(text=f"🚚 Назначить на {c}", callback_data=f"disp_set_cour_{oid}_{c}")])

        await message.answer(f"🚚 Выберите курьера для заказа №{oid}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    if text == "🔍 Поиск заказа":
        sess["state"] = "disp_search"
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)
        await message.answer("🔍 Введите **номер заказа**, **телефон** или **имя клиента**:")
        return

    if state == "disp_search":
        sess.pop("state", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        q = text.lower().strip()
        orders = load_json_file(BACKUP_FILE, [])
        found = [o for o in orders if q in str(o.get("ID", "")).lower() or q in str(o.get("Телефон", "")).lower() or q in str(o.get("Клиент", "")).lower()]

        if not found:
            await message.answer(f"❌ Заказ '{text}' не найден в системе.")
            return

        for o in found[:5]:
            oid = o.get("ID")
            card = (
                f"🔎 **Заказ №{oid}**\n"
                f"👤 **Клиент:** {o.get('Клиент')}\n"
                f"📞 **Тел:** `{o.get('Телефон')}`\n"
                f"🏠 **Адрес:** {o.get('Район')}, {o.get('Адрес')}\n"
                f"🚚 **Курьер:** `{o.get('Курьер')}`\n"
                f"📊 **Статус:** {o.get('Статус')}\n"
                f"💰 **Сумма:** `{o.get('Сумма')}` сум"
            )
            buttons = [
                [InlineKeyboardButton(text="🚚 Назначить курьера", callback_data=f"disp_reassign_{oid}")],
                [InlineKeyboardButton(text="📦 Сменить статус", callback_data=f"disp_st_menu_{oid}")]
            ]
            await message.answer(card, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        return

    if text == "💬 Написать курьеру":
        couriers = get_couriers_list()
        buttons = []
        for c in couriers:
            buttons.append([InlineKeyboardButton(text=f"✉️ Написать {c}", callback_data=f"disp_msg_cour_{c}")])
        buttons.append([InlineKeyboardButton(text="📢 Рассылка всем курьерам", callback_data="disp_msg_cour_all")])

        await message.answer("💬 Кому хотите отправить сообщение?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    if state == "disp_sending_msg":
        target_cour = sess.get("target_cour", "all")
        sess.pop("state", None)
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        if notify_courier_func:
            asyncio.create_task(notify_courier_func(f"💬 **Сообщение от Диспетчера ({username}):**\n\n{text}", target_courier=target_cour))
        await message.answer(f"✅ Сообщение отправлено курьеру: **{target_cour}**!")
        return

    await message.answer(f"👇 Главное меню Диспетчера:\n\n🌐 **CRM WebApp:** {DISPATCHER_WEBAPP_URL}", reply_markup=get_dispatcher_main_keyboard())

# --- CALLBACK HANDLERS FOR DISPATCHER ---

@router.callback_query(F.data.startswith("disp_list_"))
async def cb_disp_list(callback: CallbackQuery):
    await callback.answer()
    cat = callback.data.replace("disp_list_", "")
    orders = load_json_file(BACKUP_FILE, [])

    if cat == "pickup":
        filtered = [o for o in orders if any(w in str(o.get("Статус", "")).lower() for w in ["забор", "ожид", "нов"])]
        title = "📥 **Заказы на заборе:**"
    elif cat == "shop":
        filtered = [o for o in orders if "цех" in str(o.get("Статус", "")).lower()]
        title = "🧺 **Заказы в цеху:**"
    elif cat == "ready":
        filtered = [o for o in orders if "готов" in str(o.get("Статус", "")).lower()]
        title = "📦 **Готовые к доставке:**"
    else:
        filtered = [o for o in orders if "выполн" in str(o.get("Статус", "")).lower()]
        title = "✅ **Выполненные заказы:**"

    if not filtered:
        await callback.message.answer(f"{title}\n\n📭 Список пуст.")
        return

    msg = f"{title} ({len(filtered)} шт.)\n\n"
    for o in filtered[:10]:
        msg += f"🔹 **№{o.get('ID')}** | {o.get('Клиент')} (`{o.get('Телефон')}`)\n🏠 {o.get('Адрес')}\n🚚 Курьер: `{o.get('Курьер')}` | 💰 `{o.get('Сумма')}` сум\n\n"
    await callback.message.answer(msg, parse_mode="Markdown")

@router.callback_query(F.data.startswith("disp_sel_cour_"))
async def cb_disp_sel_cour(callback: CallbackQuery):
    await callback.answer()
    cour_name = callback.data.replace("disp_sel_cour_", "")
    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    username = sess.get("username", "Диспетчер")

    client = sess.get("disp_client", "Клиент")
    phone = sess.get("disp_phone", "")
    addr = sess.get("disp_address", "")

    new_id = get_next_order_id()
    now_str = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

    new_order = {
        "ID": str(new_id),
        "Дата": now_str,
        "Клиент": client,
        "Телефон": phone,
        "Адрес": addr,
        "Размеры": "Создано Диспетчером",
        "Площадь": "0",
        "Сумма": "0",
        "Статус": "Ожидает забора",
        "Курьер": cour_name,
        "Диспетчер": username,
        "Район": "Самарканд",
        "Язык": "Русский язык",
        "Локация": "",
        "Оплачено": "0",
        "Тип оплаты": "Наличные",
        "Причина": "Оформлено Диспетчером в боте"
    }

    orders = load_json_file(BACKUP_FILE, [])
    orders.insert(0, new_order)
    save_json_file(BACKUP_FILE, orders)

    sess.pop("state", None)
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)

    await callback.message.answer(f"🎉 **Заказ №{new_id} успешно оформлен!**\n👤 Клиент: {client}\n📞 Тел: {phone}\n🏠 Адрес: {addr}\n🚚 Назначен курьер: `{cour_name}`", reply_markup=get_dispatcher_main_keyboard(), parse_mode="Markdown")

    if notify_courier_func:
        asyncio.create_task(notify_courier_func(f"📥 **Вам назначен новый заказ №{new_id}!**\n👤 Клиент: {client}\n📞 Тел: {phone}\n🏠 Адрес: {addr}", target_courier=cour_name))

@router.callback_query(F.data.startswith("disp_set_cour_"))
async def cb_disp_set_cour(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    if len(parts) < 5:
        return

    oid = parts[3]
    cour_name = parts[4]
    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    username = sessions.get(chat_id, {}).get("username", "Диспетчер")

    orders = load_json_file(BACKUP_FILE, [])
    for o in orders:
        if str(o.get("ID")) == str(oid):
            o["Курьер"] = cour_name
            o["Диспетчер"] = username
            break

    save_json_file(BACKUP_FILE, orders)
    await callback.message.answer(f"✅ **Заказ №{oid} назначен на курьера {cour_name}!**", parse_mode="Markdown")

    if notify_courier_func:
        asyncio.create_task(notify_courier_func(f"🚚 **Вам переназначен заказ №{oid}!**", target_courier=cour_name))

@router.callback_query(F.data.startswith("disp_reassign_"))
async def cb_disp_reassign(callback: CallbackQuery):
    await callback.answer()
    oid = callback.data.replace("disp_reassign_", "").strip()
    couriers = get_couriers_list()
    buttons = []
    for c in couriers:
        buttons.append([InlineKeyboardButton(text=f"🚚 Назначить на {c}", callback_data=f"disp_set_cour_{oid}_{c}")])

    await callback.message.answer(f"🚚 Выберите нового курьера для заказа №{oid}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("disp_msg_cour_"))
async def cb_disp_msg_cour(callback: CallbackQuery):
    await callback.answer()
    cour_target = callback.data.replace("disp_msg_cour_", "").strip()
    chat_id = str(callback.message.chat.id)
    sessions = load_json_file(SESSIONS_FILE, {})
    sess = sessions.get(chat_id, {})
    sess["state"] = "disp_sending_msg"
    sess["target_cour"] = cour_target
    sessions[chat_id] = sess
    save_json_file(SESSIONS_FILE, sessions)

    await callback.message.answer(f"💬 Введите **текст сообщения** для `{cour_target}`:")
