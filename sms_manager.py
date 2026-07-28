import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

SMS_CONFIG_FILE = "sms_config.json"
SMS_HISTORY_FILE = "sms_history.json"

DEFAULT_SMS_CONFIG = {
    "enabled": True,
    "provider": "eskiz",  # eskiz, playmobile, smsru, custom_webhook, simulation
    "eskiz_email": "",
    "eskiz_password": "",
    "eskiz_token": "",
    "playmobile_login": "",
    "playmobile_password": "",
    "playmobile_originator": "3700",
    "smsru_api_id": "",
    "custom_url": "",
    "sender_name": "4546",
    "auto_on_create": True,
    "auto_on_measured": True,
    "auto_on_ready": True,
    "auto_on_completed": True,
    "template_create_ru": "Уважаемый(ая) {client}, ваш заказ №{order_id} принят. Курьер: {courier}. Cosmo Cleaning Service.",
    "template_create_uz": "Hosil bo'lgan #{order_id} buyurtmangiz qabul qilindi. Kuryer: {courier}. Cosmo Cleaning Service.",
    "template_measured_ru": "Клиент {client}, заказ №{order_id} принят в цех: {items}. Сумма: {sum} сум. Cosmo Clean.",
    "template_measured_uz": "Mijoz {client}, #{order_id} buyurtmangiz sexga berildi: {items}. Summa: {sum} so'm. Cosmo Clean.",
    "template_ready_ru": "Уважаемый(ая) {client}, ваш заказ №{order_id} высушен и готов к доставке! Скоро курьер свяжется с вами.",
    "template_ready_uz": "Hürmatli {client}, #{order_id} buyurtmangiz tayyor va yetkazib beriladi! Kuryer bog'lanadi.",
    "template_completed_ru": "Спасибо, {client}! Заказ №{order_id} выполнен. Ждем вас снова в Cosmo Cleaning Service!",
    "template_completed_uz": "Rahmat, {client}! #{order_id} buyurtmangiz bajarildi. Cosmo Cleaning Service xizmatidan foydalanganingiz uchun rahmat!"
}


