"""
Demo Items API endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import User, DemoRequest, DemoItem, Inventory
from app.schemas.demo_item import (
    DemoItemCreate,
    DemoItemUpdate,
    DemoItemResponse,
    DemoItemBulkCreate,
)

router = APIRouter()


def get_demo_item_response(item: DemoItem) -> dict:
    """Convert DemoItem to response dict with inventory info."""
    return {
        "id": item.id,
        "demo_request_id": item.demo_request_id,
        "inventory_item_id": item.inventory_item_id,
        "quantity": item.quantity,
        "inventory_item": {
            "id": item.inventory_item.id,
            "sku": item.inventory_item.sku,
            "description": item.inventory_item.description,
            "stock_quantity": item.inventory_item.stock_quantity,
        },
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("/{demo_request_id}/items", response_model=List[DemoItemResponse])
def get_demo_items(
    demo_request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all items for a demo request."""
    # Verify demo request exists
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_request_id).first()
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    items = db.query(DemoItem).filter(
        DemoItem.demo_request_id == demo_request_id
    ).all()
    
    return [get_demo_item_response(item) for item in items]


@router.post("/{demo_request_id}/items", response_model=DemoItemResponse, status_code=status.HTTP_201_CREATED)
def add_demo_item(
    demo_request_id: UUID,
    item_data: DemoItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an item to a demo request."""
    # Verify demo request exists and is in 'requested' state
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_request_id).first()
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add items to demo requests in 'requested' state"
        )
    
    # Verify inventory item exists
    inventory_item = db.query(Inventory).filter(
        Inventory.id == item_data.inventory_item_id
    ).first()
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Check if quantity is available
    if item_data.quantity > inventory_item.stock_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested quantity ({item_data.quantity}) exceeds available stock ({inventory_item.stock_quantity})"
        )
    
    # Check if item already exists in this demo request
    existing_item = db.query(DemoItem).filter(
        DemoItem.demo_request_id == demo_request_id,
        DemoItem.inventory_item_id == item_data.inventory_item_id
    ).first()
    
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This item is already in the demo request. Update the quantity instead."
        )
    
    # Create demo item
    demo_item = DemoItem(
        demo_request_id=demo_request_id,
        inventory_item_id=item_data.inventory_item_id,
        quantity=item_data.quantity,
    )
    db.add(demo_item)
    db.commit()
    db.refresh(demo_item)
    
    return get_demo_item_response(demo_item)


@router.put("/{demo_request_id}/items/{item_id}", response_model=DemoItemResponse)
def update_demo_item(
    demo_request_id: UUID,
    item_id: UUID,
    item_data: DemoItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a demo item quantity."""
    # Verify demo request exists and is in 'requested' state
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_request_id).first()
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only modify items in demo requests in 'requested' state"
        )
    
    # Get demo item
    demo_item = db.query(DemoItem).filter(
        DemoItem.id == item_id,
        DemoItem.demo_request_id == demo_request_id
    ).first()
    
    if not demo_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo item not found"
        )
    
    # Check if new quantity is available
    if item_data.quantity is not None:
        inventory_item = demo_item.inventory_item
        if item_data.quantity > inventory_item.stock_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested quantity ({item_data.quantity}) exceeds available stock ({inventory_item.stock_quantity})"
            )
        demo_item.quantity = item_data.quantity
    
    db.commit()
    db.refresh(demo_item)
    
    return get_demo_item_response(demo_item)


@router.delete("/{demo_request_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_demo_item(
    demo_request_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an item from a demo request."""
    # Verify demo request exists and is in 'requested' state
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_request_id).first()
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only remove items from demo requests in 'requested' state"
        )
    
    # Get demo item
    demo_item = db.query(DemoItem).filter(
        DemoItem.id == item_id,
        DemoItem.demo_request_id == demo_request_id
    ).first()
    
    if not demo_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo item not found"
        )
    
    db.delete(demo_item)
    db.commit()
    
    return None


@router.post("/{demo_request_id}/items/bulk", response_model=List[DemoItemResponse], status_code=status.HTTP_201_CREATED)
def add_demo_items_bulk(
    demo_request_id: UUID,
    bulk_data: DemoItemBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add multiple items to a demo request at once."""
    # Verify demo request exists and is in 'requested' state
    demo_request = db.query(DemoRequest).filter(DemoRequest.id == demo_request_id).first()
    if not demo_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo request not found"
        )
    
    if demo_request.state != "requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add items to demo requests in 'requested' state"
        )
    
    created_items = []
    errors = []
    
    for idx, item_data in enumerate(bulk_data.items):
        # Verify inventory item exists
        inventory_item = db.query(Inventory).filter(
            Inventory.id == item_data.inventory_item_id
        ).first()
        
        if not inventory_item:
            errors.append(f"Item {idx + 1}: Inventory item not found")
            continue
        
        # Check if quantity is available
        if item_data.quantity > inventory_item.stock_quantity:
            errors.append(
                f"Item {idx + 1} ({inventory_item.sku}): Requested quantity ({item_data.quantity}) exceeds available stock ({inventory_item.stock_quantity})"
            )
            continue
        
        # Check if item already exists
        existing_item = db.query(DemoItem).filter(
            DemoItem.demo_request_id == demo_request_id,
            DemoItem.inventory_item_id == item_data.inventory_item_id
        ).first()
        
        if existing_item:
            errors.append(f"Item {idx + 1} ({inventory_item.sku}): Already in demo request")
            continue
        
        # Create demo item
        demo_item = DemoItem(
            demo_request_id=demo_request_id,
            inventory_item_id=item_data.inventory_item_id,
            quantity=item_data.quantity,
        )
        db.add(demo_item)
        created_items.append(demo_item)
    
    if errors and not created_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors)
        )
    
    db.commit()
    
    # Refresh all items
    for item in created_items:
        db.refresh(item)
    
    return [get_demo_item_response(item) for item in created_items]
