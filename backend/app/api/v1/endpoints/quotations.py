"""
Quotation management endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.quotation import Quotation, QuotationItem
from app.models.order import Order
from app.services.pdf_generator import generate_quotation_pdf
from app.services.estimate_pdf_generator import generate_estimate_pdf


router = APIRouter()


def generate_quote_number(db: Session) -> str:
    """Generate unique quotation number."""
    year = datetime.now().year
    count = db.query(Quotation).filter(Quotation.quote_number.like(f"QUO-{year}-%")).count()
    return f"QUO-{year}-{count + 1:04d}"


class QuotationItemCreate(BaseModel):
    inventory_id: UUID
    description: str
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class QuotationCreate(BaseModel):
    order_id: UUID
    items: List[QuotationItemCreate]
    gst_rate: Decimal = Field(default=18.00, ge=0, le=100)
    discount_percentage: Decimal = Field(default=0.00, ge=0, le=100)
    valid_until: date
    payment_terms: str = "Net 30 days"
    delivery_terms: str = "Ex-warehouse"
    notes: str = None


class QuotationResponse(BaseModel):
    id: UUID
    quote_number: str
    order_id: UUID
    created_by: UUID
    status: str
    subtotal: Decimal
    gst_rate: Decimal
    gst_amount: Decimal
    discount_percentage: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    valid_until: date
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
def create_quotation(
    quotation_data: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.QUOTATION_CREATE))
):
    """Create quotation for an order."""
    order = db.query(Order).filter(Order.id == quotation_data.order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    quotation = Quotation(
        quote_number=generate_quote_number(db),
        order_id=quotation_data.order_id,
        created_by=current_user.id,
        status="draft",
        gst_rate=quotation_data.gst_rate,
        discount_percentage=quotation_data.discount_percentage,
        valid_until=quotation_data.valid_until,
        payment_terms=quotation_data.payment_terms,
        delivery_terms=quotation_data.delivery_terms,
        notes=quotation_data.notes
    )
    db.add(quotation)
    db.flush()
    
    for item_data in quotation_data.items:
        item = QuotationItem(
            quotation_id=quotation.id,
            inventory_id=item_data.inventory_id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            line_total=item_data.quantity * item_data.unit_price
        )
        db.add(item)
    
    db.flush()
    quotation.calculate_totals()
    db.commit()
    db.refresh(quotation)
    
    return quotation


@router.get("/", response_model=List[QuotationResponse])
def list_quotations(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.QUOTATION_READ))
):
    """List all quotations."""
    quotations = db.query(Quotation).order_by(Quotation.created_at.desc()).all()
    return quotations


@router.post("/{quotation_id}/submit", response_model=dict)
def submit_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.QUOTATION_UPDATE))
):
    """Submit quotation for approval."""
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    
    quotation.status = "pending_approval"
    db.commit()
    
    return {"message": "Quotation submitted for approval"}


@router.get("/{quotation_id}/pdf")
def download_quotation_pdf(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.QUOTATION_READ))
):
    """
    Generate and download quotation as PDF in ESTIMATE format.
    Includes company info, customer details, items, and totals.
    """
    # Fetch quotation with all relationships
    quotation = db.query(Quotation).options(
        joinedload(Quotation.order).joinedload(Order.customer),
        joinedload(Quotation.order).joinedload(Order.items).joinedload(Order.items[0].inventory),
        joinedload(Quotation.items).joinedload(QuotationItem.inventory_item)
    ).filter(Quotation.id == quotation_id).first()
    
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found"
        )
    
    # Generate PDF using the new ESTIMATE format
    pdf_buffer = generate_estimate_pdf(quotation.order)
    
    # Return as downloadable file
    filename = f"Estimate_{quotation.quote_number}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
