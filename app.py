import json
import os
import sys
import subprocess
import re
import urllib.parse
import urllib.request
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import sms_manager
import pricing_manager
import debt_manager
import salary_manager
import orders_view
import dashboard_view
import ui_theme
import locales
import dispatcher_view
import courier_view
import washer_view

st.set_page_config(page_title="Cosmo Cleaning Service CRM — WebApp", layout="wide", page_icon="🧼")

# --- РЕЖИМ ULTRA-CLEAN СВЕРХЛЕГКОГО МИНИ-ВЕБ-АПП ДЛЯ ТЕЛЕФОНА (КУРЬЕР) ---
qp = st.query_params
mode = str(qp.get("mode") or qp.get("view") or "").lower()

if mode in ["courier", "webapp", "mobile"]:
    st.markdown("""
        <style>
            header, footer, [data-testid="stSidebar"], [data-testid="stHeader"], #MainMenu, .stAppHeader { display: none !important; }
            .stApp { background: #070c18 !important; padding: 0 !important; margin: 0 !important; }
            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
            iframe { width: 100vw !important; height: 100vh !important; min-height: 100vh !important; border: none !important; position: fixed !important; top: 0 !important; left: 0 !important; z-index: 999999 !important; }
        </style>
    """, unsafe_allow_html=True)
    try:
        with open("backup_orders.json", "r", encoding="utf-8") as f:
            orders_data = f.read()
    except Exception:
        orders_data = "[]"
    try:
        with open("courier_webapp.html", "r", encoding="utf-8") as f:
            html_code = f.read()
        injection = f"<script>window.initialOrders = {orders_data};</script>"
        html_code = html_code.replace("</head>", f"{injection}\n</head>")
        components.html(html_code, height=950, scrolling=True)
    except Exception as e:
        st.error(f"Ошибка загрузки WebApp Курьера: {e}")
    st.stop()

elif mode in ["dispatcher", "disp"]:
    st.markdown("""
        <style>
            header, footer, [data-testid="stSidebar"], [data-testid="stHeader"], #MainMenu, .stAppHeader { display: none !important; }
            .stApp { background: #070c18 !important; padding: 0 !important; margin: 0 !important; }
            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
            iframe { width: 100vw !important; height: 100vh !important; min-height: 100vh !important; border: none !important; position: fixed !important; top: 0 !important; left: 0 !important; z-index: 999999 !important; }
        </style>
    """, unsafe_allow_html=True)
    try:
        with open("backup_orders.json", "r", encoding="utf-8") as f:
            orders_data = f.read()
    except Exception:
        orders_data = "[]"
    try:
        with open("dispatcher_webapp.html", "r", encoding="utf-8") as f:
            html_code = f.read()
        injection = f"<script>window.initialOrders = {orders_data};</script>"
        html_code = html_code.replace("</head>", f"{injection}\n</head>")
        components.html(html_code, height=950, scrolling=True)
    except Exception as e:
        st.error(f"Ошибка загрузки WebApp Диспетчера: {e}")
    st.stop()

ui_theme.inject_theme()

# --- ФОНОВЫЙ ЗАПУСК TELEGRAM БОТОВ (ДЛЯ STREAMLIT CLOUD / ONLINE) ---
@st.cache_resource
def start_background_bots():
    import threading
    import asyncio
    try:
        import run_bots
        def run_bots_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_bots.main())
            except Exception as e:
                print(f"[Bot Background Error] {e}")

        t = threading.Thread(target=run_bots_thread, daemon=True)
        t.start()
        print("🤖 [Background Bots] Telegram боты запущены в фоновом потоке!")
        return t
    except Exception as e:
        print(f"[Background Bot Launch Failed] {e}")
        return None

start_background_bots()

# --- ЯЗЫКОВОЙ ПАКЕТ (РУССКИЙ / O'ZBEKCHA) ---
if "lang" not in st.session_state:
    st.session_state["lang"] = "ru"


def set_lang():
    if st.session_state.get("lang_selector") == "🇷🇺 Русский":
        st.session_state["lang"] = "ru"
    else:
        st.session_state["lang"] = "uz"

LOCALES = {
    "ru": {
        "brand": "Cosmo Cleaning Service",
        "subtitle": "Профессиональная система автоматизации",
        "login": "Войти в систему",
        "register_tab": "Регистрация сотрудника",
        "username": "Имя пользователя (Логин)",
        "password": "Пароль",
        "role_select": "Выберите вашу должность:",
        "submit_reg": "Отправить заявку на регистрацию",
        "submit_login": "Войти",
        "logout": "Выйти из системы",
        "user_label": "Пользователь",
        "role_label": "Должность",
        "error_not_found": "Пользователь не найден!",
        "error_password": "Неверный пароль!",
        "warn_approval": "⚠️ Ваш аккаунт еще не одобрен администратором.",
        "success_login": "Успешный вход! Загрузка...",
        "reg_success": "🎉 Заявка отправлена! Ожидайте одобрения администратора.",
        "reg_error_exists": "Этот логин уже занят!",
        "reg_error_fields": "Заполните все поля!",
        
        # Роли
        "Dispatcher": "Диспетчер",
        "Courier": "Доставщик (Курьер)",
        "Washer": "Мойщик",
        "Cleaner": "Чистильщик от волос",
        "Admin": "Администратор",
        
        # Панели
        "panel_clean": "✨ Панель чистки от волос и сушки",
        "clean_empty": "Нет ковров на сушке и чистке.",
        "btn_cleaned": "📦 Высушено, упаковано и готово к выдаче",
        
        # Панель диспетчера
        "dispatcher_panel": "📞 Панель Диспетчера",
        "new_order": "Новый заказ",
        "dispatcher_label": "Диспетчер",
        "assign_courier": "Назначить курьера *",
        "client_name": "Имя клиента *",
        "phone": "Телефон (только 9 цифр) *",
        "address": "Точный адрес *",
        "district": "Район клиента *",
        "language": "Язык общения *",
        "comment": "Комментарий",
        "take_order": "Взять заказ (Передать курьеру)",
        "order_history": "История заказов",
        "search_by_id": "Поиск по номеру (ID):",
        "required_fields": "⚠️ Заполните все обязательные поля со звездочкой!",
        "phone_error": "⚠️ Номер телефона должен состоять из 9 цифр!",
        "order_created": "✅ Заказ № {order_id} назначен на курьера: {courier}!",
        
        # Панель курьера
        "courier_panel": "🚗 Панель Курьера",
        "your_profile": "👤 Ваш профиль курьера:",
        "new_requests": "📥 Новые заявки",
        "shop_status": "🔍 Статус в цеху",
        "delivery": "📤 Доставка",
        "no_requests": "У вас пока нет новых заявок.",
        "change_driver": "Смена курьера",
        "transfer_order": "Передать заказ:",
        "confirm_transfer": "Подтвердить передачу ⇄",
        "edit_address": "Редактирование адреса",
        "district_select": "Район:",
        "exact_address": "Точный адрес:",
        "save_changes": "Сохранить 💾",
        "accept_order": "Взять заказ",
        "reception_measurement": "📏 Прием и замер",
        "item": "Вещь:",
        "width": "Ширина (м)",
        "length": "Длина (м)",
        "quantity": "Кол-во (шт)",
        "add_item": "➕ Добавить",
        "total_sum": "💰 Итоговая сумма (со скидкой):",
        "send_to_workshop": "🚚 Отправить в цех",
        "washing_process": "🔍 Процесс стирки",
        "ready_for_delivery": "📦 Доставка №{order_id}",
        "phone_label": "📞 Телефон:",
        "district_label": "🗺️ Район:",
        "address_label": "🏠 Адрес:",
        "items_label": "🧺 Вещи:",
        "open_route": "📍 Открыть маршрут в Google Maps",
        "to_pay": "К оплате:",
        "actually_paid": "Фактически оплачено:",
        "payment_method": "Способ оплаты:",
        "cash": "Наличные",
        "card": "Карта",
        "debt_reason": "⚠️ Причина недоплаты / Скидка:",
        "complete_order": "✅ Завершить заказ",
        "debt_error": "Укажите причину недоплаты!",
        "order_completed": "Заказ закрыт!",
        
        # Панель мойщика
        "washer_panel": "🌊 Панель Цеха Мойки",
        "washer_info": "Обновляйте статус заказа по мере выполнения работы.",
        "all_completed": "Все поступившие заказы отработаны! В цеху чисто.",
        "save_status": "💾 Сохранить",
        
        # Панель администратора
        "admin_panel": "📊 Панель Администратора",
        "statistics": "📈 Статистика",
        "all_orders": "📋 Все заказы",
        "map": "🗺️ Карта",
        "settings": "⚙️ Настройки (Сотрудники)",
        "summary": "Сводка по Cosmo Cleaning Service",
        "total_orders": "Всего заказов",
        "in_progress": "В работе",
        "cash_total": "Касса (сум)",
        "employee_management": "Управление сотрудниками и доступами",
        "current_employees": "Действующие сотрудники",
        "add_employee": "Добавить сотрудника",
        "add_user_form": "Добавить сотрудника",
        "employee_login": "Логин (Username)",
        "employee_password": "Пароль",
        "employee_role": "Должность",
        "add_to_system": "Добавить в систему",
        "employee_added": "Сотрудник {login} добавлен!",
        "fill_login_password": "Заполните логин и пароль",
        "interactive_map": "Интерактивная карта заказов по районам (координаты курьеров)."
    },
    "uz": {
        "brand": "Cosmo Cleaning Service",
        "subtitle": "Professional avtomatlashtirish tizimi",
        "login": "Tizimga kirish",
        "register_tab": "Xodimni ro'yxatdan o'tkazish",
        "username": "Foydalanuvchi nomi (Login)",
        "password": "Parol",
        "role_select": "Lavozimingizni tanlang:",
        "submit_reg": "Ro'yxatdan o'tish uchun ariza yuborish",
        "submit_login": "Kirish",
        "logout": "Tizimdan chiqish",
        "user_label": "Foydalanuvchi",
        "role_label": "Lavozim",
        "error_not_found": "Foydalanuvchi topilmadi!",
        "error_password": "Noto'g'ri parol!",
        "warn_approval": "⚠️ Akkauntingiz hali administrator tomonidan tasdiqlanmagan.",
        "success_login": "Muvaffaqiyatli kirildi! Yuklanmoqda...",
        "reg_success": "🎉 Ariza yuborildi! Administrator tasdiqlashini kuting.",
        "reg_error_exists": "Ushbu login band!",
        "reg_error_fields": "Barcha maydonlarni to'ldiring!",
        
        # Rollar
        "Dispatcher": "Dispetcher",
        "Courier": "Yuboruvchi (Kuryer)",
        "Washer": "Yuvuvchi (Sex xodimi)",
        "Cleaner": "Yung va sochdan tozalovchi",
        "Admin": "Administrator",
        
        # Panellar
        "panel_clean": "✨ Quritish va yakuniy tozalash paneli",
        "clean_empty": "Quritishda narsalar yo'q.",
        "btn_cleaned": "📦 To'liq quritildi, qadoqlandi va tayyor",
        
        # Dispetcher paneli
        "dispatcher_panel": "📞 Dispetcher paneli",
        "new_order": "Yangi buyurtma",
        "dispatcher_label": "Dispetcher",
        "assign_courier": "Kuryerni tayinlash *",
        "client_name": "Mijoz ismi *",
        "phone": "Telefon (faqat 9 raqam) *",
        "address": "To'liq manzil *",
        "district": "Mijoz tumani *",
        "language": "Muloqot tili *",
        "comment": "Izoh",
        "take_order": "Buyurtmani olish (Kuryerga topshirish)",
        "order_history": "Buyurtmalar tarixi",
        "search_by_id": "Raqam bo'yicha qidirish (ID):",
        "required_fields": "⚠️ Barcha majburiy maydonlarni to'ldiring!",
        "phone_error": "⚠️ Telefon raqami 9 raqamdan iborat bo'lishi kerak!",
        "order_created": "✅ Buyurtma № {order_id} kuryerga tayinlandi: {courier}!",
        
        # Kuryer paneli
        "courier_panel": "🚗 Kuryer paneli",
        "your_profile": "👤 Sizning kuryer profilingiz:",
        "new_requests": "📥 Yangi arizalar",
        "shop_status": "🔍 Sexdagi holat",
        "delivery": "📤 Yetkazib berish",
        "no_requests": "Hozircha yangi arizalar yo'q.",
        "change_driver": "Kuryerni almashtirish",
        "transfer_order": "Buyurtmani topshirish:",
        "confirm_transfer": "Topshirishni tasdiqlash ⇄",
        "edit_address": "Manzilni tahrirlash",
        "district_select": "Tuman:",
        "exact_address": "Aniq manzil:",
        "save_changes": "Saqlash 💾",
        "accept_order": "Buyurtmani olish",
        "reception_measurement": "📏 Qabul qilish va o'lchash",
        "item": "Buyum:",
        "width": "Eni (m)",
        "length": "Bo'yi (m)",
        "quantity": "Soni (dona)",
        "add_item": "➕ Qo'shish",
        "total_sum": "💰 Yakuniy summa (chegirma bilan):",
        "send_to_workshop": "🚚 Sexga yuborish",
        "washing_process": "🔍 Yuvish jarayoni",
        "ready_for_delivery": "📦 Yetkazib berish №{order_id}",
        "phone_label": "📞 Telefon:",
        "district_label": "🗺️ Tuman:",
        "address_label": "🏠 Manzil:",
        "items_label": "🧺 Buyumlar:",
        "open_route": "📍 Google Mapsda marshrutni ochish",
        "to_pay": "To'lov:",
        "actually_paid": "Haqiqatda to'langan:",
        "payment_method": "To'lov usuli:",
        "cash": "Naqd",
        "card": "Karta",
        "debt_reason": "⚠️ Kam to'lov sababi / Chegirma:",
        "complete_order": "✅ Buyurtmani tugatish",
        "debt_error": "Kam to'lov sababini ko'rsating!",
        "order_completed": "Buyurtma yopildi!",
        
        # Yuvuvchi paneli
        "washer_panel": "🌊 Yuvish sexi paneli",
        "washer_info": "Ish bajarilishi davomida buyurtma holatini yangilang.",
        "all_completed": "Barcha kelgan buyurtmalar bajarildi! Sexda toza.",
        "save_status": "💾 Saqlash",
        
        # Administrator paneli
        "admin_panel": "📊 Administrator paneli",
        "statistics": "📈 Statistika",
        "all_orders": "📋 Barcha buyurtmalar",
        "map": "🗺️ Xarita",
        "settings": "⚙️ Sozlamalar (Xodimlar)",
        "summary": "Cosmo Cleaning Service xulosasi",
        "total_orders": "Jami buyurtmalar",
        "in_progress": "Jarayonda",
        "cash_total": "Kassa (so'm)",
        "employee_management": "Xodimlar va ruxsatlarni boshqarish",
        "current_employees": "Faol xodimlar",
        "add_employee": "Xodim qo'shish",
        "add_user_form": "Xodim qo'shish",
        "employee_login": "Login (Foydalanuvchi nomi)",
        "employee_password": "Parol",
        "employee_role": "Lavozim",
        "add_to_system": "Tizimga qo'shish",
        "employee_added": "Xodim {login} qo'shildi!",
        "fill_login_password": "Login va parolni to'ldiring!",
        "interactive_map": "Tumanlar bo'yicha buyurtmalar interaktiv xaritasi (kuryerlar koordinatalari)."
    }
}

