# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..schemas.auth import LoginRequest, Token, UserResponse
from ..auth.utils import (
    verify_password, create_access_token, 
    get_current_user, get_current_active_user
)
from datetime import timedelta, datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login endpoint that creates and returns JWT token"""
    try:
        # Find user
        user = db.query(User).filter(User.username == login_data.username).first()
        if not user or not verify_password(login_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for username: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning(f"Login attempt by inactive user: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive"
            )

        # Update last login time
        user.last_login = datetime.utcnow()
        db.commit()

        # Create access token
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=30)
        )

        logger.info(f"Successful login for user: {login_data.username}")
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.get("/me", response_model=dict)
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    """Get current user info"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": any(role.name == "admin" for role in current_user.roles) or current_user.is_superuser,
        "tasks": [task.name for task in current_user.tasks],
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user and cleanup their files"""
    try:
        cleanup_service = CleanupService(db)
        await cleanup_service.cleanup_user_files(current_user.id)
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout cleanup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error during logout"
        )