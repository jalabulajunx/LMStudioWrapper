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
from ..models.user import UploadedFile
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
    """Get all messages in a conversation including file metadata"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
            
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).order_by(ChatMessage.timestamp).all()
        
        # Get file information for messages
        message_data = []
        for msg in messages:
            files = []
            if msg.attached_files:
                file_ids = json.loads(msg.attached_files)
                if file_ids:
                    files = [{
                        'id': f.id,
                        'filename': f.filename,
                        'content_type': f.content_type,
                        'size': f.size
                    } for f in db.query(UploadedFile).filter(
                        UploadedFile.id.in_(file_ids),
                        UploadedFile.is_active == True
                    ).all()]
            
            message_data.append({
                'id': msg.id,
                'content': msg.content,
                'response': msg.response,
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                'files': files,
                'token_count': msg.token_count,
                'generation_time': msg.generation_time,
                'model_used': msg.model_used,
                'is_complete': msg.is_complete
            })
        
        return {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            },
            "messages": message_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
    """Create a new chat message with optional file attachments"""
    try:
        request_data = await request.json()
        message = request_data.get('message')
        conversation_id = request_data.get('conversation_id')
        file_ids = request_data.get('file_ids', [])
        
        if not message and not file_ids:
            raise HTTPException(status_code=400, detail="Message or files required")
        

        # Safe length check with default empty list
        file_ids = file_ids if isinstance(file_ids, list) else []
        logger.debug(f"Processing chat request - Message: {message}, Files: {len(file_ids)}")
        
        # Get or create conversation
        conversation = db.query(Conversation)\
            .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)\
            .first()
            
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        # Verify file ownership and attach files
        attached_files = []
        if file_ids:
            files = db.query(UploadedFile).filter(
                UploadedFile.id.in_(file_ids),
                UploadedFile.user_id == current_user.id,
                UploadedFile.conversation_id == conversation_id,
                UploadedFile.is_active == True
            ).all()
            
            if len(files) != len(file_ids):
                raise HTTPException(status_code=400, detail="Invalid file IDs")
                
            attached_files = files

        # Create chat message
        chat_message = ChatMessage(
            content=message,
            conversation_id=conversation_id,
            response="",
            attached_files=json.dumps(file_ids) if file_ids else None
        )
        
        if attached_files:
            chat_message.files.extend(attached_files)
            
        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)
        message_id = chat_message.id
        
        # Update conversation
        conversation.updated_at = datetime.utcnow()
        if len(conversation.messages) == 1:
            conversation.title = (message[:47] + "...") if len(message) > 50 else message
        db.commit()

        async def generate_response():
            llm_service = LLMService()
            full_response = ""
            start_time = datetime.utcnow()
            
            try:
                # Get conversation history
                history = db.query(ChatMessage)\
                    .filter(ChatMessage.conversation_id == conversation_id)\
                    .order_by(ChatMessage.timestamp)\
                    .all()
                
                # Format history for context
                conversation_history = []
                for msg in history:
                    msg_content = msg.content
                    if msg.attached_files:
                        file_ids = json.loads(msg.attached_files)
                        if file_ids:
                            files = db.query(UploadedFile).filter(
                                UploadedFile.id.in_(file_ids),
                                UploadedFile.is_active == True
                            ).all()
                            file_contents = [f"[File: {f.filename}]\n{f.file_data.decode('utf-8')}"
                                           for f in files if f.content_type in ['text/plain', 'text/csv']]
                            if file_contents:
                                msg_content += "\n\nAttached Files:\n" + "\n---\n".join(file_contents)
                    
                    conversation_history.append({
                        'content': msg_content,
                        'response': msg.response,
                        'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
                    })
                
                # Send initial context processing message
                yield f"data: {json.dumps({'progress': 'Processing conversation context...'})}\n\n"

                # Get token estimate for context
                messages = llm_service.format_messages(conversation_history, message)
                estimated_tokens = llm_service.estimate_token_length(messages)
                
                # Send context size information
                yield f"data: {json.dumps({'progress': f'Processing {estimated_tokens} estimated tokens...'})}\n\n"

                async for token in llm_service.generate_stream(
                    message, 
                    conversation_history=conversation_history
                ):
                    if await request.is_disconnected():
                        logger.info(f"Client disconnected, stopping generation for message {message_id}")
                        break

                    full_response += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
                
                # Calculate generation time
                generation_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Update message with complete data
                db_for_update = SessionLocal()
                try:
                    msg = db_for_update.query(ChatMessage).get(message_id)
                    if msg:
                        msg.response = full_response
                        msg.generation_time = generation_time
                        msg.token_count = estimated_tokens
                        msg.model_used = llm_service.get_current_model()
                        msg.is_complete = True
                        db_for_update.commit()
                        logger.debug(f"Saved response to database for message {message_id}")
                except Exception as db_error:
                    logger.error(f"Database error while saving response: {db_error}")
                finally:
                    db_for_update.close()
                
                yield "data: [DONE]\n\n"
                
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
                        msg.is_complete = False
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

@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation title - verify user owns the conversation"""
    try:
        data = await request.json()
        conversation = db.query(Conversation)\
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id  # Ensure user owns the conversation
            ).first()
            
        if not conversation:
            logger.warning(f"User {current_user.username} attempted to access unauthorized conversation {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if title := data.get("title"):
            conversation.title = title
            conversation.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(conversation)
            
            logger.info(f"Updated conversation {conversation_id} title for user {current_user.username}")
        
        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation {conversation_id} for user {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))