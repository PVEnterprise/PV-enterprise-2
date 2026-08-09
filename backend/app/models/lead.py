"""
Lead database model — hospitals/surgeons that are not yet customers.
"""
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Lead(BaseModel):
    """
    Lead model representing a prospective hospital/surgeon not yet a customer.
    """
    __tablename__ = "leads"

    name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    hospital_name = Column(String(255), nullable=True)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    state = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="active", index=True)
    converted_customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, index=True)

    # Relationships
    creator = relationship("User", back_populates="created_leads", foreign_keys="Lead.created_by")
    converted_customer = relationship("Customer", foreign_keys=[converted_customer_id])
    field_visits = relationship("FieldVisit", back_populates="lead")

    def __repr__(self) -> str:
        return f"<Lead {self.name} ({self.city})>"
