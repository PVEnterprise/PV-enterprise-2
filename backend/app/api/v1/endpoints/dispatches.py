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
from app.schemas.dispatch import DispatchCreate, DispatchResponse, InvoiceListItem
from app.api.deps import get_db, get_current_user
from app.utils.order_tracking import add_order_action

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
    if current_user.role_name not in ['inventory_admin', 'executive']:
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

        # Validate alternate item if provided
        if item_data.alternate_inventory_id:
            if not item_data.alternate_quantity or item_data.alternate_quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="alternate_quantity is required when alternate_inventory_id is provided"
                )
            if item_data.alternate_quantity > item_data.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Alternate quantity ({item_data.alternate_quantity}) cannot exceed total dispatch quantity ({item_data.quantity})"
                )
            alt_inventory = db.query(Inventory).filter(Inventory.id == item_data.alternate_inventory_id).first()
            if not alt_inventory:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Alternate inventory item {item_data.alternate_inventory_id} not found"
                )
            if item_data.alternate_quantity > alt_inventory.stock_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for alternate item {alt_inventory.sku}. Available: {alt_inventory.stock_quantity}, Requested: {item_data.alternate_quantity}"
                )
            main_qty = item_data.quantity - item_data.alternate_quantity
            if main_qty > 0 and main_qty > inventory.stock_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {inventory.sku}. Available: {inventory.stock_quantity}, Requested: {main_qty}"
                )
        else:
            # No alternate — all quantity from main inventory
            if item_data.quantity > inventory.stock_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {inventory.sku} - {inventory.description or 'No description'}. Available: {inventory.stock_quantity}, Requested: {item_data.quantity}"
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
        terms=dispatch_data.terms,
        payment_terms=dispatch_data.payment_terms,
        po_number=dispatch_data.po_number,
        dc_number=dispatch_data.dc_number,
        invoice_number=dispatch_data.invoice_number,
        bank_account_name=dispatch_data.bank_account_name,
        bank_account_number=dispatch_data.bank_account_number,
        bank_name=dispatch_data.bank_name,
        bank_ifsc=dispatch_data.bank_ifsc,
        bank_branch=dispatch_data.bank_branch,
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
            quantity=item_data.quantity,
            alternate_inventory_id=item_data.alternate_inventory_id,
            alternate_quantity=item_data.alternate_quantity
        )
        db.add(dispatch_item)
        
        # Update inventory stock
        if item_data.alternate_inventory_id and item_data.alternate_quantity:
            # Split deduction: main gets (total - alternate), alternate gets alternate_quantity
            main_qty = item_data.quantity - item_data.alternate_quantity
            alt_inventory = db.query(Inventory).filter(Inventory.id == item_data.alternate_inventory_id).first()
            alt_inventory.stock_quantity -= item_data.alternate_quantity
            if main_qty > 0:
                inventory = db.query(Inventory).filter(Inventory.id == item_data.inventory_id).first()
                inventory.stock_quantity -= main_qty
        else:
            # All quantity from main inventory
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
    
    # Track dispatch action
    dispatched_items = []
    for item_data in dispatch_data.items:
        order_item = db.query(OrderItem).filter(OrderItem.id == item_data.order_item_id).first()
        inventory = db.query(Inventory).filter(Inventory.id == item_data.inventory_id).first()
        dispatched_items.append(f"- {inventory.sku} - {inventory.description or 'No description'} (Qty: {item_data.quantity})")
    
    item_list = "\n".join(dispatched_items)
    add_order_action(
        order=order,
        action="Dispatch Created",
        user=current_user,
        details=f"Dispatch #{dispatch.dispatch_number}\nCourier: {dispatch_data.courier_name}\nTracking: {dispatch_data.tracking_number}\nItems dispatched:\n{item_list}"
    )
    
    if all_completed:
        order.status = "payment_pending"
        order.workflow_stage = "payment_pending"
        add_order_action(
            order=order,
            action="All Items Dispatched",
            user=current_user,
            details="All order items have been dispatched. Waiting for payment confirmation."
        )
    elif any_partial:
        order.status = "partially_dispatched"
    
    db.commit()
    db.refresh(dispatch)
    
    # Load relationships including inventory items
    dispatch = db.query(Dispatch).options(
        joinedload(Dispatch.items).joinedload(DispatchItem.inventory_item)
    ).filter(Dispatch.id == dispatch.id).first()
    
    return dispatch


