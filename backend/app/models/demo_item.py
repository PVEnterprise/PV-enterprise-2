"""
Demo Item database model for tracking items in demo requests.
"""
from sqlalchemy import Column, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class DemoItem(BaseModel):
    """
    DemoItem model for tracking inventory items assigned to demo requests.
    """
    __tablename__ = "demo_items"
    
    demo_request_id = Column(UUID(as_uuid=True), ForeignKey("demo_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    
    # Relationships
    demo_request = relationship("DemoRequest", back_populates="items")
    inventory_item = relationship("Inventory", back_populates="demo_items")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_demo_item_quantity_positive'),
    )
    
    def __repr__(self) -> str:
        return f"<DemoItem {self.id}: {self.quantity}x>"
