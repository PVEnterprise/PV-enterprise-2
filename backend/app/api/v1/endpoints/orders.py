"""
Order management endpoints with workflow support.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission, can_access_all_orders
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.approval import Approval
from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderWithItems,
    OrderSummary,
    OrderItemUpdate,
    OrderItemDecode,
    OrderItemDecodeMultiple,
    OrderStatusUpdate,
    OrderReject
)


router = APIRouter()


def generate_order_number(db: Session) -> str:
    """Generate unique order number."""
    year = datetime.now().year
    # Get count of orders this year
    count = db.query(Order).filter(
        Order.order_number.like(f"ORD-{year}-%")
    ).count()
    return f"ORD-{year}-{count + 1:04d}"


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.ORDER_CREATE))
):
    """
    Create a new order request.
    
    Sales representatives can create orders for customers.
    """
    # Verify customer exists
    customer = db.query(Customer).filter(Customer.id == order_data.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Create order
    order = Order(
        order_number=generate_order_number(db),
        customer_id=order_data.customer_id,
        sales_rep_id=current_user.id,
        status="draft",
        workflow_stage="order_request",
        priority=order_data.priority,
        source=order_data.source,
        notes=order_data.notes
    )
    db.add(order)
    db.flush()  # Get order ID
    
    # Create order items
    for item_data in order_data.items:
        order_item = OrderItem(
            order_id=order.id,
            item_description=item_data.item_description,
            quantity=item_data.quantity,
            status="pending",
            notes=item_data.notes
        )
        db.add(order_item)
    
    db.commit()
    db.refresh(order)
    
    return order


@router.get("/", response_model=List[OrderSummary])
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    workflow_stage: Optional[str] = None,
    customer_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List orders with filtering and pagination.
    
    - Sales reps see only their own orders
    - Other roles see all orders
    """
    query = db.query(Order).options(
        joinedload(Order.customer),  # Eager load customer relationship
        joinedload(Order.items)       # Eager load items for count
    )
    
    # Apply role-based filtering
    # Decoders, quoters, and inventory admins can see all orders for their workflow
    allowed_roles = ["decoder", "quoter", "inventory_admin", "executive"]
    
    if not can_access_all_orders(current_user.role_name):
        # Allow workflow roles to access all orders
        if current_user.role_name not in allowed_roles:
            # Sales reps can only see their own orders
            query = query.filter(Order.sales_rep_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Order.status == status)
    if workflow_stage:
        query = query.filter(Order.workflow_stage == workflow_stage)
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    
    # Order by creation date (newest first)
    query = query.order_by(Order.created_at.desc())
    
    # Pagination
    orders = query.offset(skip).limit(limit).all()
    
    # Build summary response with customer data
    summaries = []
    for order in orders:
        summaries.append(OrderSummary(
            id=order.id,
            order_number=order.order_number,
            customer_id=order.customer_id,
            customer=order.customer,  # Include customer object
            status=order.status,
            workflow_stage=order.workflow_stage,
            priority=order.priority,
            total_items=len(order.items),
            created_at=order.created_at,
            updated_at=order.updated_at,
            created_by=order.created_by,
            updated_by=order.updated_by
        ))
    
    return summaries


@router.get("/{order_id}", response_model=OrderWithItems)
def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get order details with items.
    """
    from sqlalchemy.orm import joinedload
    
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.inventory_item),
        joinedload(Order.customer)
    ).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check access permissions
    # Decoders, quoters, and inventory admins can see all orders for their workflow
    allowed_roles = ["decoder", "quoter", "inventory_admin", "executive"]
    
    if not can_access_all_orders(current_user.role_name):
        # Allow workflow roles to access all orders
        if current_user.role_name not in allowed_roles:
            # Sales reps can only see their own orders
            if order.sales_rep_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
    
    return order


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: UUID,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.ORDER_UPDATE))
):
    """
    Update order details.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update fields
    update_data = order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.ORDER_DELETE))
):
    """
    Delete an order (soft delete by setting status to cancelled).
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Soft delete
    order.status = "cancelled"
    order.updated_at = datetime.utcnow()
    db.commit()
    
    return None


@router.put("/{order_id}/decoded-items", response_model=dict)
def update_decoded_items(
    order_id: UUID,
    decode_data: OrderItemDecodeMultiple,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update all decoded items for an order.
    Deletes existing decoded items and creates new ones.
    """
    # Verify order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Delete ALL existing items for this order (both decoded and undecoded)
    db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).delete()
    
    # Create new decoded items
    for decode_item in decode_data.items:
        inventory = db.query(Inventory).filter(Inventory.id == decode_item.inventory_id).first()
        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item {decode_item.inventory_id} not found"
            )
        
        new_item = OrderItem(
            order_id=order_id,
            item_description=f"Decoded: {inventory.item_name}",
            quantity=decode_item.quantity or 1,
            inventory_id=decode_item.inventory_id,
            decoded_by=current_user.id,
            unit_price=decode_item.unit_price or inventory.unit_price,
            gst_percentage=decode_item.gst_percentage or 18.00,
            status="decoded"
        )
        db.add(new_item)
    
    db.commit()
    
    return {
        "message": f"Updated {len(decode_data.items)} decoded items",
        "items_count": len(decode_data.items)
    }


