# app/api/settings.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..auth.utils import get_current_user
import aiohttp
from ..config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/models")
async def list_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available models from LM Studio"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.LM_STUDIO_URL}/models",
                headers={"Authorization": f"Bearer {settings.LM_STUDIO_KEY}"}
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Failed to fetch models from LM Studio"
                    )
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to LM Studio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not connect to LM Studio"
        )