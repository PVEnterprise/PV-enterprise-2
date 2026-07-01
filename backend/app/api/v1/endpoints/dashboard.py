"""
Dashboard and analytics endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from decimal import Decimal

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.invoice import Invoice
from app.models.inventory import Inventory
from app.models.customer import Customer
from app.models.dispatch import Dispatch, DispatchItem
from app.models.quotation import Quotation
from app.models.demo_request import DemoRequest
from pydantic import BaseModel
from typing import Dict, List


router = APIRouter()


class DashboardStats(BaseModel):
    # Orders
    total_orders: int
    pending_orders: int
    completed_orders: int
    orders_this_month: int
    orders_last_month: int
    pending_approval_orders: int
    orders_by_stage: Dict[str, int]
    # Revenue & Finance
    total_revenue: Decimal
    revenue_this_month: Decimal
    revenue_last_month: Decimal
    total_invoiced: Decimal
    pending_invoices: int
    outstanding_amount: Decimal
    # Customers
    total_customers: int
    active_customers: int
    new_customers_this_month: int
    # Inventory
    total_inventory_items: int
    low_stock_items: int
    # Dispatches
    total_dispatches: int
    dispatches_this_month: int
    # Quotations
    total_quotations: int
    pending_quotations: int
    pending_quotation_value: Decimal
    # Finance extras
    invoiced_this_month: Decimal
    total_pending_order_value: Decimal
    # Demos
    active_demo_requests: int


class OrderStatusCount(BaseModel):
    status: str
    count: int


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.DASHBOARD_VIEW))
):
    """Get comprehensive CEO dashboard statistics."""
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    last_month_start = datetime(now.year, now.month - 1, 1) if now.month > 1 else datetime(now.year - 1, 12, 1)
    six_months_ago = now - timedelta(days=180)

    # --- Orders ---
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(
        Order.status.in_(["draft", "pending_approval", "approved"])
    ).count()
    completed_orders = db.query(Order).filter(Order.status == "completed").count()
    orders_this_month = db.query(Order).filter(Order.created_at >= month_start).count()
    orders_last_month = db.query(Order).filter(
        Order.created_at >= last_month_start, Order.created_at < month_start
    ).count()
    pending_approval_orders = db.query(Order).filter(Order.status == "pending_approval").count()
    stage_results = db.query(Order.workflow_stage, func.count(Order.id)).group_by(Order.workflow_stage).all()
    orders_by_stage = {r[0]: r[1] for r in stage_results}

    # --- Revenue & Finance ---
    total_revenue = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.payment_status == "paid"
    ).scalar() or Decimal(0)
    revenue_this_month = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.payment_status == "paid",
        Invoice.invoice_date >= month_start.date()
    ).scalar() or Decimal(0)
    revenue_last_month = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.payment_status == "paid",
        Invoice.invoice_date >= last_month_start.date(),
        Invoice.invoice_date < month_start.date()
    ).scalar() or Decimal(0)
    pending_invoices = db.query(Invoice).filter(
        Invoice.payment_status.in_(["unpaid", "partial"])
    ).count()
    outstanding_amount = db.query(func.sum(Invoice.total_amount - Invoice.paid_amount)).filter(
        Invoice.payment_status.in_(["unpaid", "partial"])
    ).scalar() or Decimal(0)

    # --- Customers ---
    total_customers = db.query(Customer).count()
    active_customers = db.query(Order.customer_id).filter(
        Order.created_at >= six_months_ago
    ).distinct().count()
    new_customers_this_month = db.query(Customer).filter(Customer.created_at >= month_start).count()

    # --- Inventory ---
    total_inventory_items = db.query(Inventory).filter(Inventory.is_active == True).count()
    low_stock_items = db.query(Inventory).filter(
        Inventory.stock_quantity <= 10, Inventory.is_active == True
    ).count()

    # --- Dispatches ---
    total_dispatches = db.query(Dispatch).count()
    dispatches_this_month = db.query(Dispatch).filter(Dispatch.created_at >= month_start).count()

    # --- Quotations ---
    total_quotations = db.query(Quotation).count()
    # Quotation value = decoded orders at any pre-PO stage (before inventory_check)
    _pre_po_stages = ['order_request', 'decoding_approval', 'quotation', 'quotation_generated', 'waiting_purchase_order', 'po_approval', 'inventory_check']
    pending_quotations = db.query(func.count(func.distinct(Order.id))).join(
        OrderItem, OrderItem.order_id == Order.id
    ).filter(
        Order.workflow_stage.in_(_pre_po_stages),
        OrderItem.unit_price.isnot(None)
    ).scalar() or 0
    pending_quotation_value = db.query(
        func.sum(
            OrderItem.unit_price
            * OrderItem.quantity
            * (1 - func.coalesce(Order.discount_percentage, 0) / 100)
            * (1 + func.coalesce(OrderItem.gst_percentage, 0) / 100)
        )
    ).join(Order, Order.id == OrderItem.order_id).filter(
        Order.workflow_stage.in_(_pre_po_stages),
        OrderItem.unit_price.isnot(None),
        OrderItem.inventory_id.isnot(None)
    ).scalar() or Decimal(0)

    # --- Finance extras ---
    # Invoiced = value of dispatched items (quantity * order unit_price)
    _dispatch_val_query = db.query(
        func.sum(DispatchItem.quantity * OrderItem.unit_price)
    ).join(OrderItem, OrderItem.id == DispatchItem.order_item_id).filter(
        OrderItem.unit_price.isnot(None)
    )
    total_invoiced = _dispatch_val_query.scalar() or Decimal(0)

    invoiced_this_month = db.query(
        func.sum(DispatchItem.quantity * OrderItem.unit_price)
    ).join(Dispatch, Dispatch.id == DispatchItem.dispatch_id
    ).join(OrderItem, OrderItem.id == DispatchItem.order_item_id
    ).filter(
        Dispatch.dispatch_date >= month_start.date(),
        OrderItem.unit_price.isnot(None)
    ).scalar() or Decimal(0)

    # Pending order value = outstanding (undelivered) qty for PO-approved orders
    # stages: inventory_check (PO approved) + payment_pending (partially dispatched)
    _dispatched_subq = db.query(
        DispatchItem.order_item_id,
        func.sum(DispatchItem.quantity).label('dispatched_qty')
    ).group_by(DispatchItem.order_item_id).subquery()

    total_pending_order_value = db.query(
        func.sum(
            (OrderItem.quantity - func.coalesce(_dispatched_subq.c.dispatched_qty, 0))
            * OrderItem.unit_price
            * (1 - func.coalesce(Order.discount_percentage, 0) / 100)
            * (1 + func.coalesce(OrderItem.gst_percentage, 0) / 100)
        )
    ).join(Order, Order.id == OrderItem.order_id
    ).outerjoin(_dispatched_subq, _dispatched_subq.c.order_item_id == OrderItem.id
    ).filter(
        Order.workflow_stage.in_(['inventory_check', 'payment_pending']),
        OrderItem.unit_price.isnot(None),
        OrderItem.inventory_id.isnot(None)
    ).scalar() or Decimal(0)

    # --- Demo Requests ---
    active_demo_requests = db.query(DemoRequest).filter(
        DemoRequest.state.in_(["requested", "placed"])
    ).count()

    return DashboardStats(
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        orders_this_month=orders_this_month,
        orders_last_month=orders_last_month,
        pending_approval_orders=pending_approval_orders,
        orders_by_stage=orders_by_stage,
        total_revenue=total_revenue,
        revenue_this_month=revenue_this_month,
        revenue_last_month=revenue_last_month,
        total_invoiced=total_invoiced,
        pending_invoices=pending_invoices,
        outstanding_amount=outstanding_amount,
        total_customers=total_customers,
        active_customers=active_customers,
        new_customers_this_month=new_customers_this_month,
        total_inventory_items=total_inventory_items,
        low_stock_items=low_stock_items,
        total_dispatches=total_dispatches,
        dispatches_this_month=dispatches_this_month,
        total_quotations=total_quotations,
        pending_quotations=pending_quotations,
        pending_quotation_value=pending_quotation_value,
        invoiced_this_month=invoiced_this_month,
        total_pending_order_value=total_pending_order_value,
        active_demo_requests=active_demo_requests,
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


@router.get("/fy-trend")
def get_fy_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.DASHBOARD_VIEW))
):
    """Get monthly Pending Order Value and Invoice Value for the current Indian FY (Apr–Mar)."""
    now = datetime.now()
    fy_start_year = now.year if now.month >= 4 else now.year - 1
    fy_start = datetime(fy_start_year, 4, 1)
    fy_end = datetime(fy_start_year + 1, 3, 31, 23, 59, 59)

    # Invoice value per month = value of items dispatched in that month
    invoice_rows = db.query(
        extract('year', Dispatch.dispatch_date).label('year'),
        extract('month', Dispatch.dispatch_date).label('month'),
        func.sum(DispatchItem.quantity * OrderItem.unit_price).label('invoice_value')
    ).join(DispatchItem, DispatchItem.dispatch_id == Dispatch.id
    ).join(OrderItem, OrderItem.id == DispatchItem.order_item_id
    ).filter(
        Dispatch.dispatch_date >= fy_start.date(),
        Dispatch.dispatch_date <= fy_end.date(),
        OrderItem.unit_price.isnot(None)
    ).group_by('year', 'month').all()

    # Pending order value per month: orders received that month, not completed/cancelled
    # price = unit_price * qty * (1 - discount%/100) * (1 + gst%/100)
    order_value_rows = db.query(
        extract('year', Order.created_at).label('year'),
        extract('month', Order.created_at).label('month'),
        func.sum(
            OrderItem.unit_price
            * OrderItem.quantity
            * (1 - func.coalesce(Order.discount_percentage, 0) / 100)
            * (1 + func.coalesce(OrderItem.gst_percentage, 0) / 100)
        ).label('order_value')
    ).join(OrderItem, OrderItem.order_id == Order.id).filter(
        Order.created_at >= fy_start,
        Order.created_at <= fy_end,
        Order.status.notin_(['completed', 'cancelled']),
        OrderItem.unit_price.isnot(None),
        OrderItem.inventory_id.isnot(None)
    ).group_by('year', 'month').all()

    invoice_map = {(int(r.year), int(r.month)): float(r.invoice_value) for r in invoice_rows}
    order_map = {(int(r.year), int(r.month)): float(r.order_value) for r in order_value_rows}

    result = []
    for i in range(12):
        month_num = ((4 - 1 + i) % 12) + 1
        year_num = fy_start_year + ((4 - 1 + i) // 12)
        key = (year_num, month_num)
        label = datetime(year_num, month_num, 1).strftime('%b')
        result.append({
            "month": label,
            "invoice_value": invoice_map.get(key, 0.0),
            "pending_order_value": order_map.get(key, 0.0),
        })

    return result


@router.get("/monthly-trend")
def get_monthly_trend(
    months: int = 6,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.DASHBOARD_VIEW))
):
    """Get monthly orders count and revenue for the last N months."""
    start_date = datetime.now() - timedelta(days=months * 31)

    revenue_rows = db.query(
        extract('year', Invoice.invoice_date).label('year'),
        extract('month', Invoice.invoice_date).label('month'),
        func.sum(Invoice.total_amount).label('revenue')
    ).filter(
        Invoice.invoice_date >= start_date.date(),
        Invoice.payment_status == "paid"
    ).group_by('year', 'month').order_by('year', 'month').all()

    order_rows = db.query(
        extract('year', Order.created_at).label('year'),
        extract('month', Order.created_at).label('month'),
        func.count(Order.id).label('count')
    ).filter(
        Order.created_at >= start_date
    ).group_by('year', 'month').order_by('year', 'month').all()

    revenue_map = {(int(r.year), int(r.month)): float(r.revenue) for r in revenue_rows}
    order_map = {(int(r.year), int(r.month)): int(r.count) for r in order_rows}

    result = []
    now = datetime.now()
    for i in range(months - 1, -1, -1):
        month = now.month - i
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        key = (year, month)
        label = datetime(year, month, 1).strftime('%b %Y')
        result.append({
            "month": label,
            "orders": order_map.get(key, 0),
            "revenue": revenue_map.get(key, 0.0)
        })

    return result


@router.get("/inventory-insights")
def get_inventory_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.DASHBOARD_VIEW))
):
    """Inventory metrics: top sold, out-of-stock pending, quotation pending."""
    now = datetime.now()
    fy_start_year = now.year if now.month >= 4 else now.year - 1
    fy_start = datetime(fy_start_year, 4, 1)

    # 1) Top 10 sold items this FY by dispatched quantity
    sold_rows = db.query(
        Inventory.sku,
        Inventory.description,
        Inventory.unit_price,
        func.sum(DispatchItem.quantity).label('total_sold')
    ).join(DispatchItem, DispatchItem.inventory_id == Inventory.id
    ).join(Dispatch, Dispatch.id == DispatchItem.dispatch_id
    ).filter(
        Dispatch.dispatch_date >= fy_start.date(),
        Inventory.is_active == True
    ).group_by(Inventory.id, Inventory.sku, Inventory.description, Inventory.unit_price
    ).order_by(func.sum(DispatchItem.quantity).desc()
    ).limit(10).all()

    top_sold = [
        {
            "sku": r.sku,
            "description": r.description,
            "unit_price": float(r.unit_price),
            "total_sold": int(r.total_sold),
        }
        for r in sold_rows
    ]

    # 2) Top 10 pending items with low stock (<5), ordered by pending order value
    out_of_stock_rows = db.query(
        Inventory.sku,
        Inventory.description,
        Inventory.unit_price,
        Inventory.stock_quantity,
        func.sum(OrderItem.quantity).label('ordered_qty'),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_value'),
    ).join(OrderItem, OrderItem.inventory_id == Inventory.id
    ).join(Order, Order.id == OrderItem.order_id
    ).filter(
        Inventory.stock_quantity < 5,
        Order.status.notin_(['completed', 'cancelled']),
        OrderItem.unit_price.isnot(None)
    ).group_by(Inventory.id, Inventory.sku, Inventory.description, Inventory.unit_price, Inventory.stock_quantity
    ).order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc()
    ).limit(10).all()

    top_out_of_stock = [
        {
            "sku": r.sku,
            "description": r.description,
            "unit_price": float(r.unit_price),
            "stock_quantity": r.stock_quantity,
            "ordered_qty": int(r.ordered_qty),
            "total_value": float(r.total_value),
        }
        for r in out_of_stock_rows
    ]

    # 3) Top 10 low-stock (<5) items in pre-PO decoded stages (decoded but no PO yet)
    _pre_po = ['order_request', 'pending_approval', 'approved', 'waiting_purchase_order']
    quotation_rows = db.query(
        Inventory.sku,
        Inventory.description,
        Inventory.unit_price,
        Inventory.stock_quantity,
        func.count(func.distinct(Order.id)).label('order_count'),
        func.sum(OrderItem.quantity).label('total_qty'),
        func.sum(
            OrderItem.quantity * OrderItem.unit_price
            * (1 - func.coalesce(Order.discount_percentage, 0) / 100)
            * (1 + func.coalesce(OrderItem.gst_percentage, 0) / 100)
        ).label('total_value'),
    ).join(OrderItem, OrderItem.inventory_id == Inventory.id
    ).join(Order, Order.id == OrderItem.order_id
    ).filter(
        Order.workflow_stage.in_(_pre_po),
        OrderItem.unit_price.isnot(None),
        Inventory.stock_quantity < 5
    ).group_by(Inventory.id, Inventory.sku, Inventory.description, Inventory.unit_price, Inventory.stock_quantity
    ).order_by(func.sum(
        OrderItem.quantity * OrderItem.unit_price
        * (1 - func.coalesce(Order.discount_percentage, 0) / 100)
        * (1 + func.coalesce(OrderItem.gst_percentage, 0) / 100)
    ).desc()
    ).limit(10).all()

    top_quotation_pending = [
        {
            "sku": r.sku,
            "description": r.description,
            "unit_price": float(r.unit_price),
            "stock_quantity": r.stock_quantity,
            "order_count": int(r.order_count),
            "total_qty": int(r.total_qty),
            "total_value": float(r.total_value),
        }
        for r in quotation_rows
    ]

    return {
        "top_sold_items": top_sold,
        "top_out_of_stock_pending": top_out_of_stock,
        "top_quotation_pending": top_quotation_pending,
    }


@router.get("/customer-insights")
def get_customer_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.DASHBOARD_VIEW))
):
    """Customer metrics: new customers, top revenue, top pending value."""
    now = datetime.now()
    fy_start_year = now.year if now.month >= 4 else now.year - 1
    fy_start = datetime(fy_start_year, 4, 1)

    # 1) Last 10 new customers
    new_cust_rows = db.query(Customer).order_by(Customer.created_at.desc()).limit(10).all()
    new_customers = [
        {
            "id": str(c.id),
            "name": c.name,
            "hospital_name": c.hospital_name,
            "city": c.city or "",
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in new_cust_rows
    ]

    # 2) Top 10 customers by revenue this FY (sum of dispatched item values)
    revenue_rows = db.query(
        Customer.id,
        Customer.name,
        Customer.hospital_name,
        func.sum(DispatchItem.quantity * OrderItem.unit_price).label('revenue'),
    ).join(Order, Order.customer_id == Customer.id
    ).join(OrderItem, OrderItem.order_id == Order.id
    ).join(DispatchItem, DispatchItem.order_item_id == OrderItem.id
    ).join(Dispatch, Dispatch.id == DispatchItem.dispatch_id
    ).filter(
        Dispatch.dispatch_date >= fy_start.date(),
        OrderItem.unit_price.isnot(None)
    ).group_by(Customer.id, Customer.name, Customer.hospital_name
    ).order_by(func.sum(DispatchItem.quantity * OrderItem.unit_price).desc()
    ).limit(10).all()

    top_revenue = [
        {
            "id": str(r.id),
            "name": r.name,
            "hospital_name": r.hospital_name,
            "revenue": float(r.revenue),
        }
        for r in revenue_rows
    ]

    # 3) Top 10 customers with highest pending order value
    # Includes every stage up to and including PO approval, plus the stages
    # that follow it (inventory_check, payment_pending) — i.e. every non-terminal stage.
    _pending_stages = [
        'order_request', 'decoding_approval', 'decoding',
        'quotation', 'quotation_generated', 'waiting_purchase_order',
        'po_approval', 'inventory_check', 'payment_pending',
    ]
    _dispatched_subq = db.query(
        DispatchItem.order_item_id,
        func.sum(DispatchItem.quantity).label('dispatched_qty')
    ).group_by(DispatchItem.order_item_id).subquery()

    pending_rows = db.query(
        Customer.id,
        Customer.name,
        Customer.hospital_name,
        func.sum(
            (OrderItem.quantity - func.coalesce(_dispatched_subq.c.dispatched_qty, 0))
            * OrderItem.unit_price
            * (1 - func.coalesce(Order.discount_percentage, 0) / 100)
            * (1 + func.coalesce(OrderItem.gst_percentage, 0) / 100)
        ).label('pending_value'),
    ).join(Order, Order.customer_id == Customer.id
    ).join(OrderItem, OrderItem.order_id == Order.id
    ).outerjoin(_dispatched_subq, _dispatched_subq.c.order_item_id == OrderItem.id
    ).filter(
        Order.workflow_stage.in_(_pending_stages),
        OrderItem.unit_price.isnot(None),
        OrderItem.inventory_id.isnot(None)
    ).group_by(Customer.id, Customer.name, Customer.hospital_name
    ).order_by(func.sum(
        (OrderItem.quantity - func.coalesce(_dispatched_subq.c.dispatched_qty, 0))
        * OrderItem.unit_price
        * (1 - func.coalesce(Order.discount_percentage, 0) / 100)
        * (1 + func.coalesce(OrderItem.gst_percentage, 0) / 100)
    ).desc()
    ).limit(10).all()

    top_pending = [
        {
            "id": str(r.id),
            "name": r.name,
            "hospital_name": r.hospital_name,
            "pending_value": float(r.pending_value) if r.pending_value else 0.0,
        }
        for r in pending_rows
    ]

    return {
        "new_customers": new_customers,
        "top_revenue_customers": top_revenue,
        "top_pending_customers": top_pending,
    }


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
