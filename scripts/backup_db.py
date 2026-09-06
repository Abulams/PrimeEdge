"""
Market-OS Automated SQLite Online Database Backup
=================================================
Performs a zero-downtime, non-blocking online snapshot of market_os.db
into C:\\Market-OS\\backups\\ with automatic 7-day retention cleanup.
"""

import os
import sqlite3
import datetime
import glob
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)
logger = logging.getLogger("MarketOSBackup")

BACKUP_DIR = r"C:\Market-OS\backups"
DB_PATH = r"C:\Market-OS\backend\market_os.db"
RETENTION_DAYS = 7


def run_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"market_os_backup_{timestamp}.db")

    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        return False

    logger.info(f"Starting online database snapshot to {backup_file}...")
    try:
        src_conn = sqlite3.connect(DB_PATH)
        dst_conn = sqlite3.connect(backup_file)

        with dst_conn:
            # SQLite online backup API handles concurrent writers seamlessly
            src_conn.backup(dst_conn, pages=100)

        dst_conn.close()
        src_conn.close()

        file_size_kb = round(os.path.getsize(backup_file) / 1024, 2)
        logger.info(f"✅ Database backup successful: {backup_file} ({file_size_kb} KB)")

        # Retention cleanup
        cleanup_old_backups()
        return True
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return False


def cleanup_old_backups():
    now = datetime.datetime.utcnow()
    pattern = os.path.join(BACKUP_DIR, "market_os_backup_*.db")
    for f in glob.glob(pattern):
        try:
            mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(f))
            if (now - mtime).days >= RETENTION_DAYS:
                os.remove(f)
                logger.info(f"Purged expired backup: {f}")
        except Exception as e:
            logger.warning(f"Could not purge {f}: {e}")


if __name__ == "__main__":
    run_backup()
