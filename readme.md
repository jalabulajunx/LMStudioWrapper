# Family Chat Application

A secure, private, and family-friendly chat application that works with local LLMs through LM Studio. Built with privacy and learning in mind.

## The prompt for Claude.ai
<details>
<summary>Original Requirements and Vision</summary>

```text
I have an idea of developing a web chat application sitting on top of LM Studio SDK. The application would be for my family to use the local LLMs instead of the publicly available ones. The LM Studio Server is housed within ArchLinux.

Key Requirements:

1. Users and Authentication
   - User authentication and logout functionality
   - Session management
   - Private conversations
   - Conversation history
   - Title modification capabilities
   - Admin user creation (no self-registration)
   - Admin can grant admin privileges

2. Chat Functionality
   - Support for long and short messages
   - Response streaming
   - Stop generation capability
   - Task-based system:
     * General chat
     * Music database queries
   - Markdown response rendering
   - Export and copy functionality
   - Conversation search

3. Design Considerations
   - Two-panel layout:
     * Left: Chat history
     * Right: Conversations
   - Intuitive UI with clear placement of:
     * Rename/Delete functions
     * New conversation button
     * Chat controls
     * Task selection
     * Logout
   - Responsive design
   - Thoughtful color scheme
   - User-friendly interface for all ages

4. Architectural Principles
   - Modular design
   - Well-documented code
   - Maintainable structure
   - Good architectural practices
   - Performance optimized
   - Security focused
   - Microservices capability

5. Deployment Requirements
   - ArchLinux compatible
   - Home network deployment
   - SystemD service integration
   - Clear package dependencies
   - Development testing support
```
</details>

## Purpose and Philosophy

This application was created with three main goals:

1. **Safe AI for Families**: Provide a secure, non-tracking environment where families (especially children) can interact with AI models locally, ensuring privacy and parental oversight.

2. **Educational Development**: Serve as a learning project to understand full-stack web development and deployment using modern technologies.

3. **Community Contribution**: Share knowledge and code with the open-source community, enabling others to create safe AI environments for their families.

## Features

- **Security & Privacy**
  - User authentication and role-based access control
  - Local model execution through LM Studio
  - No data sent to external services
  - Secure session management

- **User Management**
  - Admin dashboard for user administration
  - Role-based access (admin/user)
  - Task-based permissions
  - User activity tracking

- **Chat Interface**
  - Real-time streaming responses
  - Conversation history
  - Dark/Light mode
  - Markdown support
  - Copy/Export functionality
  - Stop generation capability

- **Settings & Customization**
  - Model selection from available LM Studio models
  - Theme preferences
  - User-specific settings

## Prerequisites

- Python 3.10 or higher
- LM Studio (latest version)
- SQLite3
- Modern web browser

## Installation

### Setting up LM Studio

