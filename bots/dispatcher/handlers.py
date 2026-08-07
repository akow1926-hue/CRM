import re
import asyncio
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from database import orders_repo, users_repo
from core import auth, logger
from bots.dispatcher.keyboards import (
    get_dispatcher_login_keyboard,
    get_dispatcher_main_keyboard
)

router = Router()

notify_courier_func = None

def set_notify_courier_hook(fn):
    global notify_courier_func
    notify_courier_func = fn


class DispatcherLoginStates(StatesGroup):
    waiting_login = State()
    waiting_password = State()


class CreateOrderStates(StatesGroup):
    waiting_client = State()
    waiting_phone = State()
    waiting_address = State()
    waiting_district = State()
    waiting_comment = State()
    waiting_priority = State()
    waiting_pickup_date = State()
    waiting_pickup_time = State()
    waiting_delivery_date = State()
    waiting_delivery_time = State()
    waiting_courier = State()


class SearchStates(StatesGroup):
    waiting_query = State()


@router.message(CommandStart())
async def cmd_dispatcher_start(message: Message):
    chat_id = str(message.chat.id)
    user = users_repo.get_user_by_telegram_id(chat_id)

    if user and user.get("Status") != "Заблокирован":
        username = user.get("Username", "Диспетчер")
        await message.answer(
            f"🎧 **С возвращением, Диспетчер {username}!**\nПанель управления диспетчера готова:",
            reply_markup=get_dispatcher_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🎧 **Панель Диспетчера Cosmo Cleaning Service**\nДля работы воспользуйтесь авторизацией:",
            reply_markup=get_dispatcher_login_keyboard(),
            parse_mode="Markdown"
        )


@router.message(Command("logout"))
async def cmd_logout(message: Message):
    chat_id = str(message.chat.id)
    user = users_repo.get_user_by_telegram_id(chat_id)
    if user:
        users_repo.bind_telegram_id(user["Username"], "")
        await message.answer(
            "✅ Вы успешно вышли из аккаунта.\nДля повторного входа используйте авторизацию:",
            reply_markup=get_dispatcher_login_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "ℹ️ Вы не авторизованы.",
            reply_markup=get_dispatcher_login_keyboard(),
            parse_mode="Markdown"
        )


