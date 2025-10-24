"""
Pydantic schemas for Order and OrderItem models.
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class InventoryBasic(BaseModel):
    """Basic inventory info for nested responses."""
    id: UUID
    sku: str
    item_name: str
    unit_price: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class CustomerBasic(BaseModel):
    """Basic customer info for nested responses."""
    id: UUID
    name: str
    hospital_name: str
    
    model_config = ConfigDict(from_attributes=True)


# OrderItem Schemas
class OrderItemBase(BaseModel):
    """Base schema for OrderItem."""
    item_description: str
    quantity: int = Field(..., gt=0)
    notes: Optional[str] = None


class OrderItemCreate(OrderItemBase):
    """Schema for creating an order item."""
    pass


class OrderItemUpdate(BaseModel):
    """Schema for updating an order item."""
    item_description: Optional[str] = None
    quantity: Optional[int] = Field(None, gt=0)
    inventory_id: Optional[UUID] = None
    unit_price: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class OrderItemDecode(BaseModel):
    """Schema for decoding an order item."""
    inventory_id: UUID
    unit_price: Optional[Decimal] = None
    quantity: Optional[int] = Field(default=1, gt=0)
    gst_percentage: Optional[Decimal] = Field(default=18.00, ge=0, le=100)


class OrderItemDecodeMultiple(BaseModel):
    """Schema for decoding an order item with multiple inventory items."""
    items: List[OrderItemDecode] = Field(..., min_length=1)


class OrderItemResponse(OrderItemBase):
    """Schema for order item response."""
    id: UUID
    order_id: UUID
    inventory_id: Optional[UUID] = None
    inventory: Optional[InventoryBasic] = Field(None, validation_alias="inventory_item", serialization_alias="inventory")  # Maps from inventory_item relationship
    decoded_by: Optional[UUID] = None
    unit_price: Optional[Decimal] = None
    gst_percentage: Optional[Decimal] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Order Schemas
class OrderBase(BaseModel):
    """Base schema for Order."""
    customer_id: UUID
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    source: Optional[str] = None
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    """Schema for creating an order."""
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    """Schema for updating an order."""
    customer_id: Optional[UUID] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    source: Optional[str] = None
    po_number: Optional[str] = None
    po_date: Optional[date] = None
    po_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""
    status: str
    workflow_stage: str


class OrderReject(BaseModel):
    """Schema for rejecting an order."""
    reason: str = Field(..., min_length=1, description="Reason for rejection")


class OrderResponse(OrderBase):
    """Schema for order response."""
    id: UUID
    order_number: str
    sales_rep_id: UUID
    customer: Optional[CustomerBasic] = None  # Nested customer data
    status: str
    workflow_stage: str
    po_number: Optional[str] = None
    po_date: Optional[date] = None
    po_amount: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OrderWithItems(OrderResponse):
    """Schema for order response with items."""
    items: List[OrderItemResponse]
    
    model_config = ConfigDict(from_attributes=True)


class OrderSummary(BaseModel):
    """Schema for order summary (for lists)."""
    id: UUID
    order_number: str
    customer_id: UUID
    customer: Optional[CustomerBasic] = None  # Include customer data
    status: str
    workflow_stage: str
    priority: str
    total_items: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)
