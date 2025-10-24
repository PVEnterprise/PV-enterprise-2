"""
Inventory database model.
"""
from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, CheckConstraint
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Inventory(BaseModel):
    """
    Inventory model for product catalog and stock management.
    """
    __tablename__ = "inventory"
    
    sku = Column(String(100), unique=True, nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    manufacturer = Column(String(255))
    model_number = Column(String(100))
    unit_price = Column(Numeric(15, 2), nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False, index=True)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    reorder_level = Column(Integer, default=10, nullable=False)
    unit_of_measure = Column(String(50), default="piece", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Computed column for available quantity
    # Note: SQLAlchemy 2.0 syntax for computed columns
    # available_quantity = computed_column(stock_quantity - reserved_quantity)
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="inventory_item")
    quotation_items = relationship("QuotationItem", back_populates="inventory_item")
    invoice_items = relationship("InvoiceItem", back_populates="inventory_item")
    dispatch_items = relationship("DispatchItem", back_populates="inventory_item")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('stock_quantity >= 0', name='check_stock_non_negative'),
        CheckConstraint('reserved_quantity >= 0', name='check_reserved_non_negative'),
        CheckConstraint('unit_price >= 0', name='check_price_non_negative'),
    )
    
    def __repr__(self) -> str:
        return f"<Inventory {self.sku}: {self.item_name}>"
    
    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (stock - reserved)."""
        return self.stock_quantity - self.reserved_quantity
    
    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below reorder level."""
        return self.available_quantity <= self.reorder_level
