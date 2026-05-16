"""
Procurement API endpoints - Executive only.
Handles procurement lifecycle: ordered -> payment_done -> order_received.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel as PydanticBase

from app.db.session import get_db
from app.models.procurement import Procurement, ProcurementItem
from app.models.inventory import Inventory
from app.models.user import User
from app.api.deps import get_current_user
from app.core.permissions import Permission, require_permission

router = APIRouter()

ALLOWED_STATUSES = ["ordered", "payment_done", "order_received"]


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ProcurementItemIn(PydanticBase):
    inventory_id: UUID
    quantity: int
    unit_price: Optional[Decimal] = None
    notes: Optional[str] = None


class ProcurementItemUpdate(PydanticBase):
    inventory_id: Optional[UUID] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    notes: Optional[str] = None


class ProcurementCreate(PydanticBase):
    supplier_name: Optional[str] = None
    notes: Optional[str] = None
    items: List[ProcurementItemIn] = []


class ProcurementUpdate(PydanticBase):
    supplier_name: Optional[str] = None
    notes: Optional[str] = None


class InventoryItemOut(PydanticBase):
    id: UUID
    sku: str
    description: Optional[str] = None
    stock_quantity: int
    unit_price: Decimal

    class Config:
        from_attributes = True


class ProcurementItemOut(PydanticBase):
    id: UUID
    procurement_id: UUID
    inventory_id: UUID
    quantity: int
    unit_price: Optional[Decimal] = None
    notes: Optional[str] = None
    inventory_item: Optional[InventoryItemOut] = None

    class Config:
        from_attributes = True


class ProcurementOut(PydanticBase):
    id: UUID
    procurement_number: str
    status: str
    supplier_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[ProcurementItemOut] = []

    class Config:
        from_attributes = True


class ReceiveAdjustment(PydanticBase):
    procurement_item_id: UUID
    quantity: int


class ReceiveRequest(PydanticBase):
    adjustments: Optional[List[ReceiveAdjustment]] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_executive(current_user: User):
    if current_user.role_name != "executive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives can access procurement"
        )


def _generate_procurement_number(db: Session) -> str:
    year = date.today().year
    prefix = f"PROC-{year}-"
    last = db.query(Procurement).filter(
        Procurement.procurement_number.like(f"{prefix}%")
    ).order_by(Procurement.procurement_number.desc()).first()

    next_num = 1
    if last:
        try:
            next_num = int(last.procurement_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            pass

    while True:
        number = f"{prefix}{next_num:04d}"
        if not db.query(Procurement).filter(Procurement.procurement_number == number).first():
            return number
        next_num += 1


def _load_full(db: Session, procurement_id) -> Procurement:
    return db.query(Procurement).options(
        joinedload(Procurement.items).joinedload(ProcurementItem.inventory_item)
    ).filter(Procurement.id == procurement_id).first()


# ── CRUD Endpoints ────────────────────────────────────────────────────────────

@router.post("/", response_model=ProcurementOut, status_code=status.HTTP_201_CREATED)
def create_procurement(
    data: ProcurementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new procurement in 'ordered' state. Executive only.
    """
    _require_executive(current_user)

    number = _generate_procurement_number(db)
    procurement = Procurement(
        procurement_number=number,
        status="ordered",
        supplier_name=data.supplier_name,
        notes=data.notes,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(procurement)
    db.flush()

    for item_in in data.items:
        inv = db.query(Inventory).filter(Inventory.id == item_in.inventory_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail=f"Inventory item {item_in.inventory_id} not found")
        pi = ProcurementItem(
            procurement_id=procurement.id,
            inventory_id=item_in.inventory_id,
            quantity=item_in.quantity,
            unit_price=item_in.unit_price,
            notes=item_in.notes,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        db.add(pi)

    db.commit()
    return _load_full(db, procurement.id)


@router.get("/", response_model=List[ProcurementOut])
def list_procurements(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List procurements. Executive only.
    """
    _require_executive(current_user)

    query = db.query(Procurement).options(
        joinedload(Procurement.items).joinedload(ProcurementItem.inventory_item)
    )
    if status_filter:
        query = query.filter(Procurement.status == status_filter)

    return query.order_by(Procurement.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{procurement_id}", response_model=ProcurementOut)
def get_procurement(
    procurement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single procurement. Executive only.
    """
    _require_executive(current_user)

    p = _load_full(db, procurement_id)
    if not p:
        raise HTTPException(status_code=404, detail="Procurement not found")
    return p


@router.put("/{procurement_id}", response_model=ProcurementOut)
def update_procurement(
    procurement_id: UUID,
    data: ProcurementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update procurement metadata (supplier, notes). Executive only.
    Only allowed in 'ordered' or 'payment_done' state.
    """
    _require_executive(current_user)

    p = db.query(Procurement).filter(Procurement.id == procurement_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Procurement not found")
    if p.status == "order_received":
        raise HTTPException(status_code=400, detail="Cannot edit a received procurement")

    if data.supplier_name is not None:
        p.supplier_name = data.supplier_name
    if data.notes is not None:
        p.notes = data.notes
    p.updated_by = current_user.id
    db.commit()
    return _load_full(db, p.id)


@router.delete("/{procurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_procurement(
    procurement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a procurement. Only allowed in 'ordered' state. Executive only.
    """
    _require_executive(current_user)

    p = db.query(Procurement).filter(Procurement.id == procurement_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Procurement not found")
    if p.status != "ordered":
        raise HTTPException(status_code=400, detail="Only procurements in 'ordered' state can be deleted")

    db.delete(p)
    db.commit()
    return None


# ── Item Management ────────────────────────────────────────────────────────────

@router.post("/{procurement_id}/items", response_model=ProcurementOut, status_code=status.HTTP_201_CREATED)
def add_procurement_item(
    procurement_id: UUID,
    item_in: ProcurementItemIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add an item to a procurement. Only allowed in 'ordered' state.
    """
    _require_executive(current_user)

    p = db.query(Procurement).filter(Procurement.id == procurement_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Procurement not found")
    if p.status != "ordered":
        raise HTTPException(status_code=400, detail="Items can only be added in 'ordered' state")

    inv = db.query(Inventory).filter(Inventory.id == item_in.inventory_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    pi = ProcurementItem(
        procurement_id=p.id,
        inventory_id=item_in.inventory_id,
        quantity=item_in.quantity,
        unit_price=item_in.unit_price,
        notes=item_in.notes,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(pi)
    db.commit()
    return _load_full(db, p.id)


@router.put("/{procurement_id}/items/{item_id}", response_model=ProcurementOut)
def update_procurement_item(
    procurement_id: UUID,
    item_id: UUID,
    item_data: ProcurementItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a procurement item. Only allowed in 'ordered' state.
    """
    _require_executive(current_user)

    p = db.query(Procurement).filter(Procurement.id == procurement_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Procurement not found")
    if p.status != "ordered":
        raise HTTPException(status_code=400, detail="Items can only be edited in 'ordered' state")

    pi = db.query(ProcurementItem).filter(
        ProcurementItem.id == item_id,
        ProcurementItem.procurement_id == procurement_id
    ).first()
    if not pi:
        raise HTTPException(status_code=404, detail="Procurement item not found")

    if item_data.quantity is not None:
        pi.quantity = item_data.quantity
    if item_data.unit_price is not None:
        pi.unit_price = item_data.unit_price
    if item_data.notes is not None:
        pi.notes = item_data.notes
    pi.updated_by = current_user.id
    db.commit()
    return _load_full(db, p.id)


@router.delete("/{procurement_id}/items/{item_id}", response_model=ProcurementOut)
def remove_procurement_item(
    procurement_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove an item from a procurement. Only allowed in 'ordered' state.
    """
    _require_executive(current_user)

    p = db.query(Procurement).filter(Procurement.id == procurement_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Procurement not found")
    if p.status != "ordered":
        raise HTTPException(status_code=400, detail="Items can only be removed in 'ordered' state")

    pi = db.query(ProcurementItem).filter(
        ProcurementItem.id == item_id,
        ProcurementItem.procurement_id == procurement_id
    ).first()
    if not pi:
        raise HTTPException(status_code=404, detail="Procurement item not found")

    db.delete(pi)
    db.commit()
    return _load_full(db, p.id)


# ── State Transitions ─────────────────────────────────────────────────────────

@router.post("/{procurement_id}/mark-payment-done", response_model=ProcurementOut)
def mark_payment_done(
    procurement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transition procurement from 'ordered' to 'payment_done'. Executive only.
    """
    _require_executive(current_user)

    p = db.query(Procurement).options(
        joinedload(Procurement.items)
    ).filter(Procurement.id == procurement_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Procurement not found")
    if p.status != "ordered":
        raise HTTPException(status_code=400, detail="Procurement must be in 'ordered' state to mark payment done")
    if not p.items:
        raise HTTPException(status_code=400, detail="Procurement must have at least one item")

    p.status = "payment_done"
    p.updated_by = current_user.id
    db.commit()
    return _load_full(db, p.id)


@router.post("/{procurement_id}/receive", response_model=ProcurementOut)
def receive_procurement(
    procurement_id: UUID,
    receive_data: ReceiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transition procurement to 'order_received' and add quantities to inventory stock.
    Executive only. Two modes:
    - No adjustments: uses original procurement quantities
    - With adjustments: uses adjusted quantities per item before adding to inventory
    """
    _require_executive(current_user)

    p = db.query(Procurement).options(
        joinedload(Procurement.items).joinedload(ProcurementItem.inventory_item)
    ).filter(Procurement.id == procurement_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Procurement not found")
    if p.status != "payment_done":
        raise HTTPException(status_code=400, detail="Procurement must be in 'payment_done' state to receive")
    if not p.items:
        raise HTTPException(status_code=400, detail="Procurement has no items")

    # Build adjustment map if provided
    adj_map: dict = {}
    if receive_data.adjustments:
        for adj in receive_data.adjustments:
            adj_map[str(adj.procurement_item_id)] = adj.quantity

    # Add quantities to inventory
    for item in p.items:
        qty = adj_map.get(str(item.id), item.quantity)
        if qty < 0:
            raise HTTPException(status_code=400, detail=f"Quantity cannot be negative for item {item.id}")
        inv = db.query(Inventory).filter(Inventory.id == item.inventory_id).first()
        if inv and qty > 0:
            inv.stock_quantity += qty

    p.status = "order_received"
    p.updated_by = current_user.id
    db.commit()
    return _load_full(db, p.id)