@router.post("/{order_id}/items/{item_id}/decode-multiple", response_model=dict)
def decode_order_item_multiple(
    order_id: UUID,
    item_id: UUID,
    decode_data: OrderItemDecodeMultiple,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Decode an order item by mapping it to multiple inventory items.
    
    This creates separate order items for each inventory item decoded.
    """
    # Verify order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Verify original order item exists
    original_item = db.query(OrderItem).filter(
        OrderItem.id == item_id,
        OrderItem.order_id == order_id
    ).first()
    
    if not original_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order item not found"
        )
    
    # Store original description
    original_description = original_item.item_description
    original_notes = original_item.notes
    
    # Process first item - update the original
    first_decode = decode_data.items[0]
    inventory = db.query(Inventory).filter(Inventory.id == first_decode.inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inventory item {first_decode.inventory_id} not found")
    
    original_item.inventory_id = first_decode.inventory_id
    original_item.decoded_by = current_user.id
    original_item.quantity = first_decode.quantity or 1
    original_item.unit_price = first_decode.unit_price or inventory.unit_price
    original_item.gst_percentage = first_decode.gst_percentage or 18.00
    original_item.status = "decoded"
    original_item.updated_at = datetime.utcnow()
    
    # Create additional items for remaining inventory items
    for decode_item in decode_data.items[1:]:
        inventory = db.query(Inventory).filter(Inventory.id == decode_item.inventory_id).first()
        if not inventory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inventory item {decode_item.inventory_id} not found")
        
        new_item = OrderItem(
            order_id=order_id,
            item_description=original_description,
            quantity=decode_item.quantity or 1,
            inventory_id=decode_item.inventory_id,
            decoded_by=current_user.id,
            unit_price=decode_item.unit_price or inventory.unit_price,
            gst_percentage=decode_item.gst_percentage or 18.00,
            status="decoded",
            notes=original_notes
        )
        db.add(new_item)
    
    db.commit()
    
    return {
        "message": f"Item decoded successfully with {len(decode_data.items)} inventory item(s)",
        "all_decoded": order.is_fully_decoded,
        "items_created": len(decode_data.items)
    }


@router.post("/{order_id}/items/{item_id}/decode", response_model=dict)
def decode_order_item(
    order_id: UUID,
    item_id: UUID,
    decode_data: OrderItemDecode,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Decode an order item by mapping it to a single inventory item.
    
    Decoders use this endpoint to map customer descriptions to SKUs.
    """
    # Verify order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Verify order item exists
    item = db.query(OrderItem).filter(
        OrderItem.id == item_id,
        OrderItem.order_id == order_id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order item not found"
        )
    
    # Verify inventory exists
    inventory = db.query(Inventory).filter(
        Inventory.id == decode_data.inventory_id
    ).first()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Update order item
    item.inventory_id = decode_data.inventory_id
    item.decoded_by = current_user.id
    item.unit_price = decode_data.unit_price or inventory.unit_price
    item.gst_percentage = decode_data.gst_percentage or 18.00
    item.status = "decoded"
    item.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Check if all items are decoded
    if order.is_fully_decoded:
        order.workflow_stage = "decoding_approval"
        order.status = "pending_approval"
        db.commit()
    
    return {"message": "Item decoded successfully", "all_decoded": order.is_fully_decoded}


@router.post("/{order_id}/submit-for-approval", response_model=dict)
def submit_order_for_approval(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit decoded order for executive approval.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if not order.is_fully_decoded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All items must be decoded before submission"
        )
    
    # Update order status
    order.workflow_stage = "decoding_approval"
    order.status = "pending_approval"
    order.updated_at = datetime.utcnow()
    
    # Create approval record
    approval = Approval(
        entity_type="order",
        entity_id=order.id,
        stage="decoding_approval",
        approver_id=None,  # Will be assigned to executive
        status="pending"
    )
    db.add(approval)
    
    db.commit()
    
    return {"message": "Order submitted for approval"}


@router.post("/{order_id}/approve", response_model=dict)
def approve_order(
    order_id: UUID,
    comments: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.ORDER_APPROVE))
):
    """
    Approve order at current workflow stage.
    
    Only executives can approve orders.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update approval record
    approval = db.query(Approval).filter(
        Approval.entity_type == "order",
        Approval.entity_id == order.id,
        Approval.status == "pending"
    ).first()
    
    if approval:
        approval.approver_id = current_user.id
        approval.status = "approved"
        approval.comments = comments
        approval.approved_at = datetime.utcnow()
    
    # Update order workflow
    if order.workflow_stage == "decoding_approval":
        order.workflow_stage = "quotation"
        order.status = "approved"
    elif order.workflow_stage == "po_approval":
        order.workflow_stage = "inventory_check"
        order.status = "approved"
    
    order.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Order approved successfully"}


@router.post("/{order_id}/reject", response_model=dict)
def reject_order(
    order_id: UUID,
    reject_data: OrderReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.ORDER_APPROVE))
):
    """
    Reject order and send back to draft for decoder to update.
    
    Only executives can reject orders.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update approval record
    approval = db.query(Approval).filter(
        Approval.entity_type == "order",
        Approval.entity_id == order.id,
        Approval.status == "pending"
    ).first()
    
    if approval:
        approval.approver_id = current_user.id
        approval.status = "rejected"
        approval.comments = reject_data.reason
        approval.approved_at = datetime.utcnow()
    
    # Update order status - send back to draft for decoder to update
    order.status = "draft"
    order.workflow_stage = "decoding"
    order.updated_at = datetime.utcnow()
    
    # Add rejection reason to order notes
    rejection_note = f"\n\n[REJECTED by {current_user.full_name} on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]\n{reject_data.reason}"
    if order.notes:
        order.notes += rejection_note
    else:
        order.notes = rejection_note.strip()
    
    db.commit()
    
    return {"message": "Order rejected and sent back to draft for decoder to update"}


