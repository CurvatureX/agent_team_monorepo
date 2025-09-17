"""Factory for creating AI provider instances."""
from typing import Dict, Optional, Type

from .base import AIProviderInterface
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


class AIProviderFactory:
    """Factory class for creating AI provider instances."""

    # Map of provider names to their implementation classes
    PROVIDERS: Dict[str, Type[AIProviderInterface]] = {
        "openai": OpenAIProvider,
        "anthropic": ClaudeProvider,
        "claude": ClaudeProvider,  # Alias
        "google": GeminiProvider,
        "gemini": GeminiProvider,  # Alias
    }

    # Map of node subtypes to provider names
    SUBTYPE_TO_PROVIDER = {
        "OPENAI_CHATGPT": "openai",
        "ANTHROPIC_CLAUDE": "anthropic",
        "GOOGLE_GEMINI": "google",
    }

    @classmethod
    def create_provider(
        cls, provider_name: str, api_key: Optional[str] = None
    ) -> AIProviderInterface:
        """
        Create an AI provider instance.

        Args:
            provider_name: Name of the provider (openai, anthropic, google)
            api_key: Optional API key (will use environment variable if not provided)

        Returns:
            AIProviderInterface instance

        Raises:
            ValueError: If provider is not supported
        """
        provider_name = provider_name.lower()

        if provider_name not in cls.PROVIDERS:
            supported = ", ".join(cls.PROVIDERS.keys())
            raise ValueError(
                f"Unsupported provider: {provider_name}. " f"Supported providers: {supported}"
            )

        provider_class = cls.PROVIDERS[provider_name]
        return provider_class(api_key=api_key)

    @classmethod
    def create_from_subtype(
        cls, subtype: str, api_key: Optional[str] = None
    ) -> AIProviderInterface:
        """
        Create an AI provider instance from node subtype.

        Args:
            subtype: Node subtype (e.g., OPENAI_CHATGPT)
            api_key: Optional API key

        Returns:
            AIProviderInterface instance

        Raises:
            ValueError: If subtype is not supported
        """
        if subtype not in cls.SUBTYPE_TO_PROVIDER:
            supported = ", ".join(cls.SUBTYPE_TO_PROVIDER.keys())
            raise ValueError(f"Unsupported subtype: {subtype}. " f"Supported subtypes: {supported}")

        provider_name = cls.SUBTYPE_TO_PROVIDER[subtype]
        return cls.create_provider(provider_name, api_key)

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names."""
        return list(cls.PROVIDERS.keys())

    @classmethod
    def get_supported_subtypes(cls) -> list[str]:
        """Get list of supported node subtypes."""
        return list(cls.SUBTYPE_TO_PROVIDER.keys())
