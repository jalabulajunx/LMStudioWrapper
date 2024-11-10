# app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import SessionLocal
from ..services.llm_service import LLMService, LMStudioConnectionError
from ..models.chat import ChatMessage, Conversation
import uuid
import json
from datetime import datetime
from typing import List, Optional

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/conversations")
async def list_conversations(db: Session = Depends(get_db)):
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

@router.post("/conversations")
async def create_conversation(db: Session = Depends(get_db)):
    conversation = Conversation(
        id=str(uuid.uuid4()),
        title="New Conversation"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    data = await request.json()
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if title := data.get("title"):
        conversation.title = title
        db.commit()
        db.refresh(conversation)
    
    return conversation

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.delete(conversation)
    db.commit()
    return {"status": "success"}

# Update the existing chat endpoint
@router.post("/chat")
async def create_chat(
    request: Request,
    db: Session = Depends(get_db)
):
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
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        if len(conversation.messages) == 1:  # First message
            conversation.title = message[:50] + "..." if len(message) > 50 else message
        db.commit()
        
        async def generate_response():
            llm_service = LLMService()
            full_response = ""
            
            try:
                async for token in llm_service.generate_stream(message):
                    full_response += token
                    yield f"data: {json.dumps({'token': token, 'conversationId': conversation_id})}\n\n"
                
                chat_message.response = full_response
                db.commit()
                
                yield f"data: [DONE]\n\n"
            except Exception as e:
                error_msg = str(e)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                raise HTTPException(status_code=500, detail=error_msg)

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))