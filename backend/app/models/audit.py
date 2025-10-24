"""
AuditLog database model for tracking all system changes.
"""
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class AuditLog(BaseModel):
    """
    AuditLog model for comprehensive audit trail.
    Records all create, update, delete, and approval actions.
    """
    __tablename__ = "audit_logs"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, approve, reject
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    old_values = Column(JSONB)  # Previous state
    new_values = Column(JSONB)  # New state
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    
    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>"
