from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Financial Portfolio Tracker"
    API_V1_STR: str = "/api"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-it-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALLOWED_HOSTS: List[str] = ["*"]  # Set to specific domains in production
    
    # Logging
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/financial_portfolio.db")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]  # In production, change to specific origins
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development") # development, production, test
    
    # Feature Flags / Trial
    FREE_TRIAL_DAYS: int = 30
    DEFAULT_OTP: Optional[str] = "123456" # Set to None in production to disable master OTP
    
    # App Specific
    PORT: int = 8000
    
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
