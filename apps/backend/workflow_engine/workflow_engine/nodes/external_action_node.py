"""
External Action Node implementation
Integrates external API adapters for workflow automation
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from enum import Enum

from sqlalchemy import text

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus
from ..services.api_adapters.base import APIAdapter, APIError, APIAdapterRegistry
from ..services.oauth2_service import OAuth2Service, create_oauth2_service
from ..services.credential_encryption import CredentialEncryption
from ..models.database import get_db_session

logger = logging.getLogger(__name__)


class ExternalAPIProvider(Enum):
    """Supported external API providers"""
    GOOGLE_CALENDAR = "google_calendar"
    GITHUB = "github"
    SLACK = "slack"
    HTTP_TOOL = "http_tool"


@dataclass
class ExternalActionConfig:
    """Configuration for External Action Node"""
    api_service: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    credential_id: Optional[str] = None
    retry_on_failure: bool = True
    timeout_seconds: int = 30
    
    def validate(self) -> List[str]:
        """Validate configuration parameters"""
        errors = []
        
        if not self.api_service:
            errors.append("api_service is required")
        
        if not self.operation:
            errors.append("operation is required")
        
        # Validate api_service is supported
        try:
            ExternalAPIProvider(self.api_service)
        except ValueError:
            valid_providers = [p.value for p in ExternalAPIProvider]
            errors.append(f"Invalid api_service '{self.api_service}'. Must be one of: {valid_providers}")
        
        return errors


@dataclass
class APICallResult:
    """Result of an external API call"""
    success: bool
    data: Dict[str, Any]
    provider: str
    operation: str
    execution_time_ms: float
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    api_response_status: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "data": self.data,
            "provider": self.provider,
            "operation": self.operation,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "api_response_status": self.api_response_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class APIAdapterFactory:
    """Factory for creating API adapters"""
    
    @staticmethod
    def create_adapter(api_service: str) -> APIAdapter:
        """Create an API adapter instance for the specified service"""
        try:
            adapter_class = APIAdapterRegistry.get_adapter_class(api_service)
            return adapter_class()
        except ValueError as e:
            logger.error(f"Failed to create adapter for {api_service}: {str(e)}")
            raise APIError(f"Unsupported API service: {api_service}")
    
    @staticmethod
    def get_available_adapters() -> List[str]:
        """Get list of available API adapters"""
        return APIAdapterRegistry.list_adapters()


class ExternalActionNodeExecutor(BaseNodeExecutor):
    """Executor for External Action nodes"""
    
    def __init__(self, 
                 oauth2_service: Optional[OAuth2Service] = None,
                 encryption_service: Optional[CredentialEncryption] = None):
        super().__init__()
        self.oauth2_service = oauth2_service
        self.encryption_service = encryption_service
        
        # If services not provided, we'll create them when needed
        # This allows for dependency injection while maintaining backwards compatibility
    
    def get_supported_subtypes(self) -> List[str]:
        """Get list of supported node subtypes"""
        return ["external_api_call", "api_integration", "webhook_call"]
    
    def validate(self, node: Any) -> List[str]:
        """Validate External Action node configuration"""
        errors = []
        
        # Validate basic node structure
        if not hasattr(node, 'parameters'):
            errors.append("Node missing parameters")
            return errors
        
        # Parse and validate configuration
        try:
            config = self._parse_config(node.parameters)
            errors.extend(config.validate())
        except Exception as e:
            errors.append(f"Invalid configuration: {str(e)}")
        
        # Validate API adapter availability
        try:
            available_adapters = APIAdapterRegistry.list_adapters()
            api_service = node.parameters.get('api_service', '')
            if api_service and api_service not in available_adapters:
                errors.append(f"API adapter '{api_service}' not available. Available: {available_adapters}")
        except Exception as e:
            errors.append(f"Failed to check adapter availability: {str(e)}")
        
        return errors
    
    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute External Action node"""
        start_time = time.time()
        logs = []
        
        try:
            # Parse configuration
            config = self._parse_config(context.node.parameters)
            logs.append(f"Executing {config.api_service}.{config.operation}")
            
            # Validate configuration
            config_errors = config.validate()
            if config_errors:
                return self._create_error_result(
                    f"Configuration validation failed: {'; '.join(config_errors)}",
                    execution_time=(time.time() - start_time) * 1000,
                    logs=logs
                )
            
            # Get user credentials for the API service
            user_id = context.metadata.get('user_id')
            if not user_id:
                return self._create_error_result(
                    "User ID not found in execution context",
                    execution_time=(time.time() - start_time) * 1000,
                    logs=logs
                )
            
            credentials = await self._get_user_credentials(user_id, config.api_service, logs)
            if not credentials:
                return self._create_error_result(
                    f"No valid credentials found for {config.api_service}. Please authorize the application.",
                    execution_time=(time.time() - start_time) * 1000,
                    logs=logs
                )
            
            # Create API adapter
            adapter = APIAdapterRegistry.create_adapter(config.api_service)
            logs.append(f"Created {config.api_service} adapter")
            
            # Execute API call
            result = await self._execute_api_call(adapter, config, credentials, logs)
            
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            
            # Log API call for audit purposes
            await self._log_api_call(context, config, result)
            
            if result.success:
                logs.append(f"API call completed successfully in {result.execution_time_ms:.2f}ms")
                return self._create_success_result(
                    output_data={
                        "api_result": result.to_dict(),
                        "response_data": result.data
                    },
                    execution_time=execution_time,
                    logs=logs,
                    metadata={
                        "api_service": config.api_service,
                        "operation": config.operation,
                        "execution_time_ms": result.execution_time_ms
                    }
                )
            else:
                logs.append(f"API call failed: {result.error_message}")
                return self._create_error_result(
                    result.error_message or "API call failed",
                    error_details={
                        "api_result": result.to_dict(),
                        "provider": config.api_service,
                        "operation": config.operation
                    },
                    execution_time=execution_time,
                    logs=logs
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"External Action execution failed: {str(e)}"
            logs.append(error_msg)
            logger.exception("External Action execution failed")
            
            return self._create_error_result(
                error_msg,
                error_details={"exception_type": type(e).__name__},
                execution_time=execution_time,
                logs=logs
            )
    
    def _parse_config(self, parameters: Dict[str, Any]) -> ExternalActionConfig:
        """Parse node parameters into configuration object"""
        return ExternalActionConfig(
            api_service=parameters.get('api_service', ''),
            operation=parameters.get('operation', ''),
            parameters=parameters.get('parameters', {}),
            credential_id=parameters.get('credential_id'),
            retry_on_failure=parameters.get('retry_on_failure', True),
            timeout_seconds=parameters.get('timeout_seconds', 30)
        )
    
    async def _get_user_credentials(self, user_id: str, api_service: str, logs: List[str]) -> Optional[Dict[str, str]]:
        """Get user credentials for the specified API service"""
        try:
            if not self.oauth2_service:
                # Create OAuth2 service if not provided
                # This is a fallback - in production, services should be injected
                logs.append("Creating OAuth2 service (fallback mode)")
                return None
            
            # Get valid token for the user and provider
            access_token = await self.oauth2_service.get_valid_token(user_id, api_service)
            
            if access_token:
                logs.append(f"Retrieved valid credentials for {api_service}")
                return {"access_token": access_token}
            else:
                logs.append(f"No valid credentials found for {api_service}")
                return None
                
        except Exception as e:
            logs.append(f"Failed to retrieve credentials for {api_service}: {str(e)}")
            logger.exception(f"Credential retrieval failed for user {user_id}, service {api_service}")
            return None
    
    async def _execute_api_call(self, 
                               adapter: APIAdapter, 
                               config: ExternalActionConfig, 
                               credentials: Dict[str, str],
                               logs: List[str]) -> APICallResult:
        """Execute the API call using the adapter"""
        call_start_time = time.time()
        
        try:
            # Validate credentials with adapter
            if not adapter.validate_credentials(credentials):
                return APICallResult(
                    success=False,
                    data={},
                    provider=config.api_service,
                    operation=config.operation,
                    execution_time_ms=0,
                    error_message="Invalid credentials format"
                )
            
            # Set timeout for the API call
            try:
                response_data = await asyncio.wait_for(
                    adapter.call(config.operation, config.parameters, credentials),
                    timeout=config.timeout_seconds
                )
                
                execution_time = (time.time() - call_start_time) * 1000
                
                return APICallResult(
                    success=True,
                    data=response_data,
                    provider=config.api_service,
                    operation=config.operation,
                    execution_time_ms=execution_time
                )
                
            except asyncio.TimeoutError:
                execution_time = (time.time() - call_start_time) * 1000
                return APICallResult(
                    success=False,
                    data={},
                    provider=config.api_service,
                    operation=config.operation,
                    execution_time_ms=execution_time,
                    error_message=f"API call timed out after {config.timeout_seconds} seconds"
                )
            
        except APIError as e:
            execution_time = (time.time() - call_start_time) * 1000
            return APICallResult(
                success=False,
                data={},
                provider=config.api_service,
                operation=config.operation,
                execution_time_ms=execution_time,
                error_message=str(e),
                error_details=getattr(e, 'response_data', None),
                api_response_status=getattr(e, 'status_code', None)
            )
        except Exception as e:
            execution_time = (time.time() - call_start_time) * 1000
            return APICallResult(
                success=False,
                data={},
                provider=config.api_service,
                operation=config.operation,
                execution_time_ms=execution_time,
                error_message=f"Unexpected error: {str(e)}",
                error_details={"exception_type": type(e).__name__}
            )
    
    async def _log_api_call(self, 
                           context: NodeExecutionContext, 
                           config: ExternalActionConfig, 
                           result: APICallResult) -> None:
        """Log API call for audit and monitoring purposes"""
        try:
            # Get user_id from context metadata
            user_id = context.metadata.get('user_id')
            if not user_id:
                logger.warning("No user_id found in context metadata, skipping database logging")
                return
            
            # Get node_id from context
            node_id = getattr(context.node, 'id', None)
            
            # Prepare request and response data (sanitized)
            request_data = {
                "operation": config.operation,
                "parameters_count": len(config.parameters) if config.parameters else 0,
                "timeout_seconds": config.timeout_seconds
            }
            
            response_data = {}
            if result.success and result.data:
                # Sanitize response data - remove sensitive information
                response_data = {
                    "data_keys": list(result.data.keys()) if isinstance(result.data, dict) else ["data"],
                    "response_size": len(str(result.data)) if result.data else 0
                }
            
            # Insert log entry into database
            with get_db_session() as db:
                insert_query = text("""
                    INSERT INTO external_api_call_logs (
                        user_id, workflow_execution_id, node_id,
                        provider, operation, api_endpoint, http_method,
                        request_data, response_data, request_headers, response_headers,
                        success, status_code, error_type, error_message,
                        response_time_ms, retry_count,
                        rate_limit_remaining, rate_limit_reset_at,
                        called_at
                    ) VALUES (
                        :user_id, :workflow_execution_id, :node_id,
                        :provider, :operation, :api_endpoint, :http_method,
                        :request_data, :response_data, :request_headers, :response_headers,
                        :success, :status_code, :error_type, :error_message,
                        :response_time_ms, :retry_count,
                        :rate_limit_remaining, :rate_limit_reset_at,
                        :called_at
                    )
                """)
                
                # Determine error type if call failed
                error_type = None
                if not result.success and result.error_message:
                    if "authentication" in result.error_message.lower() or "unauthorized" in result.error_message.lower():
                        error_type = "AuthenticationError"
                    elif "rate limit" in result.error_message.lower():
                        error_type = "RateLimitError"
                    elif "timeout" in result.error_message.lower():
                        error_type = "TimeoutError"
                    elif "network" in result.error_message.lower() or "connection" in result.error_message.lower():
                        error_type = "NetworkError"
                    else:
                        error_type = "APIError"
                
                db.execute(insert_query, {
                    "user_id": user_id,
                    "workflow_execution_id": context.execution_id,
                    "node_id": node_id,
                    "provider": config.api_service,
                    "operation": config.operation,
                    "api_endpoint": f"/{config.api_service}/{config.operation}",  # Simplified endpoint
                    "http_method": "POST",  # Most external API calls are POST
                    "request_data": request_data,
                    "response_data": response_data if result.success else None,
                    "request_headers": {},  # Could be enhanced to include actual headers
                    "response_headers": {},  # Could be enhanced to include actual response headers
                    "success": result.success,
                    "status_code": 200 if result.success else 500,  # Simplified status codes
                    "error_type": error_type,
                    "error_message": result.error_message,
                    "response_time_ms": int(result.execution_time_ms) if result.execution_time_ms else 0,
                    "retry_count": 0,  # Could be enhanced to track actual retries
                    "rate_limit_remaining": None,  # Could be enhanced with actual rate limit info
                    "rate_limit_reset_at": None,  # Could be enhanced with actual rate limit reset time
                    "called_at": datetime.now(timezone.utc)
                })
                
                db.commit()
                
                # Also log to application logs
                log_entry = {
                    "workflow_id": context.workflow_id,
                    "execution_id": context.execution_id,
                    "node_id": node_id,
                    "user_id": user_id,
                    "api_service": config.api_service,
                    "operation": config.operation,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                    "error_message": result.error_message,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                if result.success:
                    logger.info(f"External API call successful and logged to database: {log_entry}")
                else:
                    logger.warning(f"External API call failed and logged to database: {log_entry}")
                
        except Exception as e:
            logger.error(f"Failed to log API call to database: {str(e)}")
            # Fallback to application logging only
            try:
                log_entry = {
                    "api_service": config.api_service,
                    "operation": config.operation,
                    "success": result.success,
                    "error": str(e)
                }
                logger.warning(f"API call logging failed, fallback log: {log_entry}")
            except Exception:
                logger.error("Complete logging failure for API call")
    
    def prepare_execution(self, context: NodeExecutionContext) -> None:
        """Prepare for execution"""
        super().prepare_execution(context)
        # Additional preparation if needed
    
    def cleanup_execution(self, context: NodeExecutionContext) -> None:
        """Cleanup after execution"""
        super().cleanup_execution(context)
        # Additional cleanup if needed


# Factory function for creating executor with dependencies
def create_external_action_executor(
    oauth2_service: Optional[OAuth2Service] = None,
    encryption_service: Optional[CredentialEncryption] = None
) -> ExternalActionNodeExecutor:
    """Create External Action Node Executor with dependencies"""
    return ExternalActionNodeExecutor(
        oauth2_service=oauth2_service,
        encryption_service=encryption_service
    )


# Register available API adapters
def register_default_adapters():
    """Register default API adapters"""
    try:
        # Import and register adapters
        from ..services.api_adapters.google_calendar import GoogleCalendarAdapter
        from ..services.api_adapters.github import GitHubAdapter  
        from ..services.api_adapters.slack import SlackAdapter
        
        APIAdapterRegistry.register("google_calendar", GoogleCalendarAdapter)
        APIAdapterRegistry.register("github", GitHubAdapter)
        APIAdapterRegistry.register("slack", SlackAdapter)
        
        logger.info("Default API adapters registered successfully")
        
    except ImportError as e:
        logger.warning(f"Some API adapters could not be imported: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to register default adapters: {str(e)}")


# Auto-register adapters on module import
register_default_adapters()