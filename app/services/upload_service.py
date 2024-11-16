# app/services/upload_service.py
from typing import List, Optional
import hashlib
import logging
from sqlalchemy.orm import Session
from fastapi import UploadFile
from ..models.user import User, UploadedFile
from ..models.chat import ChatMessage
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class UploadService:
    def __init__(self, db: Session):
        self.db = db

    async def process_files(
        self, 
        files: List[UploadFile], 
        user: User, 
        conversation_id: str
    ) -> List[dict]:
        """Process uploaded files and store them in the database"""
        uploaded_files = []
        total_size = 0
        
        try:
            # Calculate total size
            for file in files:
                contents = await file.read()
                total_size += len(contents)
                await file.seek(0)  # Reset file pointer
            
            # Check total size limit (30MB)
            if total_size > 30 * 1024 * 1024:
                raise ValueError("Total file size exceeds 30MB limit")
            
            # Process each file
            for file in files:
                contents = await file.read()
                file_hash = hashlib.sha256(contents).hexdigest()
                
                uploaded_file = UploadedFile(
                    id=str(uuid.uuid4()),
                    filename=file.filename,
                    content_type=file.content_type,
                    size=len(contents),
                    file_hash=file_hash,
                    file_data=contents,
                    user_id=user.id,
                    conversation_id=conversation_id
                )
                
                self.db.add(uploaded_file)
                uploaded_files.append({
                    'id': uploaded_file.id,
                    'filename': file.filename,
                    'content_type': file.content_type,
                    'size': len(contents)
                })
            
            self.db.commit()
            return uploaded_files
            
        except Exception as e:
            logger.error(f"Error processing files: {str(e)}")
            self.db.rollback()
            raise

    async def get_conversation_files(
        self, 
        conversation_id: str, 
        user_id: str
    ) -> List[dict]:
        """Get file metadata for a conversation"""
        files = self.db.query(UploadedFile).filter(
            UploadedFile.conversation_id == conversation_id,
            UploadedFile.user_id == user_id,
            UploadedFile.is_active == True
        ).all()
        
        return [{
            'id': file.id,
            'filename': file.filename,
            'content_type': file.content_type,
            'size': file.size,
            'uploaded_at': file.uploaded_at
        } for file in files]

    async def deactivate_user_files(self, user_id: str):
        """Deactivate files for a user (called on logout)"""
        try:
            self.db.query(UploadedFile).filter(
                UploadedFile.user_id == user_id,
                UploadedFile.is_active == True
            ).update({'is_active': False})
            
            self.db.commit()
        except Exception as e:
            logger.error(f"Error deactivating files: {str(e)}")
            self.db.rollback()
            raise

    async def get_file_content(
        self, 
        file_id: str, 
        user_id: str
    ) -> Optional[UploadedFile]:
        """Get file content if user has access"""
        return self.db.query(UploadedFile).filter(
            UploadedFile.id == file_id,
            UploadedFile.user_id == user_id,
            UploadedFile.is_active == True
        ).first()

    async def cleanup_inactive_files(self):
        """Cleanup service to permanently remove inactive files"""
        try:
            # Delete files that have been inactive for more than 24 hours
            self.db.query(UploadedFile).filter(
                UploadedFile.is_active == False,
                UploadedFile.uploaded_at < datetime.utcnow() - timedelta(hours=24)
            ).delete()
            
            self.db.commit()
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
            self.db.rollback()
            raise