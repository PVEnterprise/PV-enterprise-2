"""
Customer database model.
"""
from sqlalchemy import Column, String, Text, ForeignKey, Numeric
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

    # Quotation defaults — remembered from the last quotation/estimate generated
    # for this customer so the modal doesn't reset to hardcoded values every time.
    bank_account_name = Column(String(100))
    bank_account_number = Column(String(50))
    bank_name = Column(String(100))
    bank_ifsc = Column(String(20))
    bank_branch = Column(String(100))
    terms_and_conditions = Column(Text)
    discount_percentage = Column(Numeric(5, 2))
    
    # Relationships
    creator = relationship("User", back_populates="created_customers", foreign_keys=[created_by])
    orders = relationship("Order", back_populates="customer")
    demo_requests = relationship("DemoRequest", back_populates="hospital")
    
    def __repr__(self) -> str:
        return f"<Customer {self.hospital_name}>"
