# app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db, SessionLocal
from ..models.chat import ChatMessage, Conversation
from ..services.llm_service import LLMService
from ..auth.utils import get_current_user
from ..models.user import User
import uuid
import json
from datetime import datetime
import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/conversations")
async def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all conversations with their latest messages"""
    try:
        conversations = db.query(Conversation)\
            .filter(Conversation.user_id == current_user.id)\
            .order_by(desc(Conversation.updated_at))\
            .all()
        
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "last_message": conv.messages[-1].content if conv.messages else None,
                "last_response": conv.messages[-1].response if conv.messages and conv.messages[-1].response else None
            }
            for conv in conversations
        ]
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations")
async def create_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation"""
    try:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            title="New Conversation",
            user_id=current_user.id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
        }
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages in a conversation"""
    try:
        # Get conversation with user check
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
            
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found or unauthorized access attempt")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).order_by(ChatMessage.timestamp).all()
        
        logger.debug(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
        
        return {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            },
            "messages": [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "response": msg.response,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                }
                for msg in messages
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving conversation: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a conversation"""
    try:
        conversation = db.query(Conversation)\
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        db.delete(conversation)
        db.commit()
        
        return {"status": "success", "message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def create_chat(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat message and get streaming response"""
    try:
        request_data = await request.json()
        message = request_data.get('message')
        conversation_id = request_data.get('conversation_id')
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        logger.debug(f"Processing chat request - Message: {message}, Conversation ID: {conversation_id}")
        
        # Get or create conversation
        conversation = db.query(Conversation)\
            .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)\
            .first()
        if not conversation:
            conversation = Conversation(
                id=conversation_id,
                user_id=current_user.id  # Associate with current user
            )
            db.add(conversation)
            db.commit()
            logger.debug(f"Created new conversation with ID: {conversation_id}")

        # Create chat message and store its ID
        chat_message = ChatMessage(
            content=message,
            conversation_id=conversation_id,
            response=""  # Initialize empty response
        )
        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)
        message_id = chat_message.id
        
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
                
                logger.debug(f"Generated full response for message {message_id}: {full_response[:100]}...")
                
                # Update the message with the complete response using a new session
                db_for_update = SessionLocal()
                try:
                    msg = db_for_update.query(ChatMessage).get(message_id)
                    if msg:
                        msg.response = full_response
                        db_for_update.commit()
                        logger.debug(f"Saved response to database for message {message_id}")
                except Exception as db_error:
                    logger.error(f"Database error while saving response: {db_error}")
                finally:
                    db_for_update.close()
                
                yield f"data: [DONE]\n\n"
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error generating response: {error_msg}")
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                
                # Save error message as response
                db_for_update = SessionLocal()
                try:
                    msg = db_for_update.query(ChatMessage).get(message_id)
                    if msg:
                        msg.response = f"Error: {error_msg}"
                        db_for_update.commit()
                except Exception as db_error:
                    logger.error(f"Database error while saving error response: {db_error}")
                finally:
                    db_for_update.close()

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all messages in a conversation"""
    try:
        conversation = db.query(Conversation)\
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = db.query(ChatMessage)\
            .filter(ChatMessage.conversation_id == conversation_id)\
            .order_by(ChatMessage.timestamp).all()
        
        return {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            },
            "messages": [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "response": msg.response,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                }
                for msg in messages
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))