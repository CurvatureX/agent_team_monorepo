"""OpenAI provider implementation with unified error handling."""
import os
from typing import Dict, Any, List, Optional, Tuple
from .base import AIProviderInterface, AIResponse, ErrorType


class OpenAIProvider(AIProviderInterface):
    """OpenAI API provider implementation."""
    
    # Supported models from the shared enums
    SUPPORTED_MODELS = [
        "gpt-5",
        "gpt-5-nano", 
        "gpt-5-mini",
        "gpt-4.1-turbo",
        "gpt-4.1-turbo-realtime",
        "gpt-4.1-turbo-preview",
        "gpt-4.1-mini",
        "gpt-4.1-mini-realtime",
        "gpt-4.1-preview",
        "o1",
        "o1-preview",
        "o1-mini",
        "o3-mini"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI provider."""
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"))
        
    def call_api(
        self,
        system_prompt: str,
        user_prompt: str, 
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AIResponse:
        """Call OpenAI API with comprehensive error handling."""
        try:
            # Validate inputs
            is_valid, error_msg = self.validate_model(model)
            if not is_valid:
                return self.create_error_response(
                    ErrorType.INVALID_REQUEST,
                    error_msg
                )
            
            if not self.api_key:
                return self.create_error_response(
                    ErrorType.AUTH_ERROR,
                    "OpenAI API key not found in environment or parameters"
                )
            
            # Import OpenAI client
            try:
                from openai import OpenAI
            except ImportError:
                return self.create_error_response(
                    ErrorType.UNKNOWN,
                    "OpenAI library not installed. Run: pip install openai"
                )
            
            # Create client
            client = OpenAI(api_key=self.api_key)
            
            # Build messages
            conversation_messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if provided
            if messages:
                conversation_messages.extend(messages)
                
            # Add current user message
            conversation_messages.append({"role": "user", "content": user_prompt})
            
            # Prepare API call parameters
            completion_params = {
                "model": model,
                "messages": conversation_messages,
                "temperature": temperature,
                "presence_penalty": presence_penalty,
                "frequency_penalty": frequency_penalty,
            }
            
            # Handle model-specific parameter differences
            if model.startswith("gpt-5"):
                # GPT-5 models use max_completion_tokens instead of max_tokens
                completion_params["max_completion_tokens"] = max_tokens
            else:
                completion_params["max_tokens"] = max_tokens
            
            # Make API call
            self.logger.info(f"Calling OpenAI API with model: {model}")
            response = client.chat.completions.create(**completion_params)
            
            # Extract content
            if not response.choices or not response.choices[0].message:
                return self.create_error_response(
                    ErrorType.RESPONSE_ERROR,
                    "Empty or invalid response structure from OpenAI",
                    response
                )
            
            content = response.choices[0].message.content
            if content is None:
                content = ""
                self.logger.warning(f"OpenAI returned None content. Model: {model}, Finish reason: {response.choices[0].finish_reason}")
                
            # Log content details for debugging
            self.logger.info(f"OpenAI response - Content length: {len(content) if content else 0}, Model: {model}")
            
            # Check finish reason for potential issues
            finish_reason = response.choices[0].finish_reason if response.choices else None
            if finish_reason and finish_reason not in ["stop", "function_call"]:
                self.logger.warning(f"OpenAI finish reason indicates potential issue: {finish_reason}")
            
            # Create success response with metadata
            metadata = {
                "model": model,
                "usage": response.usage.dict() if response.usage else {},
                "finish_reason": finish_reason
            }
            
            return self.create_success_response(
                content=content,
                raw_response=response,
                metadata=metadata
            )
            
        except Exception as e:
            # Handle specific OpenAI exceptions
            error_type = ErrorType.UNKNOWN
            error_message = str(e)
            
            # Try to identify specific error types
            if "AuthenticationError" in type(e).__name__:
                error_type = ErrorType.AUTH_ERROR
                error_message = "Invalid or missing OpenAI API key"
            elif "RateLimitError" in type(e).__name__:
                error_type = ErrorType.RATE_LIMIT
                error_message = "OpenAI API rate limit exceeded. Please try again later."
            elif "APIError" in type(e).__name__:
                error_type = ErrorType.MODEL_ERROR
                if "model" in str(e).lower():
                    error_message = f"Model error: {e}"
                else:
                    error_message = f"OpenAI API error: {e}"
            elif "APIConnectionError" in type(e).__name__:
                error_type = ErrorType.NETWORK_ERROR
                error_message = "Failed to connect to OpenAI API"
            elif "APITimeoutError" in type(e).__name__:
                error_type = ErrorType.TIMEOUT
                error_message = "OpenAI API request timed out"
            elif "unsupported parameter" in str(e).lower():
                error_type = ErrorType.INVALID_REQUEST
                # Extract the specific parameter error
                if "max_tokens" in str(e):
                    error_message = "Parameter error: Use 'max_completion_tokens' for GPT-5 models"
                else:
                    error_message = f"Invalid parameter: {e}"
            
            return self.create_error_response(error_type, error_message, e)
    
    def validate_model(self, model: str) -> Tuple[bool, str]:
        """Validate if the model is supported by OpenAI."""
        if model in self.SUPPORTED_MODELS:
            return True, ""
        
        return False, (
            f"Invalid OpenAI model '{model}'. "
            f"Supported models: {', '.join(self.SUPPORTED_MODELS)}"
        )
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported OpenAI models."""
        return self.SUPPORTED_MODELS.copy()
    
    def _detect_provider_specific_errors(self, content: str) -> Tuple[bool, str]:
        """Detect OpenAI-specific error patterns in content."""
        content_lower = content.lower()
        
        # OpenAI-specific error patterns
        if "error code:" in content_lower:
            return True, content
            
        if content.startswith('{"error":'):
            return True, content
            
        # Check for parameter errors that might be returned as content
        if "unsupported parameter" in content_lower:
            return True, content
            
        return False, ""