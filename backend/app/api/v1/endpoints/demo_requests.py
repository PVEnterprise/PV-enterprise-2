"""
API endpoints for demo request management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.db.session import get_db
from app.models.demo_request import DemoRequest
from app.models.demo_item import DemoItem
from app.models.customer import Customer
from app.models.user import User
from app.models.inventory import Inventory
from app.schemas.demo_request import (
    DemoRequestCreate,
    DemoRequestUpdate,
    DemoRequestResponse
)
from app.api.deps import get_current_user
from app.core.permissions import Permission, require_permission
from app.services.demo_challan_generator import generate_demo_challan_pdf

router = APIRouter()


def generate_demo_number(db: Session) -> str:
    """Generate unique demo request number with auto-increment logic."""
    today = date.today()
    prefix = f"DEMO-{today.year}-"
    
    # Get the last demo request number for this year
    last_demo = db.query(DemoRequest).filter(
        DemoRequest.number.like(f"{prefix}%")
    ).order_by(DemoRequest.number.desc()).first()
    
    if last_demo:
        # Extract the number part and increment
        try:
            last_num = int(last_demo.number.split('-')[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1
    
    # Keep trying until we find a unique number (collision avoidance)
    while True:
        number = f"{prefix}{next_num:04d}"
        existing = db.query(DemoRequest).filter(DemoRequest.number == number).first()
        if not existing:
            return number
        next_num += 1


@router.post("/", response_model=DemoRequestResponse, status_code=status.HTTP_201_CREATED)
def create_demo_request(
    demo_data: DemoRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new demo request.
    Available for inventory_admin and executive roles.
    """
    # Check permission
    require_permission(current_user.role_name, Permission.INVENTORY_CREATE)
    
    # Verify hospital exists if provided
    if demo_data.hospital_id:
        hospital = db.query(Customer).filter(Customer.id == demo_data.hospital_id).first()
        if not hospital:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hospital not found"
            )
    
    # Generate unique demo number
    demo_number = generate_demo_number(db)
    
    # Create demo request
    demo_request = DemoRequest(
        number=demo_number,
        hospital_id=demo_data.hospital_id,
        city=demo_data.city,
        state=demo_data.state.value,
        notes=demo_data.notes,
        created_by=current_user.id
    )
    
    db.add(demo_request)
    db.commit()
    db.refresh(demo_request)
    
    # Load relationships
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator)
    ).filter(DemoRequest.id == demo_request.id).first()
    
    return demo_request


@router.get("/", response_model=List[DemoRequestResponse])
def list_demo_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    state: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List demo requests with filtering and search.
    """
    # Check permission
    require_permission(current_user.role_name, Permission.INVENTORY_READ)
    
    query = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator)
    )
    
    # Apply filters
    if state:
        query = query.filter(DemoRequest.state == state)
    
    if search:
        search_term = f"%{search}%"
        query = query.join(Customer).filter(
            (DemoRequest.number.ilike(search_term)) |
            (Customer.hospital_name.ilike(search_term)) |
            (DemoRequest.city.ilike(search_term))
        )
    
    # Order by created date (newest first)
    query = query.order_by(DemoRequest.created_at.desc())
    
    # Pagination
    demo_requests = query.offset(skip).limit(limit).all()
    
    return demo_requests


@router.get("/{demo_id}", response_model=DemoRequestResponse)
def get_demo_request(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get demo request details.
    """
    # Check permission
    require_permission(current_user.role_name, Permission.INVENTORY_READ)
    
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator),
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    return demo_request


