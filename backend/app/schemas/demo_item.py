"""
Demo Item Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class InventoryItemBrief(BaseModel):
    """Brief inventory item info for demo item responses."""
    id: UUID
    sku: str
    description: Optional[str] = None
    stock_quantity: int
    
    class Config:
        from_attributes = True


class DemoItemBase(BaseModel):
    """Base schema for demo item data."""
    inventory_item_id: UUID
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")


class DemoItemCreate(DemoItemBase):
    """Schema for creating a demo item."""
    pass


class DemoItemUpdate(BaseModel):
    """Schema for updating a demo item."""
    quantity: Optional[int] = Field(None, gt=0, description="Quantity must be greater than 0")


class DemoItemResponse(BaseModel):
    """Schema for demo item response."""
    id: UUID
    demo_request_id: UUID
    inventory_item_id: UUID
    quantity: int
    inventory_item: InventoryItemBrief
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DemoItemBulkCreate(BaseModel):
    """Schema for bulk creating demo items."""
    items: list[DemoItemCreate]
