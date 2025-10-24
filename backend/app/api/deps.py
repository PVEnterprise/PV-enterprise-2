"""
API dependencies for authentication and authorization.
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.security import decode_token, verify_token_type
from app.core.permissions import Permission, require_permission
from app.models.user import User


# HTTP Bearer token security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_token(token)
    verify_token_type(payload, "access")
    
    user_id: Optional[UUID] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Current user if active
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


class PermissionChecker:
    """
    Dependency class for checking user permissions.
    
    Usage:
        @app.get("/orders/", dependencies=[Depends(PermissionChecker(Permission.ORDER_READ))])
        def get_orders():
            ...
    """
    
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """
        Check if current user has required permission.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Current user if authorized
            
        Raises:
            HTTPException: If user doesn't have required permission
        """
        require_permission(current_user.role_name, self.required_permission)
        return current_user


def require_executive(current_user: User = Depends(get_current_user)) -> User:
    """
    Require executive role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if executive
        
    Raises:
        HTTPException: If user is not executive
    """
    if current_user.role_name != "executive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Executive role required"
        )
    return current_user


def require_sales_rep(current_user: User = Depends(get_current_user)) -> User:
    """
    Require sales representative role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if sales rep
        
    Raises:
        HTTPException: If user is not sales rep
    """
    if current_user.role_name != "sales_rep":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales representative role required"
        )
    return current_user


def require_decoder(current_user: User = Depends(get_current_user)) -> User:
    """
    Require decoder role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if decoder
        
    Raises:
        HTTPException: If user is not decoder
    """
    if current_user.role_name != "decoder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Decoder role required"
        )
    return current_user


def require_quoter(current_user: User = Depends(get_current_user)) -> User:
    """
    Require quoter role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if quoter
        
    Raises:
        HTTPException: If user is not quoter
    """
    if current_user.role_name != "quoter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quoter role required"
        )
    return current_user


def require_inventory_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Require inventory admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if inventory admin
        
    Raises:
        HTTPException: If user is not inventory admin
    """
    if current_user.role_name != "inventory_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inventory admin role required"
        )
    return current_user
