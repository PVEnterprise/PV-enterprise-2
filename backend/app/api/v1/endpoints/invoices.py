"""
Invoice management endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.invoice import Invoice, InvoiceItem
from app.models.quotation import Quotation


router = APIRouter()


def generate_invoice_number(db: Session) -> str:
    """Generate unique invoice number."""
    year = datetime.now().year
    count = db.query(Invoice).filter(Invoice.invoice_number.like(f"INV-{year}-%")).count()
    return f"INV-{year}-{count + 1:04d}"


class InvoiceItemCreate(BaseModel):
    inventory_id: UUID
    description: str
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class InvoiceCreate(BaseModel):
    quotation_id: UUID
    order_id: UUID
    items: List[InvoiceItemCreate]
    invoice_date: date = Field(default_factory=date.today)
    due_date: date
    payment_terms: str = "Net 30 days"
    notes: str = None


class PaymentRecord(BaseModel):
    amount: Decimal = Field(..., gt=0)


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    order_id: UUID
    quotation_id: UUID
    status: str
    invoice_date: date
    due_date: date
    subtotal: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    payment_status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVOICE_CREATE))
):
    """Create invoice from quotation."""
    quotation = db.query(Quotation).filter(Quotation.id == invoice_data.quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    
    invoice = Invoice(
        invoice_number=generate_invoice_number(db),
        quotation_id=invoice_data.quotation_id,
        order_id=invoice_data.order_id,
        created_by=current_user.id,
        status="draft",
        invoice_date=invoice_data.invoice_date,
        due_date=invoice_data.due_date,
        payment_terms=invoice_data.payment_terms,
        notes=invoice_data.notes,
        gst_amount=quotation.gst_amount
    )
    db.add(invoice)
    db.flush()
    
    for item_data in invoice_data.items:
        item = InvoiceItem(
            invoice_id=invoice.id,
            inventory_id=item_data.inventory_id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            line_total=item_data.quantity * item_data.unit_price
        )
        db.add(item)
    
    db.flush()
    invoice.calculate_totals()
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.get("/", response_model=List[InvoiceResponse])
def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVOICE_READ))
):
    """List all invoices."""
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return invoices


@router.post("/{invoice_id}/payment", response_model=InvoiceResponse)
def record_payment(
    invoice_id: UUID,
    payment: PaymentRecord,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVOICE_UPDATE))
):
    """Record payment for invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    invoice.paid_amount += payment.amount
    invoice.update_payment_status()
    db.commit()
    db.refresh(invoice)
    
    return invoice
