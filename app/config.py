from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Family Chat App"
    DATABASE_URL: str = "sqlite:///./chat.db"
    LM_STUDIO_URL: str = "http://localhost:1234/v1"
    LM_STUDIO_KEY: str = "dummy-key"

    class Config:
        env_file = ".env"

settings = Settings()
