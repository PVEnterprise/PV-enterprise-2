"""
Web Push delivery for the sales PWA's location check-in reminders.
"""
import json
import logging
from typing import Optional

from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def send_push_to_subscription(db: Session, subscription: PushSubscription, payload: dict) -> bool:
    """
    Deliver one payload to one subscription.

    Returns False (and deletes the subscription) when the push service reports
    it as gone (410) or not found (404) — the browser has revoked it and it
    would only fail the same way on every future attempt.
    """
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key,
                },
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_CLAIM_EMAIL},
        )
        return True
    except WebPushException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in (404, 410):
            db.query(PushSubscription).filter(PushSubscription.id == subscription.id).delete()
            db.commit()
        else:
            logger.warning("Push delivery failed for subscription %s: %s", subscription.id, exc)
        return False


def send_location_reminder(db: Session, subscription: PushSubscription, slot: str, slot_label: str) -> bool:
    """Send one location check-in reminder for the given slot."""
    payload = {
        "type": "location_checkin_reminder",
        "slot": slot,
        "title": "Location check-in",
        "body": f"Please check in your location ({slot_label}).",
    }
    return send_push_to_subscription(db, subscription, payload)
