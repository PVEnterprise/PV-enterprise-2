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
    
    sku = Column(String(100), unique=True, nullable=False, index=True, comment="Catalog Number")
    description = Column(Text, comment="Item description")
    batch_no = Column(String(100), comment="Batch number")
    unit_price = Column(Numeric(15, 2), nullable=False, comment="Unit price in rupees")
    stock_quantity = Column(Integer, default=0, nullable=False, index=True, comment="Current stock quantity")
    hsn_code = Column(String(8), nullable=False, index=True, comment="HSN code (8 digits)")
    tax = Column(Numeric(5, 2), nullable=False, comment="Tax percentage")
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="inventory_item")
    quotation_items = relationship("QuotationItem", back_populates="inventory_item")
    invoice_items = relationship("InvoiceItem", back_populates="inventory_item")
    dispatch_items = relationship("DispatchItem", back_populates="inventory_item")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('stock_quantity >= 0', name='check_stock_non_negative'),
        CheckConstraint('unit_price >= 0', name='check_price_non_negative'),
        CheckConstraint('tax >= 0 AND tax <= 100', name='check_tax_percentage'),
        CheckConstraint("LENGTH(hsn_code) = 8", name='check_hsn_code_length'),
    )
    
    def __repr__(self) -> str:
        return f"<Inventory {self.sku}: {self.description[:50] if self.description else 'No description'}>"
    
    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (just stock quantity now)."""
        return self.stock_quantity
