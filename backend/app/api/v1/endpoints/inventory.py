"""
Inventory management endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.inventory import Inventory
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


router = APIRouter()


# Schemas
class InventoryBase(BaseModel):
    sku: str = Field(..., max_length=100, description="Catalog Number")
    description: Optional[str] = Field(None, description="Item description")
    batch_no: Optional[str] = Field(None, max_length=100, description="Batch number")
    unit_price: Decimal = Field(..., ge=0, description="Unit price in rupees")
    stock_quantity: int = Field(default=0, ge=0, description="Current stock quantity")
    hsn_code: str = Field(..., min_length=8, max_length=8, pattern="^[0-9]{8}$", description="HSN code (8 digits)")
    tax: Decimal = Field(..., ge=0, le=100, description="Tax percentage")


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    batch_no: Optional[str] = Field(None, max_length=100)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    hsn_code: Optional[str] = Field(None, min_length=8, max_length=8, pattern="^[0-9]{8}$")
    tax: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class StockUpdate(BaseModel):
    quantity: int
    operation: str = Field(..., pattern="^(add|subtract|set)$")


class InventoryResponse(InventoryBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    item_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVENTORY_CREATE))
):
    """
    Create a new inventory item.
    
    Only inventory admins and executives can create inventory items.
    """
    # Check if SKU already exists
    existing = db.query(Inventory).filter(Inventory.sku == item_data.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SKU already exists"
        )
    
    # Create inventory item
    inventory = Inventory(**item_data.model_dump())
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    
    return inventory


@router.get("/", response_model=List[InventoryResponse])
def list_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    low_stock: bool = False,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVENTORY_READ))
):
    """
    List inventory items with filtering and search.
    """
    query = db.query(Inventory)
    
    # Apply filters
    if active_only:
        query = query.filter(Inventory.is_active == True)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Inventory.sku.ilike(search_term)) |
            (Inventory.description.ilike(search_term))
        )
    
    if low_stock:
        # Filter items where stock quantity is low (< 50)
        query = query.filter(
            Inventory.stock_quantity < 50
        )
    
    # Order by SKU (catalog number)
    query = query.order_by(Inventory.sku)
    
    # Pagination
    items = query.offset(skip).limit(limit).all()
    
    return items


@router.get("/{item_id}", response_model=InventoryResponse)
def get_inventory_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVENTORY_READ))
):
    """
    Get inventory item details.
    """
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    return item


@router.put("/{item_id}", response_model=InventoryResponse)
def update_inventory_item(
    item_id: UUID,
    item_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVENTORY_UPDATE))
):
    """
    Update inventory item details.
    """
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Check SKU uniqueness if being updated
    if item_data.sku and item_data.sku != item.sku:
        existing = db.query(Inventory).filter(Inventory.sku == item_data.sku).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU already exists"
            )
    
    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVENTORY_DELETE))
):
    """
    Soft delete inventory item by marking as inactive.
    """
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    item.is_active = False
    item.updated_at = datetime.utcnow()
    db.commit()
    
    return None


@router.post("/{item_id}/stock", response_model=InventoryResponse)
def update_stock(
    item_id: UUID,
    stock_data: StockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVENTORY_UPDATE))
):
    """
    Update stock quantity.
    
    Operations:
    - add: Increase stock (receiving)
    - subtract: Decrease stock (dispatch)
    - set: Set absolute value
    """
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Update stock based on operation
    if stock_data.operation == "add":
        item.stock_quantity += stock_data.quantity
    elif stock_data.operation == "subtract":
        new_quantity = item.stock_quantity - stock_data.quantity
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient stock"
            )
        item.stock_quantity = new_quantity
    elif stock_data.operation == "set":
        if stock_data.quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock quantity cannot be negative"
            )
        item.stock_quantity = stock_data.quantity
    
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    
    return item


@router.get("/categories/list", response_model=List[str])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVENTORY_READ))
):
    """
    Get list of all unique categories.
    """
    categories = db.query(Inventory.category).distinct().filter(
        Inventory.category.isnot(None),
        Inventory.is_active == True
    ).all()
    
    return [cat[0] for cat in categories if cat[0]]
