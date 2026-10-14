"""
ctrader_copier_runner.py — Standalone Runner for PrimeEdge cTrader Copier
==========================================================================
Executes the background copier service on Linode.

Run directly with:
    python -m app.execution.ctrader_copier_runner
Or via systemd:
    systemctl start ctrader-copier.service
"""

import asyncio
import logging
import os
import signal
import sys

from app.database import SessionLocal
from app.execution.ctrader_gateway import CTraderGateway
from app.execution.ctrader_copier_service import CTraderCopierService
from app.models import UserBrokerAccount

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ctrader_copier_runner")

CTRADER_CLIENT_ID = os.getenv(
    "CTRADER_CLIENT_ID", "43796_NUbyz1CxFRhD01Tm0Jqc1hMVHd4ubgk5lZQcwtftpuH5zJozj1"
)
CTRADER_CLIENT_SECRET = os.getenv(
    "CTRADER_CLIENT_SECRET", "j9WYsJ4mG80iyHKbale8Fuxx75fO9eaMuUoOhrZWSlCS653C9C"
)
CTRADER_IS_DEMO = os.getenv("CTRADER_IS_DEMO", "true").lower() == "true"


def get_master_credentials():
    master_acc = os.getenv("MASTER_CTRADER_ACCOUNT_ID")
    master_tok = os.getenv("MASTER_ACCESS_TOKEN")

    if master_acc and master_tok:
        return int(master_acc), master_tok

    # Fallback to database for master cTrader account
    with SessionLocal() as db:
        master_uba = db.query(UserBrokerAccount).filter(
            UserBrokerAccount.platform == "ctrader",
            UserBrokerAccount.ctrader_access_token != None,
        ).first()

        if master_uba and master_uba.ctrader_account_id and master_uba.ctrader_access_token:
            logger.info("Loaded master account credentials from DB (ID: %s)", master_uba.ctrader_account_id)
            return int(master_uba.ctrader_account_id), master_uba.ctrader_access_token

    return None, None


async def main():
    logger.info("Initializing PrimeEdge cTrader Copier Service...")
    logger.info("Client ID: %s... Demo Mode: %s", CTRADER_CLIENT_ID[:12], CTRADER_IS_DEMO)

    master_account_id, master_token = get_master_credentials()

    if not master_account_id or not master_token:
        logger.warning(
            "No master cTrader account found yet in environment or DB.\n"
            "Please link your master account via OAuth at https://www.primeedge.app/api/v1/ctrader/auth?user_id=1\n"
            "Runner will poll every 15s until an account is connected..."
        )

    gateway = CTraderGateway(
        client_id=CTRADER_CLIENT_ID,
        client_secret=CTRADER_CLIENT_SECRET,
        is_demo=CTRADER_IS_DEMO,
    )

    service = CTraderCopierService(db_session_factory=SessionLocal, gateway=gateway)

    # Wait for master account if not configured yet
    while not master_account_id or not master_token:
        await asyncio.sleep(15)
        master_account_id, master_token = get_master_credentials()

    logger.info("Starting copy service for master account %s...", master_account_id)
    await service.start(master_account_id=master_account_id, master_access_token=master_token)

    # Keep runner alive until stop signal
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    logger.info("PrimeEdge cTrader Copier is actively running.")
    await stop_event.wait()

    logger.info("Shutting down copier service...")
    await service.stop()
    logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Copier runner terminated.")
