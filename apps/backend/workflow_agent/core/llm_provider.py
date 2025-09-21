"""
LLM Provider abstraction for supporting multiple LLM APIs (OpenAI, OpenRouter, etc.)
"""

import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"


class LLMConfig:
    """Configuration for LLM providers"""

    def __init__(self):
        # Read from environment variables
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()

        # Log all LLM-related environment variables for debugging
        logger.info("=== LLM Configuration Debug ===")
        logger.info(f"LLM_PROVIDER: {self.provider}")
        logger.info(f"OPENAI_MODEL env: {os.getenv('OPENAI_MODEL', 'not set')}")
        logger.info(f"OPENROUTER_MODEL env: {os.getenv('OPENROUTER_MODEL', 'not set')}")
        logger.info(f"ANTHROPIC_MODEL env: {os.getenv('ANTHROPIC_MODEL', 'not set')}")
        logger.info(f"DEFAULT_MODEL_NAME env: {os.getenv('DEFAULT_MODEL_NAME', 'not set')}")
        logger.info(f"DEFAULT_MODEL_PROVIDER env: {os.getenv('DEFAULT_MODEL_PROVIDER', 'not set')}")
        logger.info(f"LLM_MAX_TOKENS: {os.getenv('LLM_MAX_TOKENS', 'not set')}")
        logger.info(f"OPENAI_API_KEY present: {bool(os.getenv('OPENAI_API_KEY'))}")
        logger.info(f"OPENROUTER_API_KEY present: {bool(os.getenv('OPENROUTER_API_KEY'))}")
        logger.info("==============================")

        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", None)

        # OpenRouter configuration
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        # Anthropic configuration (for future use)
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

        # Common settings
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        self.timeout = int(os.getenv("LLM_TIMEOUT", "60"))

        # Embedding settings (for RAG)
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")

        # Log final selected model
        logger.info(f"Selected provider: {self.provider}")
        logger.info(f"Will use model: {self.get_model_name()}")

    def get_api_key(self) -> str:
        """Get API key for the configured provider"""
        if self.provider == LLMProvider.OPENROUTER:
            return self.openrouter_api_key
        elif self.provider == LLMProvider.ANTHROPIC:
            return self.anthropic_api_key
        else:
            return self.openai_api_key

    def get_model_name(self) -> str:
        """Get model name for the configured provider"""
        if self.provider == LLMProvider.OPENROUTER:
            return self.openrouter_model
        elif self.provider == LLMProvider.ANTHROPIC:
            return self.anthropic_model
        else:
            return self.openai_model

    def get_base_url(self) -> Optional[str]:
        """Get base URL for the configured provider"""
        if self.provider == LLMProvider.OPENROUTER:
            return self.openrouter_base_url
        elif self.provider == LLMProvider.OPENAI and self.openai_base_url:
            return self.openai_base_url
        return None


class LLMFactory:
    """Factory for creating LLM instances based on configuration"""

    @staticmethod
    def create_llm(
        config: Optional[LLMConfig] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> BaseChatModel:
        """
        Create an LLM instance based on configuration

        Args:
            config: LLM configuration (uses environment if not provided)
            temperature: Override temperature setting
            max_tokens: Override max tokens setting
            **kwargs: Additional parameters for the LLM

        Returns:
            Configured LLM instance
        """
        if config is None:
            config = LLMConfig()

        api_key = config.get_api_key()
        model_name = config.get_model_name()
        base_url = config.get_base_url()

        if not api_key:
            raise ValueError(f"API key not configured for provider: {config.provider}")

        # Use provided values or fall back to config
        temperature = temperature if temperature is not None else config.temperature
        # Don't set max_tokens if None - let the model use its maximum
        max_tokens = max_tokens if max_tokens is not None else config.max_tokens
        if max_tokens == 0:  # Use 0 as a signal for "no limit"
            max_tokens = None

        logger.info(f"Creating LLM with provider={config.provider}, model={model_name}, base_url={base_url}")
        logger.info(f"Final parameters: temperature={temperature}, max_tokens={max_tokens}, timeout={config.timeout}")

        if config.provider == LLMProvider.OPENROUTER:
            # OpenRouter uses OpenAI-compatible API
            llm_kwargs = {
                "api_key": api_key,
                "base_url": base_url,
                "model": model_name,
                "temperature": temperature,
                "timeout": config.timeout,
                "default_headers": {
                    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://starmates.ai"),
                    "X-Title": os.getenv("OPENROUTER_APP_NAME", "Starmates Workflow Agent"),
                },
                **kwargs
            }
            if max_tokens is not None:  # Only add max_tokens if it's set
                llm_kwargs["max_tokens"] = max_tokens
            logger.info(f"OpenRouter LLM kwargs: {llm_kwargs}")
            return ChatOpenAI(**llm_kwargs)
        elif config.provider == LLMProvider.ANTHROPIC:
            # For Anthropic, we could use langchain_anthropic.ChatAnthropic
            # But for now, we'll use OpenAI-compatible interface
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                api_key=api_key,
                temperature=temperature,
                timeout=config.timeout,
                **kwargs
            )
        else:
            # Default to OpenAI
            llm_kwargs = {
                "api_key": api_key,
                "model": model_name,
                "temperature": temperature,
                "timeout": config.timeout,
                **kwargs
            }

            # GPT-5 models use max_completion_tokens instead of max_tokens
            if model_name and "gpt-5" in model_name:
                if max_tokens is not None:
                    llm_kwargs["max_completion_tokens"] = max_tokens
                    logger.info(f"Using max_completion_tokens={max_tokens} for GPT-5 model: {model_name}")
            else:
                if max_tokens is not None:
                    llm_kwargs["max_tokens"] = max_tokens

            if base_url:
                llm_kwargs["base_url"] = base_url
            logger.info(f"OpenAI LLM kwargs: {llm_kwargs}")
            return ChatOpenAI(**llm_kwargs)

    @staticmethod
    def create_embedding_model(config: Optional[LLMConfig] = None):
        """
        Create an embedding model based on configuration

        Args:
            config: LLM configuration (uses environment if not provided)

        Returns:
            Configured embedding model
        """
        if config is None:
            config = LLMConfig()

        if config.embedding_provider == "openrouter":
            # OpenRouter doesn't typically provide embeddings, fall back to OpenAI
            logger.warning("OpenRouter doesn't provide embeddings, falling back to OpenAI")
            config.embedding_provider = "openai"

        if config.embedding_provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            api_key = config.openai_api_key if config.embedding_provider == "openai" else config.get_api_key()
            return OpenAIEmbeddings(
                api_key=api_key,
                model=config.embedding_model,
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {config.embedding_provider}")


# Global instance for easy access
llm_config = LLMConfig()