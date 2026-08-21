"""
APScheduler Background Worker: Manages active/sleep cycles, weekly Excel reports, and 2-minute polling.
Configured for Africa/Johannesburg timezone with South African public holiday awareness.
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError as e:
    logging.warning(f"APScheduler import warning: {e}. Install dependencies using: pip install -r requirements.txt.")
    AsyncIOScheduler = None
    CronTrigger = None
    IntervalTrigger = None

try:
    import holidays
    SA_HOLIDAYS = holidays.ZA()
except ImportError:
    logging.warning("holidays package unavailable. Falling back to default calendar.")
    SA_HOLIDAYS = {}

from services.report_service import send_weekly_report
from services.email_service import email_service

logger = logging.getLogger("agent.scheduler")

TIMEZONE_STR = "Africa/Johannesburg"


def get_johannesburg_now() -> datetime:
    """
    Returns current datetime in Africa/Johannesburg timezone.
    """
    try:
        tz = zoneinfo.ZoneInfo(TIMEZONE_STR)
        return datetime.now(tz)
    except Exception:
        return datetime.now()


def is_agent_active() -> bool:
    """
    Validates if the agent should be active or in sleep mode based on current time in Africa/Johannesburg:
    - Monday to Friday: 08:00 to 22:00
    - Saturdays: 08:00 to 15:00
    - Sundays OR South African Public Holidays: 08:00 to 13:00
    Returns False if current time falls outside these bounds.
    """
    now = get_johannesburg_now()
    weekday = now.weekday()  # 0=Monday, ..., 5=Saturday, 6=Sunday
    hour = now.hour
    today_date = now.date()

    is_public_holiday = today_date in SA_HOLIDAYS

    if is_public_holiday or weekday == 6:
        # Sunday or South African Public Holiday: 08:00 - 13:00
        active = 8 <= hour < 13
        logger.debug(f"[Scheduler] Sunday/Holiday check (Hour {hour}): active={active}")
        return active

    if weekday == 5:
        # Saturday: 08:00 - 15:00
        active = 8 <= hour < 15
        logger.debug(f"[Scheduler] Saturday check (Hour {hour}): active={active}")
        return active

    # Monday to Friday: 08:00 - 22:00
    active = 8 <= hour < 22
    logger.debug(f"[Scheduler] Weekday check (Hour {hour}): active={active}")
    return active


async def poll_inbox_and_leads() -> Dict[str, Any]:
    """
    Interval job (every 2 minutes).
    Checks if agent is active before polling unread emails and executing tasks.
    """
    if not is_agent_active():
        logger.info("[Scheduler] Agent is currently in SLEEP mode. Skipping 2-minute polling cycle.")
        return {"status": "sleeping", "active": False}

    logger.info("[Scheduler] Agent is ACTIVE. Executing 2-minute inbox polling cycle...")

    try:
        unread_emails = await email_service.fetch_unread_emails(max_results=5)
        logger.info(f"[Scheduler] Polled {len(unread_emails)} unread email(s).")
        return {"status": "polled", "active": True, "emails_count": len(unread_emails)}
    except Exception as e:
        logger.error(f"[Scheduler] Polling error: {e}")
        return {"status": "error", "active": True, "error": str(e)}


async def generate_and_send_weekly_report_job() -> None:
    """
    Cron job: Every Monday at 07:00 AM Africa/Johannesburg.
    Generates weekly Excel performance report and emails it to admin.
    """
    logger.info("[Scheduler] Triggering Monday 07:00 AM weekly Excel report job...")
    try:
        res = await send_weekly_report()
        logger.info(f"[Scheduler] Weekly report job completed: {res}")
    except Exception as e:
        logger.error(f"[Scheduler] Weekly report job failed: {e}")


class AgentScheduler:
    """
    APScheduler worker wrapper for managing active/sleep cycles and cron jobs.
    """

    def __init__(self):
        self.scheduler = None
        if AsyncIOScheduler is not None:
            self.scheduler = AsyncIOScheduler(timezone=TIMEZONE_STR)

    def start(self) -> None:
        """
        Starts the background AsyncIOScheduler.
        """
        if self.scheduler is None:
            logger.error("APScheduler is not installed. Background jobs will not run.")
            return

        # 1. 2-minute interval polling job
        self.scheduler.add_job(
            poll_inbox_and_leads,
            trigger=IntervalTrigger(minutes=2),
            id="polling_job",
            name="2-minute Inbox & Lead Polling",
            replace_existing=True
        )

        # 2. Monday 07:00 AM Weekly Excel report cron job
        self.scheduler.add_job(
            generate_and_send_weekly_report_job,
            trigger=CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=TIMEZONE_STR),
            id="weekly_report_job",
            name="Monday 07:00 AM Weekly Report",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("APScheduler worker started successfully (Timezone: Africa/Johannesburg).")

    def shutdown(self) -> None:
        """
        Shuts down the scheduler gracefully.
        """
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("APScheduler worker shut down.")


agent_scheduler = AgentScheduler()
