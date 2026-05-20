"""
Inventory management endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.inventory import Inventory
from app.models.demo_item import DemoItem
from app.models.demo_request import DemoRequest
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
    md_bag: Optional[int] = Field(None, ge=0, description="MD bag quantity")
    nani_bag: Optional[int] = Field(None, ge=0, description="Nani bag quantity")
    srinu_bag: Optional[int] = Field(None, ge=0, description="Srinu bag quantity")
    praneeth_bag: Optional[int] = Field(None, ge=0, description="Praneeth bag quantity")
    prasanna_bag: Optional[int] = Field(None, ge=0, description="Prasanna bag quantity")


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
    md_bag: Optional[int] = Field(None, ge=0)
    nani_bag: Optional[int] = Field(None, ge=0)
    srinu_bag: Optional[int] = Field(None, ge=0)
    praneeth_bag: Optional[int] = Field(None, ge=0)
    prasanna_bag: Optional[int] = Field(None, ge=0)


class StockUpdate(BaseModel):
    quantity: int
    operation: str = Field(..., pattern="^(add|subtract|set)$")


class InventoryResponse(InventoryBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    qty_in_demos: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedInventoryResponse(BaseModel):
    items: List[InventoryResponse]
    total: int
    
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
    # Check if SKU already exists (including soft-deleted)
    existing = db.query(Inventory).filter(Inventory.sku == item_data.sku).first()
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU already exists"
            )
        # Reactivate soft-deleted item with new data
        update_data = item_data.model_dump()
        for field, value in update_data.items():
            setattr(existing, field, value)
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create inventory item
    inventory = Inventory(**item_data.model_dump())
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    
    return inventory


@router.get("/", response_model=PaginatedInventoryResponse)
def list_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
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
    
    # Total count before pagination
    total = query.count()
    
    # Pagination
    items = query.offset(skip).limit(limit).all()

    # Compute qty currently out in dispatched demos per inventory item
    demo_qty_rows = (
        db.query(
            DemoItem.inventory_item_id,
            func.sum(DemoItem.quantity).label("qty")
        )
        .join(DemoRequest, DemoRequest.id == DemoItem.demo_request_id)
        .filter(DemoRequest.state == "dispatched")
        .group_by(DemoItem.inventory_item_id)
        .all()
    )
    demo_qty_map = {str(row.inventory_item_id): int(row.qty) for row in demo_qty_rows}
    for item in items:
        item.qty_in_demos = demo_qty_map.get(str(item.id), 0)

    return PaginatedInventoryResponse(items=items, total=total)


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


class InventoryUpsert(BaseModel):
    sku: str = Field(..., max_length=100, description="Catalog Number")
    description: Optional[str] = Field(default=None, description="Item description")
    batch_no: Optional[str] = Field(default=None, max_length=100, description="Batch number")
    unit_price: Optional[Decimal] = Field(default=None, ge=0, description="Unit price in rupees")
    stock_quantity: Optional[int] = Field(default=None, ge=0, description="Current stock quantity")
    hsn_code: Optional[str] = Field(default=None, min_length=8, max_length=8, pattern="^[0-9]{8}$", description="HSN code (8 digits)")
    tax: Optional[Decimal] = Field(default=None, ge=0, le=100, description="Tax percentage")
    md_bag: Optional[int] = Field(default=None, ge=0, description="MD bag quantity")
    nani_bag: Optional[int] = Field(default=None, ge=0, description="Nani bag quantity")
    srinu_bag: Optional[int] = Field(default=None, ge=0, description="Srinu bag quantity")
    praneeth_bag: Optional[int] = Field(default=None, ge=0, description="Praneeth bag quantity")
    prasanna_bag: Optional[int] = Field(default=None, ge=0, description="Prasanna bag quantity")


class UpsertResponse(BaseModel):
    """Response for upsert operation."""
    item: InventoryResponse
    created: bool  # True if created, False if updated
    
    model_config = ConfigDict(from_attributes=True)


_DEFAULT_UNIT_PRICE = Decimal('1000')
_DEFAULT_STOCK_QUANTITY = 0
_DEFAULT_HSN_CODE = '90189023'
_DEFAULT_TAX = Decimal('5')


@router.post("/upsert", response_model=UpsertResponse)
def upsert_inventory_item(
    item_data: InventoryUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.INVENTORY_CREATE))
):
    """
    Create or update an inventory item by SKU.
    
    Only Catalog No is required. All other fields are optional.
    For existing items: only fields present in the payload are updated.
    For new items: missing required fields are filled with defaults
    (unit_price=1000, stock_quantity=0, hsn_code=90189023, tax=5).
    """
    existing = db.query(Inventory).filter(Inventory.sku == item_data.sku).first()
    
    if existing:
        # Only update fields that were explicitly provided in the payload
        update_data = item_data.model_dump(exclude_unset=True)
        update_data.pop('sku', None)
        for field, value in update_data.items():
            setattr(existing, field, value)
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return UpsertResponse(item=existing, created=False)
    else:
        # Create new item, applying defaults for missing required fields
        create_data = item_data.model_dump(exclude_unset=True)
        if 'unit_price' not in create_data:
            create_data['unit_price'] = _DEFAULT_UNIT_PRICE
        if 'stock_quantity' not in create_data:
            create_data['stock_quantity'] = _DEFAULT_STOCK_QUANTITY
        if 'hsn_code' not in create_data:
            create_data['hsn_code'] = _DEFAULT_HSN_CODE
        if 'tax' not in create_data:
            create_data['tax'] = _DEFAULT_TAX
        inventory = Inventory(**create_data)
        db.add(inventory)
        db.commit()
        db.refresh(inventory)
        return UpsertResponse(item=inventory, created=True)
