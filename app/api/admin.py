# app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from ..database import get_db
from ..models.user import User, Role, Task
from ..schemas.admin import UserCreate, UserUpdate, UserResponse, RoleResponse, TaskResponse, PaginatedResponse
from ..auth.utils import get_current_admin_user, get_password_hash
from typing import List, Optional
from sqlalchemy import func
from math import ceil
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by username, email, or full name")
):
    """List users with pagination and search"""
    try:
        # Base query
        query = db.query(User).options(
            joinedload(User.roles),
            joinedload(User.tasks)
        )

        # Apply search if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.username.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.full_name.ilike(search_term))
            )

        # Get total count
        total = query.count()
        total_pages = ceil(total / page_size)

        # Apply pagination
        users = query.offset((page - 1) * page_size).limit(page_size).all()

        # Convert to response model
        items = [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                roles=[role.name for role in user.roles],
                tasks=[task.name for task in user.tasks],
                last_login=user.last_login,
                created_at=user.created_at
            ) 
            for user in users
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

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
    try:
        user = db.query(User).options(
            joinedload(User.roles),
            joinedload(User.tasks)
        ).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=[role.name for role in user.roles],
            tasks=[task.name for task in user.tasks],
            last_login=user.last_login,
            created_at=user.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new user"""
    try:
        # Check for existing username/email
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create new user
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            is_active=user_data.is_active
        )

        # Add roles
        if user_data.roles:
            roles = db.query(Role).filter(Role.id.in_(user_data.roles)).all()
            user.roles = roles

        # Add tasks
        if user_data.tasks:
            tasks = db.query(Task).filter(Task.id.in_(user_data.tasks)).all()
            user.tasks = tasks

        db.add(user)
        db.commit()
        db.refresh(user)

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=[role.name for role in user.roles],
            tasks=[task.name for task in user.tasks],
            last_login=user.last_login,
            created_at=user.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user"""
    try:
        # Get user with relationships
        user = db.query(User).options(
            joinedload(User.roles),
            joinedload(User.tasks)
        ).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate unique constraints
        if user_data.username and user_data.username != user.username:
            existing = db.query(User).filter(User.username == user_data.username).first()
            if existing:
                raise HTTPException(status_code=400, detail="Username already taken")
            user.username = user_data.username

        if user_data.email and user_data.email != user.email:
            existing = db.query(User).filter(User.email == user_data.email).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")
            user.email = user_data.email

        # Update basic fields
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.password:
            user.hashed_password = get_password_hash(user_data.password)
        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        # Update roles if provided
        if user_data.roles is not None:
            roles = db.query(Role).filter(Role.id.in_(user_data.roles)).all()
            logger.debug(f"Updating roles for user {user.username}: {[r.name for r in roles]}")
            user.roles = roles

        # Update tasks if provided
        if user_data.tasks is not None:
            tasks = db.query(Task).filter(Task.id.in_(user_data.tasks)).all()
            logger.debug(f"Updating tasks for user {user.username}: {[t.name for t in tasks]}")
            user.tasks = tasks

        try:
            db.commit()
            db.refresh(user)
            
            logger.info(f"Successfully updated user: {user.username}")
            
            return UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                roles=[role.name for role in user.roles],
                tasks=[task.name for task in user.tasks],
                last_login=user.last_login,
                created_at=user.created_at
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while updating user: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Database error while updating user"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating user: {str(e)}"
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

        # Get username for logging before deletion
        username = user.username
        
        db.delete(user)
        db.commit()
        
        logger.info(f"Deleted user: {username}")
        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all roles"""
    try:
        roles = db.query(Role).all()
        return [
            RoleResponse(
                id=role.id,
                name=role.name,
                description=role.description
            )
            for role in roles
        ]
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
        tasks = db.query(Task).filter(Task.is_active == True).all()
        return [
            TaskResponse(
                id=task.id,
                name=task.name,
                description=task.description,
                is_active=task.is_active
            )
            for task in tasks
        ]
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving tasks"
        )