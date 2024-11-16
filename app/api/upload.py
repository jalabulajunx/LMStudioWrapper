# app/api/upload.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import logging
from ..database import get_db
from ..models.user import User
from ..services.upload_service import UploadService
from ..auth.utils import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'text/plain': '.txt',
    'text/csv': '.csv'
}

@router.post("/", response_model=List[dict])
async def upload_files(
    files: List[UploadFile] = File(...),
    conversation_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload files for a conversation"""
    try:
        # Validate file count
        if len(files) > 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum 5 files allowed per upload"
            )
            
        # Validate file types
        for file in files:
            if file.content_type not in ALLOWED_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type {file.content_type} not allowed"
                )
        
        # Process files
        upload_service = UploadService(db)
        uploaded_files = await upload_service.process_files(
            files,
            current_user,
            conversation_id
        )
        
        return uploaded_files
        
    except ValueError as e:
        logger.error(f"Validation error in upload: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing upload")

@router.get("/files/{conversation_id}")
async def get_conversation_files(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get files associated with a conversation"""
    try:
        upload_service = UploadService(db)
        files = await upload_service.get_conversation_files(
            conversation_id,
            current_user.id
        )
        return files
    except Exception as e:
        logger.error(f"Error retrieving files: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving files")

@router.post("/deactivate")
async def deactivate_user_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate files when user logs out"""
    try:
        upload_service = UploadService(db)
        await upload_service.deactivate_user_files(current_user.id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deactivating files: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deactivating files")