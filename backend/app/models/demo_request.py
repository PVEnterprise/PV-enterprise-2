"""
Demo Request database model for tracking demo equipment requests.
"""
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class DemoRequest(BaseModel):
    """
    DemoRequest model for tracking demo equipment requests to hospitals.
    """
    __tablename__ = "demo_requests"
    
    number = Column(String(50), unique=True, nullable=False, index=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, index=True)
    city = Column(String(255), nullable=True)
    state = Column(String(50), nullable=False, default="requested", index=True)
    notes = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    hospital = relationship("Customer", back_populates="demo_requests")
    creator = relationship("User", back_populates="created_demo_requests", foreign_keys=[created_by])
    items = relationship("DemoItem", back_populates="demo_request", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<DemoRequest {self.number}>"