@router.put("/{demo_id}", response_model=DemoRequestResponse)
def update_demo_request(
    demo_id: UUID,
    demo_data: DemoRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update demo request details.
    """
    # Check permission
    require_permission(current_user.role_name, Permission.INVENTORY_UPDATE)
    
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    # Verify hospital if being updated and provided
    if demo_data.hospital_id is not None:
        hospital = db.query(Customer).filter(Customer.id == demo_data.hospital_id).first()
        if not hospital:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hospital not found"
            )
    
    # Update fields
    update_data = demo_data.model_dump(exclude_unset=True)
    if 'state' in update_data and update_data['state']:
        update_data['state'] = update_data['state'].value
    
    for field, value in update_data.items():
        setattr(demo_request, field, value)
    
    db.commit()
    db.refresh(demo_request)
    
    # Load relationships
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator)
    ).filter(DemoRequest.id == demo_request.id).first()
    
    return demo_request


@router.delete("/{demo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_demo_request(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete demo request.
    """
    # Check permission
    require_permission(current_user.role_name, Permission.INVENTORY_DELETE)
    
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    db.delete(demo_request)
    db.commit()
    
    return None


@router.post("/{demo_id}/submit", response_model=DemoRequestResponse)
def submit_demo_request(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit demo request for approval.
    Only allowed when state is 'requested' and has at least one item.
    """
    # Check permission - inventory admin can submit
    require_permission(current_user.role_name, Permission.INVENTORY_UPDATE)
    
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.items)
    ).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request can only be submitted when in 'requested' state"
        )
    
    if not demo_request.items or len(demo_request.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request must have at least one item before submitting"
        )
    
    demo_request.state = "submitted"
    db.commit()
    
    # Load relationships for response
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator),
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    return demo_request


@router.post("/{demo_id}/approve", response_model=DemoRequestResponse)
def approve_demo_request(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve demo request.
    Only executives can approve. Only allowed when state is 'submitted'.
    """
    # Check if user is executive
    if current_user.role_name not in ["executive", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives can approve demo requests"
        )
    
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request can only be approved when in 'submitted' state"
        )
    
    demo_request.state = "approved"
    db.commit()
    
    # Load relationships for response
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator),
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    return demo_request


@router.post("/{demo_id}/reject", response_model=DemoRequestResponse)
def reject_demo_request(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject demo request.
    Only executives can reject. Only allowed when state is 'submitted'.
    Moves back to 'requested' state.
    """
    # Check if user is executive
    if current_user.role_name not in ["executive", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives can reject demo requests"
        )
    
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request can only be rejected when in 'submitted' state"
        )
    
    demo_request.state = "requested"
    db.commit()
    
    # Load relationships for response
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator),
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    return demo_request


@router.post("/{demo_id}/dispatch", response_model=DemoRequestResponse)
def dispatch_demo_request(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dispatch demo request.
    Only inventory admin can dispatch. Only allowed when state is 'approved'.
    Subtracts demo item quantities from inventory stock.
    """
    # Check permission - inventory admin can dispatch
    require_permission(current_user.role_name, Permission.INVENTORY_UPDATE)
    
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request can only be dispatched when in 'approved' state"
        )
    
    # Subtract quantities from inventory stock
    for item in demo_request.items:
        inventory_item = db.query(Inventory).filter(Inventory.id == item.inventory_item_id).first()
        if inventory_item:
            if inventory_item.stock_quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {inventory_item.sku}. Available: {inventory_item.stock_quantity}, Required: {item.quantity}"
                )
            inventory_item.stock_quantity -= item.quantity
    
    demo_request.state = "dispatched"
    db.commit()
    
    # Load relationships for response
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator),
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    return demo_request


@router.post("/{demo_id}/receive", response_model=DemoRequestResponse)
def receive_demo_request(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark demo items as received.
    Only inventory admin can receive. Only allowed when state is 'dispatched'.
    Adds demo item quantities back to inventory stock.
    """
    # Check permission - inventory admin can receive
    require_permission(current_user.role_name, Permission.INVENTORY_UPDATE)
    
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "dispatched":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request can only be received when in 'dispatched' state"
        )
    
    # Add quantities back to inventory stock
    for item in demo_request.items:
        inventory_item = db.query(Inventory).filter(Inventory.id == item.inventory_item_id).first()
        if inventory_item:
            inventory_item.stock_quantity += item.quantity
    
    demo_request.state = "complete"
    db.commit()
    
    # Load relationships for response
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator),
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    return demo_request


@router.get("/{demo_id}/challan")
def download_demo_challan(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download demo challan PDF.
    Only available when demo request is dispatched or later.
    """
    # Check permission
    require_permission(current_user.role_name, Permission.INVENTORY_READ)
    
    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator),
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()
    
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state not in ["dispatched", "complete"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo challan is only available for dispatched or complete demo requests"
        )
    
    if not demo_request.items or len(demo_request.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request has no items"
        )
    
    # Generate PDF
    pdf_buffer = generate_demo_challan_pdf(demo_request)
    
    # Return as streaming response
    filename = f"Demo_Challan_{demo_request.number}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
