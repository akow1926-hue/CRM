import os
import sys
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from core import logger
from webapp import server, api
from bots.courier import handlers as courier_handlers
from bots.dispatcher import handlers as dispatcher_handlers

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()


async def main():
    cfg = settings.load_telegram_config()

    courier_token = cfg.get("courier_bot_token") or os.environ.get("COURIER_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    dispatcher_token = cfg.get("dispatcher_bot_token") or os.environ.get("DISPATCHER_BOT_TOKEN", "").strip()

    if not courier_token:
        print("[CRITICAL] Токен для Telegram бота не найден в .env или telegram_config.json!")
        return

    # Start WebApp REST API Server
    await server.start_web_server()

    storage = MemoryStorage()

    c_bot_instance = None
    d_bot_instance = None

    async def notify_dispatchers(text: str):
        cfg_latest = settings.load_telegram_config()
        disp_chats = cfg_latest.get("dispatcher_chats", {})
        target_bot = d_bot_instance or c_bot_instance
        if target_bot:
            for c_id in set(disp_chats.values()):
                try:
                    await target_bot.send_message(chat_id=c_id, text=text, parse_mode="Markdown")
                except Exception as e:
                    print(f"[Notify Dispatcher Error] {e}")

    async def notify_couriers(text: str, target_courier: str = "all", reply_markup=None):
        cfg_latest = settings.load_telegram_config()
        courier_chats = cfg_latest.get("courier_chats", {})
        target_bot = c_bot_instance or d_bot_instance
        if target_bot and courier_chats:
            target_clean = str(target_courier or "all").strip().lower()

            target_ids = set()
            if target_clean in ["all", "не назначен", "none", "", "все", "все курьеры"]:
                target_ids = set(courier_chats.values())
            else:
                for uname, cid in courier_chats.items():
                    u_clean = str(uname).lower()
                    if u_clean == target_clean or target_clean in u_clean or u_clean in target_clean:
                        target_ids.add(cid)
                if not target_ids:
                    target_ids = set(courier_chats.values())

            for c_id in target_ids:
                try:
                    await target_bot.send_message(chat_id=c_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
                except Exception as e:
                    print(f"[Notify Courier Error] Could not send to {c_id}: {e}")

    courier_handlers.set_notify_dispatcher_hook(notify_dispatchers)
    dispatcher_handlers.set_notify_courier_hook(notify_couriers)
    api.set_notify_hooks(c_func=notify_couriers, d_func=notify_dispatchers)

    has_two_separate_tokens = bool(dispatcher_token and dispatcher_token != courier_token)

    if has_two_separate_tokens:
        logger.log_info("🚀 [Режим: 2 Отдельных Бота]")
        logger.log_info("🚚 Запуск Бот Курьера...")
        c_bot_instance = Bot(token=courier_token)
        dp_courier = Dispatcher(storage=storage)
        dp_courier.include_router(courier_handlers.router)

        logger.log_info("🎧 Запуск Бот Диспетчера...")
        d_bot_instance = Bot(token=dispatcher_token)
        dp_dispatcher = Dispatcher(storage=storage)
        dp_dispatcher.include_router(dispatcher_handlers.router)

        try:
            await asyncio.gather(
                dp_courier.start_polling(c_bot_instance),
                dp_dispatcher.start_polling(d_bot_instance)
            )
        except Exception as e:
            logger.log_error("Ошибка при запуске ботов", e)
    else:
        logger.log_info("🚀 [Режим: Единый токен с разделением ролей Диспетчера и Курьера]")
        c_bot_instance = Bot(token=courier_token)
        d_bot_instance = c_bot_instance

        dp = Dispatcher(storage=storage)
        dp.include_router(dispatcher_handlers.router)
        dp.include_router(courier_handlers.router)

        logger.log_info("✅ Telegram-бот готов к работе (Диспетчер & Курьер)!")
        try:
            await dp.start_polling(c_bot_instance)
        except Exception as e:
            logger.log_error("Ошибка при запуске единого бота", e)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Боты остановлены.")
