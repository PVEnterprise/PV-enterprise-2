"""
Price List schemas for API validation.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class PriceListBase(BaseModel):
    """Base schema for price list."""
    name: str
    description: Optional[str] = None
    is_default: bool = False


class PriceListCreate(PriceListBase):
    """Schema for creating a price list."""
    pass


class PriceListUpdate(BaseModel):
    """Schema for updating a price list."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None


class PriceListResponse(PriceListBase):
    """Schema for price list response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)


class PriceListItemBase(BaseModel):
    """Base schema for price list item."""
    inventory_id: UUID
    unit_price: Decimal
    tax_percentage: Decimal = 5.00


class PriceListItemUpdate(BaseModel):
    """Schema for updating a price list item."""
    unit_price: Decimal
    tax_percentage: Optional[Decimal] = None


class InventoryBasic(BaseModel):
    """Basic inventory info for price list items."""
    id: UUID
    sku: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PriceListItemResponse(BaseModel):
    """Schema for price list item response."""
    id: UUID
    price_list_id: UUID
    inventory_id: UUID
    inventory: InventoryBasic
    unit_price: Decimal
    tax_percentage: Decimal
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
