"""
Order and OrderItem database models.
"""
from sqlalchemy import Column, String, Text, Integer, Numeric, ForeignKey, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Order(BaseModel):
    """
    Order model representing customer orders and their lifecycle.
    Tracks the complete workflow from request to fulfillment.
    """
    __tablename__ = "orders"
    
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    sales_rep_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True, default="draft")
    workflow_stage = Column(String(50), nullable=False, index=True, default="order_request")
    priority = Column(String(20), default="medium", nullable=False)
    source = Column(String(50))  # email, whatsapp, phone, direct
    po_number = Column(String(100))
    po_date = Column(Date)
    po_amount = Column(Numeric(15, 2))
    notes = Column(Text)
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    sales_rep = relationship("User", back_populates="created_orders", foreign_keys=[sales_rep_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    quotations = relationship("Quotation", back_populates="order")
    invoices = relationship("Invoice", back_populates="order")
    approvals = relationship("Approval", foreign_keys="Approval.entity_id", 
                           primaryjoin="and_(Order.id==Approval.entity_id, Approval.entity_type=='order')",
                           viewonly=True)
    dispatches = relationship("Dispatch", back_populates="order")
    attachments = relationship("Attachment", foreign_keys="Attachment.entity_id",
                              primaryjoin="and_(Order.id==Attachment.entity_id, Attachment.entity_type=='order')",
                              viewonly=True)
    
    def __repr__(self) -> str:
        return f"<Order {self.order_number}>"
    
    @property
    def total_items(self) -> int:
        """Get total number of items in order."""
        return len(self.items)
    
    @property
    def decoded_items_count(self) -> int:
        """Get count of decoded items."""
        return sum(1 for item in self.items if item.inventory_id is not None)
    
    @property
    def is_fully_decoded(self) -> bool:
        """Check if all items are decoded."""
        return self.total_items > 0 and self.decoded_items_count == self.total_items


class OrderItem(BaseModel):
    """
    OrderItem model representing individual items in an order.
    Tracks decoding status and inventory mapping.
    """
    __tablename__ = "order_items"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), 
                     nullable=False, index=True)
    item_description = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id"), index=True)
    decoded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    unit_price = Column(Numeric(15, 2))
    gst_percentage = Column(Numeric(5, 2), default=18.00)  # GST percentage (default 18%)
    status = Column(String(50), default="pending", nullable=False, index=True)
    notes = Column(Text)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    inventory_item = relationship("Inventory", back_populates="order_items")
    decoder = relationship("User", back_populates="decoded_items", foreign_keys=[decoded_by])
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_order_item_quantity_positive'),
    )
    
    def __repr__(self) -> str:
        return f"<OrderItem {self.id}: {self.item_description[:30]}>"
    
    @property
    def is_decoded(self) -> bool:
        """Check if item is decoded (mapped to inventory)."""
        return self.inventory_id is not None
    
    @property
    def line_total(self) -> float:
        """Calculate line total (quantity × unit_price)."""
        if self.unit_price:
            return float(self.quantity * self.unit_price)
        return 0.0
