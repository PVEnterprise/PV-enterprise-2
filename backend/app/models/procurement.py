"""
Procurement database models for tracking item procurement lifecycle.
"""
from sqlalchemy import Column, String, Text, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Procurement(BaseModel):
    """
    Procurement model for tracking supplier orders.
    Lifecycle: ordered -> payment_done -> order_received
    """
    __tablename__ = "procurements"

    procurement_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(String(30), nullable=False, default="ordered", index=True)
    supplier_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    items = relationship("ProcurementItem", back_populates="procurement", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Procurement {self.procurement_number} [{self.status}]>"


class ProcurementItem(BaseModel):
    """
    Individual item line in a Procurement.
    """
    __tablename__ = "procurement_items"

    procurement_id = Column(UUID(as_uuid=True), ForeignKey("procurements.id"), nullable=False, index=True)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(15, 2), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    procurement = relationship("Procurement", back_populates="items")
    inventory_item = relationship("Inventory", back_populates="procurement_items")

    def __repr__(self) -> str:
        return f"<ProcurementItem procurement={self.procurement_id} qty={self.quantity}>"