1. Download LM Studio from [https://lmstudio.ai/](https://lmstudio.ai/)
2. Install and launch LM Studio
3. Download a suitable family-friendly model (recommended: Mistral 7B or similar)
4. Start the local server in LM Studio

### Installing the Application

#### Linux (Arch Linux/Ubuntu)

```bash
# Install system dependencies
sudo pacman -S python python-pip sqlite   # Arch Linux
# or
sudo apt install python3 python3-pip sqlite3   # Ubuntu

# Clone the repository
git clone https://github.com/yourusername/family-chat.git
cd family-chat

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python create_tables.py --init-data

# Start the application
uvicorn app.main:app --reload
```

#### Windows

```powershell
# Install Python from python.org

# Clone the repository
git clone https://github.com/yourusername/family-chat.git
cd family-chat

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python create_tables.py --init-data

# Start the application
uvicorn app.main:app --reload
```

#### macOS

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python sqlite3

# Clone the repository
git clone https://github.com/yourusername/family-chat.git
cd family-chat

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python create_tables.py --init-data

# Start the application
uvicorn app.main:app --reload
```

### Running as a Service (Linux)

Create a systemd service file:

```ini
# /etc/systemd/system/family-chat.service
[Unit]
Description=Family Chat Application
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/family-chat
Environment="PATH=/path/to/family-chat/venv/bin"
ExecStart=/path/to/family-chat/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable family-chat
sudo systemctl start family-chat
```

## Initial Setup

1. Access the application at `http://localhost:8000`
2. Login with default admin credentials:
   - Username: admin
   - Password: admin123
3. **Important**: Change the admin password immediately
4. Create user accounts for family members
5. Configure available tasks and permissions

## Architecture

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, JavaScript, Bootstrap
- **Database**: SQLite
- **Authentication**: JWT
- **Model Interface**: LM Studio API

```
chat_app/
├── README.md
├── requirements.txt
├── app/
│   ├── main.py           # Main application
│   ├── config.py         # Configuration
│   ├── database.py       # Database setup
│   ├── models/           # Database models
│   ├── api/             # API endpoints
│   ├── services/        # Business logic
│   ├── static/          # Static files
│   └── templates/       # HTML templates
```

## Technical Details

### Backend Architecture

```python
# FastAPI Dependency Chain
main.py
├── Authentication Middleware
├── CORS Middleware
├── Database Session Middleware
└── Route Handlers
    ├── Auth Routes
    ├── Chat Routes
    ├── Admin Routes
    └── Settings Routes
```

### Database Schema

```sql
-- Core Tables
Users (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    full_name TEXT,
    hashed_password TEXT,
    is_active BOOLEAN,
    is_superuser BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_login TIMESTAMP
)

Roles (
    id UUID PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
)

Tasks (
    id UUID PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT,
    is_active BOOLEAN
)

-- Join Tables
user_roles (
    user_id UUID REFERENCES Users,
    role_id UUID REFERENCES Roles
)

user_tasks (
    user_id UUID REFERENCES Users,
    task_id UUID REFERENCES Tasks
)

-- Chat Tables
Conversations (
    id UUID PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    user_id UUID REFERENCES Users
)

ChatMessages (
    id INTEGER PRIMARY KEY,
    content TEXT,
    response TEXT,
    timestamp TIMESTAMP,
    conversation_id UUID REFERENCES Conversations
)
```

### API Endpoints

```plaintext
Authentication:
POST   /api/auth/token          - Login
GET    /api/auth/me             - Get current user

Chat:
GET    /api/conversations       - List conversations
POST   /api/conversations       - Create conversation
GET    /api/conversations/{id}  - Get conversation
PUT    /api/conversations/{id}  - Update conversation
DELETE /api/conversations/{id}  - Delete conversation
POST   /api/chat               - Send message

Admin:
GET    /api/admin/users        - List users
POST   /api/admin/users        - Create user
GET    /api/admin/users/{id}   - Get user
PUT    /api/admin/users/{id}   - Update user
DELETE /api/admin/users/{id}   - Delete user
GET    /api/admin/roles        - List roles
GET    /api/admin/tasks        - List tasks

Settings:
GET    /api/settings/models    - List available models
```

### Security Implementation

```python
# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Authentication Dependencies
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # Token validation and user retrieval
    # Returns User or raises HTTPException

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    # Admin privilege check
    # Returns User or raises HTTPException
```

## FAQ

**Q: Why use local models instead of ChatGPT?**
A: Local models provide privacy, control over content, and no data sharing with external services. This is especially important for children's safety and family privacy.

**Q: How do I choose appropriate models?**
A: Start with smaller, family-friendly models like Mistral 7B. Test responses before allowing children to use them. Consider using models specifically trained for educational purposes.

**Q: Is it safe for children?**
A: Yes, when properly configured. The application includes:
- User authentication
- Parental controls through admin accounts
- Local execution (no internet-based responses)
- Activity monitoring
- No data collection or sharing

**Q: How much computing power is needed?**
A: Requirements depend on the chosen model. Minimum recommendations:
- 16GB RAM
- Modern CPU
- SSD storage
- GPU recommended but not required for smaller models

**Q: Can it work offline?**
A: Yes, once models are downloaded in LM Studio, the entire system can operate offline.

**Q: How do I backup conversations?**
A: Use the built-in export functionality or backup the SQLite database file directly.

**Q: Can I customize the interface?**
A: Yes, the application uses Bootstrap and can be customized through CSS and template modifications.

**Q: How does the application handle multiple users simultaneously?**
A: The application uses FastAPI's async capabilities and maintains separate database sessions for each request. User sessions are managed through JWT tokens.

**Q: What happens if LM Studio crashes?**
A: The application includes error handling for LM Studio connection issues. Users receive appropriate error messages, and the application continues to function for conversation management.

**Q: Can I use multiple LLM models?**
A: Yes, you can configure multiple models in LM Studio and select them through the settings interface. Different users can be assigned different models through task permissions.

**Q: How are conversations stored?**
A: Conversations are stored in an SQLite database with separate tables for conversations and messages. Each conversation is linked to a specific user for privacy.

**Q: What's the recommended maintenance schedule?**
A: Regular maintenance should include:
- Daily: Database backups
- Weekly: Log review and cleanup
- Monthly: User activity review
- Quarterly: System updates and security review

**Q: How can I migrate to a different database?**
A: The application uses SQLAlchemy ORM, making database migration straightforward. Update the DATABASE_URL in your environment configuration and run necessary migrations.

**Q: What's the token refresh mechanism?**
A: JWT tokens expire after 30 minutes. Users are automatically redirected to login when their token expires. This can be configured in the application settings.

## Security Considerations

- Change default admin password immediately
- Use strong passwords for all accounts
- Regular database backups
- Keep LM Studio and the application updated
- Monitor user activities through admin panel
- Review model responses for appropriateness

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

GPL v3

## Acknowledgments

- Claude.ai
- Built with FastAPI
- Uses LM Studio for model inference
- Bootstrap for UI
- Community contributors and testers

## Support

- Create an issue for bugs or feature requests
- Join discussions in the repository
- Check the wiki for detailed documentation

## Roadmap

- [ ] Enhanced parental controls
- [ ] Model response filtering
- [ ] Multi-language support
- [ ] Voice interface
- [ ] Mobile responsive design improvements
- [ ] Expanded educational features

## Project Status

Active development - Regular updates and security patches

## Troubleshooting Guide

### Common Issues and Solutions

1. **Application Won't Start**
   ```bash
   # Check Python version
   python --version  # Should be 3.10+
   
   # Verify virtual environment
   which python  # Should point to venv
   
   # Check dependencies
   pip install -r requirements.txt
   
   # Verify database
   sqlite3 chat.db .tables
   ```

2. **Authentication Issues**
   ```bash
   # Reset admin password
   python scripts/reset_admin.py
   
   # Clear database sessions
   python scripts/clear_sessions.py
   ```

3. **LM Studio Connection**
   ```bash
   # Check LM Studio status
   curl http://localhost:1234/v1/models
   
   # Verify environment variables
   echo $LM_STUDIO_URL
   ```

4. **Database Issues**
   ```bash
   # Backup database
   cp chat.db chat.db.backup
   
   # Initialize fresh database
   rm chat.db
   python create_tables.py --init-data
   ```

### Error Messages

| Error Code | Message | Solution |
|------------|---------|----------|
| 401 | Not authenticated | Token expired, re-login |
| 403 | Not enough permissions | Check user roles |
| 500 | LM Studio connection error | Verify LM Studio is running |
| 502 | Bad Gateway | Check network configuration |

## Development Guidelines

### Code Style

```python
# Follow these conventions
from typing import Optional, List
from pydantic import BaseModel

class UserCreate(BaseModel):
    """
    User creation schema.
    
    Attributes:
        username: Unique username
        email: Valid email address
        password: Strong password
    """
    username: str
    email: EmailStr
    password: str
```

### Git Workflow

1. Branch Naming:
   ```bash
   feature/add-new-capability
   bugfix/fix-authentication-issue
   enhancement/improve-performance
   ```

2. Commit Messages:
   ```bash
   # Format
   type(scope): description
   
   # Examples
   feat(auth): add password reset functionality
   fix(chat): resolve message ordering issue
   docs(readme): update installation guide
   ```

### Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run with coverage
pytest --cov=app tests/
```

### Documentation

- Use Google-style docstrings
- Update API documentation
- Include code examples
- Document environment variables

### Pull Request Process

1. Create feature branch
2. Write tests
3. Update documentation
4. Create pull request
5. Address review comments
6. Merge after approval

### Performance Optimization

- Use database indexing
- Implement caching where appropriate
- Optimize database queries
- Profile endpoint performance
- Monitor memory usage

## Monitoring and Logging

```python
# Logging configuration
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'app.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 5,
            'formatter': 'standard'
        }
    },
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        }
    }
})
```