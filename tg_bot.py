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


def get_main_keyboard():
    """Главная клавиатура бота в Telegram"""
    return {
        "keyboard": [
            [{"text": "📋 Мои заказы"}, {"text": "📊 Статистика CRM"}],
            [{"text": "➕ Новый заказ"}, {"text": "🔍 Поиск заказа"}],
            [{"text": "🤖 Задать вопрос ИИ"}, {"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True
    }


def parse_order_from_text(text):
    """
    ИИ / Естественно-языковой парсер для создания заказа прямо из текста Telegram:
    Пример: "Заказ Ивана, +998901234567, Сиёб, ул. Навои 12, 3 ковра"
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    full_str = " ".join(lines)

    # Ищем телефон (9 цифр)
    phone_match = re.search(r'(\+?998)?[\s\-]?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', full_str)
    phone = phone_match.group(0) if phone_match else ""
    clean_phone = ''.join(filter(str.isdigit, phone))
    if len(clean_phone) >= 9:
        clean_phone = clean_phone[-9:]
        full_phone = f"+998 {clean_phone[:2]} {clean_phone[2:5]} {clean_phone[5:7]} {clean_phone[7:]}"
    else:
        full_phone = "+998 90 000 00 00"

    # Ищем район
    districts = ["Сиёб", "Багишамальский", "Согдиана", "Микрорайон", "Саттепо", "Железнодорожный", "Самаркандский"]
    matched_district = "Сиёб (Siyob)"
    for d in districts:
        if d.lower() in full_str.lower():
            matched_district = d
            break

    # Имя (первые слова до запятой или телефона)
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

    if callback_query:
        chat_id = callback_query["message"]["chat"]["id"]
        cb_data = callback_query.get("data", "")

        if cb_data.startswith("st_"):
            # Изменение статуса: st_STATUS_ID
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
                    send_message(token, chat_id, f"✅ <b>Заказ №{order_id} переведен в статус:</b> «{new_st}»!", get_main_keyboard())
                else:
                    send_message(token, chat_id, f"⚠️ Заказ №{order_id} не найден.")
        return

    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    user_info = message.get("from", {})
    username = user_info.get("first_name", "Пользователь")

    if text in ["/start", "Привет", "помощь", "❓ Помощь"]:
        welcome_text = (
            f"👋 <b>Привет, {username}!</b>\n\n"
            "🧼 Я <b>Cosmo CRM AI Бот</b> — ваш автоматический помощник по управлению заказами.\n\n"
            "<b>Что я умею:</b>\n"
            "• 📋 <b>Показывать заказы</b> и менять их статус\n"
            "• ➕ <b>Создавать новые заказы</b> текстом или голосом\n"
            "• 📊 <b>Выдавать статистику</b> по выручке и цеху\n"
            "• 🤖 <b>Отвечать на вопросы ИИ</b> по CRM\n\n"
            "<i>Выберите команду ниже или напишите текст свободным языком!</i>"
        )
        send_message(token, chat_id, welcome_text, get_main_keyboard())
        return

    if text == "📋 Мои заказы":
        orders = load_json_file(BACKUP_FILE, [])
        if not orders:
            send_message(token, chat_id, "ℹ️ Список заказов пуст.", get_main_keyboard())
            return

        active_orders = [o for o in orders if str(o.get("Статус")) != "Выполнен"][:10]
        if not active_orders:
            send_message(token, chat_id, "🎉 Все заказы выполнены! В цеху чисто.", get_main_keyboard())
            return

        resp_msg = f"📋 <b>Активные заказы в работе ({len(active_orders)}):</b>\n\n"
        for o in active_orders:
            o_id = o.get("ID")
            client = o.get("Клиент", "-")
            phone = o.get("Телефон", "-")
            address = f"{o.get('Район','')}, {o.get('Адрес','')}".strip(', ')
            st = o.get("Статус", "Новый")
            sum_val = o.get("Сумма", 0)

            resp_msg += (
                f"📦 <b>Заказ №{o_id}</b> ({st})\n"
                f"👤 {client} ({phone})\n"
                f"🏠 {address}\n"
                f"💰 {sum_val} сум\n\n"
            )

        send_message(token, chat_id, resp_msg, get_main_keyboard())
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
        send_message(token, chat_id, stats_msg, get_main_keyboard())
        return

    if text == "➕ Новый заказ":
        guide_msg = (
            "➕ <b>Как быстро создать заказ:</b>\n\n"
            "Напишите мне информацию о клиенте в одном сообщении, например:\n"
            "<code>Заказ: Алишер Назаров, 901234567, Сиёб, ул. Навои 14, кв 2, 2 ковра</code>\n\n"
            "ИИ автоматически распознает имя, телефон и адрес и создаст новый номер заказа!"
        )
        send_message(token, chat_id, guide_msg, get_main_keyboard())
        return

    if text.startswith("🔍 Поиск") or text.startswith("/search"):
        send_message(token, chat_id, "🔍 Напишите № заказа или имя клиента для поиска (например: <code>5200</code> или <code>Иван</code>):", get_main_keyboard())
        return

    # ---------------- ИИ ЕСТЕСТВЕННО-ЯЗЫКОВОЙ ОБРАБОТЧИК ----------------
    # Автоматическое распознавание создания заказа или поиска
    if "заказ" in text.lower() or "клиент" in text.lower() or any(char.isdigit() for char in text):
        # 1. Проверяем, если это поиск по ID
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

        # 2. Создание заказа через текст
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
            "Курьер": "Не назначен",
            "Диспетчер": f"Telegram ({username})",
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
            f"<i>Заказ автоматически добавлен в CRM и доступен на сайте!</i>"
        )
        send_message(token, chat_id, confirm_text, get_main_keyboard())
        return

    # Ответ ИИ-помощника по умолчанию
    ai_reply = (
        f"🤖 <b>Cosmo AI:</b> Получено сообщение «<i>{text}</i>».\n\n"
        "Я могу помочь вам проверить статус заказов, оформить новый заказ или рассчитать стоимость стирки. "
        "Нажмите на кнопки меню ниже или напишите данные клиента!"
    )
    send_message(token, chat_id, ai_reply, get_main_keyboard())


def run_telegram_bot():
    """Основной цикл опроса (Long Polling) Telegram Бот API"""
    token = get_tg_token()
    if not token:
        print("[TG Bot] Токен Telegram бота не найден в telegram_config.json!")
        return

    print(f"🚀 [TG Bot Started] Бот запускается для токена: {token[:10]}...")

    # Сбрасываем старый вебхук если есть
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
