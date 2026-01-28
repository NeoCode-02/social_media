from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str = "Photo Social Platform"
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 15
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    
    # Application
    APP_NAME: str = "Photo Social Platform"
    FRONTEND_URL: str
    BACKEND_URL: str
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: str = "jpg,jpeg,png,gif,webp"
    UPLOAD_DIR: str = "uploads/photos"
    PROFILE_UPLOAD_DIR: str = "uploads/profiles"
    
    # Image Processing
    IMAGE_QUALITY: int = 85
    MAX_IMAGE_WIDTH: int = 2048
    MAX_IMAGE_HEIGHT: int = 2048
    
    # Chat
    CHAT_MESSAGE_RETENTION_DAYS: int = 365
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_IMAGE_EXTENSIONS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()