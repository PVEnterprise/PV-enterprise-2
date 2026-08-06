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
from app.models.order import Order, OrderItem
from app.schemas.demo_request import (
    DemoRequestCreate,
    DemoRequestUpdate,
    DemoRequestResponse
)
from app.schemas.order import OrderResponse
from app.api.deps import get_current_user
from app.core.permissions import Permission, require_permission
from app.services.demo_challan_generator import generate_demo_challan_pdf
from app.api.v1.endpoints.orders import generate_order_number
from app.utils.order_tracking import add_order_action

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

    if demo_data.type.value == "delivery" and not demo_data.hospital_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hospital is required for Delivery type demo requests"
        )

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
        to_address=demo_data.to_address,
        type=demo_data.type.value,
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
    states: Optional[str] = None,
    search: Optional[str] = None,
    catalog_no: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List demo requests with filtering and search.
    - state: single state filter
    - states: comma-separated list of states (e.g. 'requested,dispatched')
    - catalog_no: filter to demos containing an item with this catalog number (partial match)
    """
    # Check permission
    require_permission(current_user.role_name, Permission.INVENTORY_READ)
    
    query = db.query(DemoRequest).options(
        joinedload(DemoRequest.hospital),
        joinedload(DemoRequest.creator)
    )
    
    # Multi-state filter takes priority over single state
    if states:
        state_list = [s.strip() for s in states.split(",") if s.strip()]
        if state_list:
            query = query.filter(DemoRequest.state.in_(state_list))
    elif state:
        query = query.filter(DemoRequest.state == state)
    
    if search:
        search_term = f"%{search}%"
        query = query.join(Customer, Customer.id == DemoRequest.hospital_id).filter(
            (DemoRequest.number.ilike(search_term)) |
            (Customer.hospital_name.ilike(search_term)) |
            (DemoRequest.city.ilike(search_term))
        )
    
    # Filter by catalog number (joins through demo_items -> inventory)
    if catalog_no:
        catalog_term = f"%{catalog_no}%"
        query = (
            query
            .join(DemoItem, DemoItem.demo_request_id == DemoRequest.id)
            .join(Inventory, Inventory.id == DemoItem.inventory_item_id)
            .filter(Inventory.sku.ilike(catalog_term))
            .distinct()
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
    
    update_data = demo_data.model_dump(exclude_unset=True)

    # Verify hospital if being updated and provided
    if update_data.get('hospital_id') is not None:
        hospital = db.query(Customer).filter(Customer.id == update_data['hospital_id']).first()
        if not hospital:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hospital not found"
            )

    # Validate hospital requirement against the resulting (merged) state
    final_type = update_data['type'].value if 'type' in update_data and update_data['type'] else demo_request.type
    final_hospital_id = update_data['hospital_id'] if 'hospital_id' in update_data else demo_request.hospital_id
    if final_type == "delivery" and not final_hospital_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hospital is required for Delivery type demo requests"
        )

    if 'state' in update_data and update_data['state']:
        update_data['state'] = update_data['state'].value
    if 'type' in update_data and update_data['type']:
        update_data['type'] = update_data['type'].value

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


@router.post("/{demo_id}/convert-to-order", response_model=OrderResponse)
def convert_demo_request_to_order(
    demo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Convert a Delivery-type demo request into an Order, landing directly at the
    'quotation' workflow stage with the same items (already decoded, since they're
    known inventory items).
    """
    require_permission(current_user.role_name, Permission.INVENTORY_UPDATE)

    demo_request = db.query(DemoRequest).options(
        joinedload(DemoRequest.items).joinedload(DemoItem.inventory_item)
    ).filter(DemoRequest.id == demo_id).first()

    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )

    if demo_request.type != "delivery":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Delivery type demo requests can be converted to an order"
        )

    if not demo_request.hospital_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request must have a hospital before it can be converted to an order"
        )

    if not demo_request.items or len(demo_request.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request has no items"
        )

    if demo_request.converted_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo request has already been converted to an order"
        )

    order = Order(
        order_number=generate_order_number(db),
        customer_id=demo_request.hospital_id,
        sales_rep_id=current_user.id,
        status="approved",
        workflow_stage="quotation",
        priority="medium",
        source="demo_conversion",
        notes=""
    )
    db.add(order)
    db.flush()  # Get order ID before adding items

    for demo_item in demo_request.items:
        inventory_item = demo_item.inventory_item
        order_item = OrderItem(
            order_id=order.id,
            item_description=inventory_item.description or inventory_item.sku,
            quantity=demo_item.quantity,
            inventory_id=inventory_item.id,
            unit_price=inventory_item.unit_price,
            gst_percentage=inventory_item.tax if inventory_item.tax is not None else 18.00,
            status="decoded",
            decoded_by=current_user.id
        )
        db.add(order_item)

    add_order_action(
        order=order,
        action="Order Created",
        user=current_user,
        details=f"Converted from demo request {demo_request.number}"
    )

    demo_request.converted_order_id = order.id

    db.commit()
    db.refresh(order)

    order = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.items)
    ).filter(Order.id == order.id).first()

    return order
