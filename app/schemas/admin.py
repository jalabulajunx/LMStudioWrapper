# app/schemas/admin.py
from pydantic import BaseModel, EmailStr
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
    roles: List[str] = []
    tasks: List[str] = []

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None
    tasks: Optional[List[str]] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    last_login: Optional[datetime]
    roles: List[str]
    tasks: List[str]
    created_at: datetime

    class Config:
        from_attributes = True