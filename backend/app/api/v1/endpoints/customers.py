"""
Customer management endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.customer import Customer


router = APIRouter()


class CustomerBase(BaseModel):
    name: str = Field(..., max_length=255)
    hospital_name: str = Field(..., max_length=255)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    gst_number: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    hospital_name: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    gst_number: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_CREATE))
):
    """Create a new customer."""
    customer = Customer(**customer_data.model_dump(), created_by=current_user.id)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/", response_model=List[CustomerResponse])
def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_READ))
):
    """List customers with search."""
    query = db.query(Customer)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Customer.hospital_name.ilike(search_term)) |
            (Customer.name.ilike(search_term)) |
            (Customer.gst_number.ilike(search_term))
        )
    
    query = query.order_by(Customer.hospital_name)
    customers = query.offset(skip).limit(limit).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_READ))
):
    """Get customer details."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_UPDATE))
):
    """Update customer details."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    customer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(customer)
    return customer
