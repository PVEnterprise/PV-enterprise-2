"""
Quotation and QuotationItem database models.
"""
from sqlalchemy import Column, String, Text, Integer, Numeric, ForeignKey, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Quotation(BaseModel):
    """
    Quotation model for price quotes sent to customers.
    """
    __tablename__ = "quotations"
    
    quote_number = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), nullable=False, index=True, default="draft")
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    gst_rate = Column(Numeric(5, 2), default=18.00, nullable=False)
    gst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    discount_percentage = Column(Numeric(5, 2), default=0.00)
    discount_amount = Column(Numeric(15, 2), default=0.00)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    valid_until = Column(Date)
    payment_terms = Column(Text)
    delivery_terms = Column(Text)
    notes = Column(Text)
    
    # Relationships
    order = relationship("Order", back_populates="quotations")
    creator = relationship("User", back_populates="created_quotations", foreign_keys=[created_by])
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="quotation")
    approvals = relationship("Approval", foreign_keys="Approval.entity_id",
                           primaryjoin="and_(Quotation.id==Approval.entity_id, Approval.entity_type=='quotation')",
                           viewonly=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('subtotal >= 0', name='check_quotation_subtotal_non_negative'),
        CheckConstraint('gst_rate >= 0 AND gst_rate <= 100', name='check_gst_rate_valid'),
        CheckConstraint('discount_percentage >= 0 AND discount_percentage <= 100', 
                       name='check_discount_percentage_valid'),
        CheckConstraint('total_amount >= 0', name='check_total_amount_non_negative'),
    )
    
    def __repr__(self) -> str:
        return f"<Quotation {self.quote_number}>"
    
    def calculate_totals(self) -> None:
        """Calculate subtotal, GST, discount, and total amount."""
        # Calculate subtotal from items
        self.subtotal = sum(item.line_total for item in self.items)
        
        # Calculate discount
        if self.discount_percentage:
            self.discount_amount = self.subtotal * (self.discount_percentage / 100)
        
        # Calculate amount after discount
        amount_after_discount = self.subtotal - (self.discount_amount or 0)
        
        # Calculate GST
        self.gst_amount = amount_after_discount * (self.gst_rate / 100)
        
        # Calculate total
        self.total_amount = amount_after_discount + self.gst_amount


class QuotationItem(BaseModel):
    """
    QuotationItem model representing line items in a quotation.
    """
    __tablename__ = "quotation_items"
    
    quotation_id = Column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    line_total = Column(Numeric(15, 2), nullable=False)
    
    # Relationships
    quotation = relationship("Quotation", back_populates="items")
    inventory_item = relationship("Inventory", back_populates="quotation_items")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quotation_item_quantity_positive'),
        CheckConstraint('unit_price >= 0', name='check_quotation_item_price_non_negative'),
    )
    
    def __repr__(self) -> str:
        return f"<QuotationItem {self.id}>"
    
    def calculate_line_total(self) -> None:
        """Calculate line total (quantity × unit_price)."""
        self.line_total = self.quantity * self.unit_price
