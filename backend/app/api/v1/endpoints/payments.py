"""
Payments endpoint - Accountant and Executive access.
Record and view customer payments. Show pending payment summaries.
"""
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel as PydanticModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.core.permissions import Permission, has_permission
from app.models.user import User
from app.models.payment import Payment
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.dispatch import Dispatch, DispatchItem
from app.models.inventory import Inventory


router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class PaymentCreate(PydanticModel):
    customer_id: UUID
    amount: Decimal
    order_id: Optional[UUID] = None
    payment_date: date
    notes: Optional[str] = None


class PaymentResponse(PydanticModel):
    id: UUID
    customer_id: UUID
    customer_name: str
    hospital_name: str
    order_id: Optional[UUID]
    order_number: Optional[str]
    amount: Decimal
    payment_date: date
    notes: Optional[str]
    recorded_by: UUID
    recorder_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerPaymentSummary(PydanticModel):
    customer_id: UUID
    customer_name: str
    hospital_name: str
    total_dispatched_value: Decimal
    total_paid: Decimal
    balance_due: Decimal
    dispatch_count: int
    payment_count: int


class PaymentSummary(PydanticModel):
    total_customers_with_balance: int
    total_balance_due: Decimal
    total_paid: Decimal
    total_dispatched_value: Decimal


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_current_fy_dates() -> Tuple[date, date]:
    """Return (fy_start, fy_end) for the current Indian financial year (Apr 1 – Mar 31)."""
    today = date.today()
    if today.month >= 4:
        fy_start = date(today.year, 4, 1)
        fy_end = date(today.year + 1, 3, 31)
    else:
        fy_start = date(today.year - 1, 4, 1)
        fy_end = date(today.year, 3, 31)
    return fy_start, fy_end


def _check_payment_permission(current_user: User):
    if not has_permission(current_user.role_name, Permission.PAYMENT_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accounts module access required"
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record a new payment from a customer."""
    if not has_permission(current_user.role_name, Permission.PAYMENT_CREATE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    
    # Validate customer exists
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    # Validate order if provided
    order = None
    if data.order_id:
        order = db.query(Order).filter(Order.id == data.order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.customer_id != data.customer_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order does not belong to this customer")
    
    payment = Payment(
        customer_id=data.customer_id,
        order_id=data.order_id,
        amount=data.amount,
        payment_date=data.payment_date,
        notes=data.notes,
        recorded_by=current_user.id,
    )
    payment.set_audit_fields(current_user.id, is_create=True)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return _payment_to_response(payment, customer, order, current_user)


@router.get("/", response_model=List[PaymentResponse])
def list_payments(
    customer_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all recorded payments, optionally filtered by customer."""
    _check_payment_permission(current_user)
    
    query = db.query(Payment).options(
        joinedload(Payment.customer),
        joinedload(Payment.order),
        joinedload(Payment.recorder)
    )
    
    if customer_id:
        query = query.filter(Payment.customer_id == customer_id)
    
    payments = query.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).all()
    
    results = []
    for p in payments:
        results.append(PaymentResponse(
            id=p.id,
            customer_id=p.customer_id,
            customer_name=p.customer.name if p.customer else "",
            hospital_name=p.customer.hospital_name if p.customer else "",
            order_id=p.order_id,
            order_number=p.order.order_number if p.order else None,
            amount=p.amount,
            payment_date=p.payment_date,
            notes=p.notes,
            recorded_by=p.recorded_by,
            recorder_name=p.recorder.full_name if p.recorder else "",
            created_at=p.created_at,
        ))
    return results


@router.get("/pending-summary", response_model=List[CustomerPaymentSummary])
def get_pending_payment_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get customers with dispatched items and their all-time payment balance.
    Returns only Pending (paid < dispatched) and Overpaid (paid > dispatched) customers.
    Cleared customers (paid == dispatched) are excluded.
    """
    _check_payment_permission(current_user)

    # Calculate all-time total dispatched value per customer
    dispatched_value_query = db.query(
        Customer.id.label("customer_id"),
        Customer.name.label("customer_name"),
        Customer.hospital_name.label("hospital_name"),
        func.sum(
            DispatchItem.quantity * OrderItem.unit_price
        ).label("total_dispatched_value"),
        func.count(func.distinct(Dispatch.id)).label("dispatch_count"),
    ).select_from(Customer)\
    .join(Order, Order.customer_id == Customer.id)\
    .join(Dispatch, Dispatch.order_id == Order.id)\
    .join(DispatchItem, DispatchItem.dispatch_id == Dispatch.id)\
    .join(OrderItem, DispatchItem.order_item_id == OrderItem.id)\
    .filter(OrderItem.unit_price.isnot(None))\
    .group_by(Customer.id, Customer.name, Customer.hospital_name)\
    .all()

    if not dispatched_value_query:
        return []

    customer_ids = [row.customer_id for row in dispatched_value_query]

    # Calculate all-time total paid per customer
    paid_query = db.query(
        Payment.customer_id,
        func.sum(Payment.amount).label("total_paid"),
        func.count(Payment.id).label("payment_count"),
    ).filter(Payment.customer_id.in_(customer_ids))\
    .group_by(Payment.customer_id)\
    .all()

    paid_map = {row.customer_id: (row.total_paid or Decimal("0"), row.payment_count) for row in paid_query}
    
    results = []
    for row in dispatched_value_query:
        dispatched_val = row.total_dispatched_value or Decimal("0")
        total_paid, payment_count = paid_map.get(row.customer_id, (Decimal("0"), 0))
        balance_due = dispatched_val - total_paid
        # Exclude Cleared customers (paid == dispatched)
        if balance_due == Decimal("0"):
            continue
        results.append(CustomerPaymentSummary(
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            hospital_name=row.hospital_name,
            total_dispatched_value=dispatched_val,
            total_paid=total_paid,
            balance_due=balance_due,
            dispatch_count=row.dispatch_count,
            payment_count=payment_count,
        ))
    
    # Sort: pending (positive balance) first, then overpaid (negative balance)
    results.sort(key=lambda x: x.balance_due, reverse=True)
    return results


@router.get("/summary", response_model=PaymentSummary)
def get_payment_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overall payment summary stats."""
    _check_payment_permission(current_user)
    
    pending = get_pending_payment_summary(db, current_user)
    
    total_dispatched = sum(r.total_dispatched_value for r in pending)
    total_paid = sum(r.total_paid for r in pending)
    total_balance = sum(r.balance_due for r in pending)
    customers_with_balance = sum(1 for r in pending if r.balance_due > 0)
    
    return PaymentSummary(
        total_customers_with_balance=customers_with_balance,
        total_balance_due=total_balance,
        total_paid=total_paid,
        total_dispatched_value=total_dispatched,
    )


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a payment record."""
    if not has_permission(current_user.role_name, Permission.PAYMENT_DELETE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    db.delete(payment)
    db.commit()
    return None


# ── Private helpers ───────────────────────────────────────────────────────────

def _payment_to_response(payment: Payment, customer: Customer, order, recorder: User) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        customer_id=payment.customer_id,
        customer_name=customer.name,
        hospital_name=customer.hospital_name,
        order_id=payment.order_id,
        order_number=order.order_number if order else None,
        amount=payment.amount,
        payment_date=payment.payment_date,
        notes=payment.notes,
        recorded_by=payment.recorded_by,
        recorder_name=recorder.full_name,
        created_at=payment.created_at,
    )
