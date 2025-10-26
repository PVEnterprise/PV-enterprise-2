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
        sales_rep_description=order_data.sales_rep_description,
        notes=order_data.notes
    )
    db.add(order)
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
        joinedload(Order.customer),
        joinedload(Order.attachments)
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
    item.quantity = decode_data.quantity if decode_data.quantity is not None else item.quantity
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
    from fastapi.responses import StreamingResponse
    from app.services.pdf_generator import generate_order_quotation_pdf
    
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
    
    # Generate PDF
    pdf_buffer = generate_order_quotation_pdf(order)
    
    # Return as downloadable file
    filename = f"Quotation_{order.order_number}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/{order_id}/quote-sent", response_model=dict)
def mark_quote_sent_to_customer(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark quotation as sent to customer.
    Changes workflow_stage to 'waiting_purchase_order'.
    Available for sales and executive roles.
    """
    # Check if user is sales or executive
    if current_user.role.name not in ['sales_rep', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sales representatives and executives can mark quotes as sent"
        )
    
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if order is in quotation stage
    if order.workflow_stage != "quotation":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be in quotation stage"
        )
    
    # Update workflow stage
    order.workflow_stage = "waiting_purchase_order"
    order.status = "quote_sent"
    order.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Quotation marked as sent to customer. Waiting for purchase order."}


@router.post("/{order_id}/request-po-approval", response_model=dict)
def request_po_approval(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request PO approval from executive.
    Requires at least one attachment (PO document).
    Changes workflow_stage to 'po_approval' and status to 'pending_po_approval'.
    Available for sales role.
    """
    # Check if user is sales or executive
    if current_user.role.name not in ['sales_rep', 'executive']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sales representatives can request PO approval"
        )
    
    from app.models.attachment import Attachment
    
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if order is waiting for PO
    if order.workflow_stage != "waiting_purchase_order":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be in waiting_purchase_order stage"
        )
    
    # Check if at least one attachment exists (query directly)
    attachment_count = db.query(Attachment).filter(
        Attachment.entity_type == "order",
        Attachment.entity_id == order.id
    ).count()
    
    if attachment_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload purchase order document before requesting approval"
        )
    
    # Create approval request
    approval = Approval(
        entity_type="order",
        entity_id=order.id,
        stage="po_approval",
        status="pending"
    )
    db.add(approval)
    
    # Update order workflow
    order.workflow_stage = "po_approval"
    order.status = "pending_po_approval"
    order.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "PO approval requested successfully"}


@router.post("/{order_id}/approve-po", response_model=dict)
def approve_purchase_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.APPROVAL_EXECUTE))
):
    """
    Approve purchase order.
    Changes workflow_stage to 'inventory_check'.
    Available for executive role only.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if order is in PO approval stage
    if order.workflow_stage != "po_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be in PO approval stage"
        )
    
    # Find pending approval
    approval = db.query(Approval).filter(
        Approval.entity_type == "order",
        Approval.entity_id == order.id,
        Approval.stage == "po_approval",
        Approval.status == "pending"
    ).first()
    
    if approval:
        approval.status = "approved"
        approval.approver_id = current_user.id
        approval.approved_at = datetime.utcnow()
    
    # Update all decoded order items status to "pending"
    # This marks them as ready for dispatch
    order_items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id,
        OrderItem.inventory_id.isnot(None)  # Only decoded items
    ).all()
    
    for item in order_items:
        item.status = "pending"
    
    # Update order workflow
    order.workflow_stage = "inventory_check"
    order.status = "po_approved"
    order.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Purchase order approved successfully"}


@router.post("/{order_id}/reject-po", response_model=dict)
def reject_purchase_order(
    order_id: UUID,
    rejection_data: OrderReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.APPROVAL_EXECUTE))
):
    """
    Reject purchase order with comments.
    Sends order back to waiting_purchase_order stage.
    Available for executive role only.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if order is in PO approval stage
    if order.workflow_stage != "po_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be in PO approval stage"
        )
    
    # Find pending approval
    approval = db.query(Approval).filter(
        Approval.entity_type == "order",
        Approval.entity_id == order.id,
        Approval.stage == "po_approval",
        Approval.status == "pending"
    ).first()
    
    if approval:
        approval.status = "rejected"
        approval.approver_id = current_user.id
        approval.approved_at = datetime.utcnow()
        approval.comments = rejection_data.reason
    
    # Update order - send back to waiting for PO
    order.workflow_stage = "waiting_purchase_order"
    order.status = "po_rejected"
    order.updated_at = datetime.utcnow()
    
    # Add rejection reason to order notes
    rejection_note = f"\n\n[PO Rejected by {current_user.full_name} on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]\n{rejection_data.reason}"
    if order.notes:
        order.notes += rejection_note
    else:
        order.notes = rejection_note.strip()
    
    db.commit()
    
    return {"message": "Purchase order rejected. Sales can re-upload and request approval again."}
