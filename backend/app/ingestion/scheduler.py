from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.ingestion.jobs.billing_sync import run_billing_sync
from app.ingestion.jobs.subscription_sync import run_subscription_sync

logger = logging.getLogger("erp_ingestion.scheduler")

scheduler: Optional[AsyncIOScheduler] = None


async def _run_subscription_job():
    logger.info("Starting scheduled subscription sync job...")
    try:
        res = await run_subscription_sync()
        logger.info(f"Scheduled subscription sync completed: {res}")
    except Exception as e:
        logger.error(f"Scheduled subscription sync encountered error: {e}", exc_info=True)


async def _run_billing_job():
    logger.info("Starting scheduled billing sync job...")
    try:
        res = await run_billing_sync()
        logger.info(f"Scheduled billing sync completed: {res}")
    except Exception as e:
        logger.error(f"Scheduled billing sync encountered error: {e}", exc_info=True)


def get_scheduler() -> AsyncIOScheduler:
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


def start_scheduler() -> None:
    """Initialize and start APScheduler background sync tasks."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler is disabled via configuration (SCHEDULER_ENABLED=False).")
        return

    sched = get_scheduler()
    if sched.running:
        logger.warning("Scheduler is already running.")
        return

    # 1. Daily Subscription Sync (Every day at 00:05 UTC)
    sched.add_job(
        _run_subscription_job,
        trigger=CronTrigger(hour=0, minute=5, timezone=timezone.utc),
        id="daily_subscription_sync",
        name="Daily Customer & Subscription Sync",
        replace_existing=True,
    )

    # 2. Daily Billing Sync (Every day at 00:30 UTC)
    sched.add_job(
        _run_billing_job,
        trigger=CronTrigger(hour=0, minute=30, timezone=timezone.utc),
        id="daily_billing_sync",
        name="Daily Invoices & Payments Sync",
        replace_existing=True,
    )

    sched.start()
    logger.info("APScheduler started successfully with scheduled sync jobs.")


def stop_scheduler() -> None:
    """Gracefully shutdown scheduler."""
    global scheduler
    if scheduler and scheduler.running:
        logger.info("Shutting down APScheduler...")
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("APScheduler stopped.")


def list_scheduled_jobs() -> List[Dict[str, Any]]:
    """Return status and next run times for all scheduled jobs."""
    if scheduler is None or not scheduler.running:
        return []

    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs_info
