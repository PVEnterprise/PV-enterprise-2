"""
Order action tracking utilities.
Automatically logs actions to order notes with user and timestamp.
"""
from datetime import datetime
from typing import Optional
from app.models.order import Order
from app.models.user import User


def add_order_action(
    order: Order,
    action: str,
    user: User,
    details: Optional[str] = None
) -> None:
    """
    Add an action to order notes with timestamp and user info.
    
    Args:
        order: Order instance
        action: Action description (e.g., "Order Created", "Items Decoded")
        user: User who performed the action
        details: Optional additional details
    """
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    user_info = f"{user.full_name} ({user.role.name})"
    
    action_log = f"\n\n[{timestamp}] {action} by {user_info}"
    if details:
        action_log += f"\n{details}"
    
    if order.notes:
        order.notes += action_log
    else:
        order.notes = action_log.strip()
    
    # Update order timestamp
    order.updated_at = datetime.utcnow()
