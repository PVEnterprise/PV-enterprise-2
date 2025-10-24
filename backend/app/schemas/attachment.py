"""
Pydantic schemas for Attachment model.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AttachmentBase(BaseModel):
    """Base schema for Attachment."""
    entity_type: str = Field(..., description="Type of entity (order, customer, inventory, etc.)")
    entity_id: UUID = Field(..., description="ID of the entity")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")


class AttachmentCreate(AttachmentBase):
    """Schema for creating an attachment (file info added by backend)."""
    pass


class AttachmentUpdate(BaseModel):
    """Schema for updating an attachment."""
    description: Optional[str] = Field(None, max_length=500)


class AttachmentInDB(AttachmentBase):
    """Schema for attachment in database."""
    id: UUID
    filename: str
    original_filename: str
    file_path: str
    file_type: str
    file_size: int
    file_extension: Optional[str]
    created_at: datetime
    created_by: Optional[UUID]
    
    class Config:
        from_attributes = True


class Attachment(AttachmentInDB):
    """Schema for attachment response."""
    file_size_mb: float
    is_image: bool
    is_pdf: bool
    is_document: bool
    
    class Config:
        from_attributes = True
