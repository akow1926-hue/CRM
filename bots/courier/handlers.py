import re
import asyncio
from aiogram import Router, F, Bot, State
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardRemove
from database import orders_repo, users_repo
from core import auth, logger
from bots.courier.keyboards import (
    get_courier_login_keyboard,
    get_courier_main_keyboard,
    get_order_inline_actions
)

router = Router()

notify_dispatcher_func = None

def set_notify_dispatcher_hook(fn):
    global notify_dispatcher_func
    notify_dispatcher_func = fn


class CourierLoginStates(State):
    waiting_login = State()
    waiting_password = State()


class CourierMeasureStates(State):
    waiting_width = State()
    waiting_length = State()


class CourierSearchStates(State):
    waiting_order_id = State()


@router.message(CommandStart())
async def cmd_start(message: Message):
    chat_id = str(message.chat.id)
    user = users_repo.get_user_by_telegram_id(chat_id)

    if user and user.get("Status") != "Заблокирован":
        username = user.get("Username", "Курьер")
        await message.answer(
            f"👋 **С возвращением, {username}!**\nВыберите действие из меню курьера:",
            reply_markup=get_courier_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "👋 **Добро пожаловать в службу курьеров Cosmo Cleaning!**\nПожалуйста, воспользуйтесь авторизацией:",
            reply_markup=get_courier_login_keyboard(),
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
            reply_markup=get_courier_login_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "ℹ️ Вы не авторизованы.",
            reply_markup=get_courier_login_keyboard(),
            parse_mode="Markdown"
        )


