"""
Configuration settings for Workflow Agent
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Service settings
    APP_NAME: str = "Workflow Agent"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


    # FastAPI settings
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8001"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost/workflow_agent"
    )

    # AI Model settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEFAULT_MODEL_PROVIDER: str = os.getenv("DEFAULT_MODEL_PROVIDER", "openai")
    DEFAULT_MODEL_NAME: str = os.getenv("DEFAULT_MODEL_NAME", "gpt-4")

    # LangGraph settings

    # Supabase settings for vector store (using SECRET_KEY only)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")

    # Vector embedding settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))

    # RAG settings
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))
    RAG_MAX_RESULTS: int = int(os.getenv("RAG_MAX_RESULTS", "5"))
    RAG_ENABLE_RERANKING: bool = os.getenv("RAG_ENABLE_RERANKING", "true").lower() == "true"

    # Workflow generation settings
    MAX_WORKFLOW_NODES: int = int(os.getenv("MAX_WORKFLOW_NODES", "50"))
    DEFAULT_TIMEOUT: int = int(os.getenv("DEFAULT_TIMEOUT", "300"))  # 5 minutes

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
