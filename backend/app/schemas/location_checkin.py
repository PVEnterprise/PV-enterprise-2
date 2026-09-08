"""
Pydantic schemas for employee location check-ins.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class LocationCheckinSlot(str, Enum):
    """The four scheduled reminder times (Asia/Kolkata) a rep checks in at."""
    MORNING = "10:00"
    NOON = "12:00"
    AFTERNOON = "14:30"
    EVENING = "17:00"


class LocationCheckinCreate(BaseModel):
    """Schema for submitting a location check-in captured on the device."""
    slot: LocationCheckinSlot
    hospital_name: str = Field(..., min_length=1, max_length=255, description="Free text, not linked to a customer record")
    recorded_at: datetime = Field(..., description="Device timestamp when the GPS fix was captured")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0, description="Reported GPS accuracy in meters")


class UserBrief(BaseModel):
    """Nested user information for the admin listing."""
    id: UUID
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class LocationCheckinResponse(BaseModel):
    """Schema for a location check-in response."""
    id: UUID
    user_id: UUID
    user: Optional[UserBrief] = None
    slot: str
    hospital_name: str
    recorded_at: datetime
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
