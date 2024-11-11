# create_tables.py
import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from app.database import Base, engine, SessionLocal
from app.models import User, Role, Task
from app.auth.utils import get_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")

def init_data():
    """Initialize database with default roles, tasks, and admin user"""
    db = SessionLocal()
    try:
        # Check if we already have roles
        if not db.query(Role).first():
            logger.info("Creating default roles...")
            roles = [
                Role(name="admin", description="Administrator role"),
                Role(name="user", description="Regular user role")
            ]
            db.add_all(roles)
            db.commit()
            logger.info("Default roles created")

        # Create default tasks
        if not db.query(Task).first():
            logger.info("Creating default tasks...")
            tasks = [
                Task(name="general", description="General Chat Task"),
                Task(name="music", description="Music Query Task")
            ]
            db.add_all(tasks)
            db.commit()
            logger.info("Default tasks created")

        # Create admin user if it doesn't exist
        admin_username = "admin"
        if not db.query(User).filter(User.username == admin_username).first():
            logger.info("Creating admin user...")
            
            # Get admin role
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            if not admin_role:
                raise Exception("Admin role not found")

            # Get all tasks
            all_tasks = db.query(Task).all()
            
            # Create admin user
            admin_user = User(
                username=admin_username,
                email="admin@example.com",
                full_name="System Administrator",
                hashed_password=get_password_hash("admin123"),  # Change this password in production!
                is_active=True,
                is_superuser=True
            )
            
            # Add admin role and all tasks
            admin_user.roles.append(admin_role)
            admin_user.tasks.extend(all_tasks)
            
            db.add(admin_user)
            db.commit()
            
            logger.info("""
            Admin user created successfully!
            Username: admin
            PLEASE CHANGE THE PASSWORD AFTER FIRST LOGIN!
            """)

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Database management script')
    parser.add_argument('--init-data', action='store_true', help='Initialize database with default data')
    args = parser.parse_args()

    logger.info("Creating database tables...")
    create_tables()

    if args.init_data:
        logger.info("Initializing default data...")
        init_data()
        logger.info("Database initialization completed.")