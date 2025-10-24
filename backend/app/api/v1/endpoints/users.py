"""
User management endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.core.security import get_password_hash
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserUpdate, UserWithRole, RoleResponse


router = APIRouter()


@router.post("/", response_model=UserWithRole, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.USER_CREATE))
):
    """Create new user (executives only)."""
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role_id=user_data.role_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/")
def list_users(
    search: str = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.USER_READ))
):
    """List all users with role information."""
    query = db.query(User).options(joinedload(User.role))
    
    # Apply search filter
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_filter)) |
            (User.email.ilike(search_filter))
        )
    
    users = query.all()
    
    # Build response with name and role_name for frontend compatibility
    result = []
    for user in users:
        user_dict = {
            "id": str(user.id),
            "email": user.email,
            "name": user.full_name,  # Frontend expects 'name'
            "full_name": user.full_name,
            "role_id": str(user.role_id),
            "role_name": user.role.name if user.role else None,  # Frontend expects 'role_name'
            "is_active": user.is_active,
            "last_login": user.last_login,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "role": {
                "id": str(user.role.id),
                "name": user.role.name,
                "description": user.role.description,
                "permissions": user.role.permissions,
                "created_at": user.role.created_at,
                "updated_at": user.role.updated_at
            } if user.role else None
        }
        result.append(user_dict)
    
    return result


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available roles."""
    roles = db.query(Role).all()
    return roles


@router.get("/{user_id}", response_model=UserWithRole)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.USER_READ))
):
    """Get user details."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
