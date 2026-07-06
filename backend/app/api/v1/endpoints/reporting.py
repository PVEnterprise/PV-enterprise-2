"""
Sales performance reporting endpoints — monthly per-rep detail and
management rollup across all reps/cities. Executive-only for now.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from calendar import monthrange
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel, ConfigDict

from app.db.session import get_db
from app.api.deps import PermissionChecker
from app.core.permissions import Permission, Role
from app.core.order_stages import PENDING_WORKFLOW_STAGES
from app.models.user import User
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.dispatch import DispatchItem
from app.models.field_visit import FieldVisit
from app.models.sales_attendance import SalesAttendance


router = APIRouter()


def _month_bounds(month: int, year: int) -> tuple[date, date]:
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


class OrderSummaryItem(BaseModel):
    order_number: str
    customer_name: str
    workflow_stage: str
    created_at: datetime
    po_amount: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class RepSummaryResponse(BaseModel):
    sales_rep_id: UUID
    sales_rep_name: str
    city: Optional[str] = None
    month: int
    year: int
    visit_count: int
    leave_days: int
    holiday_days: int
    orders_created: int
    orders_by_stage: dict
    orders: List[OrderSummaryItem]


class RepRollupItem(BaseModel):
    sales_rep_id: UUID
    sales_rep_name: str
    city: Optional[str] = None
    visit_count: int
    leave_days: int
    orders_created: int
    orders_completed: int
    pending_order_value: float


class CityRollupItem(BaseModel):
    city: str
    total_visits: int
    total_reps: int
    total_orders: int


class ManagementSummaryResponse(BaseModel):
    month: int
    year: int
    reps: List[RepRollupItem]
    by_city: List[CityRollupItem]


@router.get("/rep-summary", response_model=RepSummaryResponse)
def get_rep_summary(
    sales_rep_id: UUID = Query(..., description="Sales rep to summarize"),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: datetime.now().year),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.REPORTING_VIEW))
):
    """Monthly detail for a single sales rep: visits, leave/holiday days, and orders."""
    rep = db.query(User).filter(User.id == sales_rep_id).first()
    if not rep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales rep not found")

    month_start, month_end = _month_bounds(month, year)

    visit_count = db.query(func.count(FieldVisit.id)).filter(
        FieldVisit.sales_rep_id == sales_rep_id,
        FieldVisit.visit_date >= month_start,
        FieldVisit.visit_date <= month_end
    ).scalar() or 0

    attendance_counts = dict(db.query(
        SalesAttendance.status, func.count(SalesAttendance.id)
    ).filter(
        SalesAttendance.sales_rep_id == sales_rep_id,
        SalesAttendance.attendance_date >= month_start,
        SalesAttendance.attendance_date <= month_end
    ).group_by(SalesAttendance.status).all())

    orders_query = db.query(Order).options(joinedload(Order.customer)).filter(
        Order.sales_rep_id == sales_rep_id,
        Order.created_at >= month_start,
        Order.created_at <= month_end
    )
    orders = orders_query.order_by(Order.created_at.desc()).limit(50).all()

    orders_by_stage = dict(db.query(
        Order.workflow_stage, func.count(Order.id)
    ).filter(
        Order.sales_rep_id == sales_rep_id,
        Order.created_at >= month_start,
        Order.created_at <= month_end
    ).group_by(Order.workflow_stage).all())

    return RepSummaryResponse(
        sales_rep_id=rep.id,
        sales_rep_name=rep.full_name,
        city=rep.city,
        month=month,
        year=year,
        visit_count=visit_count,
        leave_days=attendance_counts.get("leave", 0),
        holiday_days=attendance_counts.get("holiday", 0),
        orders_created=orders_query.count(),
        orders_by_stage=orders_by_stage,
        orders=[
            OrderSummaryItem(
                order_number=o.order_number,
                customer_name=o.customer.hospital_name if o.customer else "",
                workflow_stage=o.workflow_stage,
                created_at=o.created_at,
                po_amount=o.po_amount,
            )
            for o in orders
        ],
    )


@router.get("/management-summary", response_model=ManagementSummaryResponse)
def get_management_summary(
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: datetime.now().year),
    city: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.REPORTING_VIEW))
):
    """Monthly rollup across all sales reps, for the management dashboard."""
    month_start, month_end = _month_bounds(month, year)

    reps_query = db.query(User).join(User.role).filter(User.role.has(name=Role.SALES_REP.value))
    if city:
        reps_query = reps_query.filter(User.city == city)
    reps = reps_query.all()

    _dispatched_subq = db.query(
        DispatchItem.order_item_id,
        func.sum(DispatchItem.quantity).label('dispatched_qty')
    ).group_by(DispatchItem.order_item_id).subquery()

    rep_rollup: List[RepRollupItem] = []
    for rep in reps:
        visit_count = db.query(func.count(FieldVisit.id)).filter(
            FieldVisit.sales_rep_id == rep.id,
            FieldVisit.visit_date >= month_start,
            FieldVisit.visit_date <= month_end
        ).scalar() or 0

        leave_days = db.query(func.count(SalesAttendance.id)).filter(
            SalesAttendance.sales_rep_id == rep.id,
            SalesAttendance.status == "leave",
            SalesAttendance.attendance_date >= month_start,
            SalesAttendance.attendance_date <= month_end
        ).scalar() or 0

        orders_created = db.query(func.count(Order.id)).filter(
            Order.sales_rep_id == rep.id,
            Order.created_at >= month_start,
            Order.created_at <= month_end
        ).scalar() or 0

        orders_completed = db.query(func.count(Order.id)).filter(
            Order.sales_rep_id == rep.id,
            Order.workflow_stage == "completed",
            Order.created_at >= month_start,
            Order.created_at <= month_end
        ).scalar() or 0

        pending_value = db.query(
            func.sum(
                (OrderItem.quantity - func.coalesce(_dispatched_subq.c.dispatched_qty, 0))
                * OrderItem.unit_price
                * (1 - func.coalesce(Order.discount_percentage, 0) / 100)
                * (1 + func.coalesce(OrderItem.gst_percentage, 0) / 100)
            )
        ).join(Order, Order.id == OrderItem.order_id
        ).outerjoin(_dispatched_subq, _dispatched_subq.c.order_item_id == OrderItem.id
        ).filter(
            Order.sales_rep_id == rep.id,
            Order.workflow_stage.in_(PENDING_WORKFLOW_STAGES),
            OrderItem.unit_price.isnot(None),
            OrderItem.inventory_id.isnot(None)
        ).scalar() or 0

        rep_rollup.append(RepRollupItem(
            sales_rep_id=rep.id,
            sales_rep_name=rep.full_name,
            city=rep.city,
            visit_count=visit_count,
            leave_days=leave_days,
            orders_created=orders_created,
            orders_completed=orders_completed,
            pending_order_value=float(pending_value),
        ))

    by_city: dict = {}
    for item in rep_rollup:
        key = item.city or "Unassigned"
        bucket = by_city.setdefault(key, {"total_visits": 0, "total_reps": 0, "total_orders": 0})
        bucket["total_visits"] += item.visit_count
        bucket["total_reps"] += 1
        bucket["total_orders"] += item.orders_created

    city_rollup = [
        CityRollupItem(city=c, **v) for c, v in sorted(by_city.items())
    ]

    rep_rollup.sort(key=lambda r: r.visit_count, reverse=True)

    return ManagementSummaryResponse(
        month=month,
        year=year,
        reps=rep_rollup,
        by_city=city_rollup,
    )
