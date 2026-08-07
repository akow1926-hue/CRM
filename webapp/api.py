import os
import asyncio
from datetime import datetime
from aiohttp import web
from database import orders_repo
from core import auth, logger

notify_courier_func = None
notify_dispatcher_func = None

def set_notify_hooks(c_func=None, d_func=None):
    global notify_courier_func, notify_dispatcher_func
    if c_func:
        notify_courier_func = c_func
    if d_func:
        notify_dispatcher_func = d_func


async def handle_webapp_index(request):
    mode = request.query.get("mode", "").lower()
    if mode == "dispatcher" or "dispatcher" in request.path:
        if os.path.exists("dispatcher_webapp.html"):
            return web.FileResponse("dispatcher_webapp.html")
    if os.path.exists("courier_webapp.html"):
        return web.FileResponse("courier_webapp.html")
    return web.Response(text="<h1>WebApp file not found</h1>", content_type="text/html", status=404)


async def handle_api_login(request):
    try:
        data = await request.json()
        login = str(data.get("login", "")).strip()
        password = str(data.get("password", "")).strip()
        client_ip = request.remote or ""

        ok, user, err = auth.authenticate_user(login, password, client_ip=client_ip)
        if ok and user:
            jwt_token, _ = auth.create_user_session(user, client_ip=client_ip)
            return web.json_response({
                "ok": True,
                "token": jwt_token,
                "user": {
                    "username": user["Username"],
                    "role": user["Role"],
                    "telegram_id": user.get("TelegramID", "")
                }
            })
        return web.json_response({"ok": False, "error": err or "Неверный логин или пароль"}, status=400)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_api_orders(request):
    orders = orders_repo.get_orders()
    return web.json_response(orders)


async def handle_api_update_status(request):
    try:
        data = await request.json()
        order_id = orders_repo.normalize_id(data.get("orderId"))
        new_status = data.get("status")
        pay_type = data.get("payType", "Наличные")
        courier = data.get("courier", "Курьер")

        updates = {"Статус": new_status, "Курьер": courier}
        if new_status == "Выполнен":
            updates["Тип оплаты"] = pay_type
            orders = orders_repo.get_orders()
            for o in orders:
                if orders_repo.normalize_id(o.get("ID")) == order_id:
                    updates["Оплачено"] = str(o.get("Сумма", "0"))
                    break

        orders_repo.update_order(order_id, updates)

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
        district = data.get("district", "Самарканд")
        items = data.get("items", "Забор ковров")
        courier = data.get("courier", "Не назначен")
        dispatcher = data.get("dispatcher", "Диспетчер")
        language = data.get("language", "Русский язык")
        priority = data.get("priority", "Обычный")
        pickup_time = data.get("pickupTime", "В любое время")
        extra_note = data.get("extraNote", "")
        delivery_date = data.get("deliveryDate", "")
        delivery_time = data.get("deliveryTime", "")

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

        full_details = f"Забор: {pickup_time} | {items}"
        if "СРОЧН" in str(priority).upper():
            full_details = f"🔥 СРОЧНО ({delivery_date} {delivery_time})! {full_details}"
        if extra_note:
            full_details += f" | Ориентир: {extra_note}"

        new_order = {
            "ID": str(new_id),
            "Дата": now_str,
            "Клиент": client,
            "Телефон": phone,
            "Адрес": address,
            "Размеры": full_details,
            "Площадь": "0",
            "Сумма": "0",
            "Статус": "Ожидает забора",
            "Курьер": courier,
            "Диспетчер": dispatcher,
            "Район": district,
            "Язык": language,
            "Локация": "",
            "Оплачено": "0",
            "Тип оплаты": "-",
            "Причина": "Создано через WebApp"
        }

        orders_repo.add_order(new_order)

        if notify_courier_func:
            msg_text = (
                f"📥 **Новый заказ №{new_id}!**\n\n"
                f"👤 **Клиент:** {client}\n"
                f"📞 **Тел:** `{phone}`\n"
                f"🏠 **Адрес:** {district}, {address}\n"
                f"💬 **Комментарий:** {items}"
            )
            target_cour = courier if (courier and courier not in ["Не назначен", "all"]) else "all"
            asyncio.create_task(notify_courier_func(msg_text, target_courier=target_cour))

        if notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(f"🆕 **Создан новый заказ №{new_id}!** (Клиент: {client}, Адрес: {district}, {address})"))

        return web.json_response({"ok": True, "orderId": new_id})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_api_update_location(request):
    try:
        data = await request.json()
        order_id = orders_repo.normalize_id(data.get("orderId", ""))
        lat = data.get("lat")
        lng = data.get("lng")
        loc_str = f"{lat}, {lng}" if (lat and lng) else str(data.get("location", "")).strip()

        found = orders_repo.update_order(order_id, {"Локация": loc_str})

        if found:
            if notify_dispatcher_func:
                asyncio.create_task(notify_dispatcher_func(f"📍 **GPS локация заказа №{order_id} обновлена из WebApp!** ({loc_str})"))
            return web.json_response({"ok": True, "location": loc_str})
        return web.json_response({"ok": False, "error": f"Заказ №{order_id} не найден"}, status=404)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_api_measure(request):
    try:
        data = await request.json()
        order_id = orders_repo.normalize_id(data.get("orderId", ""))
        width = float(data.get("width", 0))
        length = float(data.get("length", 0))
        price_per_m = float(data.get("price", 18000))

        area = round(width * length, 2)
        total = int(area * price_per_m)
        sizes_str = f"{width}x{length} м"

        updates = {
            "Размеры": sizes_str,
            "Площадь": str(area),
            "Сумма": str(total),
            "Статус": "В цеху (стирка)"
        }
        found = orders_repo.update_order(order_id, updates)

        if found and notify_dispatcher_func:
            asyncio.create_task(notify_dispatcher_func(
                f"📏 **Замеры заказа №{order_id} сохранены из WebApp!**\n"
                f"Размер: {sizes_str} ({area} кв.м) | Сумма: {total} сум"
            ))
        return web.json_response({"ok": True, "area": area, "total": total})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_api_notify_couriers(request):
    try:
        data = await request.json()
        text = str(data.get("text", "")).strip()
        courier = str(data.get("courier", "all")).strip()
        sender = str(data.get("sender", "Диспетчер")).strip()

        if text and notify_courier_func:
            msg = f"📩 **Сообщение от диспетчера ({sender}):**\n{text}"
            asyncio.create_task(notify_courier_func(msg, target_courier=courier))
            return web.json_response({"ok": True})
        return web.json_response({"ok": False, "error": "Пустой текст или функция не настроена"}, status=400)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)
