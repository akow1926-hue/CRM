# Legacy wrapper for tg_bot.py -> redirects execution to run_bots.py
import sys
import run_bots

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(run_bots.main())
    except KeyboardInterrupt:
        print("Боты остановлены.")
