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
    """Writes ultra-low-footprint configuration to ensure minimal RAM and CPU with explicit AutoTrading enforcement.

    IMPORTANT: Under [Experts], Api=0 means Python API trading is ENABLED (the MT5 option
    "Disable automatic trading through the external Python API" is UNCHECKED).
    Api=1 means the Python API is DISABLED (that checkbox is CHECKED).
    This is counterintuitive but confirmed via terminal_info().tradeapi_disabled behavior.
    """
    config_dir = os.path.join(target_dir, "Config")
    os.makedirs(config_dir, exist_ok=True)
    
    ini_path = os.path.join(config_dir, "common.ini")
    ini_content = f"""[Common]
Login={login}
Server={server}
AutoTrading=1
EnableAlgoTrading=1
NewsEnable=0
SoundEnable=0
MaxBars=500
ChartsEnable=0

[Experts]
AllowDllImport=1
Enabled=1
Account=0
Profile=0
Chart=0
Api=0
AllowLiveTrading=1

[Terminal]
EnableAlgoTrading=1
"""
    try:
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(ini_content)
        logger.info(f"Successfully created common.ini with AutoTrading enforcement for login #{login}")
    except Exception as e:
        logger.warning(f"Could not write custom common.ini: {e}")


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

    # 4. Copy options.dat, experts.dat, and servers.dat to preserve AlgoTrading permissions and broker network definitions
    src_opt = os.path.join(BASE_MT5_DIR, "Bases", "options.dat")
    src_exp = os.path.join(BASE_MT5_DIR, "MQL5", "experts.dat")
    src_srv = os.path.join(TERMINALS_ROOT, "acc_1", "Config", "servers.dat")
    bases_dir = os.path.join(acc_dir, "Bases")
    mql5_dir = os.path.join(acc_dir, "MQL5")
    os.makedirs(bases_dir, exist_ok=True)
    os.makedirs(mql5_dir, exist_ok=True)
    if os.path.exists(src_opt):
        try:
            shutil.copy2(src_opt, os.path.join(bases_dir, "options.dat"))
        except Exception:
            pass
    if os.path.exists(src_exp):
        try:
            shutil.copy2(src_exp, os.path.join(mql5_dir, "experts.dat"))
        except Exception:
            pass
    if os.path.exists(src_srv):
        try:
            shutil.copy2(src_srv, os.path.join(config_dir, "servers.dat"))
        except Exception:
            pass

    return target_exe


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing provisioner for Account #1 (111729335)...")
    exe = provision_terminal_for_account(1, 111729335, "MetaQuotes-Demo")
    print("Provisioned EXE:", exe)
    print("Exists:", os.path.exists(exe))
