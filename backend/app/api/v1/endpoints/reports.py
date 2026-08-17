"""
Territory-scoped sales reports for sales reps and executives.

A sales rep's "book" here is defined by territory, not Order.sales_rep_id:
every quotation/invoice for a customer in a territory assigned to them
counts, regardless of who actually created the underlying order.
"""
import calendar
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.territory import Territory
from app.models.order import Order
from app.models.invoice import Invoice
from app.models.quotation_log import QuotationLog
from app.utils.tax import compute_order_grand_total

router = APIRouter()


class TerritoryBasic(BaseModel):
    id: UUID
    name: str
    city: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MetricSummary(BaseModel):
    count: int
    value: Decimal


class HospitalBreakdown(BaseModel):
    hospital_name: str
    quotations_count: int
    quotations_value: Decimal
    invoices_count: int
    invoices_value: Decimal


class SalesRepSummaryResponse(BaseModel):
    sales_person_id: UUID
    sales_person_name: str
    territories: List[TerritoryBasic]
    period: str
    period_label: str
    period_start: date
    period_end: date
    quotations: MetricSummary
    invoices: MetricSummary
    hospitals: List[HospitalBreakdown]


def _resolve_sales_person(db: Session, current_user: User, sales_person_id: Optional[UUID]) -> User:
    """
    A sales rep may only ever request their own report. An executive must
    pick one — there's no company-wide rollup here, only per-rep.
    """
    if current_user.role_name == "executive":
        if not sales_person_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_person_id is required")
        target_id = sales_person_id
    elif current_user.role_name == "sales_rep":
        if sales_person_id and sales_person_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sales reps can only view their own report")
        target_id = current_user.id
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only sales reps and executives can view this report")

    person = db.query(User).options(joinedload(User.role)).filter(User.id == target_id).first()
    if not person or not person.role or person.role.name != "sales_rep":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales person not found")
    return person


def _period_range(period: str) -> tuple:
    """(start, end, label) for 'month' (calendar month to date) or 'fy' (Apr–Mar)."""
    today = date.today()
    if period == "month":
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = today.replace(day=last_day)
        label = today.strftime("%B %Y")
    elif period == "fy":
        fy_start_year = today.year if today.month >= 4 else today.year - 1
        start = date(fy_start_year, 4, 1)
        end = date(fy_start_year + 1, 3, 31)
        label = f"FY {fy_start_year}-{str(fy_start_year + 1)[-2:]}"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period must be 'month' or 'fy'")
    return start, end, label


def _compute_summary(db: Session, person: User, period: str) -> SalesRepSummaryResponse:
    start, end, label = _period_range(period)

    territories = db.query(Territory).filter(Territory.sales_person_id == person.id).all()
    territory_ids = [t.id for t in territories]

    customer_ids_subq = db.query(Customer.id).filter(Customer.territory_id.in_(territory_ids)).subquery()

    # hospital_name -> running totals, built up as quotations/invoices are found below.
    by_hospital: dict = {}

    def _bucket(hospital_name: str) -> dict:
        return by_hospital.setdefault(
            hospital_name,
            {"quotations_count": 0, "quotations_value": Decimal("0"), "invoices_count": 0, "invoices_value": Decimal("0")},
        )

    quotations_count = 0
    quotations_value = Decimal("0")
    if territory_ids:
        quotation_order_ids = (
            db.query(QuotationLog.order_id)
            .join(Order, Order.id == QuotationLog.order_id)
            .filter(Order.customer_id.in_(db.query(customer_ids_subq)))
            .filter(QuotationLog.created_at >= start)
            .filter(QuotationLog.created_at < date.fromordinal(end.toordinal() + 1))
            .distinct()
            .all()
        )
        order_ids = [r[0] for r in quotation_order_ids]
        if order_ids:
            quotation_orders = (
                db.query(Order)
                .options(joinedload(Order.items), joinedload(Order.customer))
                .filter(Order.id.in_(order_ids))
                .all()
            )
            quotations_count = len(quotation_orders)
            for order in quotation_orders:
                order_value = compute_order_grand_total(order)
                quotations_value += order_value
                hospital_name = order.customer.hospital_name if order.customer else "Unknown"
                bucket = _bucket(hospital_name)
                bucket["quotations_count"] += 1
                bucket["quotations_value"] += order_value

    invoices_count = 0
    invoices_value = Decimal("0")
    if territory_ids:
        invoices = (
            db.query(Invoice)
            .join(Order, Order.id == Invoice.order_id)
            .options(joinedload(Invoice.order).joinedload(Order.customer))
            .filter(Order.customer_id.in_(db.query(customer_ids_subq)))
            .filter(Invoice.invoice_date >= start)
            .filter(Invoice.invoice_date <= end)
            .all()
        )
        invoices_count = len(invoices)
        for invoice in invoices:
            inv_value = Decimal(str(invoice.total_amount))
            invoices_value += inv_value
            hospital_name = invoice.order.customer.hospital_name if invoice.order and invoice.order.customer else "Unknown"
            bucket = _bucket(hospital_name)
            bucket["invoices_count"] += 1
            bucket["invoices_value"] += inv_value

    hospitals = [
        HospitalBreakdown(hospital_name=name, **totals)
        for name, totals in sorted(by_hospital.items())
    ]

    return SalesRepSummaryResponse(
        sales_person_id=person.id,
        sales_person_name=person.full_name,
        territories=[TerritoryBasic.model_validate(t) for t in territories],
        period=period,
        period_label=label,
        period_start=start,
        period_end=end,
        quotations=MetricSummary(count=quotations_count, value=quotations_value),
        invoices=MetricSummary(count=invoices_count, value=invoices_value),
        hospitals=hospitals,
    )


@router.get("/sales-rep-summary", response_model=SalesRepSummaryResponse)
def get_sales_rep_summary(
    period: str = Query(..., description="'month' or 'fy'"),
    sales_person_id: Optional[UUID] = Query(None, description="Required for executives; ignored for sales reps"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = _resolve_sales_person(db, current_user, sales_person_id)
    return _compute_summary(db, person, period)


@router.get("/sales-rep-summary/pdf")
def download_sales_rep_summary_pdf(
    period: str = Query(..., description="'month' or 'fy'"),
    sales_person_id: Optional[UUID] = Query(None, description="Required for executives; ignored for sales reps"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.sales_report_pdf_generator import generate_sales_report_pdf

    person = _resolve_sales_person(db, current_user, sales_person_id)
    summary = _compute_summary(db, person, period)

    pdf_buffer = generate_sales_report_pdf(
        sales_person_name=summary.sales_person_name,
        territory_names=[t.name for t in summary.territories],
        period_label=summary.period_label,
        period_start=summary.period_start,
        period_end=summary.period_end,
        quotations_count=summary.quotations.count,
        quotations_value=summary.quotations.value,
        invoices_count=summary.invoices.count,
        invoices_value=summary.invoices.value,
        hospitals=summary.hospitals,
    )

    filename = f"Sales_Report_{summary.sales_person_name.replace(' ', '_')}_{summary.period}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
