"""
Lead management endpoints — hospitals/surgeons that are not yet customers.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.db.session import get_db
from app.api.deps import PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.customer import Customer
from app.models.lead import Lead


router = APIRouter()


class LeadBase(BaseModel):
    name: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    hospital_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    state: Optional[str] = None
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    hospital_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    state: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    converted_customer_id: Optional[UUID] = None


class LeadResponse(LeadBase):
    id: UUID
    status: str
    converted_customer_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    lead_data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.LEAD_CREATE))
):
    """Create a new lead. Only name and city are required."""
    lead = Lead(**lead_data.model_dump(), created_by=current_user.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/cities", response_model=List[str])
def list_lead_cities(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.LEAD_READ))
):
    """Distinct known cities (union of leads, customers, sales rep users) for city autocomplete."""
    cities = set()
    for model in (Lead, Customer, User):
        query = db.query(distinct(model.city)).filter(model.city.isnot(None))
        if search:
            query = query.filter(model.city.ilike(f"%{search}%"))
        cities.update(row[0] for row in query.all() if row[0])
    return sorted(cities)


@router.get("/", response_model=List[LeadResponse])
def list_leads(
    city: str = Query(..., description="City is required to scope the lead search"),
    search: Optional[str] = None,
    status_filter: str = Query("active", alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.LEAD_READ))
):
    """List leads, scoped to a required city (drives the city-first search UX)."""
    query = db.query(Lead).filter(Lead.city == city)

    if status_filter:
        query = query.filter(Lead.status == status_filter)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Lead.name.ilike(search_term)) |
            (Lead.hospital_name.ilike(search_term))
        )

    query = query.order_by(Lead.name)
    leads = query.offset(skip).limit(limit).all()
    return leads


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.LEAD_READ))
):
    """Get lead details."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.LEAD_UPDATE))
):
    """Update lead details (fill in optional fields, mark converted/dropped, etc.)."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    lead.updated_by = current_user.id
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return lead