@router.get("/invoices", response_model=List[InvoiceListItem])
def list_invoiced_dispatches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all dispatches that have a generated invoice, latest first.
    Available to executive, quoter, and decoder roles.
    """
    if current_user.role_name not in ['executive', 'quoter', 'decoder']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view invoices"
        )

    dispatches = db.query(Dispatch).options(
        joinedload(Dispatch.order).joinedload(Order.customer)
    ).filter(
        Dispatch.invoice_number.isnot(None),
        Dispatch.invoice_number != ''
    ).order_by(Dispatch.dispatch_date.desc(), Dispatch.created_at.desc()).all()

    return [
        InvoiceListItem(
            dispatch_id=d.id,
            dispatch_number=d.dispatch_number,
            invoice_number=d.invoice_number,
            dispatch_date=d.dispatch_date,
            order_id=d.order_id,
            order_number=d.order.order_number,
            customer_name=d.order.customer.name,
            created_at=d.created_at,
        )
        for d in dispatches
    ]


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


@router.get("/{dispatch_id}/invoice/pdf")
def download_dispatch_invoice_pdf(
    dispatch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate and download TAX INVOICE PDF for a dispatch.
    """
    from fastapi.responses import StreamingResponse
    from app.services.invoice_pdf_generator import generate_invoice_pdf
    from app.models.invoice import Invoice
    
    # Fetch dispatch with all relationships
    dispatch = db.query(Dispatch).options(
        joinedload(Dispatch.items).joinedload(DispatchItem.inventory_item),
        joinedload(Dispatch.items).joinedload(DispatchItem.order_item)
    ).filter(Dispatch.id == dispatch_id).first()
    
    if not dispatch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispatch not found"
        )
    
    # Check if dispatch has an invoice, if not create a temporary one for PDF generation
    if dispatch.invoice_id:
        # Fetch existing invoice
        invoice = db.query(Invoice).filter(Invoice.id == dispatch.invoice_id).first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
    else:
        # Create a temporary invoice object for PDF generation (not saved to DB)
        from datetime import date, timedelta
        from decimal import Decimal
        
        # Calculate totals from dispatch items
        subtotal = Decimal('0.00')
        total_igst = Decimal('0.00')
        
        for dispatch_item in dispatch.items:
            order_item = dispatch_item.order_item
            qty = dispatch_item.quantity
            rate = float(order_item.unit_price or 0)
            
            # Get discount from order
            order = db.query(Order).filter(Order.id == dispatch.order_id).first()
            discount_percentage = float(getattr(order, 'discount_percentage', 0) or 0)
            
            # Apply discount
            item_discount = rate * (discount_percentage / 100)
            discounted_rate = rate - item_discount
            amount = qty * discounted_rate
            
            igst_pct = float(order_item.gst_percentage or 0)
            igst_amt = amount * (igst_pct / 100)
            
            subtotal += Decimal(str(amount))
            total_igst += Decimal(str(igst_amt))
        
        grand_total = subtotal + total_igst
        
        # Create temporary invoice object
        class TempInvoice:
            def __init__(self):
                self.invoice_number = dispatch.invoice_number or f"TEMP-{dispatch.dispatch_number}"
                self.invoice_date = dispatch.dispatch_date or date.today()
                self.due_date = self.invoice_date + timedelta(days=30)
                self.payment_terms = dispatch.terms or ""
                self.notes = ""
                self.subtotal = subtotal
                self.gst_amount = total_igst
                self.total_amount = grand_total
        
        invoice = TempInvoice()
    
    # Fetch order with customer, items, and quotations
    from app.models.quotation import Quotation, QuotationItem
    order = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.items).joinedload(OrderItem.inventory_item),
        joinedload(Order.quotations).joinedload(Quotation.items)
    ).filter(Order.id == dispatch.order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Generate PDF
    pdf_buffer = generate_invoice_pdf(order, invoice, dispatch)
    
    # Return as downloadable file
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.delete("/{dispatch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dispatch(
    dispatch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a dispatch, restore inventory stock, and recalculate order item statuses.
    Available for inventory_admin and executive roles.
    """
    if current_user.role_name not in ['inventory_admin', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only inventory admins and executives can delete dispatches"
        )

    dispatch = db.query(Dispatch).options(
        joinedload(Dispatch.items)
    ).filter(Dispatch.id == dispatch_id).first()

    if not dispatch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found")

    order_id = dispatch.order_id
    dispatch_number = dispatch.dispatch_number

    # Restore inventory stock
    for item in dispatch.items:
        if item.alternate_inventory_id and item.alternate_quantity:
            main_qty = item.quantity - item.alternate_quantity
            alt_inv = db.query(Inventory).filter(Inventory.id == item.alternate_inventory_id).first()
            if alt_inv:
                alt_inv.stock_quantity += item.alternate_quantity
            if main_qty > 0:
                main_inv = db.query(Inventory).filter(Inventory.id == item.inventory_id).first()
                if main_inv:
                    main_inv.stock_quantity += main_qty
        else:
            inv = db.query(Inventory).filter(Inventory.id == item.inventory_id).first()
            if inv:
                inv.stock_quantity += item.quantity

    db.delete(dispatch)
    db.flush()

    # Recalculate order item statuses after deletion
    all_order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    for order_item in all_order_items:
        total_dispatched = sum(di.quantity for di in order_item.dispatch_items)
        if total_dispatched >= order_item.quantity:
            order_item.status = "completed"
        elif total_dispatched > 0:
            order_item.status = "partial"
        else:
            order_item.status = "pending"

    # Revert order workflow stage
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        all_completed = all(oi.status == "completed" for oi in all_order_items)
        any_dispatched = any(oi.status in ["partial", "completed"] for oi in all_order_items)

        if all_completed:
            order.status = "payment_pending"
            order.workflow_stage = "payment_pending"
        elif any_dispatched:
            order.status = "partially_dispatched"
            order.workflow_stage = "inventory_check"
        else:
            order.status = "confirmed"
            order.workflow_stage = "inventory_check"

        add_order_action(
            order=order,
            action="Dispatch Deleted",
            user=current_user,
            details=f"Dispatch #{dispatch_number} deleted. Inventory stock restored."
        )

    db.commit()
    return None


@router.get("/{dispatch_id}/delivery-challan/pdf")
@router.get("/{dispatch_id}/dc/pdf")
def download_delivery_challan_pdf(
    dispatch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate and download Delivery Challan PDF for a dispatch.
    Available at both /delivery-challan/pdf and /dc/pdf
    """
    from fastapi.responses import StreamingResponse
    from app.services.delivery_challan_pdf_generator import generate_delivery_challan_pdf
    from sqlalchemy.orm import joinedload
    
    # Fetch dispatch with all relationships
    dispatch = db.query(Dispatch).options(
        joinedload(Dispatch.items).joinedload(DispatchItem.inventory_item),
        joinedload(Dispatch.order)
    ).filter(Dispatch.id == dispatch_id).first()
    
    if not dispatch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispatch not found"
        )
    
    # Fetch order with customer
    order = db.query(Order).options(
        joinedload(Order.customer)
    ).filter(Order.id == dispatch.order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Generate PDF
    pdf_buffer = generate_delivery_challan_pdf(dispatch, order, order.customer)
    
    # Return as downloadable file
    filename = f"DC_{dispatch.dispatch_number}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
