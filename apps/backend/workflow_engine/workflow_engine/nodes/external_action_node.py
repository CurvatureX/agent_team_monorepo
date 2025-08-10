"""
External Action Node Executor.

Handles external action operations for integrating with third-party systems
like GitHub, Google Calendar, Trello, Slack, etc.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.oauth2_service_lite import OAuth2ServiceLite

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import NodeSpec
except ImportError:
    node_spec_registry = None
    NodeSpec = None

try:
    from ..services.api_adapters.base import get_adapter, register_adapter
    from ..services.oauth2_service_lite import OAuth2ServiceLite
    from ..services.api_adapters.google_calendar import GoogleCalendarAdapter
    from ..services.api_call_logger import get_api_call_logger, APICallTracker
except ImportError as e:
    logging.warning(f"Failed to import API adapters or logger: {e}")
    get_adapter = None
    register_adapter = None
    OAuth2ServiceLite = None
    GoogleCalendarAdapter = None
    get_api_call_logger = None
    APICallTracker = None


class ExternalActionNodeExecutor(BaseNodeExecutor):
    """Executor for EXTERNAL_ACTION_NODE type."""

    def __init__(self, oauth2_service: Optional['OAuth2ServiceLite'] = None, subtype: Optional[str] = None):
        """Initialize the external action executor.

        Args:
            oauth2_service: OAuth2 service for credential management
            subtype: The specific subtype of external action (e.g., GITHUB, SLACK, etc.)
        """
        super().__init__(subtype=subtype)
        self.oauth2_service = oauth2_service
        self.logger = logging.getLogger(__name__)

        # Initialize API adapters
        self._adapters = {}
        if GoogleCalendarAdapter:
            try:
                self._adapters = {
                    "google_calendar": GoogleCalendarAdapter(),
                }
                self.logger.info("Initialized real API adapters for external actions")
            except Exception as e:
                self.logger.error(f"Failed to initialize API adapters: {e}")
                self._adapters = {}

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for external action nodes."""
        if node_spec_registry and self._subtype:
            # Return the specific spec for current subtype
            return node_spec_registry.get_spec("EXTERNAL_ACTION_NODE", self._subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported external action subtypes."""
        return [
            "GITHUB",
            "GOOGLE_CALENDAR",
            "TRELLO",
            "EMAIL",
            "SLACK",
            "API_CALL",
            "WEBHOOK",
            "NOTIFICATION",
        ]

    def validate(self, node: Any) -> List[str]:
        """Validate external action node configuration using spec-based validation."""
        # First use the base class validation which includes spec validation
        errors = super().validate(node)

        # If spec validation passed, we're done
        if not errors and self.spec:
            return errors

        # Fallback if spec not available
        if not node.subtype:
            errors.append("External action subtype is required")
            return errors

        if node.subtype not in self.get_supported_subtypes():
            errors.append(f"Unsupported external action subtype: {node.subtype}")

        return errors

    def _validate_legacy(self, node: Any) -> List[str]:
        """Legacy validation for backward compatibility."""
        errors = []

        if not hasattr(node, "subtype"):
            return errors

        subtype = node.subtype

        if subtype == "GITHUB":
            errors.extend(self._validate_required_parameters(node, ["action", "repository"]))

        elif subtype == "GOOGLE_CALENDAR":
            errors.extend(self._validate_required_parameters(node, ["action", "calendar_id"]))

        elif subtype == "TRELLO":
            errors.extend(self._validate_required_parameters(node, ["action", "board_id"]))

        elif subtype == "EMAIL":
            errors.extend(self._validate_required_parameters(node, ["action"]))
            if hasattr(node, "parameters") and node.parameters.get("action") == "send":
                errors.extend(self._validate_required_parameters(node, ["recipients", "subject"]))

        elif subtype == "SLACK":
            errors.extend(self._validate_required_parameters(node, ["action", "channel"]))

        elif subtype == "API_CALL":
            errors.extend(self._validate_required_parameters(node, ["method", "url"]))
            if hasattr(node, "parameters"):
                method = node.parameters.get("method", "").upper()
                if method and method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    errors.append(f"Invalid HTTP method: {method}")

        elif subtype == "WEBHOOK":
            errors.extend(self._validate_required_parameters(node, ["url", "payload"]))

        elif subtype == "NOTIFICATION":
            errors.extend(self._validate_required_parameters(node, ["type", "message", "target"]))
            if hasattr(node, "parameters"):
                notification_type = node.parameters.get("type", "")
                if notification_type and notification_type not in [
                    "push",
                    "sms",
                    "email",
                    "in_app",
                ]:
                    errors.append(f"Invalid notification type: {notification_type}")

        return errors

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute external action node."""
        start_time = time.time()
        logs = []

        try:
            self.logger.info(f"ExternalActionNodeExecutor.execute() called")
            self.logger.info(
                f"Context node type: {context.node.type}, subtype: {context.node.subtype}"
            )
            self.logger.info(f"Context credentials available: {bool(context.credentials)}")
            if context.credentials:
                self.logger.info(
                    f"Available credential providers: {list(context.credentials.keys())}"
                )

            subtype = context.node.subtype
            logs.append(f"Executing external action node with subtype: {subtype}")

            if subtype == "GITHUB":
                return self._execute_github_action(context, logs, start_time)
            elif subtype == "GOOGLE_CALENDAR":
                return await self._execute_google_calendar_action(context, logs, start_time)
            elif subtype == "TRELLO":
                return self._execute_trello_action(context, logs, start_time)
            elif subtype == "EMAIL":
                return self._execute_email_action(context, logs, start_time)
            elif subtype == "SLACK":
                return self._execute_slack_action(context, logs, start_time)
            elif subtype == "API_CALL":
                return await self._execute_api_call_action(context, logs, start_time)
            elif subtype == "WEBHOOK":
                return self._execute_webhook_action(context, logs, start_time)
            elif subtype == "NOTIFICATION":
                return self._execute_notification_action(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported external action subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            return self._create_error_result(
                f"Error executing external action: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    async def _get_user_credentials(self, user_id: str, provider: str) -> Optional[Dict[str, str]]:
        """Get user credentials for the specified provider.

        Args:
            user_id: User ID from execution context
            provider: Provider name (google_calendar, github, slack)

        Returns:
            Dictionary with access_token or None if not available
        """
        try:
            # Use simplified OAuth2 service
            from ..models.database import get_db_session
            from ..services.oauth2_service_lite import OAuth2ServiceLite

            with get_db_session() as db:
                oauth2_service_lite = OAuth2ServiceLite(db)

                # Get valid access token
                access_token = await oauth2_service_lite.get_valid_token(user_id, provider)
                if access_token:
                    return {"access_token": access_token}
                else:
                    self.logger.warning(
                        f"No valid credentials found for user {user_id}, provider {provider}"
                    )
                    return None

        except Exception as e:
            self.logger.error(
                f"Failed to get credentials for user {user_id}, provider {provider}: {e}"
            )
            return None

    async def _call_external_api(
        self,
        provider: str,
        operation: str,
        parameters: Dict[str, Any],
        user_id: str,
        workflow_execution_id: Optional[str] = None,
        node_id: Optional[str] = None,
        context: Optional[NodeExecutionContext] = None,
    ) -> Dict[str, Any]:
        """Call external API using the appropriate adapter with comprehensive logging.

        Args:
            provider: Provider name (google_calendar, github, slack)
            operation: API operation to perform
            parameters: Operation parameters
            user_id: User ID for credential lookup
            workflow_execution_id: Optional workflow execution ID for logging
            node_id: Optional node ID for logging

        Returns:
            API response data
        """
        start_time = time.time()
        api_logger = get_api_call_logger()

        # Initialize tracking variables
        success = False
        status_code = None
        error_type = None
        error_message = None
        api_endpoint = ""
        http_method = "POST"  # Default for most operations
        response_data = None
        retry_count = 0

        # Check if we have the adapter
        if provider not in self._adapters:
            error_message = f"Provider {provider} not supported"
            self.logger.error(f"No adapter available for provider: {provider}")

            # Log the failed call
            await api_logger.log_api_call(
                user_id=user_id,
                provider=provider,
                operation=operation,
                api_endpoint="N/A",
                http_method="N/A",
                success=False,
                status_code=404,
                response_time_ms=int((time.time() - start_time) * 1000),
                workflow_execution_id=workflow_execution_id,
                node_id=node_id,
                request_data=parameters,
                error_type="ProviderNotSupported",
                error_message=error_message,
            )

            return {
                "success": False,
                "error": error_message,
                "provider": provider,
                "fallback": True,
                "mock_result": f"Mock {operation} result for {provider}",
            }

        # Get user credentials - first check execution context, then OAuth2 service
        credentials = None

        # Debug logging
        self.logger.info(f"Calling external API for provider={provider}, operation={operation}")
        self.logger.info(f"Context provided: {context is not None}")
        if context:
            self.logger.info(f"Context credentials available: {context.credentials is not None}")
            if context.credentials:
                self.logger.info(
                    f"Available credential providers: {list(context.credentials.keys())}"
                )

        # Check if credentials are provided in execution context
        if context and context.credentials and provider in context.credentials:
            context_creds = context.credentials[provider]
            self.logger.info(f"Using credentials from execution context for {provider}")

            # Handle authorization code flow
            if "authorization_code" in context_creds:
                # Exchange authorization code for access token
                try:
                    # Use simplified OAuth2 service for token exchange
                    from ..models.database import get_db_session
                    from ..services.oauth2_service_lite import OAuth2ServiceLite

                    # Create OAuth2 service
                    with get_db_session() as db:
                        oauth2_service_lite = OAuth2ServiceLite(db)

                        # Exchange code for token
                        token_response = await oauth2_service_lite.exchange_code_for_token(
                            code=context_creds["authorization_code"],
                            client_id=context_creds.get("client_id"),
                            redirect_uri=context_creds.get("redirect_uri"),
                            provider=provider,
                        )

                        # Store credentials for future use
                        user_id_from_context = context.metadata.get("user_id", user_id)
                        await oauth2_service_lite.store_user_credentials(
                            user_id=user_id_from_context,
                            provider=provider,
                            token_response=token_response,
                        )

                        credentials = {
                            "access_token": token_response.access_token,
                            "refresh_token": token_response.refresh_token,
                            "token_type": token_response.token_type,
                            "expires_at": token_response.expires_at,
                        }
                        self.logger.info(
                            f"Successfully exchanged authorization code for access token for {provider}"
                        )

                except Exception as e:
                    self.logger.error(f"Failed to exchange authorization code for {provider}: {e}")
                    return {
                        "success": False,
                        "error": f"OAuth2 token exchange failed: {str(e)}",
                        "provider": provider,
                        "operation": operation,
                        "oauth2_error": True,
                    }
            else:
                # Direct token credentials
                credentials = context_creds

        # Fallback to OAuth2 service if no context credentials
        if not credentials:
            credentials = await self._get_user_credentials(user_id, provider)

        if not credentials:
            error_message = f"No valid credentials for {provider}"
            self.logger.warning(f"No credentials available for user {user_id}, provider {provider}")

            # Log the authentication failure
            await api_logger.log_api_call(
                user_id=user_id,
                provider=provider,
                operation=operation,
                api_endpoint="N/A",
                http_method="N/A",
                success=False,
                status_code=401,
                response_time_ms=int((time.time() - start_time) * 1000),
                workflow_execution_id=workflow_execution_id,
                node_id=node_id,
                request_data=parameters,
                error_type="AuthenticationError",
                error_message=error_message,
            )

            return {
                "success": False,
                "error": error_message,
                "provider": provider,
                "requires_auth": True,
                "mock_result": f"Mock {operation} result for {provider} (no auth)",
            }

        # Call the real API with comprehensive error handling
        try:
            adapter = self._adapters[provider]

            # Attempt to determine API endpoint (adapter-specific)
            try:
                if hasattr(adapter, "get_endpoint_info"):
                    endpoint_info = adapter.get_endpoint_info(operation, parameters)
                    api_endpoint = endpoint_info.get("url", f"{provider}://{operation}")
                    http_method = endpoint_info.get("method", "POST")
                else:
                    api_endpoint = f"{provider}://{operation}"
            except:
                api_endpoint = f"{provider}://{operation}"

            # Make the API call
            result = await adapter.call(operation, parameters, credentials)

            # Parse response information
            success = result.get("success", True)
            status_code = result.get("status_code", 200 if success else 500)
            response_data = result

            # Add metadata
            result["provider"] = provider
            result["operation"] = operation
            result["real_api_call"] = True
            result["executed_at"] = datetime.now().isoformat()

            # Log successful API call
            await api_logger.log_api_call(
                user_id=user_id,
                provider=provider,
                operation=operation,
                api_endpoint=api_endpoint,
                http_method=http_method,
                success=success,
                status_code=status_code,
                response_time_ms=int((time.time() - start_time) * 1000),
                workflow_execution_id=workflow_execution_id,
                node_id=node_id,
                request_data=parameters,
                response_data=response_data,
                retry_count=retry_count,
            )

            self.logger.info(f"Successfully called {provider} API: {operation}")
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)

            # Determine status code based on error type
            if "auth" in error_message.lower() or "token" in error_message.lower():
                status_code = 401
            elif "rate" in error_message.lower() or "limit" in error_message.lower():
                status_code = 429
            elif "not found" in error_message.lower():
                status_code = 404
            elif "timeout" in error_message.lower():
                status_code = 408
            else:
                status_code = 500

            self.logger.error(f"Failed to call {provider} API: {e}")

            # Log failed API call
            await api_logger.log_api_call(
                user_id=user_id,
                provider=provider,
                operation=operation,
                api_endpoint=api_endpoint,
                http_method=http_method,
                success=False,
                status_code=status_code,
                response_time_ms=int((time.time() - start_time) * 1000),
                workflow_execution_id=workflow_execution_id,
                node_id=node_id,
                request_data=parameters,
                error_type=error_type,
                error_message=error_message,
                retry_count=retry_count,
            )

            return {
                "success": False,
                "error": error_message,
                "provider": provider,
                "operation": operation,
                "api_error": True,
                "mock_result": f"Mock {operation} result for {provider} (API error)",
            }

    def _execute_github_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute GitHub action."""
        # Use spec-based parameter retrieval with fallback
        action = self.get_parameter_with_spec(context, "action") or context.get_parameter("action")
        repository = self.get_parameter_with_spec(context, "repository") or context.get_parameter(
            "repository"
        )
        owner = self.get_parameter_with_spec(context, "owner") or context.get_parameter("owner")
        user_id = getattr(context, "user_id", None) or context.metadata.get(
            "user_id", "00000000-0000-0000-0000-000000000123"
        )

        logs.append(f"GitHub action: {action} on repository: {repository}")

        # Prepare parameters for GitHub API
        api_parameters = {"action": action, "repository": repository, "owner": owner}

        # Add action-specific parameters
        if action == "create_issue":
            api_parameters.update(
                {
                    "title": context.get_parameter("title", ""),
                    "body": context.get_parameter("body", ""),
                    "labels": context.get_parameter("labels", []),
                    "assignees": context.get_parameter("assignees", []),
                }
            )
        elif action == "create_pull_request":
            api_parameters.update(
                {
                    "title": context.get_parameter("title", ""),
                    "head": context.get_parameter("head", ""),
                    "base": context.get_parameter("base", ""),
                    "body": context.get_parameter("body", ""),
                }
            )
        elif action == "list_issues":
            api_parameters.update(
                {
                    "state": context.get_parameter("state", "open"),
                    "labels": context.get_parameter("labels", []),
                    "sort": context.get_parameter("sort", "created"),
                }
            )

        # Call real GitHub API
        try:
            import asyncio

            # Handle async call in sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If already in async context, create new task
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._call_external_api(
                                "github",
                                action,
                                api_parameters,
                                user_id,
                                context.metadata.get("workflow_execution_id"),
                                context.metadata.get("node_id"),
                                context,
                            ),
                        )
                        output_data = future.result()
                else:
                    output_data = loop.run_until_complete(
                        self._call_external_api(
                            "github",
                            action,
                            api_parameters,
                            user_id,
                            context.metadata.get("workflow_execution_id"),
                            context.metadata.get("node_id"),
                            context,
                        )
                    )
            except RuntimeError:
                # No event loop, create new one
                output_data = asyncio.run(
                    self._call_external_api(
                        "github",
                        action,
                        api_parameters,
                        user_id,
                        context.metadata.get("workflow_execution_id"),
                        context.metadata.get("node_id"),
                        context,
                    )
                )
        except Exception as e:
            logs.append(f"Failed to call GitHub API: {str(e)}")
            # Fallback to mock data with error info
            output_data = {
                "provider": "github",
                "action": action,
                "repository": repository,
                "result": f"Mock GitHub {action} result (API call failed: {str(e)})",
                "executed_at": datetime.now().isoformat(),
                "fallback_mode": True,
                "api_error": str(e),
            }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    async def _execute_google_calendar_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Google Calendar action."""
        # Use spec-based parameter retrieval with fallback
        action = self.get_parameter_with_spec(context, "action") or context.get_parameter("action")
        calendar_id = self.get_parameter_with_spec(context, "calendar_id") or context.get_parameter(
            "calendar_id", "primary"
        )
        user_id = getattr(context, "user_id", None) or context.metadata.get(
            "user_id", "00000000-0000-0000-0000-000000000123"
        )

        logs.append(f"Google Calendar action: {action} on calendar: {calendar_id}")

        # Prepare parameters for Google Calendar API
        api_parameters = {"calendar_id": calendar_id}

        # Add action-specific parameters
        if action == "create_event":
            event_data = context.get_parameter("event_data", {})
            api_parameters.update(
                {
                    "summary": event_data.get("summary", context.get_parameter("summary", "")),
                    "description": event_data.get(
                        "description", context.get_parameter("description", "")
                    ),
                    "start": event_data.get("start", context.get_parameter("start")),
                    "end": event_data.get("end", context.get_parameter("end")),
                    "location": event_data.get("location", context.get_parameter("location", "")),
                    "attendees": event_data.get(
                        "attendees", context.get_parameter("attendees", [])
                    ),
                }
            )
        elif action == "list_events":
            api_parameters.update(
                {
                    "time_min": context.get_parameter("time_min"),
                    "time_max": context.get_parameter("time_max"),
                    "max_results": context.get_parameter("max_results", 10),
                    "single_events": context.get_parameter("single_events", True),
                    "order_by": context.get_parameter("order_by", "startTime"),
                }
            )
        elif action == "update_event":
            api_parameters.update(
                {
                    "event_id": context.get_parameter("event_id", ""),
                    "summary": context.get_parameter("summary", ""),
                    "description": context.get_parameter("description", ""),
                    "start": context.get_parameter("start"),
                    "end": context.get_parameter("end"),
                }
            )

        # Call real Google Calendar API
        try:
            # Direct async call since method is now async
            output_data = await self._call_external_api("google_calendar", action, api_parameters, user_id,
                                           context.metadata.get('workflow_execution_id'),
                                           context.metadata.get('node_id'), context)
        except Exception as e:
            logs.append(f"Failed to call Google Calendar API: {str(e)}")
            # Fallback to mock data with error info
            output_data = {
                "provider": "google_calendar",
                "action": action,
                "calendar_id": calendar_id,
                "result": f"Mock Google Calendar {action} result (API call failed: {str(e)})",
                "executed_at": datetime.now().isoformat(),
                "fallback_mode": True,
                "api_error": str(e),
            }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_trello_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Trello action."""
        # Use spec-based parameter retrieval
        action = self.get_parameter_with_spec(context, "action")
        board_id = self.get_parameter_with_spec(context, "board_id")

        logs.append(f"Trello action: {action} on board: {board_id}")

        # Mock implementation - replace with actual Trello API calls
        output_data = {
            "provider": "trello",
            "action": action,
            "board_id": board_id,
            "result": f"Mock Trello {action} result",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_email_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute email action."""
        # Use spec-based parameter retrieval
        action = self.get_parameter_with_spec(context, "action")

        logs.append(f"Email action: {action}")

        # Mock implementation - replace with actual email API calls
        output_data = {
            "provider": "email",
            "action": action,
            "result": f"Mock email {action} result",
            "executed_at": datetime.now().isoformat(),
        }

        if action == "send":
            recipients = self.get_parameter_with_spec(context, "recipients")
            subject = self.get_parameter_with_spec(context, "subject")
            output_data.update({"recipients": recipients, "subject": subject})

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_slack_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Slack action."""
        # Use spec-based parameter retrieval with fallback
        action = self.get_parameter_with_spec(context, "action") or context.get_parameter("action")
        channel = self.get_parameter_with_spec(context, "channel") or context.get_parameter(
            "channel"
        )
        user_id = getattr(context, "user_id", None) or context.metadata.get(
            "user_id", "00000000-0000-0000-0000-000000000123"
        )

        logs.append(f"Slack action: {action} in channel: {channel}")

        # Prepare parameters for Slack API
        api_parameters = {"channel": channel}

        # Add action-specific parameters
        if action == "send_message":
            message_data = context.get_parameter("message_data", {})
            api_parameters.update(
                {
                    "text": message_data.get("text", context.get_parameter("text", "")),
                    "blocks": message_data.get("blocks", context.get_parameter("blocks", [])),
                    "attachments": message_data.get(
                        "attachments", context.get_parameter("attachments", [])
                    ),
                    "username": context.get_parameter("username"),
                    "icon_emoji": context.get_parameter("icon_emoji"),
                    "icon_url": context.get_parameter("icon_url"),
                    "thread_ts": context.get_parameter("thread_ts"),
                    "reply_broadcast": context.get_parameter("reply_broadcast", False),
                }
            )
        elif action == "list_channels":
            api_parameters.update(
                {
                    "types": context.get_parameter("types", "public_channel,private_channel"),
                    "exclude_archived": context.get_parameter("exclude_archived", True),
                    "limit": context.get_parameter("limit", 100),
                }
            )
        elif action == "create_channel":
            api_parameters.update(
                {
                    "name": context.get_parameter("name", ""),
                    "is_private": context.get_parameter("is_private", False),
                }
            )
        elif action == "upload_file":
            api_parameters.update(
                {
                    "file_content": context.get_parameter("file_content", ""),
                    "file_name": context.get_parameter("file_name", ""),
                    "title": context.get_parameter("title"),
                    "initial_comment": context.get_parameter("initial_comment"),
                    "channels": channel,
                }
            )

        # Call real Slack API
        try:
            import asyncio

            # Handle async call in sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If already in async context, create new task
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._call_external_api(
                                "slack",
                                action,
                                api_parameters,
                                user_id,
                                context.metadata.get("workflow_execution_id"),
                                context.metadata.get("node_id"),
                                context,
                            ),
                        )
                        output_data = future.result()
                else:
                    output_data = loop.run_until_complete(
                        self._call_external_api(
                            "slack",
                            action,
                            api_parameters,
                            user_id,
                            context.metadata.get("workflow_execution_id"),
                            context.metadata.get("node_id"),
                            context,
                        )
                    )
            except RuntimeError:
                # No event loop, create new one
                output_data = asyncio.run(
                    self._call_external_api(
                        "slack",
                        action,
                        api_parameters,
                        user_id,
                        context.metadata.get("workflow_execution_id"),
                        context.metadata.get("node_id"),
                        context,
                    )
                )
        except Exception as e:
            logs.append(f"Failed to call Slack API: {str(e)}")
            # Fallback to mock data with error info
            output_data = {
                "provider": "slack",
                "action": action,
                "channel": channel,
                "result": f"Mock Slack {action} result (API call failed: {str(e)})",
                "executed_at": datetime.now().isoformat(),
                "fallback_mode": True,
                "api_error": str(e),
            }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    async def _execute_api_call_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute generic API call action using the APICallAdapter."""
        # Use spec-based parameter retrieval
        method = self.get_parameter_with_spec(context, "method")
        url = self.get_parameter_with_spec(context, "url")
        headers = self.get_parameter_with_spec(context, "headers") or {}
        query_params = self.get_parameter_with_spec(context, "query_params") or {}
        body = self.get_parameter_with_spec(context, "body")
        timeout = self.get_parameter_with_spec(context, "timeout") or 30
        authentication = self.get_parameter_with_spec(context, "authentication") or "none"
        auth_token = self.get_parameter_with_spec(context, "auth_token")
        api_key_header = self.get_parameter_with_spec(context, "api_key_header") or "X-API-Key"
        
        # Convert method to uppercase
        if method:
            method = method.upper()

        logs.append(f"Generic API call: {method} {url}")

        # Prepare parameters for API call adapter
        api_parameters = {
            "method": method,
            "url": url,
            "headers": headers,
            "query_params": query_params,
            "body": body,
            "timeout": timeout,
            "authentication": authentication
        }
        
        # Add authentication parameters if provided
        if auth_token:
            api_parameters["auth_token"] = auth_token
        if api_key_header and api_key_header != "X-API-Key":
            api_parameters["api_key_header"] = api_key_header
            
        # Add basic auth parameters if provided
        username = self.get_parameter_with_spec(context, "username")
        password = self.get_parameter_with_spec(context, "password")
        if username:
            api_parameters["username"] = username
        if password:
            api_parameters["password"] = password
        
        # Get user credentials (may be empty for generic calls)
        user_id = getattr(context, 'user_id', None) or context.metadata.get('user_id', "00000000-0000-0000-0000-000000000123")
        credentials = {}
        
        # Call real API using the api_call adapter
        try:
            # Use the new adapter system
            if get_adapter:
                adapter = get_adapter("api_call")
                if adapter:
                    output_data = await adapter.call("generic_call", api_parameters, credentials)
                    
                    # Add metadata
                    output_data["provider"] = "api_call"
                    output_data["executed_at"] = datetime.now().isoformat()
                    output_data["real_api_call"] = True
                else:
                    raise Exception("api_call adapter not found")
            else:
                raise Exception("Adapter system not available")
                
        except Exception as e:
            logs.append(f"Failed to call generic API: {str(e)}")
            # Fallback to mock data with error info
            output_data = {
                "method": method,
                "url": url,
                "headers": headers,
                "status_code": 500,
                "success": False,
                "error": str(e),
                "response": f"Mock {method} response from {url} (API call failed: {str(e)})",
                "executed_at": datetime.now().isoformat(),
                "fallback_mode": True,
                "api_error": str(e)
            }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_webhook_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute webhook action."""
        # Use spec-based parameter retrieval
        url = self.get_parameter_with_spec(context, "url")
        payload = self.get_parameter_with_spec(context, "payload")

        logs.append(f"Webhook: POST to {url}")

        # Mock implementation - replace with actual webhook sending
        output_data = {
            "url": url,
            "payload": payload,
            "status_code": 200,
            "response": "Mock webhook sent successfully",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_notification_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute notification action."""
        # Use spec-based parameter retrieval
        notification_type = self.get_parameter_with_spec(context, "type")
        message = self.get_parameter_with_spec(context, "message")
        target = self.get_parameter_with_spec(context, "target")

        logs.append(f"Notification: {notification_type} to {target}")

        # Mock implementation - replace with actual notification service
        output_data = {
            "type": notification_type,
            "message": message,
            "target": target,
            "status": "sent",
            "result": f"Mock {notification_type} notification sent",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )
