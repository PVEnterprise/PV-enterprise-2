"""
Customer database model.
"""
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Customer(BaseModel):
    """
    Customer model representing hospitals and healthcare facilities.
    """
    __tablename__ = "customers"
    
    name = Column(String(255), nullable=False)
    hospital_name = Column(String(255), nullable=False, index=True)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(20))
    gst_number = Column(String(50), index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    creator = relationship("User", back_populates="created_customers", foreign_keys=[created_by])
    orders = relationship("Order", back_populates="customer")
    
    def __repr__(self) -> str:
        return f"<Customer {self.hospital_name}>"
