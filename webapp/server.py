from aiohttp import web
from config import settings
from core import security, logger
from webapp import api


@web.middleware
async def cors_middleware(request, handler):
    origin = request.headers.get("Origin", "")
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex

    if security.is_origin_allowed(origin):
        response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    else:
        response.headers["Access-Control-Allow-Origin"] = "null"

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    return response


async def start_web_server():
    try:
        app = web.Application(middlewares=[cors_middleware])
        app.router.add_get("/", api.handle_webapp_index)
        app.router.add_get("/webapp", api.handle_webapp_index)
        app.router.add_get("/dispatcher", api.handle_webapp_index)
        app.router.add_post("/api/login", api.handle_api_login)
        app.router.add_get("/api/orders", api.handle_api_orders)
        app.router.add_post("/api/orders/update_status", api.handle_api_update_status)
        app.router.add_post("/api/orders/update_location", api.handle_api_update_location)
        app.router.add_post("/api/orders/create", api.handle_api_create_order)
        app.router.add_post("/api/orders/measure", api.handle_api_measure)
        app.router.add_post("/api/notify_couriers", api.handle_api_notify_couriers)

        runner = web.AppRunner(app)
        await runner.setup()
        port = settings.PORT
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.log_info(f"🌐 [WebApp API] Сервер запущен на порту {port} (/webapp) с защищённым CORS!")
    except Exception as e:
        logger.log_error(f"⚠️ [WebApp API Warning] Не удалось запустить HTTP сервер", e)
