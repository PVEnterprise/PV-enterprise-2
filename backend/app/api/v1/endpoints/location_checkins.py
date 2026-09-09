"""
API endpoints for employee location check-ins.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime, timedelta

from app.db.session import get_db
from app.models.location_checkin import LocationCheckin
from app.models.user import User
from app.schemas.location_checkin import (
    LocationCheckinCreate,
    LocationCheckinResponse,
    LocationCheckinStatusUpdate,
)
from app.api.deps import get_current_user

router = APIRouter()

# Roles other than sales_rep that are allowed to see every rep's check-ins,
# and to verify/reject one.
MANAGER_ROLES = {"executive", "quoter"}


@router.post("/", response_model=LocationCheckinResponse, status_code=status.HTTP_201_CREATED)
def create_location_checkin(
    checkin_data: LocationCheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record the caller's own location for one of the four scheduled slots."""
    checkin = LocationCheckin(
        user_id=current_user.id,
        slot=checkin_data.slot.value,
        hospital_name=checkin_data.hospital_name,
        recorded_at=checkin_data.recorded_at,
        latitude=checkin_data.latitude,
        longitude=checkin_data.longitude,
        accuracy=checkin_data.accuracy,
    )
    checkin.set_audit_fields(current_user.id, is_create=True)
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


@router.get("/me", response_model=List[LocationCheckinResponse])
def list_my_location_checkins(
    checkin_date: Optional[date] = Query(None, description="Defaults to today"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The caller's own check-ins for a given day (default: today)."""
    day = checkin_date or date.today()
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)

    return (
        db.query(LocationCheckin)
        .filter(
            LocationCheckin.user_id == current_user.id,
            LocationCheckin.recorded_at >= start,
            LocationCheckin.recorded_at < end,
        )
        .order_by(LocationCheckin.recorded_at)
        .all()
    )


@router.get("/", response_model=List[LocationCheckinResponse])
def list_location_checkins(
    user_id: Optional[UUID] = Query(None),
    checkin_date: Optional[date] = Query(None, description="Defaults to today"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Every employee's check-ins for a given day (default: today).

    Restricted to manager roles (executive, quoter) — a sales rep should use
    GET /location-checkins/me instead.
    """
    if current_user.role_name not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives and quoters can view other employees' check-ins",
        )

    day = checkin_date or date.today()
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)

    query = db.query(LocationCheckin).options(joinedload(LocationCheckin.user)).filter(
        LocationCheckin.recorded_at >= start,
        LocationCheckin.recorded_at < end,
    )
    if user_id:
        query = query.filter(LocationCheckin.user_id == user_id)

    return query.order_by(LocationCheckin.user_id, LocationCheckin.recorded_at).all()


@router.patch("/{checkin_id}/status", response_model=LocationCheckinResponse)
def update_location_checkin_status(
    checkin_id: UUID,
    status_data: LocationCheckinStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a check-in verified or rejected. Restricted to manager roles (executive, quoter)."""
    if current_user.role_name not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives and quoters can verify or reject check-ins",
        )

    checkin = (
        db.query(LocationCheckin)
        .options(joinedload(LocationCheckin.user))
        .filter(LocationCheckin.id == checkin_id)
        .first()
    )
    if not checkin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")

    checkin.status = status_data.status.value
    checkin.set_audit_fields(current_user.id, is_create=False)
    db.commit()
    db.refresh(checkin)
    return checkin
