"""
Background thread that fires the weekly email every Monday at 08:00 (local time).
Started once when the Streamlit app boots.
"""
import threading
import time
import schedule
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
_started = False
_last_status: dict = {"sent_at": None, "result": None}


def _job(capital: float, n_positions: int) -> None:
    from notifications.emailer import send_weekly_email
    logger.info("Running weekly email job…")
    result = send_weekly_email(capital, n_positions)
    _last_status["sent_at"] = datetime.now().isoformat()
    _last_status["result"] = result
    if result == "OK":
        logger.info("Weekly email sent successfully.")
    else:
        logger.error(f"Weekly email failed: {result}")


def start_scheduler(capital: float = 10_000, n_positions: int = 5) -> None:
    """
    Schedule the Monday 08:00 job and spin up a daemon thread.
    Safe to call multiple times — only starts once per process.
    """
    global _started
    if _started:
        return
    _started = True

    schedule.every().monday.at("08:00").do(_job, capital=capital, n_positions=n_positions)

    def _loop():
        while True:
            schedule.run_pending()
            time.sleep(30)

    t = threading.Thread(target=_loop, daemon=True, name="email-scheduler")
    t.start()
    logger.info("Email scheduler started — fires every Monday at 08:00.")


def last_email_status() -> dict:
    return _last_status


def trigger_now(capital: float = 10_000, n_positions: int = 5) -> str:
    """Manually fire the email immediately (for testing from the UI)."""
    from notifications.emailer import send_weekly_email
    result = send_weekly_email(capital, n_positions)
    _last_status["sent_at"] = datetime.now().isoformat()
    _last_status["result"] = result
    return result
