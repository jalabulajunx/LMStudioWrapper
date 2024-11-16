# app/api/__init__.py
from .chat import router as chat_router
from .upload import router as upload_router  # Add this line

__all__ = ['chat_router', 'upload_router']  # Update this line