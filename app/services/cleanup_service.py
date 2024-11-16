# app/services/cleanup_service.py
from datetime import datetime, timedelta
import logging
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from ..models.user import User, UploadedFile
from ..models.chat import ChatMessage
import json

logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(self, db: Session):
        self.db = db

    async def cleanup_user_files(self, user_id: str):
        """
        Deactivate files when user logs out.
        Mark files as inactive but don't delete them immediately
        to allow for error recovery.
        """
        try:
            logger.info(f"Starting file cleanup for user {user_id}")
            
            # Mark files as inactive
            files_updated = self.db.query(UploadedFile).filter(
                UploadedFile.user_id == user_id,
                UploadedFile.is_active == True
            ).update({
                'is_active': False
            }, synchronize_session=False)
            
            # Update user's last_logout time
            self.db.query(User).filter(User.id == user_id).update({
                'last_logout': func.now()
            }, synchronize_session=False)
            
            self.db.commit()
            logger.info(f"Marked {files_updated} files as inactive for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error during file cleanup for user {user_id}: {str(e)}")
            self.db.rollback()
            raise

    async def cleanup_expired_files(self):
        """
        Cleanup files that have been inactive for more than 24 hours
        and are no longer referenced in any active conversations.
        """
        try:
            logger.info("Starting expired files cleanup")
            
            # Find files that have been inactive for 24+ hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Get files to delete
            files_to_delete = self.db.query(UploadedFile).filter(
                and_(
                    UploadedFile.is_active == False,
                    or_(
                        # Files marked inactive more than 24 hours ago
                        UploadedFile.uploaded_at < cutoff_time,
                        # Files belonging to users who logged out more than 24 hours ago
                        User.last_logout < cutoff_time
                    )
                )
            ).join(User).all()
            
            deleted_count = 0
            for file in files_to_delete:
                try:
                    # Check if file is still referenced in any messages
                    references = self.db.query(ChatMessage).filter(
                        ChatMessage.attached_files.contains(file.id)
                    ).count()
                    
                    if references == 0:
                        # Safe to delete as file is not referenced
                        self.db.delete(file)
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting file {file.id}: {str(e)}")
                    continue
            
            self.db.commit()
            logger.info(f"Deleted {deleted_count} expired files")
            
            # Cleanup orphaned file references
            await self.cleanup_orphaned_references()
            
        except Exception as e:
            logger.error(f"Error during expired files cleanup: {str(e)}")
            self.db.rollback()
            raise

    async def cleanup_orphaned_references(self):
        """
        Cleanup any message references to files that no longer exist.
        """
        try:
            logger.info("Starting orphaned references cleanup")
            
            messages = self.db.query(ChatMessage).filter(
                ChatMessage.attached_files.isnot(None)
            ).all()
            
            updated_count = 0
            for message in messages:
                try:
                    if message.attached_files:
                        file_ids = json.loads(message.attached_files)
                        if not file_ids:
                            continue
                            
                        # Check which files still exist
                        existing_files = self.db.query(UploadedFile.id).filter(
                            UploadedFile.id.in_(file_ids)
                        ).all()
                        existing_file_ids = [f.id for f in existing_files]
                        
                        # Update message if any files are missing
                        if len(existing_file_ids) < len(file_ids):
                            message.attached_files = json.dumps(existing_file_ids)
                            updated_count += 1
                            
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in message {message.id}")
                    message.attached_files = '[]'
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {str(e)}")
                    continue
            
            self.db.commit()
            logger.info(f"Updated {updated_count} messages with orphaned references")
            
        except Exception as e:
            logger.error(f"Error during orphaned references cleanup: {str(e)}")
            self.db.rollback()
            raise

    async def verify_database_integrity(self):
        """
        Verify database integrity and fix any inconsistencies.
        """
        try:
            logger.info("Starting database integrity check")
            
            # Check for invalid JSON in attached_files
            invalid_json = self.db.query(ChatMessage).filter(
                ChatMessage.attached_files.isnot(None)
            ).all()
            
            fixed_count = 0
            for message in invalid_json:
                try:
                    if message.attached_files:
                        json.loads(message.attached_files)
                except json.JSONDecodeError:
                    message.attached_files = '[]'
                    fixed_count += 1
            
            if fixed_count > 0:
                self.db.commit()
                logger.info(f"Fixed {fixed_count} messages with invalid JSON")
            
            # Report on database statistics
            total_files = self.db.query(UploadedFile).count()
            active_files = self.db.query(UploadedFile).filter(
                UploadedFile.is_active == True
            ).count()
            messages_with_files = self.db.query(ChatMessage).filter(
                ChatMessage.attached_files.isnot(None)
            ).count()
            
            logger.info(f"Database statistics: "
                       f"Total files: {total_files}, "
                       f"Active files: {active_files}, "
                       f"Messages with files: {messages_with_files}")
            
        except Exception as e:
            logger.error(f"Error during database integrity check: {str(e)}")
            self.db.rollback()
            raise