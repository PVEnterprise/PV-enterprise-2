"""
Application configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "Medical Equipment Supply System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # Redis (Optional)
    REDIS_URL: Optional[str] = None
    
    # Email Configuration (Optional)
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: str = "noreply@medicalequipment.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: Optional[str] = None
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "./uploads"
    
    # Company Information (for PDFs)
    COMPANY_NAME: str = "Sreedevi Life Sciences"
    COMPANY_PLOT: str = "Plot No: 173 Road No: 14"
    COMPANY_AREA: str = "Alkapuri Township"
    COMPANY_CITY: str = "Hyderabad Telangana 500089"
    COMPANY_COUNTRY: str = "India"
    COMPANY_GSTIN: str = "GSTIN 36ACGFS4458L1ZK"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    @property
    def database_url_async(self) -> str:
        """Convert sync PostgreSQL URL to async (asyncpg)."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def database_url_sync(self) -> str:
        """Ensure sync PostgreSQL URL (psycopg2)."""
        url = self.DATABASE_URL
        if "postgresql+asyncpg://" in url:
            return url.replace("postgresql+asyncpg://", "postgresql://")
        return url


# Global settings instance
settings = Settings()