def get_sms_config():
    """Загружает текущую конфигурацию СМС из sms_config.json"""
    if os.path.exists(SMS_CONFIG_FILE):
        try:
            with open(SMS_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                res = DEFAULT_SMS_CONFIG.copy()
                res.update(cfg)
                return res
        except Exception:
            pass
    return DEFAULT_SMS_CONFIG.copy()


def save_sms_config(cfg):
    """Сохраняет конфигурацию СМС в sms_config.json"""
    try:
        with open(SMS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            return True
    except Exception:
        return False


def clean_phone_digits(phone):
    """Очищает телефонный номер до международного формата без плюса (напр. 998901234567)"""
    if not phone:
        return ""
    digits = ''.join(filter(str.isdigit, str(phone)))
    if len(digits) == 9:
        digits = "998" + digits
    return digits


def get_sms_history():
    """Возвращает историю отправленных СМС"""
    if os.path.exists(SMS_HISTORY_FILE):
        try:
            with open(SMS_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_sms_history(order_id, phone, msg, provider, status_str):
    """Добавляет запись в историю отправленных СМС"""
    history = get_sms_history()
    entry = {
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "order_id": str(order_id),
        "phone": phone,
        "message": msg,
        "provider": provider,
        "status": status_str
    }
    history.insert(0, entry)
    history = history[:150]  # Храним до 150 последних записей
    try:
        with open(SMS_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_eskiz_token(email, password):
    """Запрашивает новый Bearer token от Eskiz.uz API"""
    if not email or not password:
        return ""
    try:
        url = "https://notify.eskiz.uz/api/auth/login"
        payload = json.dumps({"email": email, "password": password}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data.get('data', {}).get('token', '')
    except Exception:
        pass
    return ""


def format_sms_message(template, order_data):
    """Подставляет значения переменных в шаблон СМС"""
    if not template:
        return ""
    text = str(template)
    client_name = str(order_data.get("Клиент", order_data.get("client", "")))
    order_id = str(order_data.get("ID", order_data.get("order_id", "-")))
    courier = str(order_data.get("Курьер", order_data.get("courier", "-")))
    total_sum = str(order_data.get("Сумма", order_data.get("sum", "0")))
    items = str(order_data.get("Размеры", order_data.get("items", "-")))

    text = text.replace("{client}", client_name)
    text = text.replace("{order_id}", order_id)
    text = text.replace("{courier}", courier)
    text = text.replace("{sum}", total_sum)
    text = text.replace("{items}", items)
    return text


def send_sms_notification(phone, msg, order_id="-", provider_cfg=None):
    """
    Основная универсальная функция отправки СМС сообщений клиентам.
    Возвращает (success: bool, info_message: str)
    """
    cfg = provider_cfg or get_sms_config()

    if not cfg.get("enabled", True):
        return False, "СМС отправка отключена в настройках CRM."

    clean_phone = clean_phone_digits(phone)
    if not clean_phone or len(clean_phone) < 9:
        return False, f"Некорректный номер телефона: {phone}"

    provider = cfg.get("provider", "simulation")
    sender_name = cfg.get("sender_name", "4546") or "4546"

    # 1. СИМУЛЯЦИЯ / ТЕСТОВЫЙ РЕЖИМ (Используется для тестов или если логин/пароль еще не введены)
    if provider == "simulation" or (provider == "eskiz" and not cfg.get("eskiz_email")):
        info = f"🧪 [СИМУЛЯЦИЯ СМС] Кому: +{clean_phone} | Текст: {msg}"
        save_sms_history(order_id, clean_phone, msg, "Simulation Mode", "Успешно (Тест)")
        return True, info

    # 2. ESKIZ.UZ (Узбекистан)
    elif provider == "eskiz":
        email = cfg.get("eskiz_email", "").strip()
        password = cfg.get("eskiz_password", "").strip()
        token = cfg.get("eskiz_token", "").strip()

        if not token and email and password:
            token = get_eskiz_token(email, password)
            if token:
                cfg["eskiz_token"] = token
                save_sms_config(cfg)

        if not token:
            save_sms_history(order_id, clean_phone, msg, "Eskiz.uz", "Ошибка авторизации (Нет токена)")
            return False, "Eskiz.uz: Не удалось получить токен. Проверьте Email и Пароль."

        try:
            url = "https://notify.eskiz.uz/api/message/sms/send"
            payload = json.dumps({
                "mobile_phone": clean_phone,
                "message": msg,
                "from": sender_name,
                "callback_url": ""
            }).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8', errors='ignore')
                if response.status == 200:
                    save_sms_history(order_id, clean_phone, msg, "Eskiz.uz", "Успешно")
                    return True, "СМС успешно отправлено через Eskiz.uz!"
                else:
                    save_sms_history(order_id, clean_phone, msg, "Eskiz.uz", f"Ошибка: {res_body}")
                    return False, f"Ошибка Eskiz.uz: {res_body}"
        except urllib.error.HTTPError as e:
            err_text = e.read().decode('utf-8', errors='ignore')
            if e.code == 401 and email and password:
                # Токен мог истечь, запрашиваем новый
                new_token = get_eskiz_token(email, password)
                if new_token:
                    cfg["eskiz_token"] = new_token
                    save_sms_config(cfg)
                    return send_sms_notification(phone, msg, order_id, cfg)
            save_sms_history(order_id, clean_phone, msg, "Eskiz.uz", f"HTTP {e.code}: {err_text}")
            return False, f"Ошибка Eskiz.uz ({e.code}): {err_text}"
        except Exception as e:
            save_sms_history(order_id, clean_phone, msg, "Eskiz.uz", str(e))
            return False, f"Ошибка соединения с Eskiz.uz: {e}"

    # 3. PLAYMOBILE / SMS.UZ
    elif provider == "playmobile":
        login = cfg.get("playmobile_login", "").strip()
        password = cfg.get("playmobile_password", "").strip()
        originator = cfg.get("playmobile_originator", "3700").strip()

        if not login or not password:
            return False, "Укажите логин и пароль PlayMobile / SMS.uz"

        try:
            url = "https://send.sms.uz/api/sms/send"
            payload = json.dumps({
                "messages": [
                    {
                        "recipient": clean_phone,
                        "message-id": f"msg_{datetime.now().timestamp()}",
                        "sms": {
                            "originator": originator,
                            "content": {"text": msg}
                        }
                    }
                ]
            }).encode('utf-8')

            # Basic Auth header
            auth_str = f"{login}:{password}"
            import base64
            b64_auth = base64.b64encode(auth_str.encode()).decode()

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {b64_auth}'
            }
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    save_sms_history(order_id, clean_phone, msg, "PlayMobile", "Успешно")
                    return True, "СМС отправлено через PlayMobile!"
                else:
                    save_sms_history(order_id, clean_phone, msg, "PlayMobile", f"HTTP {response.status}")
                    return False, f"Ошибка PlayMobile API ({response.status})"
        except Exception as e:
            save_sms_history(order_id, clean_phone, msg, "PlayMobile", str(e))
            return False, f"Ошибка PlayMobile: {e}"

    # 4. SMS.RU
    elif provider == "smsru":
        api_id = cfg.get("smsru_api_id", "").strip()
        if not api_id:
            return False, "Не указан API ID для SMS.ru"
        try:
            encoded_msg = urllib.parse.quote(msg)
            url = f"https://sms.ru/sms/send?api_id={api_id}&to={clean_phone}&msg={encoded_msg}&json=1"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8', errors='ignore'))
                if res_data.get("status") == "OK":
                    save_sms_history(order_id, clean_phone, msg, "SMS.ru", "Успешно")
                    return True, "СМС успешно отправлено через SMS.ru!"
                else:
                    status_text = res_data.get("status_text", "Ошибка")
                    save_sms_history(order_id, clean_phone, msg, "SMS.ru", status_text)
                    return False, f"Ошибка SMS.ru: {status_text}"
        except Exception as e:
            save_sms_history(order_id, clean_phone, msg, "SMS.ru", str(e))
            return False, f"Ошибка SMS.ru: {e}"

    # 5. CUSTOM HTTP WEBHOOK
    elif provider == "custom_webhook":
        custom_url = cfg.get("custom_url", "").strip()
        if not custom_url:
            return False, "Не указан URL для Custom Webhook"
        try:
            target_url = custom_url.replace("{phone}", clean_phone).replace("{msg}", urllib.parse.quote(msg))
            req = urllib.request.Request(target_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                save_sms_history(order_id, clean_phone, msg, "Custom Webhook", f"HTTP {response.status}")
                return True, "СМС успешно отправлено через Custom Webhook!"
        except Exception as e:
            save_sms_history(order_id, clean_phone, msg, "Custom Webhook", str(e))
            return False, f"Ошибка Custom Webhook: {e}"

    save_sms_history(order_id, clean_phone, msg, provider, "Неизвестный провайдер")
    return False, "Неизвестный провайдер СМС"