@router.get("/{order_id}/quotation/pdf")
def generate_quotation_pdf(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate and download quotation PDF for approved order.
    
    Available for sales and executive roles.
    """
    from fastapi.responses import Response
    from sqlalchemy.orm import joinedload
    
    # Fetch order with all relationships
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.inventory_item),
        joinedload(Order.customer)
    ).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if order is approved
    if order.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be approved before generating quotation"
        )
    
    # Generate simple HTML quotation (can be enhanced with PDF library later)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Quotation - {order.order_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            .total {{ font-weight: bold; font-size: 1.2em; }}
            .header {{ margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>QUOTATION</h1>
            <p><strong>Order Number:</strong> {order.order_number}</p>
            <p><strong>Customer:</strong> {order.customer.hospital_name if order.customer else 'N/A'}</p>
            <p><strong>Contact:</strong> {order.customer.contact_person if order.customer else 'N/A'}</p>
            <p><strong>Email:</strong> {order.customer.email if order.customer else 'N/A'}</p>
            <p><strong>Date:</strong> {order.created_at.strftime('%Y-%m-%d')}</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th>SKU</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>GST %</th>
                    <th>Subtotal</th>
                    <th>GST Amount</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """
    
    grand_subtotal = 0
    grand_gst = 0
    grand_total = 0
    
    for item in order.items:
        if item.inventory_item and item.unit_price:
            subtotal = float(item.quantity * item.unit_price)
            gst_amount = float(subtotal * item.gst_percentage / 100)
            total = subtotal + gst_amount
            
            grand_subtotal += subtotal
            grand_gst += gst_amount
            grand_total += total
            
            html_content += f"""
                <tr>
                    <td>{item.inventory_item.item_name}</td>
                    <td>{item.inventory_item.sku}</td>
                    <td>{item.quantity}</td>
                    <td>₹{float(item.unit_price):,.2f}</td>
                    <td>{float(item.gst_percentage):.2f}%</td>
                    <td>₹{subtotal:,.2f}</td>
                    <td>₹{gst_amount:,.2f}</td>
                    <td>₹{total:,.2f}</td>
                </tr>
            """
    
    html_content += f"""
            </tbody>
            <tfoot>
                <tr class="total">
                    <td colspan="5">TOTAL</td>
                    <td>₹{grand_subtotal:,.2f}</td>
                    <td>₹{grand_gst:,.2f}</td>
                    <td>₹{grand_total:,.2f}</td>
                </tr>
            </tfoot>
        </table>
        
        <div style="margin-top: 40px;">
            <p><strong>Terms and Conditions:</strong></p>
            <ul>
                <li>Payment terms: Net 30 days</li>
                <li>Delivery: As per agreed schedule</li>
                <li>Prices are subject to change without notice</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename=quotation_{order.order_number}.html"
        }
    )
