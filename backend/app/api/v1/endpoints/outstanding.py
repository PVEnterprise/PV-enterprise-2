"""
Outstanding items endpoint - Executive only.
Shows all outstanding order items grouped by customer and item.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.dispatch import DispatchItem
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


router = APIRouter()


# Schemas
class OrderInfo(BaseModel):
    order_id: UUID
    order_number: str

class OutstandingItemByCustomer(BaseModel):
    order_item_id: UUID  # Individual OrderItem ID
    order_id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str
    hospital_name: str
    item_id: UUID
    item_name: str
    sku: str
    ordered: int  # Quantity ordered for this specific order item
    dispatched: int  # Quantity dispatched for this specific order item
    outstanding: int  # Outstanding for this specific order item
    unit_price: Decimal
    outstanding_value: Decimal
    item_status: str  # OrderItem status
    order_status: str  # Order status
    available_stock: int  # Current inventory stock


class OutstandingItemByItem(BaseModel):
    item_id: UUID
    item_name: str
    sku: str
    total_ordered: int
    total_dispatched: int
    outstanding_quantity: int
    unit_price: Decimal
    outstanding_value: Decimal
    customers_count: int
    orders_count: int


class OutstandingSummary(BaseModel):
    total_outstanding_items: int
    total_outstanding_value: Decimal
    total_customers: int
    total_orders: int


@router.get("/by-customer", response_model=List[OutstandingItemByCustomer])
def get_outstanding_by_customer(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get outstanding items grouped by customer and item.
    Only accessible to executives.
    """
    # Check if user is executive
    if current_user.role_name != 'executive':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives can access outstanding items"
        )
    
    # Query to get individual OrderItem records with outstanding quantities
    # Returns one row per OrderItem (not aggregated)
    # Only shows items with status 'pending' or 'partial'
    query = db.query(
        OrderItem.id.label('order_item_id'),
        Order.id.label('order_id'),
        Order.order_number.label('order_number'),
        Order.status.label('order_status'),
        OrderItem.status.label('item_status'),
        Customer.id.label('customer_id'),
        Customer.name.label('customer_name'),
        Customer.hospital_name.label('hospital_name'),
        Inventory.id.label('item_id'),
        Inventory.sku.label('item_name'),
        Inventory.sku.label('sku'),
        Inventory.stock_quantity.label('available_stock'),
        OrderItem.quantity.label('ordered'),
        func.coalesce(func.sum(DispatchItem.quantity), 0).label('dispatched'),
        OrderItem.unit_price.label('unit_price')
    ).select_from(OrderItem)\
    .join(Order, OrderItem.order_id == Order.id)\
    .join(Customer, Order.customer_id == Customer.id)\
    .join(Inventory, OrderItem.inventory_id == Inventory.id)\
    .outerjoin(DispatchItem, DispatchItem.order_item_id == OrderItem.id)\
    .filter(
        Order.status.notin_(['draft', 'cancelled', 'completed', 'rejected']),  # Exclude inactive orders
        OrderItem.inventory_id.isnot(None),  # Only decoded items
        OrderItem.status.in_(['pending', 'partial'])  # Only pending or partial items
    )\
    .group_by(
        OrderItem.id,
        Order.id,
        Order.order_number,
        Order.status,
        OrderItem.status,
        Customer.id,
        Customer.name,
        Customer.hospital_name,
        Inventory.id,
        Inventory.description,
        Inventory.sku,
        Inventory.stock_quantity,
        OrderItem.quantity,
        OrderItem.unit_price
    )\
    .order_by(Customer.name, Inventory.description)\
    .all()
    
    # Filter out items with no outstanding quantity (do this in Python since HAVING with non-aggregated columns is complex)
    query = [row for row in query if (row.ordered - row.dispatched) > 0]
    
    # Format results - one record per OrderItem
    outstanding_items = []
    for row in query:
        outstanding_qty = row.ordered - row.dispatched
        outstanding_items.append(OutstandingItemByCustomer(
            order_item_id=row.order_item_id,
            order_id=row.order_id,
            order_number=row.order_number,
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            hospital_name=row.hospital_name,
            item_id=row.item_id,
            item_name=row.item_name,
            sku=row.sku,
            ordered=row.ordered,
            dispatched=row.dispatched,
            outstanding=outstanding_qty,
            unit_price=row.unit_price,
            outstanding_value=Decimal(outstanding_qty) * row.unit_price,
            item_status=row.item_status,
            order_status=row.order_status,
            available_stock=row.available_stock
        ))
    
    return outstanding_items


@router.get("/by-item", response_model=List[OutstandingItemByItem])
def get_outstanding_by_item(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get outstanding items grouped by item.
    Only accessible to executives.
    """
    # Check if user is executive
    if current_user.role_name != 'executive':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives can access outstanding items"
        )
    
    # Query to get outstanding items by item
    query = db.query(
        Inventory.id.label('item_id'),
        Inventory.sku.label('item_name'),
        Inventory.sku.label('sku'),
        func.sum(OrderItem.quantity).label('total_ordered'),
        func.coalesce(func.sum(DispatchItem.quantity), 0).label('total_dispatched'),
        (func.sum(OrderItem.quantity) - func.coalesce(func.sum(DispatchItem.quantity), 0)).label('outstanding_quantity'),
        OrderItem.unit_price.label('unit_price'),
        func.count(func.distinct(Order.customer_id)).label('customers_count'),
        func.count(func.distinct(Order.id)).label('orders_count')
    ).select_from(Order)\
    .join(OrderItem, OrderItem.order_id == Order.id)\
    .join(Inventory, OrderItem.inventory_id == Inventory.id)\
    .outerjoin(DispatchItem, DispatchItem.order_item_id == OrderItem.id)\
    .filter(
        Order.status.notin_(['draft', 'cancelled', 'completed', 'rejected'])
    )\
    .group_by(
        Inventory.id,
        Inventory.description,
        Inventory.sku,
        OrderItem.unit_price
    )\
    .having((func.sum(OrderItem.quantity) - func.coalesce(func.sum(DispatchItem.quantity), 0)) > 0)\
    .order_by(Inventory.description)
    
    results = query.all()
    
    # Format results
    outstanding_items = []
    for row in results:
        outstanding_items.append(OutstandingItemByItem(
            item_id=row.item_id,
            item_name=row.item_name,
            sku=row.sku,
            total_ordered=row.total_ordered,
            total_dispatched=row.total_dispatched,
            outstanding_quantity=row.outstanding_quantity,
            unit_price=row.unit_price,
            outstanding_value=Decimal(row.outstanding_quantity) * row.unit_price,
            customers_count=row.customers_count,
            orders_count=row.orders_count
        ))
    
    return outstanding_items


@router.get("/summary", response_model=OutstandingSummary)
def get_outstanding_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary of outstanding items.
    Only accessible to executives.
    """
    # Check if user is executive
    if current_user.role_name != 'executive':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives can access outstanding items"
        )
    
    # Get outstanding items (individual OrderItem records)
    outstanding_items = get_outstanding_by_customer(db, current_user)
    
    # Calculate summary from individual records
    total_value = sum(item.outstanding_value for item in outstanding_items)
    unique_customers = len(set(item.customer_id for item in outstanding_items))
    unique_items = len(set(item.item_id for item in outstanding_items))
    unique_orders = len(set(item.order_id for item in outstanding_items))
    
    return OutstandingSummary(
        total_outstanding_items=unique_items,
        total_outstanding_value=total_value,
        total_customers=unique_customers,
        total_orders=unique_orders
    )
