"""Google Gemini provider implementation with unified error handling."""
import os
from typing import Any, Dict, List, Optional, Tuple

from .base import AIProviderInterface, AIResponse, ErrorType


class GeminiProvider(AIProviderInterface):
    """Google Gemini API provider implementation."""

    @property
    def SUPPORTED_MODELS(self) -> List[str]:
        """Get supported models from shared node enums."""
        try:
            from shared.models.node_enums import GoogleGeminiModel

            return [model.value for model in GoogleGeminiModel]
        except ImportError:
            # Fallback to hardcoded list if shared enums not available
            return ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"]

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini provider."""
        super().__init__(api_key or os.getenv("GOOGLE_API_KEY"))

    def call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        safety_settings: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ) -> AIResponse:
        """Call Gemini API with comprehensive error handling."""
        try:
            # Validate inputs
            is_valid, error_msg = self.validate_model(model)
            if not is_valid:
                return self.create_error_response(ErrorType.INVALID_REQUEST, error_msg)

            if not self.api_key:
                return self.create_error_response(
                    ErrorType.AUTH_ERROR, "Google API key not found in environment or parameters"
                )

            # Import Google Generative AI client
            try:
                import google.generativeai as genai
            except ImportError:
                return self.create_error_response(
                    ErrorType.UNKNOWN,
                    "Google Generative AI library not installed. Run: pip install google-generativeai",
                )

            # Configure the API key
            genai.configure(api_key=self.api_key)

            # Create the model
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            # Initialize model with generation config
            gemini_model = genai.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                safety_settings=safety_settings,
            )

            # Build the prompt
            # Gemini doesn't have a separate system prompt, so we combine them
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            # Note: Gemini doesn't support conversation history in the same way
            # as OpenAI/Claude. For multi-turn conversations, you'd need to use
            # gemini_model.start_chat() instead
            if messages:
                # For simplicity, append previous messages to the prompt
                history_text = "\n\n".join(
                    [f"{msg['role'].upper()}: {msg['content']}" for msg in messages]
                )
                full_prompt = f"{system_prompt}\n\nConversation History:\n{history_text}\n\nUSER: {user_prompt}"

            # Make API call
            self.logger.info(f"Calling Gemini API with model: {model}")
            response = gemini_model.generate_content(full_prompt)

            # Extract content
            if not response.text:
                # Check if response was blocked
                if hasattr(response, "prompt_feedback"):
                    return self.create_error_response(
                        ErrorType.RESPONSE_ERROR,
                        f"Response blocked: {response.prompt_feedback}",
                        response,
                    )

                return self.create_error_response(
                    ErrorType.RESPONSE_ERROR, "Empty response from Gemini API", response
                )

            content = response.text

            # Create success response with metadata
            metadata = {
                "model": model,
                "safety_ratings": (
                    [rating.__dict__ for rating in response.safety_ratings]
                    if hasattr(response, "safety_ratings")
                    else []
                ),
            }

            # Add usage information if available
            if hasattr(response, "usage_metadata"):
                metadata["usage"] = {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    ),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }

            return self.create_success_response(
                content=content, raw_response=response, metadata=metadata
            )

        except Exception as e:
            # Handle specific Google API exceptions
            error_type = ErrorType.UNKNOWN
            error_message = str(e)

            # Try to identify specific error types
            if "API key not valid" in str(e):
                error_type = ErrorType.AUTH_ERROR
                error_message = "Invalid Google API key"
            elif "quota" in str(e).lower() or "rate" in str(e).lower():
                error_type = ErrorType.RATE_LIMIT
                error_message = "Gemini API rate limit or quota exceeded"
            elif "not found" in str(e).lower() and "model" in str(e).lower():
                error_type = ErrorType.MODEL_ERROR
                error_message = f"Model not found: {e}"
            elif "timeout" in str(e).lower():
                error_type = ErrorType.TIMEOUT
                error_message = "Gemini API request timed out"
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                error_type = ErrorType.NETWORK_ERROR
                error_message = "Failed to connect to Gemini API"
            elif "safety" in str(e).lower() or "blocked" in str(e).lower():
                error_type = ErrorType.RESPONSE_ERROR
                error_message = f"Response blocked by safety filters: {e}"

            return self.create_error_response(error_type, error_message, e)

    def validate_model(self, model: str) -> Tuple[bool, str]:
        """Validate if the model is supported by Gemini."""
        supported_models = self.SUPPORTED_MODELS
        if model in supported_models:
            return True, ""

        return False, (
            f"Invalid Gemini model '{model}'. " f"Supported models: {', '.join(supported_models)}"
        )

    def get_supported_models(self) -> List[str]:
        """Get list of supported Gemini models."""
        return self.SUPPORTED_MODELS.copy()

    def _detect_provider_specific_errors(self, content: str) -> Tuple[bool, str]:
        """Detect Gemini-specific error patterns in content."""
        content_lower = content.lower()

        # Gemini-specific error patterns
        if "google" in content_lower and "error" in content_lower:
            return True, content

        # Gemini safety filter messages
        if "content was blocked" in content_lower:
            return True, content

        if "safety ratings" in content_lower and "harmful" in content_lower:
            return True, content

        return False, ""
