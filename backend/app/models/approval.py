"""
Approval database model for workflow approvals.
"""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Approval(BaseModel):
    """
    Approval model for tracking workflow approvals.
    Supports polymorphic relationships with multiple entity types.
    """
    __tablename__ = "approvals"
    
    entity_type = Column(String(50), nullable=False, index=True)  # order, quotation, invoice, po
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    stage = Column(String(100), nullable=False)  # decoding_approval, quotation_approval, etc.
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # Nullable until assigned
    status = Column(String(50), nullable=False, index=True, default="pending")
    comments = Column(Text)
    approved_at = Column(DateTime)
    
    # Relationships
    approver = relationship("User", back_populates="approvals", foreign_keys=[approver_id])
    
    def __repr__(self) -> str:
        return f"<Approval {self.entity_type}:{self.entity_id} - {self.status}>"
