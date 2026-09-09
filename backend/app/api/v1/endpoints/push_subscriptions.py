"""
API endpoints for registering the sales PWA's Web Push subscriptions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.schemas.push_subscription import (
    PushSubscriptionCreate,
    SendReminderRequest,
    SendReminderResponse,
    VapidPublicKeyResponse,
)
from app.api.deps import get_current_user
from app.services.location_reminder_scheduler import REMINDER_SLOTS
from app.services.push_service import send_location_reminder

router = APIRouter()

SLOT_LABELS = {slot: label for slot, label, _hour, _minute in REMINDER_SLOTS}

# Roles allowed to trigger an on-demand reminder push (mirrors location_checkins.py).
MANAGER_ROLES = {"executive", "quoter"}


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
def get_vapid_public_key():
    """The public key the frontend passes to PushManager.subscribe()."""
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not configured on this server",
        )
    return VapidPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_push_subscription(
    subscription_data: PushSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register (or re-register) the caller's device for push notifications.
    Idempotent on `endpoint`, since the browser hands back the same endpoint
    for an existing subscription.
    """
    existing = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == subscription_data.endpoint)
        .first()
    )
    if existing:
        existing.user_id = current_user.id
        existing.p256dh_key = subscription_data.keys.p256dh
        existing.auth_key = subscription_data.keys.auth
        existing.set_audit_fields(current_user.id, is_create=False)
        db.commit()
        return {"message": "Subscription updated"}

    subscription = PushSubscription(
        user_id=current_user.id,
        endpoint=subscription_data.endpoint,
        p256dh_key=subscription_data.keys.p256dh,
        auth_key=subscription_data.keys.auth,
    )
    subscription.set_audit_fields(current_user.id, is_create=True)
    db.add(subscription)
    db.commit()
    return {"message": "Subscription created"}


@router.post("/send-reminder", response_model=SendReminderResponse)
def send_reminder_now(
    request_data: SendReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Executive-only: trigger the location check-in reminder push immediately,
    instead of waiting for the scheduled time — e.g. to nudge one rep who
    hasn't checked in yet, or to test the push pipeline end to end.
    """
    if current_user.role_name not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives and quoters can send check-in reminders",
        )
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not configured on this server",
        )

    query = (
        db.query(PushSubscription)
        .join(User, User.id == PushSubscription.user_id)
        .filter(User.is_active.is_(True), User.role.has(name="sales_rep"))
    )
    if request_data.user_id:
        query = query.filter(PushSubscription.user_id == request_data.user_id)
    subscriptions = query.all()

    slot = request_data.slot.value
    slot_label = SLOT_LABELS.get(slot, slot)
    sent = sum(1 for sub in subscriptions if send_location_reminder(db, sub, slot, slot_label))

    return SendReminderResponse(sent=sent, total=len(subscriptions))


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_push_subscription(
    endpoint: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unregister a device, e.g. when the rep disables check-in reminders."""
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint,
        PushSubscription.user_id == current_user.id,
    ).delete()
    db.commit()
