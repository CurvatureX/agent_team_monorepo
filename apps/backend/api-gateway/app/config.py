"""
MVP Configuration Management with Supabase Auth support
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for MVP version with Supabase Auth"""
    
    # Supabase Configuration
    SUPABASE_URL: str = "https://your-project-id.supabase.co"  # Default placeholder
    SUPABASE_SERVICE_KEY: str = ""  # Use Service Role key (starts with sb_secret_ or eyJ)
    SUPABASE_ANON_KEY: str = ""  # Public anon key for RLS operations (required for user tokens)
    
    # gRPC Configuration
    WORKFLOW_SERVICE_HOST: str = "localhost"
    WORKFLOW_SERVICE_PORT: int = 50051
    
    # Authentication Configuration
    JWT_SECRET_KEY: Optional[str] = None  # For additional JWT operations if needed
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Default 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Default 7 days
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Vue dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "*"  # MVP: Allow all origins for development
    ]
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if os.getenv("DEBUG", "true").lower() == "true" else "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "standard")  # standard, json, simple
    
    # Security Configuration
    ENABLE_AUTH: bool = True  # Set to False to disable authentication for testing
    REQUIRE_EMAIL_VERIFICATION: bool = False  # MVP: Disable email verification for simplicity
    
    # Rate Limiting (for future implementation)
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    def get_supabase_config(self) -> dict:
        """Get Supabase configuration for client initialization"""
        return {
            "url": self.SUPABASE_URL,
            "service_key": self.SUPABASE_SERVICE_KEY,
            "anon_key": self.SUPABASE_ANON_KEY
        }
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return not self.DEBUG and "localhost" not in self.SUPABASE_URL


# Global settings instance
settings = Settings()