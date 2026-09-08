"""
Push Subscription database model for Web Push notifications.
"""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class PushSubscription(BaseModel):
    """
    A browser's Web Push subscription for one user's device, used to deliver
    the location check-in reminders when the app isn't open.
    """
    __tablename__ = "push_subscriptions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    endpoint = Column(String(1000), unique=True, nullable=False, index=True)
    p256dh_key = Column(String(255), nullable=False)
    auth_key = Column(String(255), nullable=False)

    # Relationships
    user = relationship("User", back_populates="push_subscriptions", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<PushSubscription {self.user_id} {self.endpoint[:40]}>"
