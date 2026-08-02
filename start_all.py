import subprocess
import sys
import time
import os

# utf-8 for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def main():
    print("==================================================")
    print("🚀 [CRM & Telegram Bots] Единый запуск системы")
    print("==================================================")

    processes = []
    try:
        # 1. Запуск Streamlit CRM (app.py)
        print("📊 [1/3] Запуск Streamlit CRM на порту 8501...")
        p_streamlit = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        processes.append(("Streamlit CRM", p_streamlit))

        time.sleep(2)

        # 2. Запуск Telegram Ботов + WebApp (run_bots.py)
        print("🤖 [2/3] Запуск Telegram Ботов (Диспетчер + Курьер) на порту 8080...")
        p_bots = subprocess.Popen(
            [sys.executable, "run_bots.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        processes.append(("Telegram Bots", p_bots))

        time.sleep(2)

        # 3. Запуск Cloudflare Tunnels (run_tunnels.py)
        print("🌐 [3/3] Запуск Cloudflare Tunnels (Публичные HTTPS ссылки)...")
        p_tunnels = subprocess.Popen(
            [sys.executable, "run_tunnels.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        processes.append(("Cloudflare Tunnels", p_tunnels))

        print("\n✅ Все сервисы успешно запущены и работают вместе в единой связке!")
        print("📌 CRM Streamlit доступен на: http://localhost:8501")
        print("📌 WebApp ботов доступен на: http://localhost:8080/webapp")
        print("📌 Публичные онлайн HTTPS-ссылки автоматически обновляются в telegram_config.json\n")
        print("Для остановки нажмите Ctrl+C...")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Остановка всех процессов...")
        for name, p in processes:
            print(f"Остановка {name}...")
            p.terminate()
        print("👋 Все сервисы остановлены.")

if __name__ == "__main__":
    main()
