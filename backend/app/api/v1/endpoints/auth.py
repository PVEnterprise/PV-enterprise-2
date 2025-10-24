"""
Authentication endpoints for login, logout, and token refresh.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type
)
from app.core.config import settings
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    Token,
    RefreshTokenRequest,
    UserWithRole
)
from app.api.deps import get_current_user


router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> Token:
    """
    User login endpoint.
    
    Authenticates user credentials and returns access and refresh tokens.
    
    Args:
        login_data: Login credentials (email and password)
        db: Database session
        
    Returns:
        Access and refresh tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role_name}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Token:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token
        db: Database session
        
    Returns:
        New access and refresh tokens
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    # Decode and verify refresh token
    payload = decode_token(refresh_data.refresh_token)
    verify_token_type(payload, "refresh")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role_name}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserWithRole)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information with role details
    """
    return current_user


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    User logout endpoint.
    
    Note: Since we're using JWT tokens, actual logout is handled client-side
    by removing the tokens. This endpoint is for logging purposes.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    # In a production system, you might want to:
    # 1. Add token to a blacklist (requires Redis or similar)
    # 2. Log the logout event
    # 3. Clear any server-side session data
    
    return {"message": "Successfully logged out"}
