# app/tasks/cleanup.py
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from ..services.cleanup_service import CleanupService
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def run_periodic_cleanup(db: Session):
    """Run cleanup tasks periodically"""
    cleanup_service = CleanupService(db)
    
    while True:
        try:
            logger.info("Starting periodic cleanup")
            
            # Run cleanup tasks
            await cleanup_service.cleanup_expired_files()
            await cleanup_service.cleanup_orphaned_references()
            await cleanup_service.verify_database_integrity()
            
            # Wait for next cleanup interval (every 6 hours)
            await asyncio.sleep(6 * 60 * 60)
            
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {str(e)}")
            # Wait shorter time before retry on error
            await asyncio.sleep(15 * 60)

def schedule_cleanup(background_tasks: BackgroundTasks, db: Session):
    """Schedule cleanup tasks"""
    background_tasks.add_task(run_periodic_cleanup, db)