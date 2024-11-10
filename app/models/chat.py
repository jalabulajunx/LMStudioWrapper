from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)  # UUID
    title = Column(String, nullable=False, default="New Conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    user_id = Column(String, nullable=True)  # Will be used after adding authentication
    
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    response = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    
    conversation = relationship("Conversation", back_populates="messages")

# app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import SessionLocal
from ..services.llm_service import LLMService
from ..models.chat import ChatMessage, Conversation
import uuid
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class ConversationUpdate(BaseModel):
    title: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/conversations")
async def list_conversations(db: Session = Depends(get_db)):
    """List all conversations with their latest messages"""
    try:
        conversations = db.query(Conversation).order_by(desc(Conversation.updated_at)).all()
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "last_message": conv.messages[-1].content if conv.messages else None
            }
            for conv in conversations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/conversations")
async def create_conversation(db: Session = Depends(get_db)):
    """Create a new conversation"""
    try:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            title="New Conversation"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get all messages in a conversation"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.timestamp).all()
    
    return [
        {
            "content": msg.content,
            "response": msg.response,
            "timestamp": msg.timestamp
        } for msg in messages
    ]

@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    db: Session = Depends(get_db)
):
    """Update conversation title"""
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation.title = update_data.title
        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conversation)
        
        return conversation
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update conversation: {str(e)}")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages"""
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        db.delete(conversation)
        db.commit()
        
        return {"status": "success", "message": "Conversation deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.post("/chat")
async def create_chat(request: Request, db: Session = Depends(get_db)):
    """Create a new chat message and get streaming response"""
    try:
        request_data = await request.json()
        message = request_data.get('message')
        conversation_id = request_data.get('conversation_id')
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Get or create conversation
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            conversation = Conversation(id=conversation_id)
            db.add(conversation)
            db.commit()

        # Create chat message
        chat_message = ChatMessage(
            content=message,
            conversation_id=conversation_id
        )
        db.add(chat_message)
        db.commit()
        
        # Update conversation
        conversation.updated_at = datetime.utcnow()
        if len(conversation.messages) == 1:  # First message becomes the title
            conversation.title = (message[:47] + "...") if len(message) > 50 else message
        db.commit()
        
        async def generate_response():
            llm_service = LLMService()
            full_response = ""
            
            try:
                async for token in llm_service.generate_stream(message):
                    full_response += token
                    yield f"data: {json.dumps({'token': token, 'conversationId': conversation_id})}\n\n"
                
                # Update message with complete response
                chat_message.response = full_response
                db.commit()
                
                yield f"data: [DONE]\n\n"
            except Exception as e:
                error_msg = str(e)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                db.rollback()
                raise HTTPException(status_code=500, detail=error_msg)

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))