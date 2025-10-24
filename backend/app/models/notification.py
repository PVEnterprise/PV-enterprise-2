"""
Notification database model for in-app notifications.
"""
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Notification(BaseModel):
    """
    Notification model for in-app user notifications.
    """
    __tablename__ = "notifications"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # approval_request, status_update, alert, info
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(500))  # Deep link to relevant entity
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    
    def __repr__(self) -> str:
        return f"<Notification {self.title} for user {self.user_id}>"
