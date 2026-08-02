import os
import shutil
import sys

# utf-8 for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def install():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        print("[ERROR] Не удалось определить папку AppData.")
        return

    startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
    if not os.path.exists(startup_dir):
        print(f"[ERROR] Папка автозагрузки не найдена: {startup_dir}")
        return

    source_vbs = os.path.abspath("run_background.vbs")
    target_vbs = os.path.join(startup_dir, "Start_CRM_System.vbs")

    try:
        shutil.copy2(source_vbs, target_vbs)
        print("==================================================")
        print("🎉 [Автозапуск успешно настроен!]")
        print("==================================================")
        print(f"📌 Ярлык автозапуска помещен в:\n   {target_vbs}\n")
        print("✅ Теперь при каждом включении компьютера CRM и Telegram-боты")
        print("   будут автоматически запускаться в фоновом режиме (без черных окон).")
    except Exception as e:
        print(f"[ERROR] Ошибка копирования в автозагрузку: {e}")

def remove():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return
    startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
    target_vbs = os.path.join(startup_dir, "Start_CRM_System.vbs")
    if os.path.exists(target_vbs):
        try:
            os.remove(target_vbs)
            print("🗑️ Автозапуск CRM успешно удален из Windows.")
        except Exception as e:
            print(f"[ERROR] Не удалось удалить автозапуск: {e}")
    else:
        print("ℹ️ Автозапуск ранее не был установлен.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--remove":
        remove()
    else:
        install()
