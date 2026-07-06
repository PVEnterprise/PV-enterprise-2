"""
Sales attendance endpoints — tracks present/leave/holiday status per rep per day.
"""
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, field_validator

from app.db.session import get_db
from app.api.deps import PermissionChecker
from app.core.permissions import Permission, can_access_all_field_visits
from app.models.user import User
from app.models.sales_attendance import SalesAttendance


router = APIRouter()

VALID_STATUSES = {"present", "leave", "holiday"}


class AttendanceCreate(BaseModel):
    sales_rep_id: UUID
    attendance_date: date
    status: str
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


class AttendanceResponse(BaseModel):
    id: UUID
    sales_rep_id: UUID
    attendance_date: date
    status: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def upsert_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.ATTENDANCE_CREATE))
):
    """Mark a rep's attendance for a day. Upserts — re-marking the same day updates it."""
    record = db.query(SalesAttendance).filter(
        SalesAttendance.sales_rep_id == data.sales_rep_id,
        SalesAttendance.attendance_date == data.attendance_date
    ).first()

    if record:
        record.status = data.status
        record.notes = data.notes
        record.updated_by = current_user.id
        record.updated_at = datetime.utcnow()
    else:
        record = SalesAttendance(
            sales_rep_id=data.sales_rep_id,
            attendance_date=data.attendance_date,
            status=data.status,
            notes=data.notes,
            created_by=current_user.id
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[AttendanceResponse])
def list_attendance(
    sales_rep_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.ATTENDANCE_READ))
):
    """List attendance records. Sales reps only ever see their own."""
    query = db.query(SalesAttendance)

    if not can_access_all_field_visits(current_user.role_name):
        query = query.filter(SalesAttendance.sales_rep_id == current_user.id)
    elif sales_rep_id:
        query = query.filter(SalesAttendance.sales_rep_id == sales_rep_id)

    if date_from:
        query = query.filter(SalesAttendance.attendance_date >= date_from)
    if date_to:
        query = query.filter(SalesAttendance.attendance_date <= date_to)

    query = query.order_by(SalesAttendance.attendance_date.desc())
    return query.offset(skip).limit(limit).all()
