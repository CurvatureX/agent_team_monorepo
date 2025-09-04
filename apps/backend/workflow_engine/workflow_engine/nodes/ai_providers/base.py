"""Base interface for AI providers with unified error handling."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import logging


class ErrorType(Enum):
    """Standardized error types across all AI providers."""
    NONE = "none"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    INVALID_REQUEST = "invalid_request"
    MODEL_ERROR = "model_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RESPONSE_ERROR = "response_error"
    UNKNOWN = "unknown"


@dataclass
class AIResponse:
    """Standardized response structure for all AI providers."""
    success: bool
    content: str = ""
    error_type: ErrorType = ErrorType.NONE
    error_message: str = ""
    raw_response: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "content": self.content,
            "error_type": self.error_type.value,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class AIProviderInterface(ABC):
    """Abstract base class for AI provider implementations."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize provider with optional API key."""
        self.api_key = api_key
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AIResponse:
        """
        Call the AI provider's API.
        
        Args:
            system_prompt: System message for the AI
            user_prompt: User's input message
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters
            
        Returns:
            AIResponse object with standardized structure
        """
        pass
    
    @abstractmethod
    def validate_model(self, model: str) -> Tuple[bool, str]:
        """
        Validate if the model is supported by this provider.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Get list of supported models for this provider."""
        pass
    
    def detect_error_in_content(self, content: str) -> Tuple[bool, str]:
        """
        Detect if the response content contains error indicators.
        
        This is a fallback check for cases where the API returns 200
        but the content indicates an error.
        
        Returns:
            Tuple of (is_error, error_message)
        """
        if not content:
            return True, "Empty response content"
        
        # Common error patterns across providers
        error_indicators = [
            "error:",
            "Error:",
            "ERROR:",
            "failed",
            "Failed",
            "exception",
            "Exception",
            "invalid request",
            "Invalid request",
            "unauthorized",
            "Unauthorized",
            "rate limit",
            "Rate limit",
            "api key",
            "API key",
            "not found",
            "Not found",
            "bad request",
            "Bad request",
            "internal server error",
            "Internal server error",
        ]
        
        content_lower = content.lower()
        
        # Check for error indicators
        for indicator in error_indicators:
            if indicator.lower() in content_lower[:200]:  # Check first 200 chars
                return True, f"Error indicator found: {content}"
        
        # Check for suspiciously short responses
        if len(content.strip()) < 5:
            return True, f"Response too short: '{content}'"
        
        # Provider-specific error detection can be implemented in subclasses
        return self._detect_provider_specific_errors(content)
    
    def _detect_provider_specific_errors(self, content: str) -> Tuple[bool, str]:
        """
        Override in subclasses for provider-specific error detection.
        
        Returns:
            Tuple of (is_error, error_message)
        """
        return False, ""
    
    def create_error_response(
        self, 
        error_type: ErrorType, 
        error_message: str,
        raw_error: Any = None
    ) -> AIResponse:
        """Create a standardized error response."""
        self.logger.error(f"{error_type.value}: {error_message}")
        
        return AIResponse(
            success=False,
            error_type=error_type,
            error_message=error_message,
            raw_response=raw_error,
            metadata={"provider": self.__class__.__name__}
        )
    
    def create_success_response(
        self,
        content: str,
        raw_response: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AIResponse:
        """Create a standardized success response."""
        # Final validation of content
        is_error, error_msg = self.detect_error_in_content(content)
        if is_error:
            return self.create_error_response(
                ErrorType.RESPONSE_ERROR,
                error_msg,
                raw_response
            )
        
        return AIResponse(
            success=True,
            content=content,
            raw_response=raw_response,
            metadata={
                "provider": self.__class__.__name__,
                **(metadata or {})
            }
        )