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
    token = cfg.get("bot_token", "").strip()
    if not token:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return token


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


def format_phone_number(phone_raw):
    clean_phone = ''.join(filter(str.isdigit, str(phone_raw)))
    if len(clean_phone) >= 9:
        cp = clean_phone[-9:]
        return f"+998 {cp[:2]} {cp[2:5]} {cp[5:7]} {cp[7:]}"
    return "+998 90 000 00 00"


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

    # ---------------- 1. ОБРАБОТКА CALLBACK КНОПОК ----------------
    if callback_query:
        cb_id = callback_query.get("id")
        chat_id = str(callback_query["message"]["chat"]["id"])
        cb_data = callback_query.get("data", "")
        sess = sessions.get(chat_id, {})
        lang = sess.get("lang", "ru")

        if cb_id:
            send_tg_request(token, "answerCallbackQuery", {"callback_query_id": cb_id, "text": "✅"})

        if not sess or sess.get("step") != "authenticated":
            send_message(token, chat_id, "⚠️ Вы не авторизованы. Отправьте /start!", get_remove_keyboard())
            return

        # Подтверждение создания заказа
        if cb_data == "ord_confirm_yes":
            draft = sess.get("draft", {})
            new_id = get_next_id_from_backup()
            user_name = sess.get("username", "Пользователь")
            user_role = sess.get("role", "Dispatcher")

            new_order = {
                "ID": new_id,
                "Дата": datetime.now().strftime("%d.%m.%Y, %H:%M:%S"),
                "Клиент": draft.get("client", "Клиент"),
                "Телефон": format_phone_number(draft.get("phone", "")),
                "Адрес": draft.get("address", "-"),
                "Размеры": draft.get("items", "Ковры"),
                "Площадь": "0",
                "Сумма": 0,
                "Статус": "Ожидает забора",
                "Курьер": user_name if is_courier_role(user_role) else "Не назначен",
                "Диспетчер": f"Telegram ({user_name})",
                "Район": "Сиёб (Siyob)",
                "Язык": "Русский язык",
                "Локация": "-",
                "Оплачено": 0,
                "Тип оплаты": "-",
                "Причина": "-"
            }

            orders = load_json_file(BACKUP_FILE, [])
            orders.append(new_order)
            save_json_file(BACKUP_FILE, orders)

            # Сброс визарда
            sess.pop("flow", None)
            sess.pop("flow_step", None)
            sess.pop("draft", None)
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            if lang == "uz":
                succ_msg = f"🎉 <b>YANGI BUYURTMA №{new_id} MUVAFFAQIYATLI YARATILDI!</b>\n\nCRM-ga qo'shildi va kuryerlarga yuborildi."
            else:
                succ_msg = f"🎉 <b>НОВЫЙ ЗАКАЗ №{new_id} УСПЕШНО СОЗДАН!</b>\n\nДобавлен в CRM и доступен на сайте."

            send_message(token, chat_id, succ_msg, get_keyboard_by_role(user_role, lang))
            return

        if cb_data == "ord_confirm_no":
            sess["flow"] = "create_order"
            sess["flow_step"] = "name"
            sess["draft"] = {}
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            if lang == "uz":
                msg = "🔄 <b>Qaytadan kiritish:</b>\n👤 <b>1-bosqich:</b> Mijoz ismini kiriting:"
            else:
                msg = "🔄 <b>Заполнение заново:</b>\n👤 <b>Шаг 1 из 4:</b> Введите имя клиента:"
            send_message(token, chat_id, msg)
            return

        if cb_data.startswith("edit_order_"):
            order_id = cb_data.replace("edit_order_", "").strip()
            orders = load_json_file(BACKUP_FILE, [])
            matched = [o for o in orders if str(o.get("ID")) == str(order_id)]
            if matched:
                o = matched[0]
                
                # Список курьеров для назначения
                users = load_json_file(USERS_BACKUP_FILE, [])
                couriers = [u.get("Username") for u in users if is_courier_role(u.get("Role"))]
                if not couriers:
                    couriers = ["akobir", "firuz"]

                cour_btns = [{"text": f"🚗 {c}", "callback_data": f"setcour_{c}_{order_id}"} for c in couriers[:4]]

                edit_buttons = {
                    "inline_keyboard": [
                        [
                            {"text": "📄 Забор", "callback_data": f"st_pickup_{order_id}"},
                            {"text": "🧺 В цех", "callback_data": f"st_shop_{order_id}"},
                            {"text": "🚚 Готов", "callback_data": f"st_ready_{order_id}"},
                            {"text": "✅ Выполнен", "callback_data": f"st_done_{order_id}"}
                        ],
                        cour_btns
                    ]
                }
                edit_msg = (
                    f"✏️ <b>ИЗМЕНЕНИЕ И УПРАВЛЕНИЕ ЗАКАЗОМ №{order_id}:</b>\n\n"
                    f"👤 <b>Клиент:</b> {o.get('Клиент')}\n"
                    f"🚗 <b>Текущий курьер:</b> {o.get('Курьер')}\n"
                    f"📊 <b>Текущий статус:</b> {o.get('Статус')}\n\n"
                    "<i>Выберите новый статус или назначьте курьера ниже:</i>"
                ) if lang == "ru" else (
                    f"✏️ <b>BUYURTMA №{order_id} HOLATINI O'ZGARTIRISH:</b>\n\n"
                    f"👤 <b>Mijoz:</b> {o.get('Клиент')}\n"
                    f"🚗 <b>Kuryer:</b> {o.get('Курьер')}\n"
                    f"📊 <b>Joriy holat:</b> {o.get('Статус')}\n\n"
                    "<i>Yangi holatni tanlang yoki kuryerni tayinlang:</i>"
                )
                send_message(token, chat_id, edit_msg, edit_buttons)
            return

        # Назначение курьера
        if cb_data.startswith("setcour_"):
            parts = cb_data.split("_")
            if len(parts) >= 3:
                cour_name = parts[1]
                order_id = parts[2]
                orders = load_json_file(BACKUP_FILE, [])
                for o in orders:
                    if str(o.get("ID")) == str(order_id):
                        o["Курьер"] = cour_name
                        break
                save_json_file(BACKUP_FILE, orders)
                send_message(token, chat_id, f"✅ <b>Заказ №{order_id} назначен курьеру:</b> «{cour_name}»!", get_keyboard_by_role(sess.get("role"), lang))
            return

        # Изменение статуса заказа
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
                    send_message(token, chat_id, f"✅ <b>Заказ №{order_id} переведен в статус:</b> «{new_st}»!", get_keyboard_by_role(sess.get("role"), lang))
                else:
                    send_message(token, chat_id, f"⚠️ Заказ №{order_id} не найден.")
        return

    if not message:
        return

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()
    sess = sessions.get(chat_id, {})
    curr_step = sess.get("step")

    # ---------------- 2. СТАРТ И ВЫХОД (ИНИЦИАЛИЗАЦИЯ) ----------------
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

    # ---------------- 3. ШАГ 1: ВЫБОР ЯЗЫКА ----------------
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

    # ---------------- 4. ШАГ 2: АВТОРИЗАЦИЯ (ВВОД ЛОГИНА И ПАРОЛЯ) ----------------
    if curr_step == "login" or sess.get("step") != "authenticated":
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
        return

    # ---------------- 5. ШАГ 3: АВТОРИЗОВАННЫЕ ПОЛЬЗОВАТЕЛИ ----------------
    user_name = sess.get("username", "Пользователь")
    user_role = sess.get("role", "Courier")
    lang = sess.get("lang", "ru")

    flow = sess.get("flow")
    flow_step = sess.get("flow_step")
    draft = sess.get("draft", {})

    # ==================== ВИЗАРД 1: ПОШАГОВОЕ ДОБАВЛЕНИЕ ЗАКАЗА ====================
    if flow == "create_order":
        if flow_step == "name":
            draft["client"] = text
            sess["flow_step"] = "phone"
            sess["draft"] = draft
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            if lang == "uz":
                msg = "📞 <b>2-bosqich:</b> Mijoz telefon raqamini kiriting (masalan: <code>901234567</code>):"
            else:
                msg = "📞 <b>Шаг 2 из 4:</b> Введите номер телефона клиента (например: <code>901234567</code>):"
            send_message(token, chat_id, msg)
            return

        elif flow_step == "phone":
            draft["phone"] = text
            sess["flow_step"] = "address"
            sess["draft"] = draft
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            if lang == "uz":
                msg = "🏠 <b>3-bosqich:</b> Tuman va aniq manzilni kiriting:"
            else:
                msg = "🏠 <b>Шаг 3 из 4:</b> Введите район и точный адрес клиента:"
            send_message(token, chat_id, msg)
            return

        elif flow_step == "address":
            draft["address"] = text
            sess["flow_step"] = "items"
            sess["draft"] = draft
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            if lang == "uz":
                msg = "🧺 <b>4-bosqich:</b> Buyumlar tavsifi va sonini kiriting (masalan: <code>2 ta gilam</code>):"
            else:
                msg = "🧺 <b>Шаг 4 из 4:</b> Введите описание и количество вещей (напр: <code>2 ковра</code>):"
            send_message(token, chat_id, msg)
            return

        elif flow_step == "items":
            draft["items"] = text
            sess["flow_step"] = "confirm"
            sess["draft"] = draft
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            formatted_phone = format_phone_number(draft.get("phone", ""))
            confirm_preview = (
                "📝 <b>ПРОВЕРКА ВВЕДЕННЫХ ДАННЫХ ЗАКАЗА:</b>\n\n"
                f"👤 <b>Имя клиента:</b> {draft.get('client')}\n"
                f"📞 <b>Телефон:</b> {formatted_phone}\n"
                f"🏠 <b>Адрес:</b> {draft.get('address')}\n"
                f"🧺 <b>Вещи:</b> {draft.get('items')}\n\n"
                "<i>Всё записано верно? Нажмите «Одобрить» или «Заполнить заново»:</i>"
            ) if lang == "ru" else (
                "📝 <b>BUYURTMA MA'LUMOTLARINI TEKSHIRISH:</b>\n\n"
                f"👤 <b>Mijoz:</b> {draft.get('client')}\n"
                f"📞 <b>Telefon:</b> {formatted_phone}\n"
                f"🏠 <b>Manzil:</b> {draft.get('address')}\n"
                f"🧺 <b>Buyumlar:</b> {draft.get('items')}\n\n"
                "<i>Ma'lumotlar to'g'rimi? Tasdiqlash tugmasini bosing:</i>"
            )

            inline_confirm_btns = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Одобрить и создать", "callback_data": "ord_confirm_yes"},
                        {"text": "🔄 Заполнить заново", "callback_data": "ord_confirm_no"}
                    ]
                ]
            }
            send_message(token, chat_id, confirm_preview, inline_confirm_btns)
            return

    # ==================== ВИЗАРД 2: ПОШАГОВЫЙ КАЛЬКУЛЯТОР МОЙЩИКА ====================
    if flow == "calc_size":
        if flow_step == "order_id":
            target_id = ''.join(filter(str.isdigit, text.strip()))
            orders = load_json_file(BACKUP_FILE, [])
            matched = [o for o in orders if str(o.get("ID")) == str(target_id)]
            if not matched:
                send_message(token, chat_id, f"⚠️ Заказ №{target_id} не найден. Введите другой № заказа:")
                return

            draft["calc_order_id"] = target_id
            sess["flow_step"] = "width"
            sess["draft"] = draft
            sessions[chat_id] = sess
            save_json_file(SESSIONS_FILE, sessions)

            msg = "📏 <b>Шаг 1 из 3:</b> Введите <b>ширину</b> ковра в метрах (например: <code>2.5</code>):" if lang == "ru" else "📏 <b>1-bosqich:</b> Gilam <b>enini</b> kiriting (masalan: <code>2.5</code>):"
            send_message(token, chat_id, msg)
            return

        elif flow_step == "width":
            try:
                w_val = float(text.replace(",", "."))
                draft["width"] = w_val
                sess["flow_step"] = "length"
                sess["draft"] = draft
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)

                msg = "📏 <b>Шаг 2 из 3:</b> Введите <b>длину</b> ковра в метрах (например: <code>3.0</code>):" if lang == "ru" else "📏 <b>2-bosqich:</b> Gilam <b>bo'yini</b> kiriting (masalan: <code>3.0</code>):"
                send_message(token, chat_id, msg)
            except Exception:
                send_message(token, chat_id, "⚠️ Число введено неверно. Введите ширину в метрах (напр. <code>2.5</code>):")
            return

        elif flow_step == "length":
            try:
                l_val = float(text.replace(",", "."))
                draft["length"] = l_val
                sess["flow_step"] = "price"
                sess["draft"] = draft
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)

                msg = "💰 <b>Шаг 3 из 3:</b> Введите цену за 1 кв.м в сумах (например: <code>15000</code>):" if lang == "ru" else "💰 <b>3-bosqich:</b> 1 kv.m narxini kiriting (masalan: <code>15000</code>):"
                send_message(token, chat_id, msg)
            except Exception:
                send_message(token, chat_id, "⚠️ Число введено неверно. Введите длину в метрах (напр. <code>3.0</code>):")
            return

        elif flow_step == "price":
            try:
                p_val = float(text.replace(",", ".").replace(" ", ""))
                w_val = float(draft.get("width", 0))
                l_val = float(draft.get("length", 0))
                area = round(w_val * l_val, 2)
                total_price = int(area * p_val)

                target_id = draft.get("calc_order_id")
                orders = load_json_file(BACKUP_FILE, [])
                for o in orders:
                    if str(o.get("ID")) == str(target_id):
                        o["Площадь"] = str(area)
                        o["Сумма"] = total_price
                        o["Размеры"] = f"Ковер {w_val}м x {l_val}м ({area} кв.м)"
                        o["Статус"] = "В цеху"
                        break
                save_json_file(BACKUP_FILE, orders)

                # Сброс визарда
                sess.pop("flow", None)
                sess.pop("flow_step", None)
                sess.pop("draft", None)
                sessions[chat_id] = sess
                save_json_file(SESSIONS_FILE, sessions)

                succ_calc = (
                    f"🎉 <b>ИЗМЕРЕНИЕ УСПЕШНО СОХРАНЕНО В CRM!</b>\n\n"
                    f"📦 <b>Заказ №{target_id}</b>\n"
                    f"📐 <b>Размер:</b> {w_val}м x {l_val}м\n"
                    f"📊 <b>Площадь:</b> {area} кв.м\n"
                    f"💰 <b>Итоговая стоимость:</b> {total_price:,.0f} сум"
                )
                send_message(token, chat_id, succ_calc, get_keyboard_by_role(user_role, lang))
            except Exception as e:
                send_message(token, chat_id, f"⚠️ Ошибка расчета: {e}. Введите цену за кв.м еще раз:")
            return

    # ==================== СТАРТ ПОШАГОВЫХ ВИЗАРДОВ ПО КНОПКАМ ====================
    if text in ["➕ Новый заказ", "➕ Yangi buyurtma", "➕ Новый заказ (Забор)", "➕ Yangi buyurtma (Olib ketish)"]:
        sess["flow"] = "create_order"
        sess["flow_step"] = "name"
        sess["draft"] = {}
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        msg = "👤 <b>Шаг 1 из 4:</b> Введите имя клиента:" if lang == "ru" else "👤 <b>1-bosqich:</b> Mijoz ismini kiriting:"
        send_message(token, chat_id, msg)
        return

    if text in ["📏 Измерка ковров (Калькулятор)", "📏 Gilamlarni o'lchash"]:
        sess["flow"] = "calc_size"
        sess["flow_step"] = "order_id"
        sess["draft"] = {}
        sessions[chat_id] = sess
        save_json_file(SESSIONS_FILE, sessions)

        msg = "📦 <b>Введите ID заказа для внесения размеров (например: <code>5225</code>):</b>" if lang == "ru" else "📦 <b>O'lcham kiritish uchun buyurtma ID-sini kiriting (masalan: <code>5225</code>):</b>"
        send_message(token, chat_id, msg)
        return

    if text in ["✏️ Изменение заказов", "✏️ Buyurtmani tahrirlash"]:
        msg = "✏️ Напишите № заказа, который вы хотите изменить (например: <code>5202</code>):" if lang == "ru" else "✏️ Tahrirlamoqchi bo'lgan buyurtma ID-sini kiriting (masalan: <code>5202</code>):"
        send_message(token, chat_id, msg, get_keyboard_by_role(user_role, lang))
        return

    # ===== ПРОСМОТР И ПОИСК ЗАКАЗОВ =====
    if text in ["📋 История заказов", "📋 Buyurtmalar tarixi", "📋 Все заказы"]:
        orders = load_json_file(BACKUP_FILE, [])
        resp = f"📋 <b>Последние заказы ({len(orders)}):</b>\n\n"
        for o in orders[-8:][::-1]:
            resp += f"📦 <b>№{o.get('ID')}</b> | 👤 {o.get('Клиент')} | 📊 {o.get('Статус')}\n"
        send_message(token, chat_id, resp, get_keyboard_by_role(user_role, lang))
        return

    if text in ["📦 Ожидают забора", "📦 Olib ketish kutilmoqda"]:
        orders = load_json_file(BACKUP_FILE, [])
        pickup_orders = [o for o in orders if "забор" in str(o.get("Статус","")).lower() and (str(o.get("Курьер","")).lower() in [user_name.lower(), "не назначен", ""] or not o.get("Курьер"))]
        if not pickup_orders:
            send_message(token, chat_id, "ℹ️ Нет заказов на забор.", get_keyboard_by_role(user_role, lang))
            return
        resp = f"📦 <b>Заказы ожидающие забора ({len(pickup_orders)}):</b>\n\n"
        for o in pickup_orders:
            resp += f"📦 <b>№{o.get('ID')}</b> | 👤 {o.get('Клиент')} ({o.get('Телефон')})\n🏠 {o.get('Адрес')}\n\n"
        send_message(token, chat_id, resp, get_keyboard_by_role(user_role, lang))
        return

    if text in ["🚚 Готовые заказы (На доставку)", "🚚 Tayyor buyurtmalar"]:
        orders = load_json_file(BACKUP_FILE, [])
        ready_orders = [o for o in orders if "Готов" in str(o.get("Статус",""))]
        if not ready_orders:
            send_message(token, chat_id, "ℹ️ Нет готовых заказов к выдаче.", get_keyboard_by_role(user_role, lang))
            return
        resp = f"🚚 <b>Готовые заказы к выдаче ({len(ready_orders)}):</b>\n\n"
        for o in ready_orders:
            resp += f"📦 <b>№{o.get('ID')}</b> | 👤 {o.get('Клиент')} ({o.get('Телефон')})\n💰 К оплате: {o.get('Сумма')} сум\n\n"
        send_message(token, chat_id, resp, get_keyboard_by_role(user_role, lang))
        return

    if text in ["🧼 Мыто / Не мыто (Статусы)", "🧼 Yuvilgan / Yuvilmagan", "🧺 Заказы в цеху", "🧺 Sexdagi buyurtmalar"]:
        orders = load_json_file(BACKUP_FILE, [])
        shop_orders = [o for o in orders if any(k in str(o.get("Статус","")).lower() for k in ["цех", "стирк", "мойк", "в цеху", "yuvish"])]
        if not shop_orders:
            send_message(token, chat_id, "🎉 В цеху чисто! Все ковры помыты.", get_keyboard_by_role(user_role, lang))
            return
        resp = f"🧺 <b>Заказы в цеху на стирку ({len(shop_orders)}):</b>\n\n"
        for o in shop_orders:
            resp += f"📦 <b>№{o.get('ID')}</b> | 🧺 {o.get('Размеры')} | 📊 {o.get('Статус')}\n"
        send_message(token, chat_id, resp, get_keyboard_by_role(user_role, lang))
        return

    if text.startswith("🔍") or text.startswith("/search") or text in ["🔍 Поиск заказов", "🔍 Buyurtmalarni qidirish", "🔍 Buyurtma va holat"]:
        send_message(token, chat_id, "🔍 Напишите № заказа или телефон для поиска (например: <code>5200</code> или <code>901234567</code>):", get_keyboard_by_role(user_role, lang))
        return

    # Авто-поиск по номеру заказа (ID) или номеру телефона
    clean_digits = ''.join(filter(str.isdigit, text))
    if len(clean_digits) >= 4 and not text.lower().startswith("заказ:"):
        orders = load_json_file(BACKUP_FILE, [])
        matched = []
        for o in orders:
            if clean_digits in str(o.get("ID")) or clean_digits in ''.join(filter(str.isdigit, str(o.get("Телефон")))):
                matched.append(o)

        if matched:
            o = matched[0]
            target_id = str(o.get("ID"))

            # Для Диспетчера показываем ТОЛЬКО кнопку "✏️ Изменить информацию" (согласно фото 4)
            if not is_courier_role(user_role) and not is_washer_role(user_role):
                inline_buttons = {
                    "inline_keyboard": [
                        [
                            {"text": "✏️ Изменить информацию", "callback_data": f"edit_order_{target_id}"} if lang == "ru" else {"text": "✏️ Ma'lumotlarni tahrirlash", "callback_data": f"edit_order_{target_id}"}
                        ]
                    ]
                }
            else:
                # Для Курьеров и Мойщиков быстрые кнопки смены статуса
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
                f"💰 <b>Сумма:</b> {o.get('Сумма')} сум\n"
                f"🚗 <b>Курьер:</b> {o.get('Курьер')}"
            )
            send_message(token, chat_id, info_text, inline_buttons)
            return

    # Создание заказа из свободного текста ТОЛЬКО при префиксе "заказ:" или "yangi buyurtma:"
    if text.lower().startswith("заказ:") or text.lower().startswith("yangi buyurtma:"):
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

    reply_msg = "ℹ️ Выберите нужную команду на клавиатуре ниже или введите № заказа / телефон для поиска."
    send_message(token, chat_id, reply_msg, get_keyboard_by_role(user_role, lang))


def run_telegram_bot():
    """Основной цикл опроса (Long Polling) Telegram Бот API"""
    token = get_tg_token()
    if not token:
        print("[TG Bot] Токен Telegram бота не найден в telegram_config.json!")
        return

    print(f"🚀 [TG Bot Started] Бот запускается для токена: {token[:10]}...")

    send_tg_request(token, "setWebhook", {"url": "", "drop_pending_updates": True})
    time.sleep(0.5)
    send_tg_request(token, "deleteWebhook", {"drop_pending_updates": True})

    first_res = send_tg_request(token, "getUpdates", {"offset": -1, "timeout": 1})
    offset = 0
    if first_res and first_res.get("ok") and first_res.get("result"):
        last_upd = first_res["result"][-1]
        offset = last_upd["update_id"] + 1

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
