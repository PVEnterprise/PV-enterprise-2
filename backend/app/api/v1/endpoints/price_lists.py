"""
Price Lists API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.models.price_list import PriceList, PriceListItem
from app.models.inventory import Inventory
from app.schemas.price_list import (
    PriceListCreate,
    PriceListUpdate,
    PriceListResponse,
    PriceListItemResponse,
    PriceListItemUpdate
)
from app.api.deps import get_current_user

router = APIRouter()


@router.get("", response_model=List[PriceListResponse])
def get_price_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all price lists.
    Available to quoters and executives.
    """
    # Check role
    if current_user.role_name not in ['quoter', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view price lists"
        )
    
    price_lists = db.query(PriceList).order_by(
        PriceList.is_default.desc(),
        PriceList.name
    ).all()
    
    return price_lists


@router.post("", response_model=PriceListResponse, status_code=status.HTTP_201_CREATED)
def create_price_list(
    price_list_data: PriceListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new price list.
    Automatically creates items for all inventory with standard prices.
    """
    # Check role
    if current_user.role_name not in ['quoter', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create price lists"
        )
    
    # Check if name already exists
    existing = db.query(PriceList).filter(PriceList.name == price_list_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price list with this name already exists"
        )
    
    # If setting as default, unset other defaults
    if price_list_data.is_default:
        db.query(PriceList).update({"is_default": False})
    
    # Create price list
    price_list = PriceList(
        name=price_list_data.name,
        description=price_list_data.description,
        is_default=price_list_data.is_default,
        created_by=current_user.id
    )
    db.add(price_list)
    db.flush()  # Get the ID
    
    # Create items for all inventory with standard prices and tax
    inventory_items = db.query(Inventory).all()
    for inventory in inventory_items:
        price_list_item = PriceListItem(
            price_list_id=price_list.id,
            inventory_id=inventory.id,
            unit_price=inventory.unit_price,
            tax_percentage=inventory.tax
        )
        db.add(price_list_item)
    
    db.commit()
    db.refresh(price_list)
    
    return price_list


@router.get("/{price_list_id}", response_model=PriceListResponse)
def get_price_list(
    price_list_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific price list."""
    # Check role
    if current_user.role_name not in ['quoter', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view price lists"
        )
    
    price_list = db.query(PriceList).filter(PriceList.id == price_list_id).first()
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price list not found"
        )
    
    return price_list


@router.put("/{price_list_id}", response_model=PriceListResponse)
def update_price_list(
    price_list_id: UUID,
    price_list_data: PriceListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a price list."""
    # Check role
    if current_user.role_name not in ['quoter', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update price lists"
        )
    
    price_list = db.query(PriceList).filter(PriceList.id == price_list_id).first()
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price list not found"
        )
    
    # Check if new name conflicts
    if price_list_data.name and price_list_data.name != price_list.name:
        existing = db.query(PriceList).filter(
            PriceList.name == price_list_data.name,
            PriceList.id != price_list_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price list with this name already exists"
            )
    
    # If setting as default, unset other defaults
    if price_list_data.is_default:
        db.query(PriceList).filter(PriceList.id != price_list_id).update({"is_default": False})
    
    # Update fields
    update_data = price_list_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(price_list, field, value)
    
    db.commit()
    db.refresh(price_list)
    
    return price_list


@router.delete("/{price_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price_list(
    price_list_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a price list."""
    # Check role
    if current_user.role_name not in ['quoter', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete price lists"
        )
    
    price_list = db.query(PriceList).filter(PriceList.id == price_list_id).first()
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price list not found"
        )
    
    # Prevent deleting default price list
    if price_list.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default price list"
        )
    
    db.delete(price_list)
    db.commit()
    
    return None


@router.get("/{price_list_id}/items", response_model=List[PriceListItemResponse])
def get_price_list_items(
    price_list_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all items in a price list."""
    # Check role
    if current_user.role_name not in ['quoter', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view price lists"
        )
    
    # Verify price list exists
    price_list = db.query(PriceList).filter(PriceList.id == price_list_id).first()
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price list not found"
        )
    
    # Get items with inventory data
    items = db.query(PriceListItem).options(
        joinedload(PriceListItem.inventory)
    ).join(
        Inventory, PriceListItem.inventory_id == Inventory.id
    ).filter(
        PriceListItem.price_list_id == price_list_id
    ).order_by(
        Inventory.sku
    ).all()
    
    return items


@router.put("/{price_list_id}/items/{item_id}", response_model=PriceListItemResponse)
def update_price_list_item(
    price_list_id: UUID,
    item_id: UUID,
    item_data: PriceListItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the price of an item in a price list."""
    # Check role
    if current_user.role_name not in ['quoter', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update price lists"
        )
    
    # Get item
    item = db.query(PriceListItem).filter(
        PriceListItem.id == item_id,
        PriceListItem.price_list_id == price_list_id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price list item not found"
        )
    
    # Update price and tax
    item.unit_price = item_data.unit_price
    if item_data.tax_percentage is not None:
        item.tax_percentage = item_data.tax_percentage
    db.commit()
    db.refresh(item)
    
    return item
