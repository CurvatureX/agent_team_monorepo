"""
Configuration settings for API Gateway
"""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Gateway settings
    APP_NAME: str = "API Gateway"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]

    # gRPC settings
    WORKFLOW_AGENT_HOST: str = os.getenv("WORKFLOW_AGENT_HOST", "localhost")
    WORKFLOW_AGENT_PORT: int = int(os.getenv("WORKFLOW_AGENT_PORT", "50051"))

    # Database settings (if needed for API Gateway)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./api_gateway.db")

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MCP Service settings
    MCP_ENABLED: bool = os.getenv("MCP_ENABLED", "true").lower() == "true"
    MCP_MAX_RESULTS_PER_TOOL: int = int(os.getenv("MCP_MAX_RESULTS_PER_TOOL", "100"))

    # Node Knowledge settings
    NODE_KNOWLEDGE_SUPABASE_URL: str = os.getenv("NODE_KNOWLEDGE_SUPABASE_URL", "")
    NODE_KNOWLEDGE_SUPABASE_KEY: str = os.getenv("NODE_KNOWLEDGE_SUPABASE_KEY", "")
    NODE_KNOWLEDGE_DEFAULT_THRESHOLD: float = float(
        os.getenv("NODE_KNOWLEDGE_DEFAULT_THRESHOLD", "0.3")
    )

    # Elasticsearch settings (future)
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "localhost")
    ELASTICSEARCH_PORT: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))

    class Config:
        env_file = ".env"


settings = Settings()
