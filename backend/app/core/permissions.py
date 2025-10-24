"""
Role-Based Access Control (RBAC) permissions system.
Defines permissions for each role and provides authorization utilities.
"""
from enum import Enum
from typing import List, Dict, Set
from fastapi import HTTPException, status


class Role(str, Enum):
    """User roles in the system."""
    EXECUTIVE = "executive"
    SALES_REP = "sales_rep"
    DECODER = "decoder"
    QUOTER = "quoter"
    INVENTORY_ADMIN = "inventory_admin"


class Permission(str, Enum):
    """Granular permissions for resources."""
    # Order permissions
    ORDER_CREATE = "order:create"
    ORDER_READ = "order:read"
    ORDER_READ_ALL = "order:read_all"
    ORDER_UPDATE = "order:update"
    ORDER_DELETE = "order:delete"
    ORDER_APPROVE = "order:approve"
    
    # Inventory permissions
    INVENTORY_CREATE = "inventory:create"
    INVENTORY_READ = "inventory:read"
    INVENTORY_UPDATE = "inventory:update"
    INVENTORY_DELETE = "inventory:delete"
    
    # Quotation permissions
    QUOTATION_CREATE = "quotation:create"
    QUOTATION_READ = "quotation:read"
    QUOTATION_UPDATE = "quotation:update"
    QUOTATION_DELETE = "quotation:delete"
    QUOTATION_APPROVE = "quotation:approve"
    
    # Invoice permissions
    INVOICE_CREATE = "invoice:create"
    INVOICE_READ = "invoice:read"
    INVOICE_UPDATE = "invoice:update"
    INVOICE_DELETE = "invoice:delete"
    INVOICE_APPROVE = "invoice:approve"
    
    # Customer permissions
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_READ = "customer:read"
    CUSTOMER_UPDATE = "customer:update"
    CUSTOMER_DELETE = "customer:delete"
    
    # Dashboard permissions
    DASHBOARD_VIEW = "dashboard:view"
    DASHBOARD_ANALYTICS = "dashboard:analytics"
    
    # User management permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Approval permissions
    APPROVAL_EXECUTE = "approval:execute"
    
    # Dispatch permissions
    DISPATCH_CREATE = "dispatch:create"
    DISPATCH_READ = "dispatch:read"
    DISPATCH_UPDATE = "dispatch:update"


