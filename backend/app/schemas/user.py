"""
Pydantic schemas for User and Role models.
Used for request validation and response serialization.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Role Schemas
class RoleBase(BaseModel):
    """Base schema for Role."""
    name: str = Field(..., max_length=50)
    description: Optional[str] = None
    permissions: dict = Field(default_factory=dict)


class RoleCreate(RoleBase):
    """Schema for creating a new role."""
    pass


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    permissions: Optional[dict] = None


class RoleResponse(RoleBase):
    """Schema for role response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# User Schemas
class UserBase(BaseModel):
    """Base schema for User."""
    email: EmailStr
    full_name: str = Field(..., max_length=255)


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8)
    role_id: UUID


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    role_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    """Schema for updating user password."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    role_id: UUID
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserWithRole(UserResponse):
    """Schema for user response with role details."""
    role: RoleResponse
    name: Optional[str] = None  # Alias for full_name for frontend compatibility
    role_name: Optional[str] = None  # Role name for easy access
    
    model_config = ConfigDict(from_attributes=True)


# Authentication Schemas
class Token(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for token payload."""
    sub: UUID  # user_id
    role: str
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str
