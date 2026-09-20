"""
Market-OS 24/7 Self-Healing Persistence Supervisor (Watchdog)
============================================================
Supervises and auto-recovers the 3 critical Market-OS services:
1. FastAPI Backend Server (uvicorn app.main:app on port 8000)
2. MetaTrader 5 Terminal (terminal64.exe)
3. Market-OS Execution Worker (worker/marketos_worker.py)
"""

import os
import sys
import time
import subprocess
import datetime
import logging
import requests
import psutil

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Base directories
BASE_DIR = r"C:\Market-OS"
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
WORKER_DIR = os.path.join(BASE_DIR, "worker")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

PYTHON_EXE = r"C:\Python311\python.exe"
MT5_EXE = r"C:\Program Files\MetaTrader 5\terminal64.exe"
CADDY_EXE = r"C:\Market-OS\caddy.exe"
CADDYFILE = r"C:\Market-OS\Caddyfile"

# Logging setup
log_file = os.path.join(LOGS_DIR, "watchdog.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Watchdog]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger("Watchdog")

# Managed processes
procs = {
    "uvicorn": None,
    "mt5": None,
    "worker": None,
    "caddy": None
}

def is_uvicorn_responsive() -> bool:
    """Check if the backend server is responding to HTTP requests."""
    try:
        r = requests.get("http://127.0.0.1:8000/api/v1/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def is_mt5_running() -> bool:
    """Check if terminal64.exe is running."""
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] and 'terminal64.exe' in p.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def start_mt5():
    """Start the MetaTrader 5 base terminal."""
    if not os.path.exists(MT5_EXE):
        logger.error(f"MT5 executable not found at: {MT5_EXE}")
        return
    logger.info("[START] Launching MetaTrader 5 Terminal...")
    try:
        subprocess.Popen([MT5_EXE], shell=False)
        time.sleep(5)
        logger.info("[OK] MetaTrader 5 launched.")
    except Exception as e:
        logger.error(f"Failed to start MT5: {e}")

def start_uvicorn():
    """Start the FastAPI backend server."""
    logger.info("[START] Starting FastAPI backend server on 0.0.0.0:8000...")
    try:
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                cmd = " ".join(p.info['cmdline'] or [])
                if "uvicorn" in cmd and "app.main:app" in cmd and p.pid != os.getpid():
                    p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        p = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=BACKEND_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False
        )
        procs["uvicorn"] = p
        time.sleep(3)
        logger.info(f"[OK] FastAPI backend started (PID: {p.pid}).")
    except Exception as e:
        logger.error(f"Failed to start uvicorn: {e}")

def start_worker():
    """Start the Market-OS Worker Pool Manager (20-Account Portable Pool)."""
    logger.info("[START] Starting Market-OS Worker Pool Manager...")
    try:
        pool_script = os.path.join(WORKER_DIR, "worker_pool_manager.py")
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                cmd = " ".join(p.info['cmdline'] or [])
                if "worker_pool_manager.py" in cmd and p.pid != os.getpid():
                    p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        p = subprocess.Popen(
            [PYTHON_EXE, pool_script],
            cwd=WORKER_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False
        )
        procs["worker"] = p
        time.sleep(2)
        logger.info(f"[OK] PrimeEdge Worker Pool Manager started (PID: {p.pid}).")
    except Exception as e:
        logger.error(f"Failed to start worker pool manager: {e}")

def start_caddy():
    """Start Caddy HTTPS/TLS automated reverse proxy for primeedge.app."""
    if not os.path.exists(CADDY_EXE) or not os.path.exists(CADDYFILE):
        return
    logger.info("[START] Starting Caddy HTTPS reverse proxy for primeedge.app...")
    try:
        for p in psutil.process_iter(['name']):
            try:
                if 'caddy' in (p.info.get('name') or '').lower():
                    p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        p = subprocess.Popen(
            [CADDY_EXE, "run", "--config", CADDYFILE],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False
        )
        procs["caddy"] = p
        time.sleep(2)
        logger.info(f"[OK] Caddy reverse proxy started (PID: {p.pid}).")
    except Exception as e:
        logger.error(f"Failed to start Caddy: {e}")

def main():
    logger.info("==========================================================")
    logger.info("  PRIMEEDGE 24/7 SELF-HEALING SUPERVISOR WATCHDOG ACTIVE  ")
    logger.info("  DOMAIN: primeedge.app | TLS / HTTPS SUPERVISED          ")
    logger.info("==========================================================")
    
    consecutive_http_fails = 0
    last_backup_time = time.time()  # First backup will trigger in 24 hours

    while True:
        try:
            # 1. Check & Ensure FastAPI Backend Server
            if not is_uvicorn_responsive():
                consecutive_http_fails += 1
                logger.warning(f"[WARNING] FastAPI Backend unresponsive (fail count: {consecutive_http_fails}/2)")
                if consecutive_http_fails >= 2:
                    logger.error("[FAIL] FastAPI Backend failed health check. Recycling server...")
                    start_uvicorn()
                    consecutive_http_fails = 0
            else:
                consecutive_http_fails = 0

            # 2. Check & Ensure Worker Pool Manager
            worker_alive = False
            if procs["worker"] and procs["worker"].poll() is None:
                worker_alive = True
            else:
                for p in psutil.process_iter(['name', 'cmdline']):
                    try:
                        cmd = " ".join(p.info['cmdline'] or [])
                        if "worker_pool_manager.py" in cmd:
                            worker_alive = True
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            if not worker_alive:
                logger.warning("[WARNING] PrimeEdge Worker Pool Manager NOT detected. Launching pool manager...")
                start_worker()

            # 3. Check & Ensure Caddy Reverse Proxy (primeedge.app HTTPS / Port 80 & 443)
            caddy_alive = False
            if procs["caddy"] and procs["caddy"].poll() is None:
                caddy_alive = True
            else:
                for p in psutil.process_iter(['name']):
                    try:
                        if 'caddy' in (p.info.get('name') or '').lower():
                            caddy_alive = True
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            if not caddy_alive and os.path.exists(CADDY_EXE):
                logger.warning("[WARNING] Caddy reverse proxy NOT detected. Launching Caddy...")
                start_caddy()

            # 3. Daily Automated Online Database Backup (every 24 hours)
            if time.time() - last_backup_time > 86400:
                try:
                    import importlib.util
                    backup_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "backup_db.py")
                    if os.path.exists(backup_script):
                        spec = importlib.util.spec_from_file_location("backup_db", backup_script)
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        mod.run_backup()
                        last_backup_time = time.time()
                except Exception as b_err:
                    logger.error(f"Automated backup error: {b_err}")

            time.sleep(12)

        except KeyboardInterrupt:
            logger.info("Supervisor stopped by operator.")
            break
        except Exception as e:
            logger.error(f"Watchdog loop exception: {e}")
            time.sleep(12)

if __name__ == "__main__":
    main()
