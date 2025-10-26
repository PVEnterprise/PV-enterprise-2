"""
Dashboard and analytics endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from decimal import Decimal

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.order import Order
from app.models.invoice import Invoice
from app.models.inventory import Inventory
from pydantic import BaseModel


router = APIRouter()


class DashboardStats(BaseModel):
    total_orders: int
    pending_orders: int
    completed_orders: int
    total_revenue: Decimal
    pending_invoices: int
    outstanding_amount: Decimal
    low_stock_items: int
    active_customers: int


class OrderStatusCount(BaseModel):
    status: str
    count: int


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.DASHBOARD_VIEW))
):
    """Get dashboard statistics."""
    
    # Order statistics
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(
        Order.status.in_(["draft", "pending_approval", "approved"])
    ).count()
    completed_orders = db.query(Order).filter(Order.status == "completed").count()
    
    # Revenue statistics
    total_revenue = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.payment_status == "paid"
    ).scalar() or Decimal(0)
    
    # Invoice statistics
    pending_invoices = db.query(Invoice).filter(
        Invoice.payment_status.in_(["unpaid", "partial"])
    ).count()
    
    outstanding_amount = db.query(func.sum(Invoice.total_amount - Invoice.paid_amount)).filter(
        Invoice.payment_status.in_(["unpaid", "partial"])
    ).scalar() or Decimal(0)
    
    # Inventory statistics
    low_stock_items = db.query(Inventory).filter(
        Inventory.stock_quantity <= Inventory.reorder_level,
        Inventory.is_active == True
    ).count()
    
    # Customer statistics (simplified)
    active_customers = db.query(Order.customer_id).distinct().count()
    
    return DashboardStats(
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        total_revenue=total_revenue,
        pending_invoices=pending_invoices,
        outstanding_amount=outstanding_amount,
        low_stock_items=low_stock_items,
        active_customers=active_customers
    )


@router.get("/orders-by-status")
def get_orders_by_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.DASHBOARD_VIEW))
):
    """Get order counts grouped by status."""
    results = db.query(
        Order.status,
        func.count(Order.id).label("count")
    ).group_by(Order.status).all()
    
    return [{"status": r.status, "count": r.count} for r in results]


@router.get("/revenue-trend")
def get_revenue_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.DASHBOARD_ANALYTICS))
):
    """Get revenue trend for the last N days."""
    start_date = datetime.now() - timedelta(days=days)
    
    results = db.query(
        func.date(Invoice.invoice_date).label("date"),
        func.sum(Invoice.total_amount).label("revenue")
    ).filter(
        Invoice.invoice_date >= start_date,
        Invoice.payment_status == "paid"
    ).group_by(func.date(Invoice.invoice_date)).all()
    
    return [{"date": str(r.date), "revenue": float(r.revenue)} for r in results]
