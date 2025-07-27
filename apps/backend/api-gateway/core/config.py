"""
Configuration management for API Gateway
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    APP_NAME: str = "API Gateway"
    API_TITLE: str = "API Gateway"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # gRPC Configuration
    WORKFLOW_SERVICE_HOST: str = os.getenv("WORKFLOW_SERVICE_HOST", "localhost")
    WORKFLOW_SERVICE_PORT: int = int(os.getenv("WORKFLOW_SERVICE_PORT", "50051"))
    WORKFLOW_AGENT_HOST: str = os.getenv("WORKFLOW_AGENT_HOST", "localhost")
    WORKFLOW_AGENT_PORT: int = int(os.getenv("WORKFLOW_AGENT_PORT", "50051"))
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "*"  # Allow all origins for development
    ]
    
    # MCP Configuration
    MCP_ENABLED: bool = os.getenv("MCP_ENABLED", "true").lower() == "true"
    NODE_KNOWLEDGE_SUPABASE_URL: str = os.getenv("NODE_KNOWLEDGE_SUPABASE_URL", "")
    NODE_KNOWLEDGE_SUPABASE_KEY: str = os.getenv("NODE_KNOWLEDGE_SUPABASE_KEY", "")
    NODE_KNOWLEDGE_DEFAULT_THRESHOLD: float = float(os.getenv("NODE_KNOWLEDGE_DEFAULT_THRESHOLD", "0.5"))
    MCP_MAX_RESULTS_PER_TOOL: int = int(os.getenv("MCP_MAX_RESULTS_PER_TOOL", "100"))
    
    # Security Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # Elasticsearch Configuration
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "localhost")
    ELASTICSEARCH_PORT: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()