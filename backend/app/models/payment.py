"""
Payment database model for recording customer payments.
"""
from sqlalchemy import Column, String, Text, ForeignKey, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Payment(BaseModel):
    """
    Payment model for tracking payments received from customers.
    """
    __tablename__ = "payments"
    
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True, index=True)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    payment_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id])
    order = relationship("Order", foreign_keys=[order_id])
    recorder = relationship("User", foreign_keys=[recorded_by])
    
    def __repr__(self) -> str:
        return f"<Payment {self.id} customer={self.customer_id} amount={self.amount}>"
