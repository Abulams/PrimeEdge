"""
Market OS Portable MT5 Terminal Manager
========================================
Manages automated creation, configuration, and lifecycle of isolated,
dedicated portable MetaTrader 5 terminal directories per customer account.
"""

import os
import shutil
import logging

logger = logging.getLogger("TerminalManager")

BASE_MT5 = r"C:\Program Files\MetaTrader 5"
TERMINALS_ROOT = r"C:\Market-OS\terminals"
TEMPLATE_DIR = os.path.join(TERMINALS_ROOT, "template")


def prepare_template() -> str:
    """
    Creates a clean base template directory for rapid cloning.
    Excludes user history, cache, and locked files.
    """
    if not os.path.exists(TEMPLATE_DIR):
        logger.info(f"Creating clean MT5 portable template from {BASE_MT5}...")
        os.makedirs(TEMPLATE_DIR, exist_ok=True)

    # 1. Copy core binaries
    for item in ["terminal64.exe", "metatester64.exe", "Terminal.ico"]:
        src = os.path.join(BASE_MT5, item)
        dst = os.path.join(TEMPLATE_DIR, item)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                logger.warning(f"Could not copy {item}: {e}")

    # 2. Copy Config folder (ignoring dynamic history/dat files)
    src_cfg = os.path.join(BASE_MT5, "Config")
    dst_cfg = os.path.join(TEMPLATE_DIR, "Config")
    if os.path.exists(src_cfg) and not os.path.exists(dst_cfg):
        try:
            shutil.copytree(src_cfg, dst_cfg, ignore=shutil.ignore_patterns("*.hcc", "*.dat", "*.lock", "*.tmp"))
        except Exception as e:
            logger.warning(f"Could not copy Config: {e}")
            os.makedirs(dst_cfg, exist_ok=True)

    # 3. Copy Profiles folder
    src_prof = os.path.join(BASE_MT5, "Profiles")
    dst_prof = os.path.join(TEMPLATE_DIR, "Profiles")
    if os.path.exists(src_prof) and not os.path.exists(dst_prof):
        try:
            shutil.copytree(src_prof, dst_prof, ignore=shutil.ignore_patterns("*.hcc", "*.lock"))
        except Exception as e:
            logger.warning(f"Could not copy Profiles: {e}")

    return TEMPLATE_DIR


def provision_account_terminal(account_id: int, login: int, server: str) -> str:
    """
    Provisions a dedicated portable MT5 terminal directory for a specific account.
    Configures common.ini for automated trading, zero sound, and headless operation.
    Returns the absolute path to terminal64.exe for this instance.
    """
    prepare_template()
    instance_dir = os.path.join(TERMINALS_ROOT, f"acc_{account_id}_{login}")

    if not os.path.exists(instance_dir):
        logger.info(f"Provisioning dedicated portable MT5 instance at {instance_dir}...")
        try:
            shutil.copytree(TEMPLATE_DIR, instance_dir)
        except Exception as e:
            logger.error(f"Error copying template to {instance_dir}: {e}")
            os.makedirs(instance_dir, exist_ok=True)
            for item in ["terminal64.exe", "metatester64.exe", "Terminal.ico"]:
                src = os.path.join(TEMPLATE_DIR, item)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(instance_dir, item))

    # Configure Config/common.ini for this specific terminal instance
    config_dir = os.path.join(instance_dir, "Config")
    os.makedirs(config_dir, exist_ok=True)
    common_ini = os.path.join(config_dir, "common.ini")

    ini_content = (
        "[Common]\r\n"
        f"Login={login}\r\n"
        f"Server={server}\r\n"
        "Sound=0\r\n"
        "News=0\r\n"
        "\r\n"
        "[Experts]\r\n"
        "Enabled=1\r\n"
        "Account=0\r\n"
        "Profile=0\r\n"
        "Api=1\r\n"
    )

    try:
        with open(common_ini, "w", encoding="utf-16-le") as f:
            f.write(ini_content)
    except Exception as e:
        logger.warning(f"Could not write common.ini: {e}")

    exe_path = os.path.join(instance_dir, "terminal64.exe")
    return exe_path


def cleanup_account_terminal(account_id: int, login: int):
    """Gracefully cleans up terminal directory if account is deleted."""
    instance_dir = os.path.join(TERMINALS_ROOT, f"acc_{account_id}_{login}")
    if os.path.exists(instance_dir):
        try:
            shutil.rmtree(instance_dir, ignore_errors=True)
            logger.info(f"Cleaned up terminal directory {instance_dir}")
        except Exception as e:
            logger.error(f"Could not remove {instance_dir}: {e}")
