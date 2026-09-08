"""
Fires the four daily location check-in reminders (10:00, 12:00, 14:30, 17:00
Asia/Kolkata) to every sales rep's subscribed devices via Web Push.

Runs in-process via APScheduler. Safe as-is only because the backend runs as
a single uvicorn process (see start_server.sh / the systemd unit) — if that
ever changes to multiple workers, this must move to a single dedicated
process so the same slot doesn't fire once per worker.
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.services.push_service import send_location_reminder

logger = logging.getLogger(__name__)

# (slot key, human label, hour, minute) — slot key must match
# LocationCheckinSlot in app/schemas/location_checkin.py.
REMINDER_SLOTS = [
    ("10:00", "10:00 AM", 10, 0),
    ("12:00", "12:00 PM", 12, 0),
    ("14:30", "2:30 PM", 14, 30),
    ("17:00", "5:00 PM", 17, 0),
]

_scheduler: Optional[BackgroundScheduler] = None


def _send_reminders_for_slot(slot: str, slot_label: str) -> None:
    db = SessionLocal()
    try:
        subscriptions = (
            db.query(PushSubscription)
            .join(User, User.id == PushSubscription.user_id)
            .filter(User.is_active.is_(True), User.role.has(name="sales_rep"))
            .all()
        )
        sent = 0
        for subscription in subscriptions:
            if send_location_reminder(db, subscription, slot, slot_label):
                sent += 1
        logger.info("Location reminder %s: sent to %d/%d subscriptions", slot, sent, len(subscriptions))
    finally:
        db.close()


def start_location_reminder_scheduler() -> Optional[BackgroundScheduler]:
    """Start the background scheduler. Call once, at app startup."""
    global _scheduler
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.warning("VAPID keys not configured — location check-in reminders are disabled")
        return None

    scheduler = BackgroundScheduler(timezone=settings.LOCATION_REMINDER_TIMEZONE)
    for slot, slot_label, hour, minute in REMINDER_SLOTS:
        scheduler.add_job(
            _send_reminders_for_slot,
            trigger=CronTrigger(hour=hour, minute=minute),
            args=[slot, slot_label],
            id=f"location_reminder_{slot}",
            replace_existing=True,
        )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_location_reminder_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