# Role-based permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.EXECUTIVE: {
        # Full access to orders
        Permission.ORDER_CREATE,
        Permission.ORDER_READ,
        Permission.ORDER_READ_ALL,
        Permission.ORDER_UPDATE,
        Permission.ORDER_DELETE,
        Permission.ORDER_APPROVE,
        
        # Full access to inventory
        Permission.INVENTORY_CREATE,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_UPDATE,
        Permission.INVENTORY_DELETE,
        
        # Full access to quotations
        Permission.QUOTATION_CREATE,
        Permission.QUOTATION_READ,
        Permission.QUOTATION_UPDATE,
        Permission.QUOTATION_DELETE,
        Permission.QUOTATION_APPROVE,
        
        # Full access to invoices
        Permission.INVOICE_CREATE,
        Permission.INVOICE_READ,
        Permission.INVOICE_UPDATE,
        Permission.INVOICE_DELETE,
        Permission.INVOICE_APPROVE,
        
        # Customer management
        Permission.CUSTOMER_CREATE,
        Permission.CUSTOMER_READ,
        Permission.CUSTOMER_UPDATE,
        Permission.CUSTOMER_DELETE,
        
        # Dashboard access
        Permission.DASHBOARD_VIEW,
        Permission.DASHBOARD_ANALYTICS,
        
        # User management
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        
        # Approvals
        Permission.APPROVAL_EXECUTE,
        
        # Dispatch
        Permission.DISPATCH_CREATE,
        Permission.DISPATCH_READ,
        Permission.DISPATCH_UPDATE,
    },
    
    Role.SALES_REP: {
        # Can create orders and view own orders
        Permission.ORDER_CREATE,
        Permission.ORDER_READ,  # Limited to own orders
        
        # Can only view customers (read-only)
        Permission.CUSTOMER_READ,
        
        # Basic dashboard view
        Permission.DASHBOARD_VIEW,
    },
    
    Role.DECODER: {
        # Can read orders assigned to them and update items
        Permission.ORDER_READ,
        Permission.ORDER_UPDATE,  # Limited to decoding
        
        # Read-only inventory access
        Permission.INVENTORY_READ,
        
        # Can view customers
        Permission.CUSTOMER_READ,
        
        # Basic dashboard
        Permission.DASHBOARD_VIEW,
    },
    
    Role.QUOTER: {
        # Can read orders and create quotations
        Permission.ORDER_READ,
        
        # Full quotation access
        Permission.QUOTATION_CREATE,
        Permission.QUOTATION_READ,
        Permission.QUOTATION_UPDATE,
        Permission.QUOTATION_DELETE,
        
        # Full invoice access
        Permission.INVOICE_CREATE,
        Permission.INVOICE_READ,
        Permission.INVOICE_UPDATE,
        Permission.INVOICE_DELETE,
        
        # Read inventory for pricing
        Permission.INVENTORY_READ,
        
        # Read customers
        Permission.CUSTOMER_READ,
        
        # Dashboard access
        Permission.DASHBOARD_VIEW,
    },
    
    Role.INVENTORY_ADMIN: {
        # Read orders to fulfill
        Permission.ORDER_READ,
        
        # Full inventory access
        Permission.INVENTORY_CREATE,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_UPDATE,
        Permission.INVENTORY_DELETE,
        
        # Dispatch management
        Permission.DISPATCH_CREATE,
        Permission.DISPATCH_READ,
        Permission.DISPATCH_UPDATE,
        
        # Read customers
        Permission.CUSTOMER_READ,
        
        # Dashboard access
        Permission.DASHBOARD_VIEW,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """
    Get all permissions for a given role.
    
    Args:
        role: User role
        
    Returns:
        Set of permissions for the role
    """
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(user_role: str, required_permission: Permission) -> bool:
    """
    Check if a user role has a specific permission.
    
    Args:
        user_role: User's role as string
        required_permission: Permission to check
        
    Returns:
        True if role has permission, False otherwise
    """
    try:
        role = Role(user_role)
        permissions = get_role_permissions(role)
        return required_permission in permissions
    except ValueError:
        return False


def require_permission(user_role: str, required_permission: Permission) -> None:
    """
    Require a specific permission, raise exception if not authorized.
    
    Args:
        user_role: User's role as string
        required_permission: Permission to check
        
    Raises:
        HTTPException: If user doesn't have required permission
    """
    if not has_permission(user_role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {required_permission.value}"
        )


def require_any_permission(
    user_role: str,
    required_permissions: List[Permission]
) -> None:
    """
    Require at least one of the specified permissions.
    
    Args:
        user_role: User's role as string
        required_permissions: List of permissions (user needs at least one)
        
    Raises:
        HTTPException: If user doesn't have any of the required permissions
    """
    for permission in required_permissions:
        if has_permission(user_role, permission):
            return
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions"
    )


def require_all_permissions(
    user_role: str,
    required_permissions: List[Permission]
) -> None:
    """
    Require all of the specified permissions.
    
    Args:
        user_role: User's role as string
        required_permissions: List of permissions (user needs all)
        
    Raises:
        HTTPException: If user doesn't have all required permissions
    """
    for permission in required_permissions:
        require_permission(user_role, permission)


def can_approve(user_role: str) -> bool:
    """
    Check if user can approve orders/quotations/invoices.
    
    Args:
        user_role: User's role as string
        
    Returns:
        True if user can approve, False otherwise
    """
    return has_permission(user_role, Permission.APPROVAL_EXECUTE)


def can_access_all_orders(user_role: str) -> bool:
    """
    Check if user can access all orders or only their own.
    
    Args:
        user_role: User's role as string
        
    Returns:
        True if user can access all orders, False if limited to own orders
    """
    return has_permission(user_role, Permission.ORDER_READ_ALL)
