"""
API endpoints for dispatch management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID
from datetime import datetime, date

from app.db.session import get_db
from app.models.dispatch import Dispatch, DispatchItem
from app.models.order import Order, OrderItem
from app.models.inventory import Inventory
from app.models.user import User
from app.schemas.dispatch import DispatchCreate, DispatchResponse
from app.api.deps import get_current_user

router = APIRouter()


def generate_dispatch_number(db: Session) -> str:
    """Generate unique dispatch number."""
    today = date.today()
    prefix = f"DISP-{today.year}-"
    
    # Get count of dispatches created today
    count = db.query(Dispatch).filter(
        Dispatch.dispatch_number.like(f"{prefix}%")
    ).count()
    
    return f"{prefix}{count + 1:04d}"


@router.post("/", response_model=DispatchResponse, status_code=status.HTTP_201_CREATED)
def create_dispatch(
    dispatch_data: DispatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new dispatch for an order.
    Available for inventory_admin and executive roles.
    """
    # Check role
    if current_user.role.name not in ['inventory_admin', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only inventory admins and executives can create dispatches"
        )
    
    # Verify order exists and is in inventory_check stage
    order = db.query(Order).filter(Order.id == dispatch_data.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.workflow_stage != "inventory_check":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be in inventory_check stage to create dispatch"
        )
    
    # Validate each dispatch item
    for item_data in dispatch_data.items:
        # Check order item exists
        order_item = db.query(OrderItem).filter(
            OrderItem.id == item_data.order_item_id,
            OrderItem.order_id == dispatch_data.order_id
        ).first()
        
        if not order_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order item {item_data.order_item_id} not found"
            )
        
        # Calculate outstanding quantity
        dispatched_qty = sum(di.quantity for di in order_item.dispatch_items)
        outstanding_qty = order_item.quantity - dispatched_qty
        
        if item_data.quantity > outstanding_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dispatch quantity ({item_data.quantity}) exceeds outstanding quantity ({outstanding_qty}) for item {order_item.item_description}"
            )
        
        # Check inventory stock
        inventory = db.query(Inventory).filter(Inventory.id == item_data.inventory_id).first()
        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item {item_data.inventory_id} not found"
            )
        
        # Check against total stock quantity (we'll update reserved during dispatch)
        if item_data.quantity > inventory.stock_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {inventory.item_name}. Available: {inventory.stock_quantity}, Requested: {item_data.quantity}"
            )
    
    # Create dispatch
    dispatch = Dispatch(
        dispatch_number=generate_dispatch_number(db),
        order_id=dispatch_data.order_id,
        invoice_id=dispatch_data.invoice_id,
        dispatch_date=dispatch_data.dispatch_date,
        courier_name=dispatch_data.courier_name,
        tracking_number=dispatch_data.tracking_number,
        status=dispatch_data.status,
        notes=dispatch_data.notes,
        created_by=current_user.id
    )
    db.add(dispatch)
    db.flush()  # Get dispatch ID
    
    # Create dispatch items and update inventory
    for item_data in dispatch_data.items:
        dispatch_item = DispatchItem(
            dispatch_id=dispatch.id,
            order_item_id=item_data.order_item_id,
            inventory_id=item_data.inventory_id,
            quantity=item_data.quantity
        )
        db.add(dispatch_item)
        
        # Update inventory - reduce stock quantity when dispatched
        inventory = db.query(Inventory).filter(Inventory.id == item_data.inventory_id).first()
        inventory.stock_quantity -= item_data.quantity
        
        # Update OrderItem status based on dispatch
        order_item = db.query(OrderItem).filter(OrderItem.id == item_data.order_item_id).first()
        total_dispatched = sum(di.quantity for di in order_item.dispatch_items) + item_data.quantity
        
        if total_dispatched >= order_item.quantity:
            order_item.status = "completed"
        elif total_dispatched > 0:
            order_item.status = "partial"
        else:
            order_item.status = "pending"
    
    # Update overall order status based on all items
    all_order_items = db.query(OrderItem).filter(OrderItem.order_id == dispatch_data.order_id).all()
    all_completed = all(item.status == "completed" for item in all_order_items)
    any_partial = any(item.status in ["partial", "completed"] for item in all_order_items)
    
    if all_completed:
        order.status = "completed"
    elif any_partial:
        order.status = "partially_dispatched"
    
    db.commit()
    db.refresh(dispatch)
    
    # Load relationships including inventory items
    dispatch = db.query(Dispatch).options(
        joinedload(Dispatch.items).joinedload(DispatchItem.inventory_item)
    ).filter(Dispatch.id == dispatch.id).first()
    
    return dispatch


@router.get("/{dispatch_id}", response_model=DispatchResponse)
def get_dispatch(
    dispatch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dispatch details."""
    dispatch = db.query(Dispatch).options(
        joinedload(Dispatch.items).joinedload(DispatchItem.inventory_item)
    ).filter(Dispatch.id == dispatch_id).first()
    
    if not dispatch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispatch not found"
        )
    
    return dispatch


@router.get("/order/{order_id}", response_model=List[DispatchResponse])
def get_order_dispatches(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all dispatches for an order."""
    dispatches = db.query(Dispatch).options(
        joinedload(Dispatch.items).joinedload(DispatchItem.inventory_item)
    ).filter(Dispatch.order_id == order_id).order_by(Dispatch.created_at.desc()).all()
    
    return dispatches