lang = st.session_state["lang"]
t = LOCALES[lang]

# Брендинг
st.markdown("""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 18px; margin-bottom: 16px; text-align: center;">
        <h3 style="margin: 0; color: #1e3a8a; font-weight: 700;">🧼 Cosmo Cleaning Service CRM</h3>
    </div>
""", unsafe_allow_html=True)

PRICES = {
    "Ковёр": {"price": 15000, "type": "sqm"},
    "Курпача": {"price": 15000, "type": "sqm"},
    "Занавески": {"price": 12000, "type": "sqm"},
    "Одеяло": {"price": 35000, "type": "pcs"},
    "Покрывало": {"price": 25000, "type": "pcs"},
    "Подушка": {"price": 15000, "type": "pcs"}
}

EXPECTED_HEADERS = [
    "ID", "Дата", "Клиент", "Телефон", "Адрес", "Размеры", "Площадь", 
    "Сумма", "Статус", "Курьер", "Диспетчер", "Район", "Язык", 
    "Локация", "Оплачено", "Тип оплаты", "Причина"
]

def get_next_order_id(df):
    try:
        if df is not None and not df.empty and "ID" in df.columns:
            # Игнорируем архивные импортированные заказы из Telegram при расчете следующего ID
            if "Диспетчер" in df.columns:
                manual_df = df[df["Диспетчер"] != "Telegram Импорт"]
            else:
                manual_df = df
            numeric_ids = pd.to_numeric(manual_df["ID"], errors='coerce').dropna()
            # Ограничиваем рабочий диапазон серии заказов 5200..5999 (архивные ID 10000+ игнорируются)
            valid_ids = numeric_ids[(numeric_ids >= 5200) & (numeric_ids < 6000)]
            if not valid_ids.empty:
                next_id = int(valid_ids.max()) + 1
                return max(5218, next_id)
        return 5218
    except Exception:
        return 5218


# Добавьте эту строку, если её нет:
GSHEET_CONFIG_FILE = "gsheet_config.json"

def get_gsheet_config():
    if os.path.exists(GSHEET_CONFIG_FILE):
        try:
            with open(GSHEET_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"gsheet_url": ""}

def save_gsheet_config(url):
    try:
        with open(GSHEET_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"gsheet_url": url.strip()}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def safe_get_secret(key_name, default=""):
    try:
        if hasattr(st, "secrets"):
            return st.secrets.get(key_name, default)
    except BaseException:
        pass
    return default


def safe_get_secret_dict(key_name):
    try:
        if hasattr(st, "secrets") and key_name in st.secrets:
            val = st.secrets[key_name]
            if isinstance(val, str):
                return json.loads(val)
            elif isinstance(val, dict):
                return dict(val)
    except BaseException:
        pass
    return None


# Подключение к Google Таблицам
@st.cache_resource
def connect_gsheet():
    client = None
    
    # 1. Секреты в st.secrets (GCP_JSON или gcp_service_account)
    try:
        gcp_json = safe_get_secret_dict("GCP_JSON")
        if gcp_json:
            if "private_key" in gcp_json and isinstance(gcp_json["private_key"], str):
                gcp_json["private_key"] = gcp_json["private_key"].replace("\\n", "\n")
            client = gspread.service_account_from_dict(gcp_json)
        else:
            gcp_acc = safe_get_secret_dict("gcp_service_account")
            if gcp_acc:
                if "private_key" in gcp_acc and isinstance(gcp_acc["private_key"], str):
                    gcp_acc["private_key"] = gcp_acc["private_key"].replace("\\n", "\n")
                client = gspread.service_account_from_dict(gcp_acc)
    except Exception:
        pass

    # 2. Локальный файл key.json
    if client is None and os.path.exists("key.json"):
        try:
            with open("key.json", "r", encoding="utf-8") as f:
                key_dict = json.load(f)
            if "private_key" in key_dict and isinstance(key_dict["private_key"], str):
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            client = gspread.service_account_from_dict(key_dict)
        except Exception:
            pass

    if client is None:
        return None, None, None, "Учетные данные Google Service Account не найдены в st.secrets или key.json"

    # 3. Открытие таблицы
    cfg = get_gsheet_config()
    secret_url = safe_get_secret("GSHEET_URL", "").strip()
    DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1zYbTgS1aQc-1aeP0EeAo-KeohbTAyGYumJLQQxmBZRk/edit"
    gsheet_url = cfg.get("gsheet_url", "").strip() or secret_url or DEFAULT_GSHEET_URL

    sheet_name = "Мойка Ковров CRM"
    try:
        if gsheet_url:
            db = client.open_by_url(gsheet_url)
        else:
            try:
                db = client.open(sheet_name)
            except Exception:
                db = client.create(sheet_name)

        sheet1 = db.sheet1

        try:
            sheet1.update(values=[EXPECTED_HEADERS], range_name="A1")
        except Exception:
            pass

        try:
            user_sheet = db.worksheet("Пользователи")
        except gspread.exceptions.WorksheetNotFound:
            user_sheet = db.add_worksheet(title="Пользователи", rows="100", cols="4")
            user_sheet.append_row(["Username", "Password", "Role", "Status"])
            user_sheet.append_row(["admin", "admin123", "Администратор", "Активен"])

        return db, sheet1, user_sheet, ""
    except Exception as e:
        return None, None, None, str(e)


use_gsheet = False
db, sheet, user_sheet = None, None, None

_db, _sheet, _user_sheet, _err = connect_gsheet()
if _db is not None and _sheet is not None:
    db, sheet, user_sheet = _db, _sheet, _user_sheet
    use_gsheet = True
    st.session_state["gsheet_error"] = ""
else:
    use_gsheet = False
    st.session_state["gsheet_error"] = _err

qp = st.query_params
if "logged_in" not in st.session_state or not st.session_state.get("logged_in"):
    user_val = str(qp.get("user", "")).strip()
    role_val = str(qp.get("role", "")).strip()

    if "role=" in user_val and not role_val:
        parts = user_val.split("role=")
        user_val = parts[0].strip("&? ")
        role_val = parts[1].strip()

    if user_val and role_val:
        st.session_state["logged_in"] = True
        st.session_state["username"] = user_val
        st.session_state["role"] = role_val
    else:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""

