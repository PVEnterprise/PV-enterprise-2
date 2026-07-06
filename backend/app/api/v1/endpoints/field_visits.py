"""
Field visit endpoints — logs a sales rep's visit to a customer or lead.
"""
from typing import List, Optional
from uuid import UUID
from datetime import date, time, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.db.session import get_db
from app.api.deps import PermissionChecker
from app.core.permissions import Permission, can_access_all_field_visits, Role
from app.models.user import User
from app.models.field_visit import FieldVisit


router = APIRouter()


class FieldVisitBase(BaseModel):
    visit_date: date
    customer_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    in_time: Optional[time] = None
    out_time: Optional[time] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def exactly_one_target(self):
        if bool(self.customer_id) == bool(self.lead_id):
            raise ValueError("Exactly one of customer_id or lead_id must be set")
        return self


class FieldVisitCreate(FieldVisitBase):
    sales_rep_id: Optional[UUID] = None


class FieldVisitUpdate(BaseModel):
    visit_date: Optional[date] = None
    customer_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    in_time: Optional[time] = None
    out_time: Optional[time] = None
    notes: Optional[str] = None


class FieldVisitResponse(FieldVisitBase):
    id: UUID
    sales_rep_id: UUID
    customer_name: Optional[str] = None
    lead_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SalesRepOption(BaseModel):
    id: UUID
    full_name: str
    city: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


def _to_response(visit: FieldVisit) -> FieldVisitResponse:
    data = FieldVisitResponse.model_validate(visit)
    data.customer_name = visit.customer.hospital_name if visit.customer else None
    data.lead_name = visit.lead.name if visit.lead else None
    return data


@router.get("/sales-reps", response_model=List[SalesRepOption])
def list_sales_reps_for_visit_logging(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.FIELD_VISIT_CREATE))
):
    """Minimal sales rep list for the Log Visit rep picker (no full user:read permission needed)."""
    query = db.query(User).join(User.role).filter(User.role.has(name=Role.SALES_REP.value))
    if search:
        query = query.filter(User.full_name.ilike(f"%{search}%"))
    return query.order_by(User.full_name).all()


@router.post("/", response_model=FieldVisitResponse, status_code=status.HTTP_201_CREATED)
def create_field_visit(
    visit_data: FieldVisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.FIELD_VISIT_CREATE))
):
    """Log a field visit against a customer or a lead."""
    sales_rep_id = visit_data.sales_rep_id
    if sales_rep_id is None:
        if current_user.role_name == Role.SALES_REP.value:
            sales_rep_id = current_user.id
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_rep_id is required")

    visit = FieldVisit(
        **visit_data.model_dump(exclude={"sales_rep_id"}),
        sales_rep_id=sales_rep_id,
        created_by=current_user.id
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return _to_response(visit)


@router.get("/", response_model=List[FieldVisitResponse])
def list_field_visits(
    sales_rep_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.FIELD_VISIT_READ))
):
    """List field visits. Sales reps only ever see their own, regardless of sales_rep_id passed."""
    query = db.query(FieldVisit).options(
        joinedload(FieldVisit.customer), joinedload(FieldVisit.lead)
    )

    if not can_access_all_field_visits(current_user.role_name):
        query = query.filter(FieldVisit.sales_rep_id == current_user.id)
    elif sales_rep_id:
        query = query.filter(FieldVisit.sales_rep_id == sales_rep_id)

    if date_from:
        query = query.filter(FieldVisit.visit_date >= date_from)
    if date_to:
        query = query.filter(FieldVisit.visit_date <= date_to)

    query = query.order_by(FieldVisit.visit_date.desc())
    visits = query.offset(skip).limit(limit).all()
    return [_to_response(v) for v in visits]


@router.get("/{visit_id}", response_model=FieldVisitResponse)
def get_field_visit(
    visit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.FIELD_VISIT_READ))
):
    """Get a single field visit."""
    visit = db.query(FieldVisit).options(
        joinedload(FieldVisit.customer), joinedload(FieldVisit.lead)
    ).filter(FieldVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field visit not found")

    if not can_access_all_field_visits(current_user.role_name) and visit.sales_rep_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return _to_response(visit)


@router.put("/{visit_id}", response_model=FieldVisitResponse)
def update_field_visit(
    visit_id: UUID,
    visit_data: FieldVisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.FIELD_VISIT_CREATE))
):
    """Correct a field visit entry (e.g. fix a mis-keyed time or target)."""
    visit = db.query(FieldVisit).filter(FieldVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field visit not found")

    update_data = visit_data.model_dump(exclude_unset=True)
    customer_id = update_data.get("customer_id", visit.customer_id)
    lead_id = update_data.get("lead_id", visit.lead_id)
    if bool(customer_id) == bool(lead_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of customer_id or lead_id must be set"
        )

    for field, value in update_data.items():
        setattr(visit, field, value)

    visit.updated_by = current_user.id
    visit.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(visit)
    return _to_response(visit)
