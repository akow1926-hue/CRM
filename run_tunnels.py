import subprocess
import time
import sys
import os
import re
import threading
import json

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

CONFIG_FILE = "telegram_config.json"

def update_bot_urls(courier_url=None, dispatcher_url=None):
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        
        updated = False
        if courier_url:
            cfg["courier_webapp_url"] = courier_url
            updated = True
        if dispatcher_url:
            cfg["dispatcher_webapp_url"] = dispatcher_url
            updated = True
            
        if updated:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[URL Update Error] {e}")

def monitor_cloudflared(port, name, update_fn):
    exe_path = os.path.abspath("cloudflared.exe") if os.path.exists("cloudflared.exe") else "cloudflared"
    cmd = f'"{exe_path}" tunnel --url http://localhost:{port}'
    
    while True:
        try:
            print(f"⚡ [Cloudflare Tunnel] Starting tunnel for port {port} ({name})...")
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            
            for line in p.stdout:
                print(f"[{name}] {line.strip()}")
                if "trycloudflare.com" in line:
                    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                    if match:
                        url = match.group(0)
                        print(f"🎉 [{name}] LIVE URL: {url}")
                        update_fn(url)
            p.wait()
        except Exception as e:
            print(f"⚠️ [{name}] Tunnel error: {e}")
        time.sleep(3)

def update_courier_url(url):
    update_bot_urls(courier_url=url + "/webapp")

def update_dispatcher_url(url):
    update_bot_urls(dispatcher_url=url)

if __name__ == "__main__":
    t1 = threading.Thread(target=monitor_cloudflared, args=(8080, "Courier WebApp", update_courier_url), daemon=True)
    t2 = threading.Thread(target=monitor_cloudflared, args=(8501, "Dispatcher CRM", update_dispatcher_url), daemon=True)
    
    t1.start()
    t2.start()
    
    print("🚀 [Cloudflare Tunnels] Active for Port 8080 (Courier WebApp) and Port 8501 (Dispatcher CRM)!")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Tunnels stopped.")
