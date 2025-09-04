"""Anthropic Claude provider implementation with unified error handling."""
import os
from typing import Dict, Any, List, Optional, Tuple
from .base import AIProviderInterface, AIResponse, ErrorType


class ClaudeProvider(AIProviderInterface):
    """Anthropic Claude API provider implementation."""
    
    # Supported models from the shared enums
    SUPPORTED_MODELS = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229", 
        "claude-3-haiku-20240307",
        "claude-3.5-sonnet-20241022",
        "claude-3.5-haiku-20241022"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude provider."""
        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"))
        
    def call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop_sequences: Optional[List[str]] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AIResponse:
        """Call Claude API with comprehensive error handling."""
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
                    "Anthropic API key not found in environment or parameters"
                )
            
            # Import Anthropic client
            try:
                import anthropic
            except ImportError:
                return self.create_error_response(
                    ErrorType.UNKNOWN,
                    "Anthropic library not installed. Run: pip install anthropic"
                )
            
            # Create client
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Build messages in Claude format
            conversation_messages = []
            
            # Add conversation history if provided
            if messages:
                for msg in messages:
                    # Claude expects user/assistant roles only in messages
                    if msg["role"] == "system":
                        # System messages are handled separately in Claude
                        continue
                    conversation_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Add current user message
            conversation_messages.append({
                "role": "user",
                "content": user_prompt
            })
            
            # Prepare API call parameters
            create_params = {
                "model": model,
                "messages": conversation_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,  # Claude handles system prompt separately
            }
            
            # Add optional parameters
            if stop_sequences:
                create_params["stop_sequences"] = stop_sequences
            
            # Make API call
            self.logger.info(f"Calling Claude API with model: {model}")
            response = client.messages.create(**create_params)
            
            # Extract content from Claude's response format
            if not response.content:
                return self.create_error_response(
                    ErrorType.RESPONSE_ERROR,
                    "Empty response from Claude API",
                    response
                )
            
            # Claude returns content as a list of content blocks
            content_parts = []
            for content_block in response.content:
                if hasattr(content_block, 'text'):
                    content_parts.append(content_block.text)
            
            content = ''.join(content_parts)
            
            if not content:
                return self.create_error_response(
                    ErrorType.RESPONSE_ERROR,
                    "No text content in Claude response",
                    response
                )
            
            # Create success response with metadata
            metadata = {
                "model": model,
                "usage": {
                    "input_tokens": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                    "output_tokens": response.usage.output_tokens if hasattr(response, 'usage') else 0,
                },
                "stop_reason": response.stop_reason if hasattr(response, 'stop_reason') else None
            }
            
            return self.create_success_response(
                content=content,
                raw_response=response,
                metadata=metadata
            )
            
        except Exception as e:
            # Handle specific Anthropic exceptions
            error_type = ErrorType.UNKNOWN
            error_message = str(e)
            
            # Try to identify specific error types
            if "AuthenticationError" in type(e).__name__:
                error_type = ErrorType.AUTH_ERROR
                error_message = "Invalid or missing Anthropic API key"
            elif "RateLimitError" in type(e).__name__:
                error_type = ErrorType.RATE_LIMIT
                error_message = "Claude API rate limit exceeded. Please try again later."
            elif "BadRequestError" in type(e).__name__:
                error_type = ErrorType.INVALID_REQUEST
                error_message = f"Invalid request: {e}"
            elif "APIConnectionError" in type(e).__name__:
                error_type = ErrorType.NETWORK_ERROR
                error_message = "Failed to connect to Claude API"
            elif "APITimeoutError" in type(e).__name__:
                error_type = ErrorType.TIMEOUT
                error_message = "Claude API request timed out"
            elif "model" in str(e).lower():
                error_type = ErrorType.MODEL_ERROR
                error_message = f"Model error: {e}"
            
            return self.create_error_response(error_type, error_message, e)
    
    def validate_model(self, model: str) -> Tuple[bool, str]:
        """Validate if the model is supported by Claude."""
        if model in self.SUPPORTED_MODELS:
            return True, ""
        
        return False, (
            f"Invalid Claude model '{model}'. "
            f"Supported models: {', '.join(self.SUPPORTED_MODELS)}"
        )
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported Claude models."""
        return self.SUPPORTED_MODELS.copy()
    
    def _detect_provider_specific_errors(self, content: str) -> Tuple[bool, str]:
        """Detect Claude-specific error patterns in content."""
        content_lower = content.lower()
        
        # Claude-specific error patterns
        if "anthropic" in content_lower and "error" in content_lower:
            return True, content
            
        # Claude sometimes returns error messages in a specific format
        if content.startswith("I'm sorry") and "error" in content_lower:
            return True, content
            
        return False, ""