"""
Territory management endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.db.session import get_db
from app.api.deps import PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.customer import Customer
from app.models.territory import Territory


router = APIRouter()


class TerritoryBase(BaseModel):
    name: str = Field(..., max_length=255)
    city: Optional[str] = None


class TerritoryCreate(TerritoryBase):
    sales_person_id: Optional[UUID] = None


class TerritoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = None
    sales_person_id: Optional[UUID] = None
    clear_sales_person: bool = False


class TerritoryResponse(TerritoryBase):
    id: UUID
    sales_person_id: Optional[UUID] = None
    sales_person_name: Optional[str] = None
    customer_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CustomerIdsPayload(BaseModel):
    customer_ids: List[UUID]


def _validate_sales_person(db: Session, sales_person_id: UUID) -> None:
    """A territory's sales person must be an active user with the sales_rep role."""
    user = db.query(User).options(joinedload(User.role)).filter(User.id == sales_person_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sales person not found")
    if not user.role or user.role.name != "sales_rep":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sales person must be a user with the sales_rep role"
        )


def _to_response(territory: Territory, customer_count: int) -> TerritoryResponse:
    return TerritoryResponse(
        id=territory.id,
        name=territory.name,
        city=territory.city,
        sales_person_id=territory.sales_person_id,
        sales_person_name=territory.sales_person.full_name if territory.sales_person else None,
        customer_count=customer_count,
    )


def _customer_counts(db: Session, territory_ids: List[UUID]) -> dict:
    if not territory_ids:
        return {}
    rows = (
        db.query(Customer.territory_id, func.count(Customer.id))
        .filter(Customer.territory_id.in_(territory_ids))
        .group_by(Customer.territory_id)
        .all()
    )
    return {territory_id: count for territory_id, count in rows}


@router.post("/", response_model=TerritoryResponse, status_code=status.HTTP_201_CREATED)
def create_territory(
    territory_data: TerritoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.TERRITORY_CREATE))
):
    """Create a new territory."""
    existing = db.query(Territory).filter(Territory.name == territory_data.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A territory with this name already exists")

    if territory_data.sales_person_id:
        _validate_sales_person(db, territory_data.sales_person_id)

    territory = Territory(
        name=territory_data.name,
        city=territory_data.city,
        sales_person_id=territory_data.sales_person_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(territory)
    db.commit()
    db.refresh(territory)
    return _to_response(territory, 0)


@router.get("/", response_model=List[TerritoryResponse])
def list_territories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.TERRITORY_READ))
):
    """List territories with search."""
    query = db.query(Territory).options(joinedload(Territory.sales_person))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Territory.name.ilike(search_term)) |
            (Territory.city.ilike(search_term))
        )

    query = query.order_by(Territory.name)
    territories = query.offset(skip).limit(limit).all()

    counts = _customer_counts(db, [t.id for t in territories])
    return [_to_response(t, counts.get(t.id, 0)) for t in territories]


@router.get("/{territory_id}", response_model=TerritoryResponse)
def get_territory(
    territory_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.TERRITORY_READ))
):
    """Get territory details."""
    territory = db.query(Territory).options(joinedload(Territory.sales_person)).filter(Territory.id == territory_id).first()
    if not territory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")

    counts = _customer_counts(db, [territory.id])
    return _to_response(territory, counts.get(territory.id, 0))


@router.put("/{territory_id}", response_model=TerritoryResponse)
def update_territory(
    territory_id: UUID,
    territory_data: TerritoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.TERRITORY_UPDATE))
):
    """Update territory details."""
    territory = db.query(Territory).filter(Territory.id == territory_id).first()
    if not territory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")

    if territory_data.name is not None and territory_data.name != territory.name:
        existing = db.query(Territory).filter(
            Territory.name == territory_data.name, Territory.id != territory_id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A territory with this name already exists")
        territory.name = territory_data.name

    if territory_data.city is not None:
        territory.city = territory_data.city

    if territory_data.clear_sales_person:
        territory.sales_person_id = None
    elif territory_data.sales_person_id is not None:
        _validate_sales_person(db, territory_data.sales_person_id)
        territory.sales_person_id = territory_data.sales_person_id

    territory.updated_by = current_user.id
    territory.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(territory)

    counts = _customer_counts(db, [territory.id])
    return _to_response(territory, counts.get(territory.id, 0))


@router.delete("/{territory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_territory(
    territory_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.TERRITORY_DELETE))
):
    """Delete a territory. Customers in it become unassigned."""
    territory = db.query(Territory).filter(Territory.id == territory_id).first()
    if not territory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")

    db.delete(territory)
    db.commit()
    return None


@router.get("/{territory_id}/customers")
def list_territory_customers(
    territory_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.TERRITORY_READ))
):
    """List customers currently assigned to this territory, with search."""
    territory = db.query(Territory).filter(Territory.id == territory_id).first()
    if not territory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")

    query = db.query(Customer).filter(Customer.territory_id == territory_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Customer.hospital_name.ilike(search_term)) |
            (Customer.name.ilike(search_term)) |
            (Customer.gst_number.ilike(search_term))
        )

    query = query.order_by(Customer.hospital_name)
    return query.offset(skip).limit(limit).all()


@router.post("/{territory_id}/customers", status_code=status.HTTP_200_OK)
def add_customers_to_territory(
    territory_id: UUID,
    payload: CustomerIdsPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.TERRITORY_UPDATE))
):
    """Bulk-assign customers to this territory."""
    territory = db.query(Territory).filter(Territory.id == territory_id).first()
    if not territory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")

    if not payload.customer_ids:
        return {"updated": 0}

    updated = (
        db.query(Customer)
        .filter(Customer.id.in_(payload.customer_ids))
        .update({Customer.territory_id: territory_id}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}


@router.delete("/{territory_id}/customers", status_code=status.HTTP_200_OK)
def remove_customers_from_territory(
    territory_id: UUID,
    payload: CustomerIdsPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.TERRITORY_UPDATE))
):
    """Bulk-unassign customers from this territory."""
    territory = db.query(Territory).filter(Territory.id == territory_id).first()
    if not territory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")

    if not payload.customer_ids:
        return {"updated": 0}

    updated = (
        db.query(Customer)
        .filter(Customer.id.in_(payload.customer_ids), Customer.territory_id == territory_id)
        .update({Customer.territory_id: None}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}
