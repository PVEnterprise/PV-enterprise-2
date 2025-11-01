"""
Price List models for managing custom pricing.
"""
from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class PriceList(Base):
    """Price list for custom pricing."""
    __tablename__ = "price_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    items = relationship("PriceListItem", back_populates="price_list", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])


class PriceListItem(Base):
    """Individual item pricing in a price list."""
    __tablename__ = "price_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_id = Column(UUID(as_uuid=True), ForeignKey("price_lists.id", ondelete="CASCADE"), nullable=False)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    tax_percentage = Column(Numeric(5, 2), nullable=False, default=5.00)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    price_list = relationship("PriceList", back_populates="items")
    inventory = relationship("Inventory")
