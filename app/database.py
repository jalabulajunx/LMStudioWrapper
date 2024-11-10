# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create regular synchronous engine and session for normal operations
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create async engine and session for streaming operations
async_engine = create_async_engine(
    settings.DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///')
)
async_session = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

# Database Dependency for regular operations
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Async Database Dependency for streaming operations
async def get_async_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()