"""
Pydantic schemas for Demo Request API.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class DemoRequestState(str, Enum):
    """Demo request state enum."""
    REQUESTED = "requested"
    SUBMITTED = "submitted"  # Submitted for approval
    APPROVED = "approved"    # Approved by executive
    DISPATCHED = "dispatched"
    COMPLETE = "complete"    # Items received back, stock restored


class DemoRequestBase(BaseModel):
    """Base schema for demo request."""
    hospital_id: Optional[UUID] = Field(None, description="Hospital/Customer ID")
    city: Optional[str] = Field(None, max_length=255, description="City")
    state: DemoRequestState = Field(default=DemoRequestState.REQUESTED, description="Demo request state")
    notes: Optional[str] = Field(None, description="Additional notes")


class DemoRequestCreate(DemoRequestBase):
    """Schema for creating a demo request."""
    pass


class DemoRequestUpdate(BaseModel):
    """Schema for updating a demo request."""
    number: Optional[str] = Field(None, max_length=50)
    hospital_id: Optional[UUID] = None
    city: Optional[str] = Field(None, max_length=255)
    state: Optional[DemoRequestState] = None
    notes: Optional[str] = None


class HospitalInfo(BaseModel):
    """Nested hospital information."""
    id: UUID
    name: str
    hospital_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class CreatorInfo(BaseModel):
    """Nested creator information."""
    id: UUID
    full_name: str
    email: str
    
    model_config = ConfigDict(from_attributes=True)


class InventoryItemBrief(BaseModel):
    """Brief inventory item info."""
    id: UUID
    sku: str
    description: Optional[str] = None
    stock_quantity: int
    
    model_config = ConfigDict(from_attributes=True)


class DemoItemBrief(BaseModel):
    """Brief demo item info for demo request response."""
    id: UUID
    inventory_item_id: UUID
    quantity: int
    inventory_item: InventoryItemBrief
    
    model_config = ConfigDict(from_attributes=True)


class DemoRequestResponse(DemoRequestBase):
    """Schema for demo request response."""
    id: UUID
    number: str
    hospital: Optional[HospitalInfo] = None
    creator: CreatorInfo
    items: list[DemoItemBrief] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
