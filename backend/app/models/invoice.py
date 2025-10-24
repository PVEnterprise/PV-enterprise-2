"""
Invoice and InvoiceItem database models.
"""
from sqlalchemy import Column, String, Text, Integer, Numeric, ForeignKey, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Invoice(BaseModel):
    """
    Invoice model for billing documents and payment tracking.
    """
    __tablename__ = "invoices"
    
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    quotation_id = Column(UUID(as_uuid=True), ForeignKey("quotations.id"), index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), nullable=False, index=True, default="draft")
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    gst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(15, 2), default=0.00, nullable=False)
    payment_status = Column(String(50), default="unpaid", nullable=False, index=True)
    payment_terms = Column(Text)
    notes = Column(Text)
    
    # Relationships
    quotation = relationship("Quotation", back_populates="invoices")
    order = relationship("Order", back_populates="invoices")
    creator = relationship("User", back_populates="created_invoices", foreign_keys=[created_by])
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    approvals = relationship("Approval", foreign_keys="Approval.entity_id",
                           primaryjoin="and_(Invoice.id==Approval.entity_id, Approval.entity_type=='invoice')",
                           viewonly=True)
    dispatches = relationship("Dispatch", back_populates="invoice")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('subtotal >= 0', name='check_invoice_subtotal_non_negative'),
        CheckConstraint('total_amount >= 0', name='check_invoice_total_non_negative'),
        CheckConstraint('paid_amount >= 0', name='check_paid_amount_non_negative'),
        CheckConstraint('due_date >= invoice_date', name='check_due_date_after_invoice_date'),
    )
    
    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number}>"
    
    @property
    def balance(self) -> float:
        """Calculate outstanding balance (total - paid)."""
        return float(self.total_amount - self.paid_amount)
    
    def update_payment_status(self) -> None:
        """Update payment status based on paid amount."""
        if self.paid_amount == 0:
            self.payment_status = "unpaid"
        elif self.paid_amount >= self.total_amount:
            self.payment_status = "paid"
        else:
            self.payment_status = "partial"
    
    def calculate_totals(self) -> None:
        """Calculate subtotal, GST, and total amount from items."""
        self.subtotal = sum(item.line_total for item in self.items)
        # GST is typically included in the line totals or calculated separately
        # For simplicity, assuming items include GST
        self.total_amount = self.subtotal + self.gst_amount


class InvoiceItem(BaseModel):
    """
    InvoiceItem model representing line items in an invoice.
    """
    __tablename__ = "invoice_items"
    
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    line_total = Column(Numeric(15, 2), nullable=False)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    inventory_item = relationship("Inventory", back_populates="invoice_items")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_invoice_item_quantity_positive'),
        CheckConstraint('unit_price >= 0', name='check_invoice_item_price_non_negative'),
    )
    
    def __repr__(self) -> str:
        return f"<InvoiceItem {self.id}>"
    
    def calculate_line_total(self) -> None:
        """Calculate line total (quantity × unit_price)."""
        self.line_total = self.quantity * self.unit_price
