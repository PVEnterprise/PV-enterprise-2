"""
Pydantic schemas for Dispatch and DispatchItem.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class DispatchItemBase(BaseModel):
    order_item_id: UUID
    inventory_id: UUID
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


class DispatchItemCreate(DispatchItemBase):
    pass


class InventoryBasic(BaseModel):
    """Basic inventory info for dispatch items."""
    id: UUID
    sku: str
    description: Optional[str] = None
    unit_price: Decimal
    tax: Decimal

    model_config = ConfigDict(from_attributes=True)


class DispatchItemResponse(DispatchItemBase):
    id: UUID
    dispatch_id: UUID
    inventory_item: Optional[InventoryBasic] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DispatchBase(BaseModel):
    dispatch_date: date
    courier_name: Optional[str] = None
    tracking_number: Optional[str] = None
    status: str = "pending"
    notes: Optional[str] = None


class DispatchCreate(DispatchBase):
    order_id: UUID
    invoice_id: Optional[UUID] = None
    items: List[DispatchItemCreate]


class DispatchResponse(DispatchBase):
    id: UUID
    dispatch_number: str
    order_id: UUID
    invoice_id: Optional[UUID] = None
    created_by: UUID
    items: List[DispatchItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