BACKUP_FILE = "backup_orders.json"
USERS_BACKUP_FILE = "backup_users.json"

DEFAULT_USERS_DATA = [
    {"Username": "admin", "Password": "admin123", "Role": "Администратор", "Status": "Активен"},
    {"Username": "Алишер Каримов", "Password": "123456", "Role": "Доставщик (Курьер)", "Status": "Активен"},
    {"Username": "Бобур Ибрагимов", "Password": "123456", "Role": "Доставщик (Курьер)", "Status": "Активен"},
    {"Username": "Сардор Турсунов", "Password": "123456", "Role": "Доставщик (Курьер)", "Status": "Активен"},
    {"Username": "washer", "Password": "123456", "Role": "Мойщик", "Status": "Активен"}
]


def save_local_users(df):
    """Авто-бекап пользователей в локальный JSON файл"""
    try:
        df.to_json(USERS_BACKUP_FILE, orient="records", force_ascii=False, indent=2)
    except Exception:
        pass


def load_local_users():
    """Загрузка данных пользователей из локального бекапа"""
    if os.path.exists(USERS_BACKUP_FILE):
        try:
            return pd.read_json(USERS_BACKUP_FILE)
        except Exception:
            pass
    df = pd.DataFrame(DEFAULT_USERS_DATA)
    save_local_users(df)
    return df


def save_local_backup(df):
    """Авто-бекап данных заказов в локальный JSON файл"""
    try:
        df.to_json(BACKUP_FILE, orient="records", force_ascii=False, indent=2)
    except Exception:
        pass


def load_local_backup():
    """Загрузка данных заказов из локального бекапа при отсутствии сети"""
    if os.path.exists(BACKUP_FILE):
        try:
            return pd.read_json(BACKUP_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=EXPECTED_HEADERS)


CONFIG_FILE = "telegram_config.json"


def get_tg_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if "courier_chats" not in cfg:
                    cfg["courier_chats"] = {}
                if "dispatcher_chats" not in cfg:
                    cfg["dispatcher_chats"] = {}
                return cfg
        except Exception:
            pass
    return {
        "courier_bot_token": "",
        "dispatcher_bot_token": "",
        "bot_token": "",
        "chat_id": "",
        "courier_chats": {},
        "dispatcher_chats": {}
    }


