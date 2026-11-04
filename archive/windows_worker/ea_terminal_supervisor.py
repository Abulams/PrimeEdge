"""
Market-OS EA Terminal Supervisor
=================================
Lightweight process supervisor for EA-bridge mode accounts.
Replaces account_worker.py for accounts using the native MQL5 EA Bridge.

Responsibilities:
  - Deploy MarketOS_Bridge.ex5 and configure WebRequest in the MT5 sandbox
  - Launch terminal64.exe /portable and keep it alive
  - Report heartbeats to cloud (received FROM the EA itself via ea_bridge_router)
  - Monitor terminal health and restart on crash (with backoff)

Does NOT:
  - Import MetaTrader5 Python library
  - Open Windows Named Pipes / IPC
  - Execute orders directly (the EA does this natively)
"""

import os
import sys
import time
import logging
import subprocess
import argparse
import shutil
import signal
import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser()
parser.add_argument("--account-id", type=int, required=True)
args = parser.parse_args()
ACCOUNT_ID = args.account_id

CLOUD_URL = os.getenv("MARKETOS_CLOUD_URL", "http://127.0.0.1:8000")
WORKER_ID = os.getenv("WORKER_ID", "vps-lon-worker-1")
WORKER_KEY = os.getenv("WORKER_KEY", "wkey_master_cloud_london")
HEADERS = {"X-Worker-Id": WORKER_ID, "X-Worker-Key": WORKER_KEY, "Content-Type": "application/json"}

TERMINALS_ROOT = r"C:\Market-OS\terminals"
EA_SOURCE_EX5 = r"C:\Market-OS\mql5\MarketOS_Bridge.ex5"
LOGS_DIR = r"C:\Market-OS\logs"
os.makedirs(LOGS_DIR, exist_ok=True)

log_file = os.path.join(LOGS_DIR, f"ea_supervisor_{ACCOUNT_ID}.log")
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [EA_SUP #{ACCOUNT_ID}] [%(levelname)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
)
logger = logging.getLogger(f"EASupervisor-{ACCOUNT_ID}")


def get_account_info() -> dict:
    """Fetch account details from cloud backend."""
    try:
        r = requests.get(
            f"{CLOUD_URL}/api/v1/execution/worker/accounts",
            headers=HEADERS,
            timeout=8
        )
        if r.status_code == 200:
            for acc in r.json():
                if acc.get("account_id") == ACCOUNT_ID:
                    return acc
    except Exception as e:
        logger.warning(f"Could not fetch account info: {e}")
    return {}


def deploy_ea_to_sandbox(sandbox_dir: str) -> bool:
    """Deploy MarketOS_Bridge.ex5 into the MT5 sandbox MQL5/Experts folder."""
    experts_dir = os.path.join(sandbox_dir, "MQL5", "Experts")
    os.makedirs(experts_dir, exist_ok=True)
    dest = os.path.join(experts_dir, "MarketOS_Bridge.ex5")

    if not os.path.exists(EA_SOURCE_EX5):
        logger.error(f"EA source binary not found: {EA_SOURCE_EX5}")
        return False

    shutil.copy2(EA_SOURCE_EX5, dest)
    logger.info(f"Deployed MarketOS_Bridge.ex5 to {dest}")
    return True


def configure_webrequest(config_dir: str, login: int, server: str) -> None:
    """Update common.ini to enable WebRequest and set the correct API URL and startup EA."""
    ini_path = os.path.join(config_dir, "common.ini")
    base = f"""[StartUp]
Expert=MarketOS_Bridge.ex5
Symbol=EURUSD
Period=M1

[Common]
Login={login}
Server={server}
AutoTrading=1
EnableAlgoTrading=1
NewsEnable=0
SoundEnable=0
MaxBars=500
ChartsEnable=1

[Experts]
AllowDllImport=1
Enabled=1
Account=0
Profile=0
Chart=0
Api=0
AllowLiveTrading=1
WebRequest=1
WebRequestUrl=http://127.0.0.1:8000,https://primeedge.app

[Terminal]
EnableAlgoTrading=1
"""
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(base)
    logger.info(f"Configured common.ini with [StartUp] Expert=MarketOS_Bridge and WebRequest for login #{login}")


def write_startup_chart(sandbox_dir: str) -> None:
    """Write a chart profile that auto-attaches MarketOS_Bridge EA on startup.
    Writes to both root Profiles and MQL5/Profiles to support all MT5 portable builds.
    """
    chart_content = (
        "<chart>\r\n"
        "id=128968168864101562\r\n"
        "symbol=EURUSD\r\n"
        "period_type=1\r\n"
        "period_size=1\r\n"
        "digits=5\r\n"
        "tick_size=0.000000\r\n"
        "position_time=1249992000\r\n"
        "scale_fix=0\r\n"
        "scale=4\r\n"
        "mode=1\r\n"
        "fore=0\r\n"
        "grid=0\r\n"
        "volume=0\r\n"
        "scroll=1\r\n"
        "shift=0\r\n"
        "ohlc=0\r\n"
        "one_click=1\r\n"
        "<expert>\r\n"
        "name=MarketOS_Bridge\r\n"
        "flags=339\r\n"
        "window_num=0\r\n"
        "<inputs>\r\n"
        "InpServerUrl=http://127.0.0.1:8000\r\n"
        "InpWorkerKey=wkey_master_cloud_london\r\n"
        "InpWorkerId=vps-lon-worker-1\r\n"
        "InpTimerMs=1000\r\n"
        "InpMagic=888001\r\n"
        "</inputs>\r\n"
        "</expert>\r\n"
        "</chart>\r\n"
    )
    import codecs
    target_dirs = [
        os.path.join(sandbox_dir, "Profiles", "Charts", "Default"),
        os.path.join(sandbox_dir, "MQL5", "Profiles", "Charts", "Default")
    ]
    for c_dir in target_dirs:
        os.makedirs(c_dir, exist_ok=True)
        with codecs.open(os.path.join(c_dir, "chart01.chr"), "w", encoding="utf-16-le") as f:
            f.write(chart_content)
        with codecs.open(os.path.join(c_dir, "order.wnd"), "w", encoding="utf-16-le") as f:
            f.write("chart01.chr\r\n")
        logger.info(f"Wrote startup chart with MarketOS_Bridge attached to {c_dir}")


