"""
Dispatch and DispatchItem database models for shipment tracking.
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Dispatch(BaseModel):
    """
    Dispatch model for tracking shipments and deliveries.
    """
    __tablename__ = "dispatches"
    
    dispatch_number = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), index=True)
    dispatch_date = Column(Date, nullable=False)
    courier_name = Column(String(255))
    tracking_number = Column(String(100))
    status = Column(String(50), default="pending", nullable=False, index=True)
    notes = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="dispatches")
    invoice = relationship("Invoice", back_populates="dispatches")
    creator = relationship("User", back_populates="created_dispatches", foreign_keys=[created_by])
    items = relationship("DispatchItem", back_populates="dispatch", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Dispatch {self.dispatch_number}>"


class DispatchItem(BaseModel):
    """
    DispatchItem model representing items in a dispatch.
    """
    __tablename__ = "dispatch_items"
    
    dispatch_id = Column(UUID(as_uuid=True), ForeignKey("dispatches.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    dispatch = relationship("Dispatch", back_populates="items")
    inventory_item = relationship("Inventory", back_populates="dispatch_items")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_dispatch_item_quantity_positive'),
    )
    
    def __repr__(self) -> str:
        return f"<DispatchItem {self.id}>"
