# app/models/__init__.py
from .user import User, Role, Task, user_roles, user_tasks
from .chat import Conversation, ChatMessage

# This ensures all models are imported when importing from models
__all__ = ['User', 'Role', 'Task', 'Conversation', 'ChatMessage', 'user_roles', 'user_tasks']