def kill_existing_terminal(sandbox_dir: str) -> None:
    """Kill any existing terminal64.exe instances for this sandbox."""
    sandbox_norm = sandbox_dir.replace("\\", "/").lower()
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "exe"]):
            try:
                exe = (proc.info.get("exe") or "").replace("\\", "/").lower()
                if "terminal64" in exe and sandbox_norm in exe:
                    proc.kill()
                    logger.info(f"Killed stale terminal64 (PID {proc.info['pid']}) for acc_{ACCOUNT_ID}")
            except Exception:
                pass
    except ImportError:
        pass


def launch_terminal(terminal_exe: str, sandbox_dir: str) -> subprocess.Popen:
    """Launch terminal64.exe in portable mode with no stdout/stderr capture."""
    proc = subprocess.Popen(
        [terminal_exe, "/portable"],
        cwd=sandbox_dir,
    )
    logger.info(f"Launched terminal64.exe (PID: {proc.pid}) for acc_{ACCOUNT_ID}")
    return proc


def report_error_to_cloud(message: str) -> None:
    try:
        requests.patch(
            f"{CLOUD_URL}/api/v1/execution/worker/report-error",
            json={"account_id": ACCOUNT_ID, "error_message": message},
            headers=HEADERS,
            timeout=5
        )
    except Exception:
        pass


def run():
    logger.info("=" * 60)
    logger.info(f"  Market-OS EA Terminal Supervisor — Account #{ACCOUNT_ID}")
    logger.info(f"  Mode: Native MQL5 EA Bridge (Zero Python IPC)")
    logger.info("=" * 60)

    # Step 1: Fetch account details
    acc_info = {}
    for attempt in range(10):
        acc_info = get_account_info()
        if acc_info:
            break
        logger.warning(f"Waiting for backend (attempt {attempt + 1}/10)...")
        time.sleep(6)

    if not acc_info:
        logger.error(f"Could not fetch account #{ACCOUNT_ID} from backend. Exiting.")
        sys.exit(1)

    login = acc_info["login"]
    server = acc_info.get("broker_server", "MetaQuotes-Demo")
    sandbox_dir = os.path.join(TERMINALS_ROOT, f"acc_{ACCOUNT_ID}")
    terminal_exe = os.path.join(sandbox_dir, "terminal64.exe")
    config_dir = os.path.join(sandbox_dir, "Config")
    profiles_dir = os.path.join(sandbox_dir, "Profiles")

    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(profiles_dir, exist_ok=True)

    logger.info(f"Account: Login #{login} | Server: {server} | Sandbox: {sandbox_dir}")

    if not os.path.exists(terminal_exe):
        logger.error(f"terminal64.exe not found at {terminal_exe}. Run provisioner first.")
        sys.exit(1)

    # Step 2: Deploy EA and configure
    deploy_ea_to_sandbox(sandbox_dir)
    configure_webrequest(config_dir, login, server)
    write_startup_chart(sandbox_dir)

    # Step 3: Kill any stale terminal and launch fresh
    kill_existing_terminal(sandbox_dir)
    time.sleep(2)

    terminal_proc = launch_terminal(terminal_exe, sandbox_dir)
    consecutive_crashes = 0

    # Step 4: Supervisor loop — just keep terminal alive
    while True:
        time.sleep(10)
        ret = terminal_proc.poll()

        if ret is not None:
            consecutive_crashes += 1
            logger.warning(
                f"Terminal for acc_{ACCOUNT_ID} exited (code: {ret}). "
                f"Crash #{consecutive_crashes}. Restarting in {min(consecutive_crashes * 10, 60)}s..."
            )

            if consecutive_crashes >= 5:
                report_error_to_cloud(f"Terminal crash loop (5 consecutive crashes). Last exit code: {ret}")
                logger.error("5 consecutive crashes — entering 5-minute cooldown.")
                time.sleep(300)
                consecutive_crashes = 0

            backoff = min(consecutive_crashes * 10, 60)
            time.sleep(backoff)

            kill_existing_terminal(sandbox_dir)
            time.sleep(2)
            terminal_proc = launch_terminal(terminal_exe, sandbox_dir)
        else:
            # Terminal is alive — reset crash counter on sustained uptime
            consecutive_crashes = 0


if __name__ == "__main__":
    run()
