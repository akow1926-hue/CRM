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


def get_keyboard_by_role(role):
    """Клавиатура в зависимости от роли авторизованного пользователя"""
    if role in ["Courier", "Доставщик (Курьер)", "Yuboruvchi (Kuryer)", "Курьер"]:
        return {
            "keyboard": [
                [{"text": "📋 Мои заказы"}, {"text": "➕ Новый забор"}],
                [{"text": "🔍 Поиск заказа"}, {"text": "🚪 Выйти из бота (/logout)"}]
            ],
            "resize_keyboard": True
        }
    elif role in ["Washer", "Cleaner", "Мойщик", "Чистильщик"]:
        return {
            "keyboard": [
                [{"text": "🧺 Заказы в цеху"}, {"text": "🔍 Поиск заказа"}],
                [{"text": "🚪 Выйти из бота (/logout)"}]
            ],
            "resize_keyboard": True
        }
    else: # Admin & Dispatcher
        return {
            "keyboard": [
                [{"text": "📋 Все заказы"}, {"text": "📊 Статистика CRM"}],
                [{"text": "➕ Новый заказ"}, {"text": "🔍 Поиск заказа"}],
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


def process_telegram_update(token, update):
    """Обработка входящего сообщения от пользователя Telegram"""
    message = update.get("message") or update.get("edited_message")
    callback_query = update.get("callback_query")

    sessions = load_json_file(SESSIONS_FILE, {})

    if callback_query:
        chat_id = str(callback_query["message"]["chat"]["id"])
        cb_data = callback_query.get("data", "")
        sess = sessions.get(chat_id)

        if not sess:
            send_message(token, chat_id, "⚠️ Вы не авторизованы. Напишите логин и пароль!")
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
                    send_message(token, chat_id, f"✅ <b>Заказ №{order_id} переведен в статус:</b> «{new_st}»!", get_keyboard_by_role(sess.get("role")))
                else:
                    send_message(token, chat_id, f"⚠️ Заказ №{order_id} не найден.")
        return

    if not message:
        return

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()
    sess = sessions.get(chat_id)

    # ---------------- 1. ОБРАБОТКА ВЫХОДА ИЗ СИСТЕМЫ ----------------
    if text in ["/logout", "🚪 Выйти из бота (/logout)"]:
        if chat_id in sessions:
            del sessions[chat_id]
            save_json_file(SESSIONS_FILE, sessions)
        send_message(token, chat_id, "🔒 <b>Вы успешно вышли из системы Cosmo CRM.</b>\nДля входа отправьте логин и пароль!")
        return

    # ---------------- 2. ПРОВЕРКА АВТОРИЗАЦИИ ПОЛЬЗОВАТЕЛЯ ----------------
    if not sess:
        # Проверяем, если сообщение содержит логин и пароль через пробел
        parts = text.split()
        if len(parts) == 2:
            login_attempt, pass_attempt = parts[0].strip(), parts[1].strip()
            user_auth = authenticate_user(login_attempt, pass_attempt)
            
            if user_auth:
                sessions[chat_id] = {
                    "username": user_auth["username"],
                    "role": user_auth["role"],
                    "auth_date": datetime.now().strftime("%d.%m.%Y, %H:%M:%S")
                }
                save_json_file(SESSIONS_FILE, sessions)
                
                # Авто-сохранение Chat ID курьера в telegram_config.json
                if "Courier" in user_auth["role"] or "Курьер" in user_auth["role"]:
                    cfg = load_json_file(CONFIG_FILE, {})
                    c_chats = cfg.get("courier_chats", {})
                    c_chats[user_auth["username"]] = chat_id
                    cfg["courier_chats"] = c_chats
                    save_json_file(CONFIG_FILE, cfg)

                welcome_msg = (
                    f"🎉 <b>АВТОРИЗАЦИЯ УСПЕШНА!</b>\n\n"
                    f"👤 <b>Пользователь:</b> {user_auth['username']}\n"
                    f"💼 <b>Роль:</b> {user_auth['role']}\n\n"
                    f"<i>Вам доступны функции CRM согласно вашей роли.</i>"
                )
                send_message(token, chat_id, welcome_msg, get_keyboard_by_role(user_auth["role"]))
                return
            else:
                send_message(token, chat_id, "❌ <b>Ошибка авторизации!</b>\nНеверный логин или пароль. Попробуйте еще раз в формате:\n<code>логин пароль</code>")
                return
        else:
            auth_prompt = (
                "🔒 <b>Вход в Cosmo CRM Bot:</b>\n\n"
                "Для доступа к управлению заказами введите ваш <b>логин и пароль</b> через пробел:\n"
                "<code>логин пароль</code>\n\n"
                "<i>Пример: akobir 123456</i>"
            )
            send_message(token, chat_id, auth_prompt)
            return

    # ---------------- 3. АВТОРИЗОВАННЫЕ КОМАНДЫ ----------------
    user_name = sess.get("username", "Пользователь")
    user_role = sess.get("role", "Courier")

    if text in ["/start", "Привет", "помощь", "❓ Помощь"]:
        welcome_text = (
            f"👋 <b>Привет, {user_name}!</b>\n"
            f"💼 <b>Ваша роль:</b> {user_role}\n\n"
            "🧼 Я <b>Cosmo CRM AI Бот</b> — ваш помощник по управлению заказами.\n\n"
            "<b>Доступные функции:</b>\n"
            "• 📋 <b>Просмотр заказов</b> и изменение статусов\n"
            "• ➕ <b>Создание новых заказов</b> текстом или голосом\n"
            "• 📊 <b>Статистика CRM</b>\n"
            "• 🚪 <b>Выход из аккаунта:</b> /logout\n\n"
            "<i>Выберите команду ниже на клавиатуре!</i>"
        )
        send_message(token, chat_id, welcome_text, get_keyboard_by_role(user_role))
        return

    if text in ["📋 Мои заказы", "📋 Все заказы", "🧺 Заказы в цеху"]:
        orders = load_json_file(BACKUP_FILE, [])
        if not orders:
            send_message(token, chat_id, "ℹ️ Список заказов пуст.", get_keyboard_by_role(user_role))
            return

        # Курьеры видят свои заказы, Админ/Диспетчер видят все
        if "Courier" in user_role or "Курьер" in user_role:
            user_orders = [o for o in orders if str(o.get("Курьер", "")).lower() == user_name.lower() and str(o.get("Статус")) != "Выполнен"]
        else:
            user_orders = [o for o in orders if str(o.get("Статус")) != "Выполнен"][:10]

        if not user_orders:
            send_message(token, chat_id, f"🎉 Нет активных заказов для {user_name}!", get_keyboard_by_role(user_role))
            return

        resp_msg = f"📋 <b>Активные заказы ({len(user_orders)}):</b>\n\n"
        for o in user_orders:
            o_id = o.get("ID")
            client = o.get("Клиент", "-")
            phone = o.get("Телефон", "-")
            address = f"{o.get('Район','')}, {o.get('Адрес','')}".strip(', ')
            st_val = o.get("Статус", "Новый")
            sum_val = o.get("Сумма", 0)

            resp_msg += (
                f"📦 <b>Заказ №{o_id}</b> ({st_val})\n"
                f"👤 {client} ({phone})\n"
                f"🏠 {address}\n"
                f"💰 {sum_val} сум\n\n"
            )

        send_message(token, chat_id, resp_msg, get_keyboard_by_role(user_role))
        return

    if text == "📊 Статистика CRM":
        orders = load_json_file(BACKUP_FILE, [])
        total = len(orders)
        new_cnt = sum(1 for o in orders if o.get("Статус") == "Ожидает забора")
        shop_cnt = sum(1 for o in orders if o.get("Статус") == "В цеху")
        ready_cnt = sum(1 for o in orders if o.get("Статус") == "Готов")
        done_cnt = sum(1 for o in orders if o.get("Статус") == "Выполнен")

        revenue = 0
        for o in orders:
            try:
                revenue += float(str(o.get("Сумма", 0)).replace(" ", "").replace(",", "."))
            except Exception:
                pass

        stats_msg = (
            "📊 <b>Сводка Cosmo Cleaning CRM:</b>\n\n"
            f"📦 <b>Всего заказов:</b> {total}\n"
            f"📄 <b>Ожидают забора:</b> {new_cnt}\n"
            f"🧺 <b>В цеху / Стирка:</b> {shop_cnt}\n"
            f"🚚 <b>Готовы к доставке:</b> {ready_cnt}\n"
            f"✅ <b>Выполнено:</b> {done_cnt}\n\n"
            f"💰 <b>Общая сумма:</b> {revenue:,.0f} сум"
        )
        send_message(token, chat_id, stats_msg, get_keyboard_by_role(user_role))
        return

    if text in ["➕ Новый заказ", "➕ Новый забор"]:
        guide_msg = (
            "➕ <b>Как быстро создать заказ:</b>\n\n"
            "Напишите мне информацию о клиенте в одном сообщении, например:\n"
            "<code>Заказ: Алишер Назаров, 901234567, Сиёб, ул. Навои 14, кв 2, 2 ковра</code>\n\n"
            "ИИ автоматически распознает имя, телефон и адрес и создаст новый номер заказа!"
        )
        send_message(token, chat_id, guide_msg, get_keyboard_by_role(user_role))
        return

    if text.startswith("🔍 Поиск") or text.startswith("/search"):
        send_message(token, chat_id, "🔍 Напишите № заказа или имя клиента для поиска (например: <code>5200</code> или <code>Иван</code>):", get_keyboard_by_role(user_role))
        return

    # ---------------- 4. ИИ ЕСТЕСТВЕННО-ЯЗЫКОВОЙ ОБРАБОТЧИК ----------------
    if "заказ" in text.lower() or "клиент" in text.lower() or any(char.isdigit() for char in text):
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
                    f"🔎 <b>Найден заказ №{target_id}:</b>\n\n"
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
            "Курьер": user_name if "Courier" in user_role or "Курьер" in user_role else "Не назначен",
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
            f"🎉 <b>НОВЫЙ ЗАКАЗ №{new_id} УСПЕШНО СОЗДАН!</b>\n\n"
            f"👤 <b>Клиент:</b> {parsed['client']}\n"
            f"📞 <b>Телефон:</b> {parsed['phone']}\n"
            f"🏠 <b>Адрес/Инфо:</b> {parsed['address']}\n"
            f"📍 <b>Район:</b> {parsed['district']}\n"
            f"🟡 <b>Статус:</b> Ожидает забора\n\n"
            f"<i>Заказ автоматически добавлен в CRM!</i>"
        )
        send_message(token, chat_id, confirm_text, get_keyboard_by_role(user_role))
        return

    ai_reply = (
        f"🤖 <b>Cosmo AI:</b> Получено сообщение «<i>{text}</i>».\n\n"
        "Вы можете проверить статус заказов, оформить новый заказ или запросить статистику. "
        "Нажмите на кнопки меню ниже!"
    )
    send_message(token, chat_id, ai_reply, get_keyboard_by_role(user_role))


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
