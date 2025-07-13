"""
Configuration settings for Workflow Agent
"""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service settings
    APP_NAME: str = "Workflow Agent"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # gRPC settings
    GRPC_HOST: str = os.getenv("GRPC_HOST", "[::]")
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50051"))
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "10"))

    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost/workflow_agent"
    )

    # Redis settings (for state management)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # AI Model settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEFAULT_MODEL_PROVIDER: str = os.getenv("DEFAULT_MODEL_PROVIDER", "openai")
    DEFAULT_MODEL_NAME: str = os.getenv("DEFAULT_MODEL_NAME", "gpt-4")

    # LangGraph settings
    LANGGRAPH_CHECKPOINT_BACKEND: str = os.getenv("LANGGRAPH_CHECKPOINT_BACKEND", "redis")

    # Workflow generation settings
    MAX_WORKFLOW_NODES: int = int(os.getenv("MAX_WORKFLOW_NODES", "50"))
    DEFAULT_TIMEOUT: int = int(os.getenv("DEFAULT_TIMEOUT", "300"))  # 5 minutes

    class Config:
        env_file = ".env"


settings = Settings()
