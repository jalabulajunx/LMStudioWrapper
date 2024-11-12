# tests/conftest.py
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from typing import Generator, Dict, Any
from datetime import datetime, timedelta

from app.database import Base, get_db
from app.main import app
from app.models.user import User, Role, Task
from app.models.chat import Conversation, ChatMessage
from app.services.llm_service import LLMService
from app.auth.utils import create_access_token, get_password_hash

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """Create a FastAPI TestClient with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def mock_llm_service(monkeypatch):
    """Mock LM Studio service responses."""
    async def mock_generate_stream(*args, **kwargs):
        yield "This is a "
        yield "test response "
        yield "from the mocked LLM service."

    monkeypatch.setattr(
        LLMService,
        "generate_stream",
        mock_generate_stream
    )

@pytest.fixture
def mock_llm_service_error(monkeypatch):
    """Mock LM Studio service with error response."""
    async def mock_generate_stream(*args, **kwargs):
        raise Exception("LM Studio connection error")

    monkeypatch.setattr(
        LLMService,
        "generate_stream",
        mock_generate_stream
    )

@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user with necessary roles and tasks."""
    # Create roles
    user_role = Role(name="user", description="Regular user role")
    admin_role = Role(name="admin", description="Admin role")
    db_session.add_all([user_role, admin_role])
    
    # Create tasks
    general_task = Task(name="general", description="General chat task")
    music_task = Task(name="music", description="Music query task")
    db_session.add_all([general_task, music_task])
    
    # Create test user
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpass123"),
        is_active=True
    )
    user.roles.append(user_role)
    user.tasks.append(general_task)
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_admin(db_session) -> User:
    """Create a test admin user."""
    admin_role = db_session.query(Role).filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Admin role")
        db_session.add(admin_role)
    
    admin = User(
        username="testadmin",
        email="admin@example.com",
        full_name="Test Admin",
        hashed_password=get_password_hash("adminpass123"),
        is_active=True,
        is_superuser=True
    )
    admin.roles.append(admin_role)
    
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin

@pytest.fixture
def test_conversation(db_session, test_user) -> Conversation:
    """Create a test conversation with messages."""
    conversation = Conversation(
        id="test-conv-id",
        title="Test Conversation",
        user_id=test_user.id
    )
    db_session.add(conversation)
    
    messages = [
        ChatMessage(
            content="Hello",
            response="Hi there!",
            conversation_id=conversation.id
        ),
        ChatMessage(
            content="How are you?",
            response="I'm doing well, thank you!",
            conversation_id=conversation.id
        )
    ]
    db_session.add_all(messages)
    db_session.commit()
    return conversation

@pytest.fixture
def user_token(test_user) -> Dict[str, Any]:
    """Create an authentication token for the test user."""
    access_token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def admin_token(test_admin) -> Dict[str, Any]:
    """Create an authentication token for the test admin."""
    access_token = create_access_token(data={"sub": test_admin.username})
    return {"Authorization": f"Bearer {access_token}"}