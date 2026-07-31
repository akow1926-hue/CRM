import os
import sys
import json
import time
import urllib.request
import urllib.parse
import re
from datetime import datetime

# Файлы конфигурации и данных CRM
CONFIG_FILE = "telegram_config.json"
BACKUP_FILE = "backup_orders.json"
USERS_BACKUP_FILE = "backup_users.json"
SESSIONS_FILE = "telegram_sessions.json"


def load_json_file(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json_file(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def get_tg_token():
    cfg = load_json_file(CONFIG_FILE, {})
    return cfg.get("bot_token", "").strip()


def send_tg_request(token, method, payload=None):
    """Отправка HTTP запроса к Telegram Bot API (без внешних зависимостей)"""
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if payload:
            data_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
        else:
            req = urllib.request.Request(url)

        with urllib.request.urlopen(req, timeout=25) as resp:
            res_text = resp.read().decode('utf-8')
            return json.loads(res_text)
    except Exception as e:
        print(f"[TG Error] Method {method} failed: {e}")
        return None


def send_message(token, chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return send_tg_request(token, "sendMessage", payload)


def get_lang_keyboard():
    """Клавиатура выбора языка при старте бота"""
    return {
        "keyboard": [
            [{"text": "🇷🇺 Русский язык"}, {"text": "🇺🇿 O'zbek tili"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }


def get_remove_keyboard():
    """Скрытие старой клавиатуры для неавторизованных пользователей"""
    return {"remove_keyboard": True}


def is_courier_role(role):
    r = str(role).lower()
    return "courier" in r or "курьер" in r or "доставщик" in r or "yuboruvchi" in r or "kuryer" in r


def is_washer_role(role):
    r = str(role).lower()
    return "washer" in r or "cleaner" in r or "мойщик" in r or "чистильщик" in r or "yuvuvchi" in r or "tozalovchi" in r or "sex" in r


def is_admin_role(role):
    r = str(role).lower()
    return "admin" in r or "админ" in r or "administrator" in r


def get_keyboard_by_role(role, lang="ru"):
    """Клавиатура для ролей: Диспетчер, Курьер, Мойщик (Админ исключен)"""
    if lang == "uz":
        if is_courier_role(role):
            return {
                "keyboard": [
                    [{"text": "📦 Olib ketish kutilmoqda"}, {"text": "🚚 Tayyor buyurtmalar"}],
                    [{"text": "➕ Yangi buyurtma (Olib ketish)"}, {"text": "🔍 Buyurtma va holat"}],
                    [{"text": "🚪 Chiqish (/logout)"}]
                ],
                "resize_keyboard": True
            }
        elif is_washer_role(role):
            return {
                "keyboard": [
                    [{"text": "📏 Gilamlarni o'lchash"}, {"text": "🧼 Yuvilgan / Yuvilmagan"}],
                    [{"text": "🧺 Sexdagi buyurtmalar"}, {"text": "🔍 Buyurtmani qidirish"}],
                    [{"text": "🚪 Chiqish (/logout)"}]
                ],
                "resize_keyboard": True
            }
        else: # Dispatcher (Диспетчер)
            return {
                "keyboard": [
                    [{"text": "➕ Yangi buyurtma"}, {"text": "📋 Buyurtmalar tarixi"}],
                    [{"text": "🔍 Buyurtmalarni qidirish"}, {"text": "✏️ Buyurtmani tahrirlash"}],
                    [{"text": "🚪 Chiqish (/logout)"}]
                ],
                "resize_keyboard": True
            }
    else: # Russian
        if is_courier_role(role):
            return {
                "keyboard": [
                    [{"text": "📦 Ожидают забора"}, {"text": "🚚 Готовые заказы (На доставку)"}],
                    [{"text": "➕ Новый заказ (Забор)"}, {"text": "🔍 Поиск и статус заказа"}],
                    [{"text": "🚪 Выйти из бота (/logout)"}]
                ],
                "resize_keyboard": True
            }
        elif is_washer_role(role):
            return {
                "keyboard": [
                    [{"text": "📏 Измерка ковров (Калькулятор)"}, {"text": "🧼 Мыто / Не мыто (Статусы)"}],
                    [{"text": "🧺 Заказы в цеху"}, {"text": "🔍 Поиск заказа"}],
                    [{"text": "🚪 Выйти из бота (/logout)"}]
                ],
                "resize_keyboard": True
            }
        else: # Dispatcher (Диспетчер)
            return {
                "keyboard": [
                    [{"text": "➕ Новый заказ"}, {"text": "📋 История заказов"}],
                    [{"text": "🔍 Поиск заказов"}, {"text": "✏️ Изменение заказов"}],
                    [{"text": "🚪 Выйти из бота (/logout)"}]
                ],
                "resize_keyboard": True
            }


def authenticate_user(login, password):
    """Проверка логина и пароля по файлу backup_users.json"""
    users = load_json_file(USERS_BACKUP_FILE, [])
    for u in users:
        u_name = str(u.get("Username", "")).strip()
        u_pass = str(u.get("Password", "")).strip()
        u_status = str(u.get("Status", "Активен")).strip()
        u_role = str(u.get("Role", "Courier")).strip()

        if u_name.lower() == login.lower() and u_pass == password and u_status != "Заблокирован":
            return {
                "username": u_name,
                "role": u_role
            }
    return None


def parse_order_from_text(text):
    """Естественно-языковой парсер для создания заказа из Telegram"""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    full_str = " ".join(lines)

    phone_match = re.search(r'(\+?998)?[\s\-]?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', full_str)
    phone = phone_match.group(0) if phone_match else ""
    clean_phone = ''.join(filter(str.isdigit, phone))
    if len(clean_phone) >= 9:
        clean_phone = clean_phone[-9:]
        full_phone = f"+998 {clean_phone[:2]} {clean_phone[2:5]} {clean_phone[5:7]} {clean_phone[7:]}"
    else:
        full_phone = "+998 90 000 00 00"

    districts = ["Сиёб", "Багишамальский", "Согдиана", "Микрорайон", "Саттепо", "Железнодорожный", "Самаркандский"]
    matched_district = "Сиёб (Siyob)"
    for d in districts:
        if d.lower() in full_str.lower():
            matched_district = d
            break

    client_name = "Клиент"
    clean_name = re.sub(r'(\+?998)?[\s\-]?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', '', full_str)
    clean_name = re.sub(r'заказ|новый|создай|клиент|адрес|район|тел', '', clean_name, flags=re.IGNORECASE)
    parts = [p.strip() for p in clean_name.split(",") if p.strip()]
    if parts:
        client_name = parts[0][:30]

    return {
        "client": client_name.capitalize(),
        "phone": full_phone,
        "district": matched_district,
        "address": full_str,
        "items": "Ковры (создано из Telegram)"
    }


def get_next_id_from_backup():
    orders = load_json_file(BACKUP_FILE, [])
    max_id = 5218
    for o in orders:
        try:
            val = int(float(str(o.get("ID", 0))))
            if 5200 <= val < 9000 and val > max_id:
                max_id = val
        except Exception:
            pass
    return max_id + 1


PROCESSED_UPDATES = set()

def process_telegram_update(token, update):
    """Обработка входящего сообщения от пользователя Telegram"""
    update_id = update.get("update_id")
    if update_id in PROCESSED_UPDATES:
        return
    if update_id is not None:
        PROCESSED_UPDATES.add(update_id)
        if len(PROCESSED_UPDATES) > 2000:
            PROCESSED_UPDATES.clear()

    message = update.get("message") or update.get("edited_message")
    callback_query = update.get("callback_query")

    sessions = load_json_file(SESSIONS_FILE, {})

    # ---------------- ОБРАБОТКА CALLBACK КНОПОК ----------------
    if callback_query:
        cb_id = callback_query.get("id")
        chat_id = str(callback_query["message"]["chat"]["id"])
        cb_data = callback_query.get("data", "")
        sess = sessions.get(chat_id)

        # Подтверждение клика чтобы кнопка не крутилась бесконечно
        if cb_id:
            send_tg_request(token, "answerCallbackQuery", {"callback_query_id": cb_id, "text": "✅ Обновлено!"})

        if not sess or sess.get("step") != "authenticated":
            send_message(token, chat_id, "⚠️ Вы не авторизованы. Отправьте /start!", get_remove_keyboard())
            return

        if cb_data.startswith("st_"):
            parts = cb_data.split("_")
            if len(parts) >= 3:
                new_st_code = parts[1]
                order_id = parts[2]

                st_map = {
                    "pickup": "Ожидает забора",
                    "shop": "В цеху",
                    "ready": "Готов",
                    "done": "Выполнен"
                }
                new_st = st_map.get(new_st_code, "В цеху")

                orders = load_json_file(BACKUP_FILE, [])
                found = False
                for o in orders:
                    if str(o.get("ID")) == str(order_id):
                        o["Статус"] = new_st
                        found = True
                        break

                if found:
                    save_json_file(BACKUP_FILE, orders)
                    send_message(token, chat_id, f"✅ <b>Заказ №{order_id} переведен в статус:</b> «{new_st}»!", get_keyboard_by_role(sess.get("role"), sess.get("lang", "ru")))
                else:
                    send_message(token, chat_id, f"⚠️ Заказ №{order_id} не найден.")
        return

    if not message:
        return

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()
    sess = sessions.get(chat_id, {})
    curr_step = sess.get("step")

    # ---------------- 1. СТАРТ И ВЫХОД (ИНИЦИАЛИЗАЦИЯ) ----------------
    if text in ["/logout", "🚪 Выйти из бота (/logout)", "🚪 Chiqish (/logout)"]:
        if chat_id in sessions:
            del sessions[chat_id]
            save_json_file(SESSIONS_FILE, sessions)
        send_message(token, chat_id, "🔒 <b>Вы вышли из системы / Tizimdan chiqdingiz.</b>\n\nОтправьте /start для нового входа!", get_remove_keyboard())
        return

    if text == "/start" or not curr_step:
        sessions[chat_id] = {"step": "lang"}
        save_json_file(SESSIONS_FILE, sessions)
        
        start_msg = (
            "👋 <b>Добро пожаловать в Cosmo Cleaning CRM Bot!</b>\n"
            "Пожалуйста, выберите язык общения:\n\n"
            "👋 <b>Cosmo Cleaning CRM Bot-ga xush kelibsiz!</b>\n"
            "Iltimos, muloqot tilini tanlang:"
        )
        send_message(token, chat_id, start_msg, get_lang_keyboard())
        return

    # ---------------- 2. ШАГ 1: ВЫБОР ЯЗЫКА ----------------
    if curr_step == "lang" or text in ["🇷🇺 Русский язык", "🇺🇿 O'zbek tili"]:
        lang = "uz" if "O'zbek" in text else "ru"
        sessions[chat_id] = {
            "step": "login",
            "lang": lang
        }
        save_json_file(SESSIONS_FILE, sessions)

        if lang == "uz":
            prompt = (
                "🌐 <b>O'zbek tili tanlandi.</b>\n\n"
                "🔒 <b>CRM-ga kirish:</b>\n"
                "Iltimos, login va parolingizni joy tashlab kiriting:\n"
                "<code>login parol</code>\n\n"
                "<i>Misol: akobir akobir</i>"
            )
        else:
            prompt = (
                "🌐 <b>Выбран русский язык.</b>\n\n"
                "🔒 <b>Авторизация в CRM:</b>\n"
                "Пожалуйста, введите ваш логин и пароль через пробел:\n"
                "<code>логин пароль</code>\n\n"
                "<i>Пример: akobir akobir</i>"
            )
        send_message(token, chat_id, prompt, get_remove_keyboard())
        return

    # ---------------- 3. ШАГ 2: АВТОРИЗАЦИЯ (ВВОД ЛОГИНА И ПАРОЛЯ) ----------------
    if curr_step == "login" or curr_step != "authenticated":
        parts = text.split()
        lang = sess.get("lang", "ru")

        if len(parts) == 2:
            login_attempt, pass_attempt = parts[0].strip(), parts[1].strip()
            user_auth = authenticate_user(login_attempt, pass_attempt)

            if user_auth:
                user_role = user_auth["role"]

                # Проверка: Админам доступ к боту запрещен!
                if is_admin_role(user_role):
                    if lang == "uz":
                        err_admin = "⚠️ <b>Kirish cheklangan:</b> Administratorlar CRM-ni veb-sayt orqali boshqaradi. Botga kirish faqat xodimlar (Dispetcher, Kuryer, Yuvuvchi) uchun mo'ljallangan."
                    else:
                        err_admin = "⚠️ <b>Доступ ограничен:</b> Администраторы управляют CRM через веб-сайт. Вход в бот предназначен только для линейного персонала (Диспетчеры, Курьеры, Мойщики)."
                    send_message(token, chat_id, err_admin, get_remove_keyboard())
                    return

                # Успешный вход для Диспетчера, Курьера, Мойщика
                sessions[chat_id] = {
                    "step": "authenticated",
                    "username": user_auth["username"],
                    "role": user_role,
                    "lang": lang,
                    "auth_date": datetime.now().strftime("%d.%m.%Y, %H:%M:%S")
                }
                save_json_file(SESSIONS_FILE, sessions)

                # Привязка Chat ID курьера
                if is_courier_role(user_role):
                    cfg = load_json_file(CONFIG_FILE, {})
                    c_chats = cfg.get("courier_chats", {})
                    c_chats[user_auth["username"]] = chat_id
                    cfg["courier_chats"] = c_chats
                    save_json_file(CONFIG_FILE, cfg)

                if lang == "uz":
                    welcome_msg = (
                        f"🎉 <b>MUVAFFAQIYATLI KIRISH!</b>\n\n"
                        f"👤 <b>Foydalanuvchi:</b> {user_auth['username']}\n"
                        f"💼 <b>Lavozim:</b> {user_role}\n\n"
                        f"<i>Lavozimingizga mos tugmalar quyida paydo bo'ldi.</i>"
                    )
                else:
                    welcome_msg = (
                        f"🎉 <b>УСПЕШНАЯ АВТОРИЗАЦИЯ!</b>\n\n"
                        f"👤 <b>Пользователь:</b> {user_auth['username']}\n"
                        f"💼 <b>Роль:</b> {user_role}\n\n"
                        f"<i>Вам доступны функции CRM согласно вашей роли.</i>"
                    )

                send_message(token, chat_id, welcome_msg, get_keyboard_by_role(user_role, lang))
                return
            else:
                if lang == "uz":
                    err_msg = "❌ <b>Kirishda xatolik!</b> Noto'g'ri login yoki parol. Qaytadan kiriting:\n<code>login parol</code>"
                else:
                    err_msg = "❌ <b>Ошибка входа!</b> Неверный логин или пароль. Попробуйте еще раз в формате:\n<code>логин пароль</code>"
                send_message(token, chat_id, err_msg, get_remove_keyboard())
                return
        else:
            if lang == "uz":
                auth_req = "🔒 <b>Iltimos, login va parolingizni joy tashlab kiriting:</b>\n<code>login parol</code>"
            else:
                auth_req = "🔒 <b>Пожалуйста, введите ваш логин и пароль через пробел:</b>\n<code>логин пароль</code>"
            send_message(token, chat_id, auth_req, get_remove_keyboard())
            return

    # ---------------- 4. ШАГ 3: АВТОРИЗОВАННЫЕ КОМАНДЫ (ПО РОЛЯМ) ----------------
    user_name = sess.get("username", "Пользователь")
    user_role = sess.get("role", "Courier")
    lang = sess.get("lang", "ru")

    # ----- ДИСПЕТЧЕР (DISPATCHER) -----
    if not is_courier_role(user_role) and not is_washer_role(user_role):
        if text in ["➕ Новый заказ", "➕ Yangi buyurtma"]:
            msg = "➕ <b>Введите данные клиента:</b>\n<code>Заказ: Иван, 901234567, Сиёб, ул. Навои 14, 2 ковра</code>"
            send_message(token, chat_id, msg, get_keyboard_by_role(user_role, lang))
            return

        if text in ["📋 История заказов", "📋 Buyurtmalar tarixi"]:
            orders = load_json_file(BACKUP_FILE, [])
            resp = f"📋 <b>Последние заказы ({len(orders)}):</b>\n\n"
            for o in orders[-8:][::-1]:
                resp += f"📦 <b>№{o.get('ID')}</b> | 👤 {o.get('Клиент')} | 📊 {o.get('Статус')}\n"
            send_message(token, chat_id, resp, get_keyboard_by_role(user_role, lang))
            return

    # ----- КУРЬЕР (COURIER) -----
    if is_courier_role(user_role):
        if text in ["📦 Ожидают забора", "📦 Olib ketish kutilmoqda"]:
            orders = load_json_file(BACKUP_FILE, [])
            pickup_orders = [o for o in orders if str(o.get("Курьер","")).lower() == user_name.lower() and "забор" in str(o.get("Статус","")).lower()]
            if not pickup_orders:
                send_message(token, chat_id, "ℹ️ Нет заказов на забор.", get_keyboard_by_role(user_role, lang))
                return
            resp = f"📦 <b>Заказы на забор ({len(pickup_orders)}):</b>\n\n"
            for o in pickup_orders:
                resp += f"📦 <b>№{o.get('ID')}</b> | 👤 {o.get('Клиент')} ({o.get('Телефон')})\n🏠 {o.get('Адрес')}\n\n"
            send_message(token, chat_id, resp, get_keyboard_by_role(user_role, lang))
            return

        if text in ["🚚 Готовые заказы (На доставку)", "🚚 Tayyor buyurtmalar"]:
            orders = load_json_file(BACKUP_FILE, [])
            ready_orders = [o for o in orders if "Готов" in str(o.get("Статус",""))]
            if not ready_orders:
                send_message(token, chat_id, "ℹ️ Нет готовых заказов на доставку.", get_keyboard_by_role(user_role, lang))
                return
            resp = f"🚚 <b>Готовые заказы на доставку ({len(ready_orders)}):</b>\n\n"
            for o in ready_orders:
                resp += f"📦 <b>№{o.get('ID')}</b> | 👤 {o.get('Клиент')}\n💰 К оплате: {o.get('Сумма')} сум\n\n"
            send_message(token, chat_id, resp, get_keyboard_by_role(user_role, lang))
            return

    # ----- МОЙЩИК / ЧИСТИЛЬЩИК (WASHER / CLEANER) -----
    if is_washer_role(user_role):
        if text in ["📏 Измерка ковров (Калькулятор)", "📏 Gilamlarni o'lchash"]:
            msg = (
                "📏 <b>Калькулятор измерения ковра:</b>\n\n"
                "Формула: <code>Ширина x Длина x Цена_за_кв.м</code>\n"
                "Пример: 3м x 4м = 12 кв.м x 15,000 сум = <b>180,000 сум</b>"
            )
            send_message(token, chat_id, msg, get_keyboard_by_role(user_role, lang))
            return

        if text in ["🧼 Мыто / Не мыто (Статусы)", "🧼 Yuvilgan / Yuvilmagan", "🧺 Заказы в цеху", "🧺 Sexdagi buyurtmalar"]:
            orders = load_json_file(BACKUP_FILE, [])
            shop_orders = [o for o in orders if "цех" in str(o.get("Статус","")).lower()]
            if not shop_orders:
                send_message(token, chat_id, "🎉 В цеху чисто! Все ковры помыты.", get_keyboard_by_role(user_role, lang))
                return
            resp = f"🧺 <b>Заказы в цеху на стирку ({len(shop_orders)}):</b>\n\n"
            for o in shop_orders:
                resp += f"📦 <b>№{o.get('ID')}</b> | 🧺 {o.get('Размеры')} | 📊 {o.get('Статус')}\n"
            send_message(token, chat_id, resp, get_keyboard_by_role(user_role, lang))
            return

    # ----- ПОИСК И ЕСТЕСТВЕННЫЙ ЯЗЫК ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ -----
    if text.startswith("🔍") or text.startswith("/search"):
        send_message(token, chat_id, "🔍 Напишите № заказа или телефон (например: <code>5200</code>):", get_keyboard_by_role(user_role, lang))
        return

    # Авто-поиск по номеру заказа (4 цифры)
    digit_match = re.findall(r'\b\d{4}\b', text)
    if digit_match and len(text) < 15:
        target_id = digit_match[0]
        orders = load_json_file(BACKUP_FILE, [])
        matched = [o for o in orders if str(o.get("ID")) == str(target_id)]
        if matched:
            o = matched[0]
            inline_buttons = {
                "inline_keyboard": [
                    [
                        {"text": "🧺 В цех", "callback_data": f"st_shop_{target_id}"},
                        {"text": "🚚 Готов", "callback_data": f"st_ready_{target_id}"},
                        {"text": "✅ Выполнен", "callback_data": f"st_done_{target_id}"}
                    ]
                ]
            }
            info_text = (
                f"🔎 <b>Заказ №{target_id}:</b>\n\n"
                f"👤 <b>Клиент:</b> {o.get('Клиент')}\n"
                f"📞 <b>Телефон:</b> {o.get('Телефон')}\n"
                f"🏠 <b>Адрес:</b> {o.get('Район')}, {o.get('Адрес')}\n"
                f"🧺 <b>Вещи:</b> {o.get('Размеры')}\n"
                f"📊 <b>Статус:</b> {o.get('Статус')}\n"
                f"💰 <b>Сумма:</b> {o.get('Сумма')} сум"
            )
            send_message(token, chat_id, info_text, inline_buttons)
            return

    # Парсер создания заказа по тексту
    has_phone = bool(re.search(r'(\+?998)?[\s\-]?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text))
    if "заказ" in text.lower() or "клиент" in text.lower() or has_phone:
        parsed = parse_order_from_text(text)
        new_id = get_next_id_from_backup()

        new_order = {
            "ID": new_id,
            "Дата": datetime.now().strftime("%d.%m.%Y, %H:%M:%S"),
            "Клиент": parsed["client"],
            "Телефон": parsed["phone"],
            "Адрес": parsed["address"],
            "Размеры": parsed["items"],
            "Площадь": "0",
            "Сумма": 0,
            "Статус": "Ожидает забора",
            "Курьер": user_name if is_courier_role(user_role) else "Не назначен",
            "Диспетчер": f"Telegram ({user_name})",
            "Район": parsed["district"],
            "Язык": "Русский язык",
            "Локация": "-",
            "Оплачено": 0,
            "Тип оплаты": "-",
            "Причина": "-"
        }

        orders = load_json_file(BACKUP_FILE, [])
        orders.append(new_order)
        save_json_file(BACKUP_FILE, orders)

        confirm_text = (
            f"🎉 <b>НОВЫЙ ЗАКАЗ №{new_id} СОЗДАН!</b>\n\n"
            f"👤 <b>Клиент:</b> {parsed['client']}\n"
            f"📞 <b>Телефон:</b> {parsed['phone']}\n"
            f"🏠 <b>Адрес:</b> {parsed['address']}\n"
            f"🟡 <b>Статус:</b> Ожидает забора"
        )
        send_message(token, chat_id, confirm_text, get_keyboard_by_role(user_role, lang))
        return

    reply_msg = "ℹ️ Выберите нужную команду на клавиатуре ниже или напишите № заказа для поиска."
    send_message(token, chat_id, reply_msg, get_keyboard_by_role(user_role, lang))


def run_telegram_bot():
    """Основной цикл опроса (Long Polling) Telegram Бот API"""
    token = get_tg_token()
    if not token:
        print("[TG Bot] Токен Telegram бота не найден в telegram_config.json!")
        return

    print(f"🚀 [TG Bot Started] Бот запускается для токена: {token[:10]}...")

    send_tg_request(token, "deleteWebhook")

    offset = 0
    while True:
        try:
            res = send_tg_request(token, "getUpdates", {"offset": offset, "timeout": 20})
            if res and res.get("ok"):
                updates = res.get("result", [])
                for u in updates:
                    offset = u["update_id"] + 1
                    process_telegram_update(token, u)
            time.sleep(1)
        except KeyboardInterrupt:
            print("[TG Bot] Остановлен пользователем.")
            break
        except Exception as e:
            print(f"[TG Bot Error]: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_telegram_bot()
