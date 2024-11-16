# app/models/user.py
from sqlalchemy import Table, Column, String, Boolean, DateTime, ForeignKey, Integer, LargeBinary, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import uuid

# Association tables
user_roles = Table('user_roles',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE')),
    Column('role_id', String, ForeignKey('roles.id', ondelete='CASCADE'))
)

user_tasks = Table('user_tasks',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE')),
    Column('task_id', String, ForeignKey('tasks.id', ondelete='CASCADE'))
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    last_login = Column(DateTime(timezone=True), default=None, nullable=True)
    last_logout = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    tasks = relationship("Task", secondary=user_tasks, back_populates="users")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="user", cascade="all, delete-orphan")

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    users = relationship("User", secondary=user_tasks, back_populates="tasks")

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    file_data = Column(LargeBinary, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Foreign Keys
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="uploaded_files")
    conversation = relationship("Conversation", back_populates="files")
    messages = relationship("ChatMessage", secondary="message_files", back_populates="files")

# Intermediary table for message-file relationships
message_files = Table(
    'message_files',
    Base.metadata,
    Column('message_id', Integer, ForeignKey('chat_messages.id', ondelete='CASCADE')),
    Column('file_id', String, ForeignKey('uploaded_files.id', ondelete='CASCADE'))
)