"""
Pydantic schemas for Web Push subscription registration.
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from app.schemas.location_checkin import LocationCheckinSlot


class PushSubscriptionKeys(BaseModel):
    """The keys nested inside the browser's PushSubscription.toJSON() output."""
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    """Schema for registering a browser's push subscription."""
    endpoint: str = Field(..., max_length=1000)
    keys: PushSubscriptionKeys


class VapidPublicKeyResponse(BaseModel):
    """The public VAPID key the frontend needs to create a push subscription."""
    public_key: str


class SendReminderRequest(BaseModel):
    """Executive-triggered, on-demand version of the scheduled reminder push."""
    slot: LocationCheckinSlot
    user_id: Optional[UUID] = Field(None, description="Omit to send to every subscribed sales rep")


class SendReminderResponse(BaseModel):
    sent: int
    total: int
