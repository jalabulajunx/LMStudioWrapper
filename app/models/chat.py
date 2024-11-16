# app/models/chat.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, default="New Conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    user = relationship("User", back_populates="conversations")
    files = relationship("UploadedFile", back_populates="conversation", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    response = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    
    # New columns for enhanced functionality
    attached_files = Column(Text)  # JSON string of file IDs
    token_count = Column(Integer)
    generation_time = Column(Float)
    model_used = Column(String)
    is_complete = Column(Boolean, default=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    files = relationship("UploadedFile", secondary="message_files", back_populates="messages")