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
from app.models.dispatch import Dispatch, DispatchItem
from app.models.quotation_log import QuotationLog
from app.models.location_checkin import LocationCheckin
from app.utils.tax import compute_order_grand_total

router = APIRouter()

# workflow_stage values reached only once a quotation has actually been sent
# to the customer (see orders.py: workflow_stage moves to
# waiting_purchase_order together with status="quote_sent", both in the
# normal approval flow and in the executive's direct-quotation flow).
PASSED_QUOTATION_STAGES = {
    "waiting_purchase_order",
    "po_approval",
    "inventory_check",
    "payment_pending",
    "completed",
}


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


class HospitalVisits(BaseModel):
    hospital_name: str
    visits: int


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
    # Verified location check-ins (see LocationCheckin.status) in this period.
    # A "visit" is one calendar day with at least one verified check-in at
    # that hospital — same-day repeats don't inflate the count.
    territory_visits: List[HospitalVisits]  # every hospital in the rep's territory, including zero-visit ones
    other_visits: List[HospitalVisits]  # hospital names the rep typed via "Other", not in any territory


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


def _compute_visits(
    db: Session, person: User, territory_ids: List[UUID], start: date, end: date
) -> tuple:
    """
    (territory_visits, other_visits) — a "visit" is one calendar day with at
    least one verified check-in at that hospital name; repeats the same day
    don't add another visit. Matching is by exact hospital_name string,
    which is how the sales PWA's hospital picker stores it either way (the
    customer's own hospital_name when picked from the territory list, or
    whatever the rep typed under "Other").
    """
    territory_hospital_names = {
        name
        for (name,) in db.query(Customer.hospital_name).filter(Customer.territory_id.in_(territory_ids)).all()
    } if territory_ids else set()

    end_exclusive = date.fromordinal(end.toordinal() + 1)
    checkins = (
        db.query(LocationCheckin)
        .filter(
            LocationCheckin.user_id == person.id,
            LocationCheckin.status == "verified",
            LocationCheckin.recorded_at >= start,
            LocationCheckin.recorded_at < end_exclusive,
        )
        .all()
    )

    visit_days: dict = {}
    for checkin in checkins:
        visit_days.setdefault(checkin.hospital_name, set()).add(checkin.recorded_at.date())

    territory_visits = [
        HospitalVisits(hospital_name=name, visits=len(visit_days.get(name, set())))
        for name in sorted(territory_hospital_names)
    ]
    other_visits = [
        HospitalVisits(hospital_name=name, visits=len(days))
        for name, days in sorted(visit_days.items())
        if name not in territory_hospital_names
    ]
    return territory_visits, other_visits


