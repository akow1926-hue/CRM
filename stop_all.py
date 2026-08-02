import os
import sys

# utf-8 for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def stop():
    print("==================================================")
    print("🛑 [CRM & Telegram Bots] Остановка всех сервисов...")
    print("==================================================")
    
    # Kill streamlit, cloudflared, python start_all/run_bots/run_tunnels processes
    cmd = (
        'powershell -Command "'
        'Get-Process -Name streamlit -ErrorAction SilentlyContinue | Stop-Process -Force; '
        'Get-Process -Name cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force; '
        'Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like \'*start_all.py*\' -or $_.CommandLine -like \'*run_bots.py*\' -or $_.CommandLine -like \'*run_tunnels.py*\' } | ForEach-Object { $_.Terminate() }'
        '"'
    )
    os.system(cmd)
    print("✅ Все фоновые процессы CRM, Telegram-ботов и туннелей успешно остановлены!")

if __name__ == "__main__":
    stop()
