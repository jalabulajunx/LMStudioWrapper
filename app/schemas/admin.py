# app/schemas/admin.py
from pydantic import BaseModel, EmailStr, conint
from typing import List, Optional
from datetime import datetime

class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class TaskResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    is_active: bool = True
    roles: List[str] = []  # Role IDs
    tasks: List[str] = []  # Task IDs

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None  # Role IDs
    tasks: Optional[List[str]] = None  # Task IDs

class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: str
    is_active: bool
    roles: List[str]  # Role names
    tasks: List[str]  # Task names
    last_login: Optional[datetime] = None
    created_at: datetime

    @classmethod
    def model_validate(cls, user):
        return cls(
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

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: conint(ge=1)  # greater than or equal to 1
    page_size: conint(ge=1)
    total_pages: int