# app/main.py
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from .config import settings
from .api import chat_router
from .api.auth import router as auth_router
from .database import engine, Base
from .auth.utils import get_current_user, get_current_admin_user
from .models.user import User
import logging
from .api.admin import router as admin_router
from .api.settings import router as settings_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(
    admin_router,
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)]
)
app.include_router(
    settings_router,
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)]
)

templates = Jinja2Templates(directory="app/templates")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page"""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.APP_NAME
        }
    )

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Show chat page or redirect to login if not authenticated"""
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "app_name": settings.APP_NAME
        }
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Show admin page"""
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "app_name": settings.APP_NAME
        }
    )

@app.get("/settings", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Show admin page"""
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "app_name": settings.APP_NAME
        }
    )

# Add error handler for authentication errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    if exc.status_code == 401 and not request.url.path.startswith('/api/'):
        return RedirectResponse(url="/login", status_code=303)
    raise exc