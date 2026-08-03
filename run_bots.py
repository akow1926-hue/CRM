import os
import sys
import json
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiohttp import web

import courier_bot
import dispatcher_bot

# utf-8 for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()

CONFIG_FILE = "telegram_config.json"

def load_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[Config Error] {e}")

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            tg_sec = st.secrets.get("telegram", st.secrets)
            for k in ["courier_bot_token", "dispatcher_bot_token", "bot_token", "chat_id"]:
                if not cfg.get(k) and k in tg_sec:
                    cfg[k] = str(tg_sec[k])
            if not cfg.get("courier_chats") and "courier_chats" in tg_sec:
                cfg["courier_chats"] = dict(tg_sec["courier_chats"])
            if not cfg.get("dispatcher_chats") and "dispatcher_chats" in tg_sec:
                cfg["dispatcher_chats"] = dict(tg_sec["dispatcher_chats"])
    except Exception:
        pass

    return cfg

async def start_web_server():
    try:
        app = web.Application()
        app.router.add_get("/", courier_bot.handle_webapp_index)
        app.router.add_get("/webapp", courier_bot.handle_webapp_index)
        app.router.add_get("/dispatcher", courier_bot.handle_webapp_index)
        app.router.add_post("/api/login", courier_bot.handle_api_login)
        app.router.add_get("/api/orders", courier_bot.handle_api_orders)
        app.router.add_post("/api/orders/update_status", courier_bot.handle_api_update_status)
        app.router.add_post("/api/orders/update_location", courier_bot.handle_api_update_location)
        app.router.add_post("/api/orders/create", courier_bot.handle_api_create_order)
        app.router.add_post("/api/orders/measure", courier_bot.handle_api_measure)
        app.router.add_post("/api/notify_couriers", courier_bot.handle_api_notify_couriers)

        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"🌐 [WebApp API] Сервер запущен на порту {port} (/webapp) !")
    except Exception as e:
        print(f"⚠️ [WebApp API Warning] Не удалось запустить локальный HTTP сервер: {e}")

async def main():
    cfg = load_config()
    
    courier_token = cfg.get("courier_bot_token") or cfg.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    dispatcher_token = cfg.get("dispatcher_bot_token") or os.environ.get("DISPATCHER_BOT_TOKEN", "").strip()

    if not courier_token:
        print("[CRITICAL] Токен для Telegram бота не найден в telegram_config.json или .env!")
        return

    # WebApp Server
    await start_web_server()

    # Define notification hooks
    c_bot_instance = None
    d_bot_instance = None

    async def notify_dispatchers(text: str):
        cfg_latest = load_config()
        disp_chats = cfg_latest.get("dispatcher_chats", {})
        target_bot = d_bot_instance or c_bot_instance
        if target_bot:
            for c_id in set(disp_chats.values()):
                try:
                    await target_bot.send_message(chat_id=c_id, text=text, parse_mode="Markdown")
                except Exception as e:
                    print(f"[Notify Dispatcher Error] {e}")

    async def notify_courier(text: str, target_courier: str = "all"):
        cfg_latest = load_config()
        courier_chats = cfg_latest.get("courier_chats", {})
        target_bot = c_bot_instance or d_bot_instance
        if target_bot:
            if target_courier == "all":
                for c_id in set(courier_chats.values()):
                    try:
                        await target_bot.send_message(chat_id=c_id, text=text, parse_mode="Markdown")
                    except Exception as e:
                        print(f"[Notify Courier Error] {e}")
            else:
                c_id = courier_chats.get(target_courier.lower())
                if c_id:
                    try:
                        await target_bot.send_message(chat_id=c_id, text=text, parse_mode="Markdown")
                    except Exception as e:
                        print(f"[Notify Courier Error] {e}")

    courier_bot.set_notify_dispatcher_hook(notify_dispatchers)
    dispatcher_bot.set_notify_courier_hook(notify_courier)

    # Check if we have two distinct tokens
    has_two_separate_tokens = bool(dispatcher_token and dispatcher_token != courier_token)

    if has_two_separate_tokens:
        print("🚀 [Режим: 2 Отдельных Бота]")
        print("🚚 Запуск Бот Курьера...")
        c_bot_instance = Bot(token=courier_token)
        dp_courier = Dispatcher()
        dp_courier.include_router(courier_bot.router)

        print("🎧 Запуск Бот Диспетчера...")
        d_bot_instance = Bot(token=dispatcher_token)
        dp_dispatcher = Dispatcher()
        dp_dispatcher.include_router(dispatcher_bot.router)

        await asyncio.gather(
            dp_courier.start_polling(c_bot_instance),
            dp_dispatcher.start_polling(d_bot_instance)
        )
    else:
        print("🚀 [Режим: Единый токен с разделением ролей Диспетчера и Курьера]")
        print("💡 Если укажете второй токен 'dispatcher_bot_token' в telegram_config.json, боты разделятся на 2 разных аккаунта!")
        
        c_bot_instance = Bot(token=courier_token)
        d_bot_instance = c_bot_instance

        dp = Dispatcher()
        # Order of routers: dispatcher_bot router first, then courier_bot router
        dp.include_router(dispatcher_bot.router)
        dp.include_router(courier_bot.router)

        print("✅ Telegram-бот готов к работе (Диспетчер & Курьер)!")
        await dp.start_polling(c_bot_instance)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Боты остановлены.")