@router.message(F.text == "🔑 Войти по логину и паролю")
async def start_login(message: Message, state: State):
    await state.clear()
    await message.answer(
        "🔑 Введите ваш логин:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(DispatcherLoginStates.waiting_login)


@router.message(StateFilter(DispatcherLoginStates.waiting_login))
async def process_login(message: Message, state: State):
    login = str(message.text or "").strip()
    if not login:
        await message.answer("⚠️ Логин не может быть пустым. Введите логин:")
        return
    await state.update_data(login=login)
    await message.answer("🔒 Введите пароль:")
    await state.set_state(DispatcherLoginStates.waiting_password)


@router.message(StateFilter(DispatcherLoginStates.waiting_password))
async def process_password(message: Message, state: State):
    data = await state.get_data()
    login = data.get("login", "")
    password = str(message.text or "").strip()
    chat_id = str(message.chat.id)

    success, user, err = auth.login_telegram_user(chat_id, login, password)

    if success and user:
        await message.answer(
            f"✅ **Авторизация успешна!**\nДобро пожаловать, {user['Username']}!",
            reply_markup=get_dispatcher_main_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        await message.answer(
            f"❌ **Ошибка авторизации:** {err or 'Неверный логин или пароль'}\nПопробуйте снова:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        await state.set_state(DispatcherLoginStates.waiting_login)


@router.message(F.text == "➕ Создать заказ")
async def start_create_order(message: Message, state: State):
    await state.clear()
    await message.answer(
        "👤 Введите имя клиента:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(CreateOrderStates.waiting_client)


@router.message(StateFilter(CreateOrderStates.waiting_client))
async def process_client(message: Message, state: State):
    client = str(message.text or "").strip()
    if not client:
        await message.answer("⚠️ Имя клиента не может быть пустым.")
        return
    await state.update_data(client=client)
    await message.answer("📞 Введите номер телефона клиента:")
    await state.set_state(CreateOrderStates.waiting_phone)


@router.message(StateFilter(CreateOrderStates.waiting_phone))
async def process_phone(message: Message, state: State):
    phone = str(message.text or "").strip()
    await state.update_data(phone=phone)
    await message.answer("🏠 Введите адрес клиента:")
    await state.set_state(CreateOrderStates.waiting_address)


@router.message(StateFilter(CreateOrderStates.waiting_address))
async def process_address(message: Message, state: State):
    address = str(message.text or "").strip()
    await state.update_data(address=address)
    await message.answer("📍 Введите район:")
    await state.set_state(CreateOrderStates.waiting_district)


@router.message(StateFilter(CreateOrderStates.waiting_district))
async def process_district(message: Message, state: State):
    district = str(message.text or "").strip()
    await state.update_data(district=district)
    await message.answer("💬 Введите комментарий к заказу (размеры, особенности):")
    await state.set_state(CreateOrderStates.waiting_comment)


@router.message(StateFilter(CreateOrderStates.waiting_comment))
async def process_comment(message: Message, state: State):
    comment = str(message.text or "").strip()
    await state.update_data(comment=comment)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 СРОЧНО", callback_data="priority_urgent")],
        [InlineKeyboardButton(text="📅 Обычный", callback_data="priority_normal")]
    ])
    await message.answer("⚡ Выберите приоритет заказа:", reply_markup=kb)
    await state.set_state(CreateOrderStates.waiting_priority)


@router.callback_query(StateFilter(CreateOrderStates.waiting_priority), F.data.startswith("priority_"))
async def process_priority(callback: CallbackQuery, state: State):
    priority = "СРОЧНЫЙ" if callback.data == "priority_urgent" else "Обычный"
    await state.update_data(priority=priority)
    await callback.answer()
    await callback.message.edit_text(f"⚡ Приоритет: {priority}")
    await callback.message.answer("📅 Введите дату забора (дд.мм.гггг):")
    await state.set_state(CreateOrderStates.waiting_pickup_date)


@router.message(StateFilter(CreateOrderStates.waiting_pickup_date))
async def process_pickup_date(message: Message, state: State):
    date_str = str(message.text or "").strip()
    await state.update_data(pickup_date=date_str)
    await message.answer("🕐 Введите время забора (например: 09:00 - 12:00):")
    await state.set_state(CreateOrderStates.waiting_pickup_time)


@router.message(StateFilter(CreateOrderStates.waiting_pickup_time))
async def process_pickup_time(message: Message, state: State):
    time_str = str(message.text or "").strip()
    await state.update_data(pickup_time=time_str)
    await message.answer("📅 Введите дату доставки (дд.мм.гггг):")
    await state.set_state(CreateOrderStates.waiting_delivery_date)


@router.message(StateFilter(CreateOrderStates.waiting_delivery_date))
async def process_delivery_date(message: Message, state: State):
    date_str = str(message.text or "").strip()
    await state.update_data(delivery_date=date_str)
    await message.answer("🕐 Введите время доставки (например: 14:00 - 18:00):")
    await state.set_state(CreateOrderStates.waiting_delivery_time)


@router.message(StateFilter(CreateOrderStates.waiting_delivery_time))
async def process_delivery_time(message: Message, state: State):
    time_str = str(message.text or "").strip()
    await state.update_data(delivery_time=time_str)
    await message.answer("🚚 Выберите курьера:")
    await state.set_state(CreateOrderStates.waiting_courier)


@router.message(StateFilter(CreateOrderStates.waiting_courier))
async def process_courier(message: Message, state: State):
    courier = str(message.text or "").strip()
    if not courier:
        await message.answer("⚠️ Укажите курьера.")
        return

    data = await state.get_data()
    chat_id = str(message.chat.id)
    user = users_repo.get_user_by_telegram_id(chat_id)
    dispatcher_name = user.get("Username", "Диспетчер") if user else "Диспетчер"

    orders = orders_repo.get_orders()
    max_id = 5218
    for o in orders:
        try:
            val = int(float(orders_repo.normalize_id(o.get("ID", 0))))
            if val > max_id:
                max_id = val
        except Exception:
            pass
    new_id = max_id + 1
    now_str = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

    full_details = f"Забор: {data.get('pickup_time', '')} | {data.get('comment', '')}"
    if data.get("priority") == "СРОЧНЫЙ":
        full_details = f"🔥 СРОЧНО ({data.get('delivery_date', '')} {data.get('delivery_time', '')})! {full_details}"

    new_order = {
        "ID": str(new_id),
        "Дата": now_str,
        "Клиент": data.get("client", ""),
        "Телефон": data.get("phone", ""),
        "Адрес": data.get("address", ""),
        "Размеры": full_details,
        "Площадь": "0",
        "Сумма": "0",
        "Статус": "Ожидает забора",
        "Курьер": courier,
        "Диспетчер": dispatcher_name,
        "Район": data.get("district", ""),
        "Язык": "Русский язык",
        "Локация": "",
        "Оплачено": "0",
        "Тип оплаты": "-",
        "Причина": "Создано через Telegram"
    }

    orders_repo.add_order(new_order)
    await message.answer(
        f"✅ **Заказ №{new_id} создан!**\n"
        f"👤 Клиент: {data.get('client')}\n"
        f"🏠 Адрес: {data.get('district')}, {data.get('address')}\n"
        f"🚚 Курьер: {courier}",
        reply_markup=get_dispatcher_main_keyboard(),
        parse_mode="Markdown"
    )
    await state.clear()

    if notify_courier_func:
        msg_text = (
            f"📥 **Новый заказ №{new_id}!**\n\n"
            f"👤 **Клиент:** {data.get('client')}\n"
            f"📞 **Тел:** `{data.get('phone')}`\n"
            f"🏠 **Адрес:** {data.get('district')}, {data.get('address')}\n"
            f"💬 **Комментарий:** {data.get('comment')}"
        )
        asyncio.create_task(notify_courier_func(msg_text, target_courier=courier if courier else "all"))


@router.message(F.text == "📋 Все заказы")
async def handle_all_orders(message: Message):
    orders = orders_repo.get_orders()
    if not orders:
        await message.answer("📋 В системе пока нет заказов.")
        return

    msg = "📋 **Последние заказы в системе:**\n\n"
    for o in orders[:8]:
        msg += f"• **№{o.get('ID')}** | {o.get('Клиент')} ({o.get('Район')}) — `{o.get('Статус')}`\n"

    await message.answer(msg, parse_mode="Markdown")


@router.message(F.text == "🚚 Назначить курьера")
async def start_assign_courier(message: Message):
    orders = orders_repo.get_orders()
    unassigned = [o for o in orders if not str(o.get("Курьер", "")).strip() or str(o.get("Курьер", "")).strip().lower() in ["не назначен", "none", ""]]
    if not unassigned:
        await message.answer("🚚 Нет заказов без назначенного курьера.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"№{o.get('ID')} — {o.get('Клиент')}", callback_data=f"assign_{o.get('ID')}")]
        for o in unassigned[:10]
    ])
    await message.answer("🚚 Выберите заказ для назначения курьера:", reply_markup=kb)


@router.callback_query(F.data.startswith("assign_"))
async def process_assign_courier(callback: CallbackQuery, state: State):
    order_id = callback.data.replace("assign_", "").strip()
    await callback.answer()
    await callback.message.edit_text(f"✏️ Введите имя курьера для заказа №{order_id}:")
    await state.set_state(SearchStates.waiting_query)
    await state.update_data(order_id=order_id, action="assign_courier")


@router.message(F.text == "🔍 Поиск заказа")
async def start_search(message: Message, state: State):
    await state.clear()
    await message.answer(
        "🔍 Введите номер заказа или имя клиента для поиска:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(SearchStates.waiting_query)


@router.message(StateFilter(SearchStates.waiting_query))
async def process_search(message: Message, state: State):
    query = str(message.text or "").strip().lower()
    data = await state.get_data()
    action = data.get("action", "search")
    await state.clear()

    if action == "assign_courier":
        order_id = data.get("order_id")
        courier = str(message.text or "").strip()
        if not courier:
            await message.answer("⚠️ Имя курьера не может быть пустым.", reply_markup=get_dispatcher_main_keyboard())
            return
        orders_repo.update_order(order_id, {"Курьер": courier})
        await message.answer(
            f"✅ Курьер **{courier}** назначен на заказ №{order_id}!",
            reply_markup=get_dispatcher_main_keyboard(),
            parse_mode="Markdown"
        )
        if notify_courier_func:
            asyncio.create_task(notify_courier_func(f"🚚 **Вы назначены на заказ №{order_id}!**", target_courier=courier))
        return

    orders = orders_repo.get_orders()
    found = [o for o in orders if query in str(o.get("ID", "")).lower() or query in str(o.get("Клиент", "")).lower()]
    if not found:
        await message.answer("❌ Ничего не найдено.", reply_markup=get_dispatcher_main_keyboard())
        return

    msg = "🔍 **Результаты поиска:**\n\n"
    for o in found[:10]:
        msg += f"• **№{o.get('ID')}** | {o.get('Клиент')} ({o.get('Район')}) — `{o.get('Статус')}`\n"
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_dispatcher_main_keyboard())
