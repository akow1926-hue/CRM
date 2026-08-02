import subprocess
import time
import sys
import threading

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def monitor_tunnel(port, subdomain):
    cmd = f"npx -y localtunnel --port {port} --subdomain {subdomain}"
    while True:
        try:
            print(f"[Tunnel Monitor] Starting localtunnel for port {port} ({subdomain})...")
            p = subprocess.Popen(cmd, shell=True)
            p.wait()
        except Exception as e:
            print(f"[Tunnel Monitor] Error for {subdomain}: {e}")
        time.sleep(3)

if __name__ == "__main__":
    t1 = threading.Thread(target=monitor_tunnel, args=(8080, "all-camels-dance"), daemon=True)
    t2 = threading.Thread(target=monitor_tunnel, args=(8501, "all-camels-dispatcher"), daemon=True)
    
    t1.start()
    t2.start()
    
    print("[Tunnel Monitor] Persistent tunnel monitoring active for ports 8080 and 8501!")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Tunnel Monitor] Stopped.")