@router.message(F.text == "🔑 Войти по логину и паролю")
async def start_login(message: Message, state: State):
    await state.clear()
    await message.answer(
        "🔑 Введите ваш логин:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(CourierLoginStates.waiting_login)


@router.message(StateFilter(CourierLoginStates.waiting_login))
async def process_login(message: Message, state: State):
    login = str(message.text or "").strip()
    if not login:
        await message.answer("⚠️ Логин не может быть пустым. Введите логин:")
        return
    await state.update_data(login=login)
    await message.answer("🔒 Введите пароль:")
    await state.set_state(CourierLoginStates.waiting_password)


@router.message(StateFilter(CourierLoginStates.waiting_password))
async def process_password(message: Message, state: State, bot: Bot):
    data = await state.get_data()
    login = data.get("login", "")
    password = str(message.text or "").strip()
    chat_id = str(message.chat.id)

    success, user, err = auth.login_telegram_user(chat_id, login, password)

    if success and user:
        await message.answer(
            f"✅ **Авторизация успешна!**\nДобро пожаловать, {user['Username']}!",
            reply_markup=get_courier_main_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        await message.answer(
            f"❌ **Ошибка авторизации:** {err or 'Неверный логин или пароль'}\nПопробуйте снова:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        await state.set_state(CourierLoginStates.waiting_login)


@router.message(F.text == "📦 Готовые заказы")
async def handle_ready_orders(message: Message):
    orders = orders_repo.get_orders()
    ready = [o for o in orders if "готов" in str(o.get("Статус", "")).lower()]

    if not ready:
        await message.answer("📦 Нет готовых заказов на выдачу.")
        return

    for o in ready[:10]:
        o_id = o.get("ID")
        txt = (
            f"📦 **Заказ №{o_id}**\n"
            f"👤 **Клиент:** {o.get('Клиент')}\n"
            f"📞 **Тел:** `{o.get('Телефон')}`\n"
            f"🏠 **Адрес:** {o.get('Район')}, {o.get('Адрес')}\n"
            f"💰 **Сумма:** {o.get('Сумма')} сум"
        )
        kb = get_order_inline_actions(o_id, o.get("Статус", ""), o.get("Адрес", ""), o.get("Район", ""), o.get("Локация", ""))
        await message.answer(txt, reply_markup=kb, parse_mode="Markdown")


@router.message(F.text == "📥 Забор ковров")
async def handle_pickup_orders(message: Message):
    orders = orders_repo.get_orders()
    pickups = [o for o in orders if "забор" in str(o.get("Статус", "")).lower() or "ожид" in str(o.get("Статус", "")).lower()]

    if not pickups:
        await message.answer("📥 Нет заказов, ожидающих забора.")
        return

    for o in pickups[:10]:
        o_id = o.get("ID")
        txt = (
            f"📥 **Забор №{o_id}**\n"
            f"👤 **Клиент:** {o.get('Клиент')}\n"
            f"📞 **Тел:** `{o.get('Телефон')}`\n"
            f"🏠 **Адрес:** {o.get('Район')}, {o.get('Адрес')}\n"
            f"💬 **Комментарий:** {o.get('Размеры')}"
        )
        kb = get_order_inline_actions(o_id, o.get("Статус", ""), o.get("Адрес", ""), o.get("Район", ""), o.get("Локация", ""))
        await message.answer(txt, reply_markup=kb, parse_mode="Markdown")


@router.message(F.text == "🚚 Доставка ковров")
async def handle_delivery_orders(message: Message):
    orders = orders_repo.get_orders()
    delivery = [o for o in orders if "доставк" in str(o.get("Статус", "")).lower() or "готов" in str(o.get("Статус", "")).lower()]

    if not delivery:
        await message.answer("🚚 Нет заказов на доставку.")
        return

    for o in delivery[:10]:
        o_id = o.get("ID")
        txt = (
            f"🚚 **Доставка №{o_id}**\n"
            f"👤 **Клиент:** {o.get('Клиент')}\n"
            f"📞 **Тел:** `{o.get('Телефон')}`\n"
            f"🏠 **Адрес:** {o.get('Район')}, {o.get('Адрес')}\n"
            f"💰 **Сумма:** {o.get('Сумма')} сум"
        )
        kb = get_order_inline_actions(o_id, o.get("Статус", ""), o.get("Адрес", ""), o.get("Район", ""), o.get("Локация", ""))
        await message.answer(txt, reply_markup=kb, parse_mode="Markdown")


@router.message(F.text == "📋 Мои заказы")
async def handle_my_orders(message: Message):
    chat_id = str(message.chat.id)
    user = users_repo.get_user_by_telegram_id(chat_id)
    if not user:
        await message.answer("ℹ️ Сначала авторизуйтесь через меню входа.")
        return

    cour_name = user.get("Username", "")
    orders = orders_repo.get_orders()
    my = [o for o in orders if str(o.get("Курьер", "")).strip().lower() == cour_name.lower()]

    if not my:
        await message.answer("📋 У вас пока нет заказов.")
        return

    msg = "📋 **Ваши заказы:**\n\n"
    for o in my[:15]:
        msg += f"• **№{o.get('ID')}** | {o.get('Клиент')} ({o.get('Район')}) — `{o.get('Статус')}`\n"

    await message.answer(msg, parse_mode="Markdown")


@router.message(F.text == "🔍 Поиск заказа")
async def start_search(message: Message, state: State):
    await state.clear()
    await message.answer(
        "🔍 Введите номер заказа для поиска:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(CourierSearchStates.waiting_order_id)


@router.message(StateFilter(CourierSearchStates.waiting_order_id))
async def process_search(message: Message, state: State):
    order_id = str(message.text or "").strip()
    order = orders_repo.get_order_by_id(order_id)
    await state.clear()

    if not order:
        await message.answer("❌ Заказ не найден.", reply_markup=get_courier_main_keyboard())
        return

    txt = (
        f"🔍 **Заказ №{order.get('ID')}**\n"
        f"👤 **Клиент:** {order.get('Клиент')}\n"
        f"📞 **Тел:** `{order.get('Телефон')}`\n"
        f"🏠 **Адрес:** {order.get('Район')}, {order.get('Адрес')}\n"
        f"💬 **Комментарий:** {order.get('Размеры')}\n"
        f"💰 **Сумма:** {order.get('Сумма')} сум\n"
        f"📊 **Статус:** `{order.get('Статус')}`\n"
        f"🚚 **Курьер:** {order.get('Курьер')}"
    )
    kb = get_order_inline_actions(order.get('ID'), order.get('Статус', ''), order.get('Адрес', ''), order.get('Район', ''), order.get('Локация', ''))
    await message.answer(txt, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("cour_claim_"))
async def callback_claim_order(callback: CallbackQuery):
    order_id = callback.data.replace("cour_claim_", "").strip()
    chat_id = str(callback.message.chat.id)
    user = users_repo.get_user_by_telegram_id(chat_id)
    cour_name = user.get("Username", "Курьер") if user else "Курьер"

    orders_repo.update_order(order_id, {"Статус": "Взял на забор", "Курьер": cour_name})
    await callback.answer(f"✅ Вы взяли заказ №{order_id}!")
    await callback.message.edit_text(f"🚗 **Заказ №{order_id} переведен в статус 'Взял на забор' ({cour_name})**", parse_mode="Markdown")

    if notify_dispatcher_func:
        asyncio.create_task(notify_dispatcher_func(f"🚗 **Курьер {cour_name} взял забор №{order_id}!**"))


@router.callback_query(F.data.startswith("cour_loc_"))
async def callback_attach_location(callback: CallbackQuery):
    order_id = callback.data.replace("cour_loc_", "").strip()
    await callback.answer("📍 Отправьте вашу геолокацию для этого заказа")
    await callback.message.answer(
        f"📍 Пожалуйста, отправьте геолокацию для заказа №{order_id}.\nИли введите координаты в формате: `широта, долгота`",
        parse_mode="Markdown"
    )
    await callback.message.edit_reply_markup(reply_markup=None)


@router.message(F.location)
async def handle_location(message: Message):
    chat_id = str(message.chat.id)
    user = users_repo.get_user_by_telegram_id(chat_id)
    if not user:
        await message.answer("ℹ️ Сначала авторизуйтесь.")
        return

    lat = message.location.latitude
    lng = message.location.longitude
    loc_str = f"{lat}, {lng}"

    cour_name = user.get("Username", "")
    orders = orders_repo.get_orders()
    target_order = None
    for o in orders:
        if str(o.get("Курьер", "")).strip().lower() == cour_name.lower() and "забор" in str(o.get("Статус", "")).lower():
            target_order = o
            break

    if not target_order:
        await message.answer("⚠️ Нет активного заказа на забор для привязки локации.")
        return

    o_id = target_order.get("ID")
    orders_repo.update_order(o_id, {"Локация": loc_str})
    await message.answer(f"✅ Локация обновлена для заказа №{o_id}: `{loc_str}`", parse_mode="Markdown")


@router.message(F.text.regexp(r"^\s*\d+(\.\d+)?\s*,\s*\d+(\.\d+)?\s*$"))
async def handle_location_text(message: Message):
    chat_id = str(message.chat.id)
    user = users_repo.get_user_by_telegram_id(chat_id)
    if not user:
        return

    loc_str = str(message.text or "").strip()
    cour_name = user.get("Username", "")
    orders = orders_repo.get_orders()
    target_order = None
    for o in orders:
        if str(o.get("Курьер", "")).strip().lower() == cour_name.lower() and "забор" in str(o.get("Статус", "")).lower():
            target_order = o
            break

    if not target_order:
        return

    o_id = target_order.get("ID")
    orders_repo.update_order(o_id, {"Локация": loc_str})
    await message.answer(f"✅ Локация обновлена для заказа №{o_id}: `{loc_str}`", parse_mode="Markdown")


@router.callback_query(F.data.startswith("cour_measure_"))
async def callback_start_measure(callback: CallbackQuery, state: State):
    order_id = callback.data.replace("cour_measure_", "").strip()
    await callback.answer("📏 Введите ширину в метрах")
    await callback.message.answer(
        f"📏 **Замеры для заказа №{order_id}**\nВведите ширину в метрах (например: `3.5`):",
        parse_mode="Markdown"
    )
    await state.set_state(CourierMeasureStates.waiting_width)
    await state.update_data(order_id=order_id)


@router.message(StateFilter(CourierMeasureStates.waiting_width))
async def process_width(message: Message, state: State):
    try:
        width = float(str(message.text or "").replace(",", ".").strip())
        await state.update_data(width=width)
        await message.answer("📐 Теперь введите длину в метрах:")
        await state.set_state(CourierMeasureStates.waiting_length)
    except ValueError:
        await message.answer("⚠️ Неверный формат. Введите число, например: `3.5`")


@router.message(StateFilter(CourierMeasureStates.waiting_length))
async def process_length(message: Message, state: State):
    try:
        length = float(str(message.text or "").replace(",", ".").strip())
        data = await state.get_data()
        order_id = data.get("order_id")
        width = data.get("width", 0)
        area = round(width * length, 2)
        price_per_m = 18000
        total = int(area * price_per_m)
        sizes_str = f"{width}x{length} м"

        updates = {
            "Размеры": sizes_str,
            "Площадь": str(area),
            "Сумма": str(total),
            "Статус": "В цеху (стирка)"
        }
        orders_repo.update_order(order_id, updates)
        await message.answer(
            f"✅ Замеры сохранены для заказа №{order_id}\n"
            f"📏 Размер: {sizes_str} ({area} кв.м)\n"
            f"💰 Сумма: {total} сум",
            parse_mode="Markdown"
        )
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Неверный формат. Введите число, например: `4.2`")


@router.callback_query(F.data.startswith("cour_ready_"))
async def callback_ready_delivery(callback: CallbackQuery):
    order_id = callback.data.replace("cour_ready_", "").strip()
    orders_repo.update_order(order_id, {"Статус": "Готов к доставке"})
    await callback.answer(f"✅ Заказ №{order_id} готов к доставке!")
    await callback.message.edit_text(f"📦 **Заказ №{order_id} переведен в статус 'Готов к доставке'**", parse_mode="Markdown")


@router.callback_query(F.data.startswith("cour_finish_"))
async def callback_finish_order(callback: CallbackQuery):
    order_id = callback.data.replace("cour_finish_", "").strip()
    orders_repo.update_order(order_id, {"Статус": "Выполнен"})
    await callback.answer(f"✅ Заказ №{order_id} выполнен!")
    await callback.message.edit_text(f"🎉 **Заказ №{order_id} успешно выполнен!**", parse_mode="Markdown")