def save_tg_config(courier_bot_token=None, dispatcher_bot_token=None, chat_id=None, courier_chats=None, dispatcher_chats=None, courier_webapp_url=None, dispatcher_webapp_url=None, **kwargs):
    try:
        existing = get_tg_config()

        # Positional call fallback if save_tg_config(val1, val2) was used
        if courier_bot_token is not None and dispatcher_bot_token is not None and chat_id is None:
            v2 = str(dispatcher_bot_token).strip()
            if v2.startswith("-") or v2.isdigit():
                chat_id = v2
                dispatcher_bot_token = None

        c_token = str(courier_bot_token).strip() if courier_bot_token is not None else existing.get("courier_bot_token", "")
        d_token = str(dispatcher_bot_token).strip() if dispatcher_bot_token is not None else existing.get("dispatcher_bot_token", "")
        c_id = str(chat_id).strip() if chat_id is not None else existing.get("chat_id", "")

        c_chats = courier_chats if courier_chats is not None else existing.get("courier_chats", {})
        d_chats = dispatcher_chats if dispatcher_chats is not None else existing.get("dispatcher_chats", {})

        data = {
            "courier_bot_token": c_token,
            "dispatcher_bot_token": d_token,
            "bot_token": c_token or d_token or existing.get("bot_token", ""),
            "chat_id": c_id,
            "courier_chats": c_chats,
            "dispatcher_chats": d_chats,
            "courier_webapp_url": str(courier_webapp_url).strip() if courier_webapp_url is not None else existing.get("courier_webapp_url", ""),
            "dispatcher_webapp_url": str(dispatcher_webapp_url).strip() if dispatcher_webapp_url is not None else existing.get("dispatcher_webapp_url", "")
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[save_tg_config error] {e}")
        return False


def send_telegram_notification(msg, target_couriers=None):
    """
    Отправка уведомлений через Telegram Бота персонально каждому выбранному курьеру и/или в общую группу.
    """
    cfg = get_tg_config()
    courier_token = cfg.get("courier_bot_token") or cfg.get("bot_token", "")
    dispatcher_token = cfg.get("dispatcher_bot_token") or cfg.get("bot_token", "")
    
    # Use courier token for notifying couriers, fallback to general token
    bot_token = courier_token or dispatcher_token
    if not bot_token:
        return False

    chat_ids_to_send = set()
    
    # 1. Основной Chat ID группы / администратора
    main_chat_id = (st.session_state.get("tg_chat_id") or cfg.get("chat_id", "")).strip()
    if main_chat_id:
        for cid in main_chat_id.split(","):
            if cid.strip():
                chat_ids_to_send.add(cid.strip())

    # 2. Персональные Chat ID выбранных курьеров
    courier_chats = cfg.get("courier_chats", {})
    if target_couriers:
        if isinstance(target_couriers, str):
            c_names = [c.strip() for c in target_couriers.split(",") if c.strip()]
        elif isinstance(target_couriers, list):
            c_names = target_couriers
        else:
            c_names = []

        for cname in c_names:
            cname_clean = cname.lower()
            found_cid = None
            for key_c, val_cid in courier_chats.items():
                if key_c.lower() == cname_clean or cname_clean in key_c.lower():
                    found_cid = val_cid
                    break
            if found_cid and str(found_cid).strip():
                chat_ids_to_send.add(str(found_cid).strip())
    else:
        # If no target specified, send to all registered couriers
        for cname, cid_val in courier_chats.items():
            if str(cid_val).strip():
                chat_ids_to_send.add(str(cid_val).strip())

    if not chat_ids_to_send:
        return False

    success = False
    for cid in chat_ids_to_send:
        try:
            url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
            payload = json.dumps({"chat_id": str(cid).strip(), "text": msg, "parse_mode": "HTML"}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    success = True
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            st.error(f"⚠️ Ошибка Telegram API для Chat ID ({cid}): {err_body}")
            if "chat not found" in err_body or "blocked" in err_body or "Forbidden" in err_body:
                st.warning(f"💡 Убедитесь, что курьер/пользователь (Chat ID: {cid}) открыл бота в Telegram и нажал кнопку /start!")
        except Exception as e:
            st.error(f"⚠️ Ошибка отправки Telegram: {e}")

    return success


# --- SMS УВЕДОМЛЕНИЯ И ИНТЕРФЕЙС / SMS SOZLAMALARI ---
def render_sms_settings_ui(key_prefix="sb"):
    """Отображает панель управления настройками SMS провайдеров и шаблонов"""
    cfg = sms_manager.get_sms_config()
    st.markdown("### 📱 Настройки СМС рассылок")
    
    enabled = st.checkbox("Включить отправку СМС клиентам", value=cfg.get("enabled", True), key=f"{key_prefix}_enabled")
    
    provider_options = ["eskiz", "playmobile", "smsru", "custom_webhook", "simulation"]
    current_prov = cfg.get("provider", "eskiz")
    prov_idx = provider_options.index(current_prov) if current_prov in provider_options else 0
    
    provider = st.selectbox(
        "SMS Gateway Провайдер:",
        provider_options,
        index=prov_idx,
        format_func=lambda x: {
            "eskiz": "Eskiz.uz (Узбекистан - notify.eskiz.uz)",
            "playmobile": "PlayMobile / SMS.uz (Узбекистан)",
            "smsru": "SMS.ru",
            "custom_webhook": "Custom Webhook API (GET/POST)",
            "simulation": "🧪 Тестовый режим (Симуляция без оплаты)"
        }.get(x, x),
        key=f"{key_prefix}_prov"
    )
    
    sender_name = st.text_input("Имя отправителя / Sender ID (напр. 4546 или CosmoClean):", value=cfg.get("sender_name", "4546"), key=f"{key_prefix}_sender")
    
    if provider == "eskiz":
        st.info("ℹ️ Укажите Email и Пароль от вашего личного кабинета на **notify.eskiz.uz**")
        eskiz_email = st.text_input("Eskiz Email:", value=cfg.get("eskiz_email", ""), key=f"{key_prefix}_esk_email")
        eskiz_pass = st.text_input("Eskiz Пароль:", value=cfg.get("eskiz_password", ""), type="password", key=f"{key_prefix}_esk_pass")
        cfg["eskiz_email"] = eskiz_email
        cfg["eskiz_password"] = eskiz_pass
    elif provider == "playmobile":
        pm_login = st.text_input("PlayMobile Логин:", value=cfg.get("playmobile_login", ""), key=f"{key_prefix}_pm_log")
        pm_pass = st.text_input("PlayMobile Пароль:", value=cfg.get("playmobile_password", ""), type="password", key=f"{key_prefix}_pm_pass")
        pm_orig = st.text_input("Originator Code (Originator ID):", value=cfg.get("playmobile_originator", "3700"), key=f"{key_prefix}_pm_orig")
        cfg["playmobile_login"] = pm_login
        cfg["playmobile_password"] = pm_pass
        cfg["playmobile_originator"] = pm_orig
    elif provider == "smsru":
        smsru_key = st.text_input("SMS.ru api_id:", value=cfg.get("smsru_api_id", ""), type="password", key=f"{key_prefix}_ru_key")
        cfg["smsru_api_id"] = smsru_key
    elif provider == "custom_webhook":
        c_url = st.text_input("Webhook URL (с переменными {phone} и {msg}):", value=cfg.get("custom_url", ""), key=f"{key_prefix}_cust_url")
        st.caption("Пример: `https://myapi.com/sms?to={phone}&text={msg}`")
        cfg["custom_url"] = c_url
        
    st.markdown("#### ⚡ Автоматическая отправка СМС по этапам")
    col_a1, col_a2 = st.columns(2)
    auto_create = col_a1.checkbox("🆕 При создании заказа", value=cfg.get("auto_on_create", True), key=f"{key_prefix}_ac")
    auto_measured = col_a2.checkbox("📐 При замере в цех", value=cfg.get("auto_on_measured", True), key=f"{key_prefix}_am")
    auto_ready = col_a1.checkbox("📦 При готовности заказа", value=cfg.get("auto_on_ready", True), key=f"{key_prefix}_ar")
    auto_completed = col_a2.checkbox("✅ При завершении заказа", value=cfg.get("auto_on_completed", True), key=f"{key_prefix}_acomp")
    
    with st.expander("📝 Настройки шаблонов текстов СМС", expanded=False):
        st.caption("Переменные: `{client}`, `{order_id}`, `{courier}`, `{sum}`, `{items}`")
        t_create = st.text_area("1. Новый заказ:", value=cfg.get("template_create_ru", ""), key=f"{key_prefix}_tc", height=70)
        t_measured = st.text_area("2. Принят в цех и замерен:", value=cfg.get("template_measured_ru", ""), key=f"{key_prefix}_tm", height=70)
        t_ready = st.text_area("3. Высушен и готов к доставке:", value=cfg.get("template_ready_ru", ""), key=f"{key_prefix}_tr", height=70)
        t_completed = st.text_area("4. Заказ завершен:", value=cfg.get("template_completed_ru", ""), key=f"{key_prefix}_tcomp", height=70)
    
    cfg["enabled"] = enabled
    cfg["provider"] = provider
    cfg["sender_name"] = sender_name
    cfg["auto_on_create"] = auto_create
    cfg["auto_on_measured"] = auto_measured
    cfg["auto_on_ready"] = auto_ready
    cfg["auto_on_completed"] = auto_completed
    cfg["template_create_ru"] = t_create
    cfg["template_measured_ru"] = t_measured
    cfg["template_ready_ru"] = t_ready
    cfg["template_completed_ru"] = t_completed
    
    if st.button("💾 Сохранить настройки СМС", type="primary", key=f"{key_prefix}_save_btn", use_container_width=True):
        if sms_manager.save_sms_config(cfg):
            st.success("✅ Настройки СМС успешно сохранены!")
            st.rerun()
    
    st.divider()
    st.markdown("#### 🧪 Тестовая отправка СМС")
    if provider == "eskiz":
        st.caption("ℹ️ Для тестирования в Eskiz.uz разрешены тексты: `Это тест от Eskiz`, `Bu Eskiz dan test`, `This is test from Eskiz`")
        default_test_text = "Это тест от Eskiz"
    else:
        default_test_text = "Тест СМС от Cosmo Cleaning Service!"

    c_t1, c_t2 = st.columns([1, 2])
    test_phone = c_t1.text_input("Телефон (9 цифр):", placeholder="901234567", key=f"{key_prefix}_test_p")
    test_msg = c_t2.text_input("Текст сообщения:", value=default_test_text, key=f"{key_prefix}_test_m")
    if st.button("🚀 Отправить тестовое СМС", key=f"{key_prefix}_test_btn", use_container_width=True):
        if not test_phone:
            st.warning("Укажите номер телефона!")
        else:
            with st.spinner("Отправка СМС через " + provider + "..."):
                ok, info = sms_manager.send_sms_notification(test_phone, test_msg, order_id="TEST", provider_cfg=cfg)
                if ok:
                    st.success(f"✅ {info}")
                else:
                    st.error(f"❌ {info}")


def render_sms_history_ui():
    """Отображает логи и историю отправленных СМС сообщений"""
    st.markdown("### 📜 История отправленных СМС")
    history = sms_manager.get_sms_history()
    if not history:
        st.info("История отправки СМС пока пуста.")
    else:
        df_hist = pd.DataFrame(history)
        df_hist.columns = ["Время", "Заказ №", "Телефон", "Сообщение", "Провайдер", "Статус"]
        st.dataframe(df_hist, use_container_width=True, hide_index=True)


def render_sms_quick_send_box(order_row, key_prefix="sms"):
    """Панель ручной отправки СМС клиенту для любого заказа"""
    client = order_row.get("Клиент", "Клиент")
    phone = str(order_row.get("Телефон", ""))
    order_id = str(order_row.get("ID", "-"))
    
    with st.expander(f"📱 Отправить СМС клиенту ({client})", expanded=False):
        sms_cfg = sms_manager.get_sms_config()
        
        template_choice = st.selectbox(
            "Быстрый выбор шаблона:",
            [
                "Свой текст",
                "🆕 Новый заказ",
                "📐 Прием и замер",
                "📦 Готов к доставке",
                "✅ Заказ выполнен"
            ],
            key=f"{key_prefix}_tmpl_{order_id}"
        )
        
        default_text = ""
        if template_choice == "🆕 Новый заказ":
            default_text = sms_manager.format_sms_message(sms_cfg.get("template_create_ru", ""), order_row)
        elif template_choice == "📐 Прием и замер":
            default_text = sms_manager.format_sms_message(sms_cfg.get("template_measured_ru", ""), order_row)
        elif template_choice == "📦 Готов к доставке":
            default_text = sms_manager.format_sms_message(sms_cfg.get("template_ready_ru", ""), order_row)
        elif template_choice == "✅ Заказ выполнен":
            default_text = sms_manager.format_sms_message(sms_cfg.get("template_completed_ru", ""), order_row)
        
        sms_body = st.text_area(
            "Текст СМС:",
            value=default_text,
            height=90,
            key=f"{key_prefix}_text_{order_id}"
        )
        
        st.caption(f"📞 Получатель: `{phone}`")
        
        if st.button("🚀 Отправить СМС клиенту", type="primary", key=f"{key_prefix}_send_btn_{order_id}"):
            if not sms_body.strip():
                st.warning("Введите текст СМС!")
            else:
                with st.spinner("Отправка СМС..."):
                    ok, resp_msg = sms_manager.send_sms_notification(phone, sms_body, order_id=order_id)
                    if ok:
                        st.success(f"✅ {resp_msg}")
                    else:
                        st.error(f"❌ {resp_msg}")


def generate_receipt_html(row):
    """Генерация стильного печатного HTML-чека для клиента"""
    order_id = row.get('ID', '-')
    client = row.get('Клиент', '-')
    phone = row.get('Телефон', '-')
    address = f"{row.get('Район', '')}, {row.get('Адрес', '')}".strip(', ')
    items = row.get('Размеры', '-')
    measurements = row.get('Измерения', '-')
    
    try:
        sum_val = int(float(row.get('Сумма', 0)))
    except Exception:
        sum_val = 0
        
    try:
        paid_val = int(float(row.get('Оплачено', 0)))
    except Exception:
        paid_val = sum_val
        
    ptype = row.get('Тип оплаты', 'Наличные')
    date_val = row.get('Дата', datetime.now().strftime("%d.%m.%Y"))

    receipt_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background: #ffffff; color: #1e293b; padding: 20px; }}
            .receipt-box {{ max-width: 400px; margin: 0 auto; border: 2px solid #1e3a8a; border-radius: 12px; padding: 20px; font-size: 14px; }}
            .header {{ text-align: center; border-bottom: 2px dashed #94a3b8; padding-bottom: 12px; margin-bottom: 12px; }}
            .logo {{ font-size: 20px; font-weight: bold; color: #1e3a8a; }}
            .row {{ display: flex; justify-content: space-between; margin-bottom: 6px; }}
            .items {{ background: #f1f5f9; padding: 10px; border-radius: 6px; margin: 12px 0; }}
            .total {{ font-size: 16px; font-weight: bold; text-align: right; border-top: 2px solid #1e3a8a; padding-top: 10px; margin-top: 10px; }}
            .footer {{ text-align: center; font-size: 12px; color: #64748b; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="receipt-box">
            <div class="header">
                <div class="logo">✨ Cosmo Cleaning Service ✨</div>
                <div>Чек № {order_id} | {date_val}</div>
            </div>
            <div class="row"><b>Клиент:</b> <span>{client}</span></div>
            <div class="row"><b>Тел:</b> <span>{phone}</span></div>
            <div class="row"><b>Адрес:</b> <span>{address}</span></div>
            
            <div class="items">
                <b>🧺 Заказ:</b> {items}<br>
                {"<b>📏 Замеры:</b> " + str(measurements) if str(measurements) not in ["-", "nan", "None", ""] else ""}
            </div>

            <div class="row"><b>Сумма заказа:</b> <span>{sum_val:,} сум</span></div>
            <div class="row"><b>Способ оплаты:</b> <span>{ptype}</span></div>
            
            <div class="total">
                Оплачено: {paid_val:,} сум
            </div>
            <div class="footer">
                Спасибо за заказ! 🧼<br>Cosmo Cleaning Service
            </div>
        </div>
    </body>
    </html>
    """
    return receipt_html


def get_clean_orders():
    if use_gsheet and sheet is not None:
        try:
            data = sheet.get_all_values()
            if len(data) > 1:
                headers = [str(h).strip() for h in data[0]]
                records = data[1:]
                df = pd.DataFrame(records, columns=headers)
                df = df.loc[:, ~df.columns.duplicated()]
                for col in EXPECTED_HEADERS:
                    if col not in df.columns:
                        df[col] = ""
                save_local_backup(df)
                return df
        except Exception:
            pass
    return load_local_backup()


def get_users_df():
    if use_gsheet and user_sheet is not None:
        try:
            data = user_sheet.get_all_records()
            if data:
                df = pd.DataFrame([{str(k).strip(): v for k, v in d.items()} for d in data])
                save_local_users(df)
                return df
        except Exception:
            pass
    return load_local_users()


def add_user_to_db(username, password, role, status="Ожидает одобрения"):
    try:
        u_df = get_users_df()
        new_row = pd.DataFrame([{"Username": str(username).strip(), "Password": str(password).strip(), "Role": role, "Status": status}])
        u_df = pd.concat([u_df, new_row], ignore_index=True)
        save_local_users(u_df)

        if use_gsheet and user_sheet is not None:
            try:
                user_sheet.append_row([username, password, role, status])
            except Exception:
                pass
        return True
    except Exception as e:
        st.error(f"Ошибка при добавлении пользователя: {e}")
        return False


def update_user_status(username, new_status):
    try:
        u_df = get_users_df()
        if not u_df.empty and "Username" in u_df.columns:
            u_df.loc[u_df["Username"].astype(str) == str(username), "Status"] = new_status
            save_local_users(u_df)

        if use_gsheet and user_sheet is not None:
            try:
                try:
                    cell = user_sheet.find(str(username), in_column=1)
                except Exception:
                    cell = user_sheet.find(str(username))
                row = cell.row
                header_row = [str(h).strip() for h in user_sheet.row_values(1)]
                col_idx = 4
                if "Status" in header_row:
                    col_idx = header_row.index("Status") + 1
                elif "Статус" in header_row:
                    col_idx = header_row.index("Статус") + 1
                user_sheet.update_cell(row, col_idx, new_status)
            except Exception:
                pass
        return True
    except Exception as e:
        st.error(f"Ошибка обновления пользователя: {e}")
        return False


def delete_user(username):
    try:
        u_df = get_users_df()
        if not u_df.empty and "Username" in u_df.columns:
            u_df = u_df[u_df["Username"].astype(str) != str(username)]
            save_local_users(u_df)

        if use_gsheet and user_sheet is not None:
            try:
                try:
                    cell = user_sheet.find(str(username), in_column=1)
                except Exception:
                    cell = user_sheet.find(str(username))
                user_sheet.delete_rows(cell.row)
            except Exception:
                pass
        return True
    except Exception as e:
        st.error(f"Ошибка удаления пользователя: {e}")
        return False


def normalize_id_str(val):
    try:
        if pd.isna(val) or val is None:
            return ""
        v_str = str(val).strip()
        if v_str.endswith(".0"):
            v_str = v_str[:-2]
        return str(int(float(v_str)))
    except Exception:
        return str(val).strip()


def update_order_in_sheet(order_id, updates):
    try:
        target_id = normalize_id_str(order_id)
        current_df = get_clean_orders()
        if not current_df.empty and "ID" in current_df.columns:
            mask = current_df["ID"].apply(normalize_id_str) == target_id
            if mask.any():
                for col_key, val in updates.items():
                    if isinstance(col_key, str):
                        if col_key not in current_df.columns:
                            current_df[col_key] = ""
                        current_df[col_key] = current_df[col_key].astype(object)
                        current_df.loc[mask, col_key] = str(val) if val is not None else ""
                save_local_backup(current_df)

        if use_gsheet and sheet is not None:
            try:
                cell = None
                try:
                    cell = sheet.find(str(target_id), in_column=1)
                except Exception:
                    cell = sheet.find(str(order_id))
                if cell is not None:
                    row = cell.row
                    header_row = [str(h).strip() for h in sheet.row_values(1)]
                    
                    for col_key, value in updates.items():
                        if isinstance(col_key, str) and col_key in header_row:
                            col_idx = header_row.index(col_key) + 1
                            sheet.update_cell(row, col_idx, value)
                        elif isinstance(col_key, int):
                            sheet.update_cell(row, col_key, value)
            except Exception:
                pass
        return True
    except Exception as e:
        st.error(f"Ошибка обновления заказа: {e}")
        return False


def delete_order_in_sheet(order_id):
    try:
        target_id = normalize_id_str(order_id)
        current_df = get_clean_orders()
        if not current_df.empty and "ID" in current_df.columns:
            mask = current_df["ID"].apply(normalize_id_str) == target_id
            if mask.any():
                updated_df = current_df[~mask].copy()
                save_local_backup(updated_df)

        if use_gsheet and sheet is not None:
            try:
                cell = None
                try:
                    cell = sheet.find(str(target_id), in_column=1)
                except Exception:
                    cell = sheet.find(str(order_id))
                if cell is not None:
                    sheet.delete_rows(cell.row)
            except Exception:
                pass
        return True
    except Exception as e:
        st.error(f"Ошибка удаления заказа: {e}")
        return False


def add_order_to_sheet(order_data):
    try:
        current_df = get_clean_orders()
        order_id = order_data.get("ID") or get_next_order_id(current_df)
        date_now = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

        new_row = {
            "ID": order_id,
            "Дата": date_now,
            "Клиент": order_data.get("Клиент", ""),
            "Телефон": order_data.get("Телефон", ""),
            "Адрес": order_data.get("Адрес", ""),
            "Размеры": order_data.get("Размеры", ""),
            "Площадь": order_data.get("Площадь", 0),
            "Сумма": order_data.get("Сумма", 0),
            "Статус": order_data.get("Статус", "Ожидает забора"),
            "Курьер": order_data.get("Курьер", ""),
            "Диспетчер": order_data.get("Диспетчер", ""),
            "Район": order_data.get("Район", ""),
            "Язык": order_data.get("Язык", ""),
            "Локация": order_data.get("Локация", "-"),
            "Оплачено": order_data.get("Оплачено", 0),
            "Тип оплаты": order_data.get("Тип оплаты", "-"),
            "Причина": order_data.get("Причина", "-")
        }

        updated_df = pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True)
        save_local_backup(updated_df)

        if use_gsheet and sheet is not None:
            try:
                sheet.append_row([
                    order_id, date_now, order_data.get("Клиент", ""),
                    order_data.get("Телефон", ""), order_data.get("Адрес", ""),
                    order_data.get("Размеры", ""), order_data.get("Площадь", 0),
                    order_data.get("Сумма", 0), order_data.get("Статус", "Ожидает забора"),
                    order_data.get("Курьер", ""), order_data.get("Диспетчер", ""),
                    order_data.get("Район", ""), order_data.get("Язык", ""),
                    order_data.get("Локация", "-"), order_data.get("Оплачено", 0),
                    order_data.get("Тип оплаты", "-"), order_data.get("Причина", "-")
                ])
            except Exception:
                pass
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения заказа: {e}")
        return False


# Координаты Главного Цеха (Самарканд)
FACTORY_LAT, FACTORY_LNG = 39.6644, 66.9388

# Координаты центральных точек районов Самарканда для резервного отображения на карте
DISTRICT_COORDS = {
    "Сиёб (Siyob)": (39.6550, 66.9750),
    "Багишамальский": (39.6400, 66.9500),
    "Согдиана": (39.6700, 66.9300),
    "Микрорайон": (39.6800, 66.9200),
    "Саттепо": (39.6300, 66.9100),
    "Железнодорожный": (39.6750, 66.9050),
    "Самаркандский р-н": (39.6600, 66.9400),
    "Самарканд город": (39.6542, 66.9597),
    "Сельский район": (39.6200, 66.9000),
    "Фабричный": (39.6644, 66.9388)
}


def extract_coords(loc_str, district=None):
    """Извлекает (lat, lng, is_exact_gps) из текста локации или с фолбэком по району"""
    if loc_str and isinstance(loc_str, str):
        # 1. Поиск lat=... lng=...
        match = re.search(r'lat=([0-9\.]+).*?lng=([0-9\.]+)', loc_str, re.IGNORECASE)
        if match:
            return float(match.group(1)), float(match.group(2)), True

        # 2. Поиск URL параметров ll=... или rtext=...~lat,lng
        match_url = re.search(r'(?:ll=|rtext=.*?~|q=)([0-9\.]+)[,%2C]+([0-9\.]+)', loc_str, re.IGNORECASE)
        if match_url:
            n1, n2 = float(match_url.group(1)), float(match_url.group(2))
            if 30.0 <= n1 <= 45.0 and 60.0 <= n2 <= 75.0:
                return n1, n2, True
            elif 60.0 <= n1 <= 75.0 and 30.0 <= n2 <= 45.0:
                return n2, n1, True

        # 3. Поиск любых двух десятичных чисел (широта и долгота)
        numbers = re.findall(r'[0-9]+\.[0-9]+', loc_str)
        if len(numbers) >= 2:
            num1, num2 = float(numbers[0]), float(numbers[1])
            if 30.0 <= num1 <= 45.0 and 60.0 <= num2 <= 75.0:
                return num1, num2, True
            elif 60.0 <= num1 <= 75.0 and 30.0 <= num2 <= 45.0:
                return num2, num1, True

    # 4. Резервный фолбэк по району
    if district and district in DISTRICT_COORDS:
        lat, lng = DISTRICT_COORDS[district]
        return lat, lng, False

    return None


def get_yandex_route_url(district, address, loc_str):
    """
    Строит прямую ссылку для открывания навигатора по ТОЧНОЙ геолокации или адресу курьера.
    Возвращает tuple: (web_url, is_exact_gps, navi_deeplink)
    """
    coords_res = extract_coords(loc_str, district)
    if coords_res:
        lat, lng, is_exact = coords_res
        if is_exact:
            web_url = f'https://yandex.ru/maps/?rtext=~{lat},{lng}&rtt=auto'
            navi_deeplink = f'yandexnavi://build_route_on_map?lat_to={lat}&lon_to={lng}'
            return web_url, True, navi_deeplink
    
    clean_addr = str(address).strip() if address and str(address).strip() not in ["-", ""] else ""
    full_address = f'Самарканд, {district}, {clean_addr}'.strip(', ')
    encoded_address = urllib.parse.quote(full_address)
    web_url = f'https://yandex.ru/maps/?rtext=~{encoded_address}&rtt=auto'
    navi_deeplink = f'yandexnavi://build_route_on_map?lat_to=&lon_to=&text={encoded_address}'
    return web_url, False, navi_deeplink


def update_lang_from_login():
    val = st.session_state.get("login_lang_radio")
    if val == "🇷🇺 Русский":
        st.session_state["lang"] = "ru"
    else:
        st.session_state["lang"] = "uz"


def update_lang_from_sidebar():
    val = st.session_state.get("sidebar_lang_select")
    if val == "🇷🇺 Русский":
        st.session_state["lang"] = "ru"
    else:
        st.session_state["lang"] = "uz"


# --- ВХОД И РЕГИСТРАЦИЯ ---
if not st.session_state["logged_in"]:
    st.radio(
        "Language / Тил:",
        ["🇷🇺 Русский", "🇺🇿 O'zbekcha"],
        horizontal=True,
        index=0 if st.session_state.get("lang", "ru") == "ru" else 1,
        key="login_lang_radio",
        on_change=update_lang_from_login
    )
    t = LOCALES[st.session_state["lang"]]
    
    choice = st.radio(f"{t['user_label']}:", [t["login"], t["register_tab"]], horizontal=True)
    users_df = get_users_df()
    
    if choice == t["login"]:
        with st.form("login_form"):
            username_input = st.text_input(t["username"]).strip()
            password_input = st.text_input(t["password"], type="password").strip()
            login_submit = st.form_submit_button(t["submit_login"])
            
        if login_submit:
            user_row = users_df[users_df["Username"] == username_input]
            if user_row.empty:
                st.error(t["error_not_found"])
            else:
                db_password = str(user_row.iloc[0]["Password"]).strip()
                db_status = user_row.iloc[0]["Status"]
                db_role = user_row.iloc[0]["Role"]
                
                role_eng_map = {
                    "Администратор": "Administrator", "Administrator": "Administrator", "Admin": "Administrator",
                    "Диспетчер": "Dispatcher", "Dispetcher": "Dispatcher",
                    "Доставщик (Курьер)": "Courier", "Yuboruvchi (Kuryer)": "Courier", "Курьер": "Courier",
                    "Мойщик": "Washer", "Yuvuvchi (Sex xodimi)": "Washer",
                    "Чистильщик от волос": "Cleaner", "Yung va sochdan tozalovchi": "Cleaner"
                }
                final_role = role_eng_map.get(db_role, db_role)
                
                if password_input != db_password:
                    st.error(t["error_password"])
                elif db_status == "Ожидает одобрения":
                    st.warning(t["warn_approval"])
                elif db_status == "Активен":
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username_input
                    st.session_state["role"] = final_role
                    st.query_params["user"] = username_input
                    st.query_params["role"] = final_role
                    st.success(t["success_login"])
                    st.rerun()
                    
    elif choice == t["register_tab"]:
        with st.form("register_form"):
            reg_username = st.text_input(t["username"]).strip()
            reg_password = st.text_input(t["password"], type="password").strip()
            reg_role = st.selectbox(
                t["role_select"],
                [t["Courier"], t["Washer"]]
            )
            reg_submit = st.form_submit_button(t["submit_reg"])
            
        if reg_submit:
            if not reg_username or not reg_password:
                st.error(t["reg_error_fields"])
            elif reg_username in users_df["Username"].values:
                st.error(t["reg_error_exists"])
            else:
                if add_user_to_db(reg_username, reg_password, reg_role, "Ожидает одобрения"):
                    st.success(t["reg_success"])
    st.stop()

# --- БОКОВАЯ ПАНЕЛЬ ---
st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        color: #f8fafc !important;
    }
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

if os.path.exists("cosmo_logo.jpg"):
    st.sidebar.image("cosmo_logo.jpg", use_container_width=True)

st.sidebar.markdown(f"### ✨ {LOCALES[st.session_state['lang']]['brand']}")
st.sidebar.selectbox(
    "Language / Тил", 
    ["🇷🇺 Русский", "🇺🇿 O'zbekcha"], 
    index=0 if st.session_state.get("lang", "ru") == "ru" else 1,
    key="sidebar_lang_select",
    on_change=update_lang_from_sidebar
)

t = LOCALES[st.session_state["lang"]]

st.sidebar.markdown("---")
st.sidebar.write(f"👤 **{t['user_label']}:** `{st.session_state['username']}`")

disp_role_map = {
    "Administrator": t["Admin"],
    "Dispatcher": t["Dispatcher"],
    "Courier": t["Courier"],
    "Washer": t["Washer"],
    "Cleaner": t["Cleaner"]
}
st.sidebar.write(f"💼 **{t['role_label']}:** `{disp_role_map.get(st.session_state['role'], st.session_state['role'])}`")

if use_gsheet:
    st.sidebar.success("🌐 База: Google Sheets (Online)")
else:
    st.sidebar.info("💻 База: Локальная (Offline)")
if "admin_nav_choice" not in st.session_state:
    st.session_state["admin_nav_choice"] = "📊 Главный дашборд"

if "settings_subtab" not in st.session_state:
    st.session_state["settings_subtab"] = "🤖 Telegram Бот и Курьеры"

st.sidebar.markdown("---")

user_role = st.session_state.get("role", "Administrator")

# Показываем боковые панели администратора только для Администратора
if user_role in ["Administrator", "Admin", "Администратор"]:
    # 1. Кнопка-панель "📌 Разделы CRM" (кнопки внутри)
    with st.sidebar.expander("📌 Разделы CRM", expanded=True):
        nav_items = [
            ("📊 Главный дашборд", "sb_btn_dash"),
            ("📋 Все заказы", "sb_btn_orders"),
            ("💰 Долги клиентов", "sb_btn_debts"),
            ("💵 Зарплаты и Комиссии", "sb_btn_salary"),
            ("👥 Управление сотрудниками", "sb_btn_users"),
            ("🗺️ Карта заказов", "sb_btn_map")
        ]
        for label, btn_key in nav_items:
            is_active = (st.session_state.get("admin_nav_choice") == label)
            if st.button(
                label,
                key=btn_key,
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state["admin_nav_choice"] = label
                st.rerun()

    # 2. Кнопка-панель "⚙️ Настройки CRM" (кнопки внутри)
    with st.sidebar.expander("⚙️ Настройки CRM", expanded=(st.session_state.get("admin_nav_choice") == "⚙️ Настройки")):
        settings_sub_items = [
            ("🤖 Telegram Бот и Курьеры", "sub_btn_tg"),
            ("🌐 Google Таблица", "sub_btn_gs"),
            ("📱 Настройки SMS", "sub_btn_sms_cfg"),
            ("📜 История SMS", "sub_btn_sms_hist"),
            ("🏷️ Прейскурант цен", "sub_btn_pricing"),
            ("💾 Бекап и Резерв", "sub_btn_backup")
        ]
        for sub_label, sub_key in settings_sub_items:
            is_sub_active = (st.session_state.get("admin_nav_choice") == "⚙️ Настройки" and st.session_state.get("settings_subtab") == sub_label)
            if st.button(
                sub_label,
                key=sub_key,
                use_container_width=True,
                type="primary" if is_sub_active else "secondary"
            ):
                st.session_state["admin_nav_choice"] = "⚙️ Настройки"
                st.session_state["settings_subtab"] = sub_label
                st.rerun()

    with st.sidebar.expander("📲 Telegram Уведомления", expanded=False):
        cfg = get_tg_config()
        default_token = st.session_state.get("tg_bot_token") or cfg.get("bot_token", "")
        default_chat = st.session_state.get("tg_chat_id") or cfg.get("chat_id", "")
        
        tg_token = st.text_input("Bot Token:", value=default_token, type="password", key="tg_token_input")
        tg_chat = st.text_input("Chat ID:", value=default_chat, key="tg_chat_input")
        
        if tg_token or tg_chat:
            st.session_state["tg_bot_token"] = tg_token
            st.session_state["tg_chat_id"] = tg_chat
            save_tg_config(courier_bot_token=tg_token, chat_id=tg_chat)
            
        if tg_token and tg_chat:
            st.success("✅ Бот подключен")
            if st.button("🧪 Отправить тест в Telegram", key="test_tg_btn"):
                res = send_telegram_notification("🧪 <b>Тестовое сообщение от Cosmo CRM!</b>\nБот успешно настроен и работает!")
                if res:
                    st.success("🎉 Тестовое сообщение доставлено!")

    with st.sidebar.expander("📱 SMS Уведомления", expanded=False):
        render_sms_settings_ui(key_prefix="sb_sms")

admin_nav_choice = st.session_state.get("admin_nav_choice", "📊 Главный дашборд")

if st.sidebar.button(f"{t['logout']} 🔓"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.query_params.clear()
    st.rerun()


df = get_clean_orders()
role = st.session_state["role"]

ui_theme.inject_theme()

couriers_df = get_users_df()
courier_list = []
if not couriers_df.empty and "Role" in couriers_df.columns:
    courier_list = couriers_df[couriers_df["Role"].isin(["Courier", "Доставщик (Курьер)", "Yuboruvchi (Kuryer)"])]["Username"].tolist()
if not courier_list:
    courier_list = ["Алишер Каримов", "Бобур Ибрагимов", "Сардор Турсунов"]

if role in ["Dispatcher", "Диспетчер", "Dispetcher"]:
    dispatcher_view.render_dispatcher_view(
        df=df, t=t, courier_list=courier_list,
        get_next_order_id_func=get_next_order_id,
        add_order_func=add_order_to_sheet,
        update_order_func=update_order_in_sheet,
        send_tg_func=send_telegram_notification,
        sms_mgr=sms_manager
    )

elif role in ["Courier", "Доставщик (Курьер)", "Yuboruvchi (Kuryer)", "Курьер"]:
    courier_view.render_courier_view(
        df=df, t=t, courier_name=st.session_state.get("username", "Курьер"),
        update_order_func=update_order_in_sheet,
        delete_order_func=delete_order_in_sheet,
        add_order_func=add_order_to_sheet,
        get_next_order_id_func=get_next_order_id,
        get_yandex_route_url_func=get_yandex_route_url,
        send_tg_func=send_telegram_notification,
        active_couriers=courier_list
    )

elif role in ["Washer", "Cleaner", "Мойщик", "Чистильщик от волос", "Yuvuvchi (Sex xodimi)", "Yung va sochdan tozalovchi"]:
    washer_view.render_washer_view(
        df=df, t=t, washer_name=st.session_state.get("username", "Мойщик"),
        update_order_func=update_order_in_sheet,
        send_tg_func=send_telegram_notification
    )

elif role in ["Administrator", "Admin", "Администратор"]:
    lang = st.session_state.get("lang", "ru")
    
    if "Главный дашборд" in admin_nav_choice:
        dashboard_view.render_dashboard_view(df)

    elif "Все заказы" in admin_nav_choice:
        orders_view.render_orders_view(df, update_order_in_sheet, generate_receipt_html)

    elif "Долги клиентов" in admin_nav_choice:
        debt_manager.render_debts_ui(df, update_order_in_sheet)

    elif "Зарплаты" in admin_nav_choice:
        salary_manager.render_salary_ui(df, get_users_df())

    # ===================== КАРТА (ЯНДЕКС.КАРТЫ) =====================
    elif "Карта заказов" in admin_nav_choice:
        st.subheader("🗺️ Карта заказов и логистики")
        
        # 1. Фильтры даты, ID и категорий
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        with col_f1:
            show_all_dates = st.checkbox("📅 Все даты (показать все заказы)", value=True, key="admin_map_alldates")
            if not show_all_dates:
                filter_date = st.date_input("Выберите дату", value=datetime.today(), key="admin_map_date")
        with col_f2:
            search_id = st.text_input("🔍 Поиск по ID", placeholder="Например: 5200", key="admin_map_id")
        with col_f3:
            status_filter = st.multiselect(
                "🎨 Фильтр меток на карте:",
                ["🟠 Ожидают забора", "🔴 В работе / Не доставлены", "🟢 Доставлены (Выполнены)"],
                default=["🟠 Ожидают забора", "🔴 В работе / Не доставлены", "🟢 Доставлены (Выполнены)"]
            )
            
        # 2. Фильтрация данных
        map_df = df.copy()
        
        is_search_by_id = False
        if search_id.strip():
            map_df = map_df[map_df["ID"].astype(str) == search_id.strip()]
            is_search_by_id = True
        elif not show_all_dates:
            formatted_date = filter_date.strftime("%d.%m.%Y")
            if "Дата" in map_df.columns:
                map_df = map_df[map_df["Дата"].astype(str).str.contains(formatted_date)]
        
        pending_pickup_df = map_df[map_df["Статус"] == "Ожидает забора"]
        in_progress_df = map_df[~map_df["Статус"].isin(["Ожидает забора", "Выполнен"])]
        completed_df = map_df[map_df["Статус"] == "Выполнен"]
        
        if is_search_by_id:
            if not map_df.empty:
                row_info = map_df.iloc[0]
                st.success(f"✅ **Найден заказ №{row_info['ID']}**")
                
                with st.expander("📄 Раскрыть полную информацию о заказе", expanded=True):
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.write(f"📅 **Дата приема:** {row_info.get('Дата', 'Не указана')}")
                        st.write(f"👤 **Клиент:** {row_info.get('Клиент', '')}")
                        st.write(f"📞 **Телефон:** {row_info.get('Телефон', '')}")
                    with col_info2:
                        st.write(f"📌 **Статус:** {row_info.get('Статус', '')}")
                        st.write(f"🏠 **Адрес:** {row_info.get('Район', '')}, {row_info.get('Адрес', '')}")
                        st.write(f"🚗 **Курьер:** {row_info.get('Курьер', '')}")
                    with col_info3:
                        st.write(f"🧺 **Вещи:** {row_info.get('Размеры', '')}")
                        st.write(f"💰 **Сумма:** {row_info.get('Сумма', '0')} сум")
                    
                    st.divider()
                    r_data = generate_receipt_html(row_info)
                    st.download_button(
                        label="🧾 Скачать Чек для этого заказа (HTML)",
                        data=r_data,
                        file_name=f"receipt_{row_info['ID']}.html",
                        mime="text/html",
                        key=f"search_receipt_{row_info['ID']}"
                    )
            else:
                st.error(f"❌ Заказ с номером {search_id.strip()} не найден.")
        else:
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("📦 Всего на карте", len(map_df))
            col_m2.metric("🟠 Ожидают забора", len(pending_pickup_df))
            col_m3.metric("🔴 В работе (Цех)", len(in_progress_df))
            col_m4.metric("🟢 Доставлено", len(completed_df))
        
        st.divider()

        # 3. Собираем данные в JSON
        markers_data = []
        debug_info = []

        for idx, row in map_df.iterrows():
            loc = str(row.get("Локация", ""))
            status = str(row.get("Статус", ""))
            district = str(row.get("Район", ""))
            
            if status == "Ожидает забора":
                category_name, preset, status_badge = "🟠 Ожидают забора", "islands#orangeDotIcon", "🟠 Ожидает забора"
            elif status == "Выполнен":
                category_name, preset, status_badge = "🟢 Доставлены (Выполнены)", "islands#greenDotIcon", "🟢 Доставлен (Выполнен)"
            else:
                category_name, preset, status_badge = "🔴 В работе / Не доставлены", "islands#redDotIcon", f"🔴 В процессе ({status})"

            if category_name not in status_filter:
                continue

            coords_res = extract_coords(loc, district)
            if coords_res:
                lat, lng, is_exact = coords_res
                marker_preset = preset if is_exact else "islands#yellowDotIcon"
                markers_data.append({
                    "id": str(row.get("ID", "")),
                    "lat": lat,
                    "lng": lng,
                    "client": str(row.get("Клиент", "Неизвестно")),
                    "phone": str(row.get("Телефон", "")),
                    "address": f"{district}, {row.get('Адрес', '')}",
                    "items": str(row.get("Размеры", "-")),
                    "status_badge": status_badge + (" (📍 GPS)" if is_exact else f" (🗺️ Ориентир: {district})"),
                    "preset": marker_preset
                })
                debug_info.append(f"✅ Заказ №{row.get('ID')}: Метка добавлена ({'Точный GPS' if is_exact else 'Фолбэк по району: ' + district}) -> [{lat}, {lng}]")
            else:
                debug_info.append(f"⚠️ Заказ №{row.get('ID')}: Не удалось распознать локацию даже по району: '{loc}'")

        # Превращаем список в JSON строку
        markers_json = json.dumps(markers_data, ensure_ascii=False)
        FACTORY_LAT, FACTORY_LNG = 39.6644, 66.9388 

        # 4. HTML и чистый JS
        yandex_map_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <script src="https://api-maps.yandex.ru/2.1/?lang=ru_RU" type="text/javascript"></script>
            <style>
                #map {{ width: 100%; height: 550px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
                .legend {{ background: #ffffff; padding: 10px 15px; border-radius: 8px; font-family: sans-serif; font-size: 13px; margin-top: 10px; display: flex; gap: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
                .legend-item {{ display: flex; align-items: center; gap: 6px; }}
                .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            
            <div class="legend">
                <div class="legend-item"><span class="dot" style="background: #1E88E5;"></span> 🏢 Цех (ул. Зебунисо, 20)</div>
                <div class="legend-item"><span class="dot" style="background: #FFA726;"></span> 🟠 Ожидает забора</div>
                <div class="legend-item"><span class="dot" style="background: #EF5350;"></span> 🔴 В работе / Не доставлен</div>
                <div class="legend-item"><span class="dot" style="background: #66BB6A;"></span> 🟢 Доставлен</div>
            </div>

            <script type="text/javascript">
                ymaps.ready(init);
                function init() {{
                    var myMap = new ymaps.Map("map", {{
                        center: [{FACTORY_LAT}, {FACTORY_LNG}], 
                        zoom: 12,
                        controls: ['zoomControl', 'typeSelector', 'fullscreenControl', 'geolocationControl']
                    }});
                    
                    var bounds = [];
                    
                    // Добавляем Цех
                    var factoryPlacemark = new ymaps.Placemark([{FACTORY_LAT}, {FACTORY_LNG}], {{
                        balloonContent: '🏢 <b>Главный Цех / Фабрика</b><br>ул. Зебунисо, 20'
                    }}, {{
                        preset: 'islands#blueFactoryIcon',
                        iconColor: '#1E88E5'
                    }});
                    myMap.geoObjects.add(factoryPlacemark);
                    bounds.push([{FACTORY_LAT}, {FACTORY_LNG}]);
                    
                    // Безопасно загружаем данные заказов из Python
                    var mapData = {markers_json};
                    
                    // Рисуем точки
                    mapData.forEach(function(item) {{
                        var balloonHtml = "<div style='font-family: Arial, sans-serif; padding: 5px;'>" +
                            "<h4 style='margin: 0 0 5px 0; color: #333;'>📦 Заказ №" + item.id + "</h4>" +
                            "<b>Статус:</b> " + item.status_badge + "<br>" +
                            "<b>👤 Клиент:</b> " + item.client + "<br>" +
                            "<b>📞 Телефон:</b> " + item.phone + "<br>" +
                            "<b>🏠 Адрес:</b> " + item.address + "<br>" +
                            "<b>🧺 Вещи:</b> " + item.items +
                            "</div>";

                        var pm = new ymaps.Placemark([item.lat, item.lng], {{
                            balloonContent: balloonHtml,
                            hintContent: "Заказ №" + item.id + " - " + item.client
                        }}, {{
                            preset: item.preset
                        }});
                        
                        myMap.geoObjects.add(pm);
                        bounds.push([item.lat, item.lng]);
                    }});

                    // Умное масштабирование
                    if (bounds.length > 0) {{
                        myMap.setBounds(bounds, {{
                            checkZoomRange: true,
                            zoomMargin: 40
                        }}).then(function () {{
                            if (myMap.getZoom() > 15) myMap.setZoom(15);
                        }});
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
        components.html(yandex_map_html, height=620)

        # Диагностика
        with st.expander("🛠️ Диагностика карты (Техническая инфа)", expanded=True):
            st.write(f"Отображено на карте: **{len(markers_data)}** из **{len(map_df)}** заказов.")
            for info in debug_info:
                st.text(info)

    # ===================== СОТРУДНИКИ =====================
    elif "Управление сотрудниками" in admin_nav_choice:
        st.subheader("👥 " + t["employee_management"])
        col_users_list, col_add_user = st.columns([2, 1])
        
        with col_users_list:
            u_df = get_users_df() 
            
            # 1. СЕКЦИЯ: ЗАЯВКИ НА РЕГИСТРАЦИЮ (ОЖИДАЮТ ОДОБРЕНИЯ)
            status_col = "Status" if "Status" in u_df.columns else "Статус"
            pending_users = pd.DataFrame()
            if not u_df.empty and status_col in u_df.columns:
                pending_users = u_df[u_df[status_col].isin(["Ожидает одобрения", "Ожидает", "Pending"])]
            
            if not pending_users.empty:
                st.markdown("#### 📥 **Заявки на регистрацию (Ожидают одобрения):**")
                for p_idx, p_row in pending_users.iterrows():
                    p_name = p_row.get("Username", p_row.get("Логин", ""))
                    p_role = p_row.get("Role", p_row.get("Должность", ""))
                    
                    st.info(f"⏳ **{p_name}** | Должность: `{p_role}` | Статус: **Ожидает одобрения**")
                    cp1, cp2 = st.columns(2)
                    if cp1.button(f"✅ Одобрить {p_name}", key=f"appr_usr_{p_name}_{p_idx}", type="primary"):
                        if update_user_status(p_name, "Активен"):
                            st.success(f"Сотрудник {p_name} успешно одобрен!")
                            st.rerun()
                    if cp2.button(f"❌ Отклонить {p_name}", key=f"rej_usr_{p_name}_{p_idx}"):
                        if delete_user(p_name):
                            st.warning(f"Заявка сотрудника {p_name} отклонена.")
                            st.rerun()
                st.divider()
            
            # 2. СЕКЦИЯ: ДЕЙСТВУЮЩИЕ И УВОЛЕННЫЕ СОТРУДНИКИ
            active_fired_users = u_df
            if not u_df.empty and status_col in u_df.columns:
                active_fired_users = u_df[~u_df[status_col].isin(["Ожидает одобрения", "Ожидает", "Pending"])]
            
            st.markdown(f"#### **{t['current_employees']}**")
            st.dataframe(active_fired_users, use_container_width=True, hide_index=True)
            
            st.divider()
            st.markdown("#### ⚙️ Управление сотрудниками (Увольнение / Восстановление / Удаление):")
            if not active_fired_users.empty:
                for u_idx, u_row in active_fired_users.iterrows():
                    u_name = u_row.get("Username", u_row.get("Логин", ""))
                    u_role = u_row.get("Role", u_row.get("Должность", ""))
                    u_status = u_row.get(status_col, "Активен")
                    
                    if u_name:
                        c_info, c_act1, c_act2 = st.columns([2, 1, 1])
                        is_active = u_status in ["Активен", "Одобрен"]
                        status_badge = "🟢 Активен" if is_active else "🔴 Уволен"
                        c_info.write(f"👤 **{u_name}** (`{u_role}`) | {status_badge}")
                        
                        if is_active:
                            if c_act1.button("🛑 Уволить", key=f"fire_usr_{u_name}_{u_idx}"):
                                if update_user_status(u_name, "Уволен"):
                                    st.success(f"Сотрудник {u_name} уволен!")
                                    st.rerun()
                        else:
                            if c_act1.button("✅ Восстановить", key=f"rest_usr_{u_name}_{u_idx}"):
                                if update_user_status(u_name, "Активен"):
                                    st.success(f"Сотрудник {u_name} восстановлен!")
                                    st.rerun()
                                    
                        if c_act2.button("🗑️ Удалить", key=f"del_usr_{u_name}_{u_idx}"):
                            if delete_user(u_name):
                                st.success(f"Сотрудник {u_name} полностью удален из базы!")
                                st.rerun()
            
        with col_add_user:
            st.markdown(f"#### **{t['add_employee']}**")
            with st.form("admin_add_user_form", clear_on_submit=True):
                new_login = st.text_input(t["employee_login"])
                new_pass = st.text_input(t["employee_password"], type="password")
                new_role_preset = st.selectbox(t["employee_role"], ["Доставщик (Курьер)", "Мойщик", "Администратор", "Диспетчер", "Чистильщик от волос", "✍️ Ввести другую должность..."])
                if new_role_preset == "✍️ Ввести другую должность...":
                    new_role = st.text_input("Название должности:").strip()
                else:
                    new_role = new_role_preset
                
                submit_new_user = st.form_submit_button("➕ " + t["add_to_system"], type="primary")
                
                if submit_new_user:
                    if new_login and new_pass and new_role:
                        if add_user_to_db(new_login, new_pass, new_role, "Активен"):
                            st.success(t["employee_added"].format(login=new_login))
                            st.rerun()
                    else:
                        st.error(t["fill_login_password"])

    # ===================== НАСТРОЙКИ СИСТЕМЫ =====================
    elif "Настройки" in admin_nav_choice:
        sel_sub = st.session_state.get("settings_subtab", "🤖 Telegram Бот и Курьеры")

        if "Telegram" in sel_sub:
            st.subheader("🤖 Управление ботами Telegram (Курьер & Диспетчер)")
            tg_cfg = get_tg_config()
            
            c1, c2 = st.columns(2)
            courier_token_input = c1.text_input("🚚 Токен Бот-Курьера:", value=tg_cfg.get("courier_bot_token") or tg_cfg.get("bot_token", ""), placeholder="7922655457:AAEcMY...", key="admin_tg_cour_token")
            disp_token_input = c2.text_input("🎧 Токен Бот-Диспетчера:", value=tg_cfg.get("dispatcher_bot_token", ""), placeholder="8123456789:AABcDE...", key="admin_tg_disp_token")
            
            st.caption("💡 Если токен Диспетчера не указан, единый бот будет обрабатывать роли Диспетчера и Курьера автоматически.")
            
            st.markdown("#### 🌐 Ссылки на WebApp интерфейсы для Ботов Telegram:")
            w1, w2 = st.columns(2)
            cour_w_url_input = w1.text_input(
                "🌐 Ссылка на WebApp Курьера:",
                value=tg_cfg.get("courier_webapp_url", ""),
                placeholder="Например: https://crm-cosmo.streamlit.app/webapp",
                key="admin_tg_cour_w_url"
            )
            disp_w_url_input = w2.text_input(
                "🌐 Ссылка на WebApp Диспетчера:",
                value=tg_cfg.get("dispatcher_webapp_url", ""),
                placeholder="Например: https://crm-cosmo.streamlit.app",
                key="admin_tg_disp_w_url"
            )
            st.caption("💡 Укажите рабочую HTTPS ссылку на сайт CRM для открывания WebApp прямо из Telegram.")

            main_chat_input = st.text_input("📢 Основной Chat ID (Группа / Чаты Диспетчеров):", value=tg_cfg.get("chat_id", ""), placeholder="-1001234567890 или 12345678", key="admin_tg_main_chat")
            
            st.markdown("#### 👥 Персональные Chat ID курьеров (для уведомлений о новых заказах):")
            st.caption("Каждый курьер пишет `/start` в Бот Курьера, и его Chat ID привязывается к аккаунту:")
            
            courier_chats_input = {}
            u_df = get_users_df()
            cour_names = u_df[u_df["Role"].astype(str).str.contains("Курьер|Courier|Yuboruvchi|Доставщик", case=False, na=False)]["Username"].tolist() if not u_df.empty else ["akobir", "firuz", "Алишер Каримов"]
            
            existing_c_chats = tg_cfg.get("courier_chats", {})
            for cname in cour_names:
                cid_val = st.text_input(f"Chat ID курьера `{cname}`:", value=existing_c_chats.get(cname, "") or existing_c_chats.get(cname.lower(), ""), key=f"tg_cid_{cname}")
                if cid_val.strip():
                    courier_chats_input[cname] = cid_val.strip()
            
            if st.button("🚀 Сохранить настройки Telegram Ботов и WebApp ссылок", type="primary", use_container_width=True, key="save_tg_btn"):
                if save_tg_config(
                    courier_bot_token=courier_token_input,
                    dispatcher_bot_token=disp_token_input,
                    chat_id=main_chat_input,
                    courier_chats=courier_chats_input,
                    courier_webapp_url=cour_w_url_input,
                    dispatcher_webapp_url=disp_w_url_input
                ):
                    st.success("✅ Настройки ботов и ссылки WebApp успешно сохранены!")
                    st.rerun()

            st.markdown("---")
            st.markdown("### ⚡ Автоматический Cloudflare Туннель (HTTPS для Telegram)")
            st.info("💡 Если CRM запущен локально на вашем компьютере, нажмите эту кнопку для автоматического создания HTTPS туннеля через `cloudflared.exe`.")

            c_tun1, c_tun2 = st.columns(2)
            with c_tun1:
                if st.button("⚡ Запустить Cloudflare Туннель (run_tunnels.py)", key="btn_run_tunnels", use_container_width=True):
                    import subprocess
                    try:
                        subprocess.Popen([sys.executable, "run_tunnels.py"], cwd=os.getcwd())
                        st.success("🎉 Cloudflare Туннель запущен! Живые HTTPS-ссылки автоматически привяжутся к ботам.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка запуска туннеля: {e}")

            with c_tun2:
                if st.button("🔄 Проверить текущие активные ссылки", key="btn_refresh_urls", use_container_width=True):
                    st.rerun()

            st.markdown("---")
            st.markdown("### 🤖 Запуск двух Ботов Telegram (Курьер + Диспетчер)")
            st.info("Скрипт `run_bots.py` запускает Бот Курьера и Бот Диспетчера одновременно с веб-сервером WebApp.")
            
            if st.button("⚡ Запустить Ботов Telegram (run_bots.py)", key="launch_tg_bot_bg", use_container_width=True):
                if not courier_token_input.strip() and not disp_token_input.strip():
                    st.error("Укажите хотя бы один Telegram Bot Token перед запуском!")
                else:
                    import subprocess
                    try:
                        subprocess.Popen([sys.executable, "run_bots.py"], cwd=os.getcwd())
                        st.success("🎉 Боты Telegram успешно запущены в фоновом режиме через `run_bots.py`!")
                    except Exception as err:
                        st.error(f"Ошибка запуска ботов: {err}")

        elif "Google" in sel_sub:
            st.subheader("🌐 Интеграция с Google Таблицей")
            
            gs_err = st.session_state.get("gsheet_error", "")
            if use_gsheet:
                st.success("🟢 Google Таблица успешно подключена и работает в онлайн-режиме!")
            elif gs_err:
                if "Invalid JWT Signature" in gs_err or "invalid_grant" in gs_err:
                    st.error("⚠️ **Ошибка авторизации Google:** Файл `key.json` содержит недействительный ключ сервисного аккаунта (`Invalid JWT Signature`).\n\n💡 **Решение:** Пожалуйста, загрузите свежий рабочий файл `key.json` ниже.")
                elif "SpreadsheetNotFound" in gs_err or "404" in gs_err:
                    st.error("⚠️ **Таблица не найдена или нет доступа:** Убедитесь, что вы предоставили доступ к вашей Google Таблице для сервисного бота со статусом **Редактор (Editor)**.")
                else:
                    st.warning(f"⚠️ Ошибка подключения к Google Sheets: {gs_err}")

            st.markdown("""
            **Инструкция по подключению вашей Google Таблицы:**
            1. Откройте вашу Google Таблицу в браузере.
            2. Нажмите синюю кнопку **«Настройки доступа» (Share)** в правом верхнем углу.
            3. Добавьте этот email сервисного аккаунта с правами **«Редактор» (Editor)**:  
               `moyka-crm@moyka-kovrov-crm.iam.gserviceaccount.com`
            4. Скопируйте ссылку (URL) из адресной строки браузера и вставьте её ниже.
            """)
            
            g_cfg = get_gsheet_config()
            curr_url = g_cfg.get("gsheet_url", "")
            
            new_url = st.text_input("Ссылка на Google Таблицу (GSHEET_URL):", value=curr_url, placeholder="https://docs.google.com/spreadsheets/d/...")
            
            st.markdown("##### 🔑 Файл ключей Google Service Account (key.json):")
            st.caption("Загрузите свежий JSON файл ключей Google Service Account (`key.json`) ниже:")
            uploaded_key = st.file_uploader("Загрузить новый key.json", type=["json"], key="admin_key_upload")
            if uploaded_key is not None:
                try:
                    key_bytes = uploaded_key.read()
                    key_data = json.loads(key_bytes.decode('utf-8'))
                    with open("key.json", "w", encoding="utf-8") as f:
                        json.dump(key_data, f, ensure_ascii=False, indent=2)
                    st.cache_resource.clear()
                    st.success("✅ Файл ключей key.json успешно обновлен! Кэш очищен.")
                except Exception as e:
                    st.error(f"Ошибка чтения key.json: {e}")
                    
            if st.button("🚀 Сохранить и Подключить Google Таблицу", type="primary", use_container_width=True):
                if save_gsheet_config(new_url):
                    st.cache_resource.clear()
                    st.success("✅ Настройки Google Таблицы сохранены! Перезагрузка системы...")
                    st.rerun()

        elif "Настройки SMS" in sel_sub:
            render_sms_settings_ui(key_prefix="admin_tab_sms")
            
        elif "История SMS" in sel_sub:
            render_sms_history_ui()
            
        elif "Прейскурант" in sel_sub:
            st.subheader("🏷️ Официальный прейскурант цен Cosmo Cleaning Service")
            cat_data = []
            for k, v in pricing_manager.PRICING_CATALOG.items():
                cat_data.append({
                    "Услуга": v.get("name_ru"),
                    "Единица": v.get("unit"),
                    "Базовая цена": f"{v.get('price'):,} сум",
                    "Диапазон": f"{v.get('min_price'):,} - {v.get('max_price'):,} сум" if v.get('min_price') != v.get('max_price') else "Фиксированная",
                    "Описание": v.get("desc_ru")
                })
            st.dataframe(pd.DataFrame(cat_data), use_container_width=True, hide_index=True)
            
        elif "Бекап" in sel_sub:
            st.subheader("💾 Резервное копирование данных (Backup)")
            st.write(f"Текущий локальный файл резервной копии: `{BACKUP_FILE}`")
            if os.path.exists(BACKUP_FILE):
                st.success("✅ Файл локального бекапа существует и активен.")
                with open(BACKUP_FILE, "r", encoding="utf-8") as bf:
                    json_str = bf.read()
                st.download_button(
                    label="📥 Скачать полный бекап заказов (JSON)",
                    data=json_str,
                    file_name=f"cosmo_orders_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.warning("Бекап пока не создан.")
