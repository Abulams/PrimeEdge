"""
Market-OS Worker Pool Manager
============================
Orchestrates the pool of isolated account workers.
Dynamically scales to 20 concurrent cloud MT5 accounts without login collisions:
  - Polls active cloud accounts from backend
  - Automatically provisions portable sandbox for each account
  - Spawns and supervises dedicated `account_worker.py` subprocess per account
  - Restarts dead workers with backoff
  - Safely stops workers when an account is disabled in web UI
"""

import os
import sys
import time
import logging
import subprocess
import requests
from typing import Dict, Optional

# Set UTF-8 encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logs_dir = r"C:\Market-OS\logs"
os.makedirs(logs_dir, exist_ok=True)
pool_log = os.path.join(logs_dir, "pool_manager.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [POOL_MGR] [%(levelname)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(pool_log, encoding="utf-8")
    ]
)
logger = logging.getLogger("WorkerPoolManager")

CLOUD_URL = os.getenv("MARKETOS_CLOUD_URL", "http://127.0.0.1:8000")
WORKER_ID = os.getenv("WORKER_ID", "vps-lon-worker-1")
WORKER_KEY = os.getenv("WORKER_KEY", "wkey_master_cloud_london")

HEADERS = {
    "X-Worker-Id": WORKER_ID,
    "X-Worker-Key": WORKER_KEY,
    "Content-Type": "application/json"
}

WORKER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "account_worker.py")


class WorkerPoolManager:
    def __init__(self):
        self.active_processes: Dict[int, subprocess.Popen] = {}
        self.failures: Dict[int, Dict] = {}  # acc_id -> {"count": int, "last_failure": float, "spawn_time": float}
        self.last_sync_time = 0

    def fetch_target_accounts(self) -> Dict[int, Dict]:
        """Fetch all accounts that have auto_execution_enabled=True."""
        try:
            r = requests.get(f"{CLOUD_URL}/api/v1/execution/worker/accounts", headers=HEADERS, timeout=8)
            if r.status_code == 200:
                accounts = r.json()
                active = {}
                for acc in accounts:
                    if acc.get("auto_execution_enabled"):
                        active[acc["account_id"]] = acc
                return active
        except Exception as e:
            logger.error(f"Error fetching active accounts from cloud: {e}")
        return {}

    def spawn_worker_for_account(self, account_id: int, login: int):
        """Spawns an isolated Python subprocess for the given account."""
        logger.info(f"🚀 Spawning dedicated worker for Account #{account_id} (Login: {login})...")
        cmd = [sys.executable, WORKER_SCRIPT, "--account-id", str(account_id)]
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.active_processes[account_id] = proc
            if account_id not in self.failures:
                self.failures[account_id] = {"count": 0, "last_failure": 0.0, "spawn_time": time.time()}
            else:
                self.failures[account_id]["spawn_time"] = time.time()

            logger.info(f"✅ Worker for Account #{account_id} started (PID: {proc.pid})")
        except Exception as e:
            logger.error(f"Failed to spawn worker for Account #{account_id}: {e}")

    def stop_worker_for_account(self, account_id: int):
        """Terminates the worker process for an account that was deactivated."""
        if account_id in self.active_processes:
            proc = self.active_processes[account_id]
            logger.info(f"🛑 Stopping worker for deactivated Account #{account_id} (PID: {proc.pid})...")
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            del self.active_processes[account_id]
        if account_id in self.failures:
            del self.failures[account_id]

    def reconcile_pool(self):
        """Reconciles active subprocesses with desired cloud state."""
        target_accounts = self.fetch_target_accounts()

        # 1. Stop workers for accounts that are no longer active
        for acc_id in list(self.active_processes.keys()):
            if acc_id not in target_accounts:
                self.stop_worker_for_account(acc_id)

        # 2. Start or health-check workers for active accounts
        now = time.time()
        for acc_id, acc_data in target_accounts.items():
            login = acc_data.get("login")
            proc = self.active_processes.get(acc_id)
            f_info = self.failures.setdefault(acc_id, {"count": 0, "last_failure": 0.0, "spawn_time": 0.0})

            # Check circuit breaker cooldown
            if f_info["count"] >= 3:
                cooldown_remaining = int(300 - (now - f_info["last_failure"]))
                if cooldown_remaining > 0:
                    # Still in 5-minute cooldown, skip restart
                    continue
                else:
                    logger.info(f"Circuit breaker cooldown expired for Account #{acc_id} — allowing retry.")
                    f_info["count"] = 0

            if proc is None:
                self.spawn_worker_for_account(acc_id, login)
            else:
                ret = proc.poll()
                if ret is not None:
                    uptime = now - f_info.get("spawn_time", now)
                    if uptime > 60:
                        f_info["count"] = 0
                    else:
                        f_info["count"] += 1
                        f_info["last_failure"] = now

                    if f_info["count"] >= 3:
                        logger.warning(
                            f"⚠️ Account #{acc_id} failed {f_info['count']} consecutive times (exit code {ret}). "
                            "Entering 5-minute circuit breaker cooldown to protect CPU/system."
                        )
                    else:
                        logger.warning(f"⚠️ Worker for Account #{acc_id} exited with code {ret} (attempt {f_info['count']}/3). Restarting...")
                        self.spawn_worker_for_account(acc_id, login)

    def run(self):
        logger.info("================================================================")
        logger.info("  MARKET-OS 20-ACCOUNT CLOUD WORKER POOL MANAGER                ")
        logger.info("  ISOLATION: FULL PROCESS & PORTABLE MT5 SANDBOX                ")
        logger.info("================================================================")

        while True:
            try:
                self.reconcile_pool()
                time.sleep(8)
            except KeyboardInterrupt:
                logger.info("Pool manager shutting down. Terminating all workers...")
                for acc_id in list(self.active_processes.keys()):
                    self.stop_worker_for_account(acc_id)
                break
            except Exception as e:
                logger.error(f"Pool manager loop exception: {e}")
                time.sleep(5)


if __name__ == "__main__":
    manager = WorkerPoolManager()
    manager.run()