def _dispatch_invoice_value(dispatch: Dispatch, order: Order) -> Decimal:
    """
    Stand-in invoice value for a dispatch with no linked Invoice record yet —
    the same per-item calculation the invoice PDF itself uses in that case
    (see dispatches.py's TempInvoice): qty * (unit_price - order discount%),
    plus that item's own GST%.
    """
    discount_percentage = Decimal(str(getattr(order, "discount_percentage", 0) or 0))
    subtotal = Decimal("0")
    total_gst = Decimal("0")
    for dispatch_item in dispatch.items:
        order_item = dispatch_item.order_item
        if not order_item:
            continue
        qty = Decimal(str(dispatch_item.quantity))
        rate = Decimal(str(order_item.unit_price or 0))
        discounted_rate = rate - (rate * discount_percentage / 100)
        amount = qty * discounted_rate
        gst_pct = Decimal(str(order_item.gst_percentage or 0))
        total_gst += amount * gst_pct / 100
        subtotal += amount
    return subtotal + total_gst


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

    # --- Invoices: a dispatch being created counts as an invoice being generated —
    # its own linked Invoice's value is used when one exists (an executive/quoter
    # created one properly), otherwise the same item-level calculation the invoice
    # PDF itself falls back to (see dispatches.py's TempInvoice). A real Invoice
    # with no dispatch at all (e.g. a service invoice) still counts on its own,
    # by its invoice_date, computed first so a same-month invoice can also count
    # toward quotations below.
    invoices_count = 0
    invoices_value = Decimal("0")
    invoiced_order_ids: dict = {}  # order_id -> Order, for the quotations fallback below
    counted_invoice_ids: set = set()

    if territory_ids:
        dispatches = (
            db.query(Dispatch)
            .join(Order, Order.id == Dispatch.order_id)
            .options(
                joinedload(Dispatch.items).joinedload(DispatchItem.order_item),
                joinedload(Dispatch.order).joinedload(Order.customer),
            )
            .filter(Order.customer_id.in_(db.query(customer_ids_subq)))
            .filter(Dispatch.dispatch_date >= start)
            .filter(Dispatch.dispatch_date <= end)
            .all()
        )
        for dispatch in dispatches:
            order = dispatch.order
            hospital_name = order.customer.hospital_name if order and order.customer else "Unknown"

            if dispatch.invoice_id:
                invoice = db.query(Invoice).filter(Invoice.id == dispatch.invoice_id).first()
                inv_value = Decimal(str(invoice.total_amount)) if invoice else Decimal("0")
                if invoice:
                    counted_invoice_ids.add(invoice.id)
            else:
                inv_value = _dispatch_invoice_value(dispatch, order) if order else Decimal("0")

            invoices_count += 1
            invoices_value += inv_value
            bucket = _bucket(hospital_name)
            bucket["invoices_count"] += 1
            bucket["invoices_value"] += inv_value
            if order:
                invoiced_order_ids[order.id] = order

        orphan_invoices = (
            db.query(Invoice)
            .join(Order, Order.id == Invoice.order_id)
            .options(joinedload(Invoice.order).joinedload(Order.customer))
            .filter(Order.customer_id.in_(db.query(customer_ids_subq)))
            .filter(Invoice.invoice_date >= start)
            .filter(Invoice.invoice_date <= end)
            .filter(~Invoice.id.in_(counted_invoice_ids))
            .all()
        )
        for invoice in orphan_invoices:
            inv_value = Decimal(str(invoice.total_amount))
            invoices_count += 1
            invoices_value += inv_value
            hospital_name = invoice.order.customer.hospital_name if invoice.order and invoice.order.customer else "Unknown"
            bucket = _bucket(hospital_name)
            bucket["invoices_count"] += 1
            bucket["invoices_value"] += inv_value
            if invoice.order:
                invoiced_order_ids[invoice.order.id] = invoice.order

    # --- Quotations: an order counts if any of the following happened this period —
    # (1) a QuotationLog entry was created (the normal "quotation generated" signal),
    # (2) it has passed the quotation stage and its quotation_date falls in the period
    #     (catches orders whose QuotationLog is missing or dated outside the period), or
    # (3) it was invoiced this period — an invoice can't exist without a quotation,
    #     so an invoiced order always counts as quoted too, regardless of when the
    #     quotation itself happened.
    # Each qualifying order counts once even if it matches more than one of these.
    quotations_count = 0
    quotations_value = Decimal("0")
    if territory_ids:
        quoted_orders: dict = {}

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
            for order in (
                db.query(Order)
                .options(joinedload(Order.items), joinedload(Order.customer))
                .filter(Order.id.in_(order_ids))
                .all()
            ):
                quoted_orders[order.id] = order

        for order in (
            db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.customer))
            .filter(Order.customer_id.in_(db.query(customer_ids_subq)))
            .filter(Order.workflow_stage.in_(PASSED_QUOTATION_STAGES))
            .filter(Order.quotation_date >= start)
            .filter(Order.quotation_date <= end)
            .all()
        ):
            quoted_orders[order.id] = order

        for order in invoiced_order_ids.values():
            quoted_orders[order.id] = order

        quotations_count = len(quoted_orders)
        for order in quoted_orders.values():
            order_value = compute_order_grand_total(order)
            quotations_value += order_value
            hospital_name = order.customer.hospital_name if order.customer else "Unknown"
            bucket = _bucket(hospital_name)
            bucket["quotations_count"] += 1
            bucket["quotations_value"] += order_value

    hospitals = [
        HospitalBreakdown(hospital_name=name, **totals)
        for name, totals in sorted(by_hospital.items())
    ]

    territory_visits, other_visits = _compute_visits(db, person, territory_ids, start, end)

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
        territory_visits=territory_visits,
        other_visits=other_visits,
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
        territory_visits=summary.territory_visits,
        other_visits=summary.other_visits,
    )

    filename = f"Sales_Report_{summary.sales_person_name.replace(' ', '_')}_{summary.period}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
