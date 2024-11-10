from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request  # Add this import

from .config import settings  # Add this import
from .api import chat_router
from .database import engine, Base

app = FastAPI(title=settings.APP_NAME)

# Create database tables
Base.metadata.create_all(bind=engine)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(chat_router, prefix="/api")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):  # Add type hint for request
    return templates.TemplateResponse("chat.html", {"request": request})
