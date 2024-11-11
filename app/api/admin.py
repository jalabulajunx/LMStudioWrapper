# app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, Role, Task
from ..schemas.admin import UserCreate, UserUpdate, UserResponse, RoleResponse, TaskResponse
from ..auth.utils import get_current_admin_user, get_password_hash
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all users"""
    try:
        users = db.query(User).all()
        return users
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving users"
        )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user details"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new user"""
    try:
        # Check if username or email already exists
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            is_active=user_data.is_active
        )

        # Add roles
        roles = db.query(Role).filter(Role.id.in_(user_data.roles)).all()
        user.roles = roles

        # Add tasks
        tasks = db.query(Task).filter(Task.id.in_(user_data.tasks)).all()
        user.tasks = tasks

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user"""
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check username/email uniqueness if changed
        if user_data.username and user_data.username != user.username:
            if db.query(User).filter(User.username == user_data.username).first():
                raise HTTPException(status_code=400, detail="Username already taken")
            user.username = user_data.username

        if user_data.email and user_data.email != user.email:
            if db.query(User).filter(User.email == user_data.email).first():
                raise HTTPException(status_code=400, detail="Email already registered")
            user.email = user_data.email

        # Update fields
        if user_data.full_name:
            user.full_name = user_data.full_name
        if user_data.password:
            user.hashed_password = get_password_hash(user_data.password)
        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        # Update roles if provided
        if user_data.roles is not None:
            roles = db.query(Role).filter(Role.id.in_(user_data.roles)).all()
            user.roles = roles

        # Update tasks if provided
        if user_data.tasks is not None:
            tasks = db.query(Task).filter(Task.id.in_(user_data.tasks)).all()
            user.tasks = tasks

        db.commit()
        db.refresh(user)
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete user"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent deleting yourself
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting user"
        )

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all roles"""
    try:
        roles = db.query(Role).all()
        return roles
    except Exception as e:
        logger.error(f"Error listing roles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving roles"
        )

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all tasks"""
    try:
        tasks = db.query(Task).all()
        return tasks
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving tasks"
        )