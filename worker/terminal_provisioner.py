"""
Market-OS Portable Terminal Provisioner
======================================
Sets up and maintains isolated, lightweight MT5 terminal sandboxes in /portable mode.
Each cloud user account receives its own dedicated sandbox directory:
  C:\Market-OS\terminals\acc_<account_id>\

Configurations are stripped of news feeds, audio engines, and large chart buffers 
to reduce memory footprint from ~350MB down to ~45MB per instance.
"""

import os
import sys
import shutil
import logging
import subprocess

logger = logging.getLogger("TerminalProvisioner")

BASE_MT5_DIR = r"C:\Program Files\MetaTrader 5"
BASE_MT5_EXE = os.path.join(BASE_MT5_DIR, "terminal64.exe")
TERMINALS_ROOT = r"C:\Market-OS\terminals"


def ensure_terminals_root() -> str:
    os.makedirs(TERMINALS_ROOT, exist_ok=True)
    return TERMINALS_ROOT


def get_account_terminal_dir(account_id: int) -> str:
    return os.path.join(TERMINALS_ROOT, f"acc_{account_id}")


def get_account_terminal_exe(account_id: int) -> str:
    return os.path.join(get_account_terminal_dir(account_id), "terminal64.exe")


def create_optimized_ini_config(target_dir: str, login: int, server: str):
    """Writes ultra-low-footprint configuration to ensure minimal RAM and CPU."""
    config_dir = os.path.join(target_dir, "Config")
    os.makedirs(config_dir, exist_ok=True)
    
    ini_path = os.path.join(config_dir, "common.ini")
    ini_content = f"""[Common]
Login={login}
Server={server}
AutoTrading=1
NewsEnable=0
SoundEnable=0
MaxBars=500
ChartsEnable=0
"""
    try:
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(ini_content)
    except Exception as e:
        logger.warning(f"Could not write custom common.ini for acc #{account_id}: {e}")


def provision_terminal_for_account(account_id: int, login: int, server: str) -> str:
    """
    Provisions or updates a dedicated portable MT5 instance for a specific account.
    Returns the absolute path to terminal64.exe in that sandbox.
    """
    ensure_terminals_root()
    acc_dir = get_account_terminal_dir(account_id)
    os.makedirs(acc_dir, exist_ok=True)

    target_exe = get_account_terminal_exe(account_id)

    # 1. Hard-link or copy terminal64.exe
    if not os.path.exists(target_exe):
        try:
            # Try NTFS hardlink first to save disk space and accelerate launch
            os.link(BASE_MT5_EXE, target_exe)
            logger.info(f"Created hard-linked terminal64.exe for Account #{account_id}")
        except Exception:
            shutil.copy2(BASE_MT5_EXE, target_exe)
            logger.info(f"Copied terminal64.exe for Account #{account_id}")

    # 2. Ensure minimal Config directory
    config_dir = os.path.join(acc_dir, "Config")
    os.makedirs(config_dir, exist_ok=True)
    profiles_dir = os.path.join(acc_dir, "Profiles")
    os.makedirs(profiles_dir, exist_ok=True)

    # 3. Apply memory-optimized config
    create_optimized_ini_config(acc_dir, login, server)

    return target_exe


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing provisioner for Account #1 (111729335)...")
    exe = provision_terminal_for_account(1, 111729335, "MetaQuotes-Demo")
    print("Provisioned EXE:", exe)
    print("Exists:", os.path.exists(exe))
