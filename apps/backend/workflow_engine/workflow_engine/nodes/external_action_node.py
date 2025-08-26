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
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..services.oauth2_service_lite import OAuth2ServiceLite

from shared.models.node_enums import ExternalActionSubtype, NodeType
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

# Lazy imports to avoid circular dependency during factory initialization
get_adapter = None
register_adapter = None
OAuth2ServiceLite = None
GoogleCalendarAdapter = None
get_api_call_logger = None
APICallTracker = None


def _ensure_api_adapters():
    """Lazily import API adapters only when needed."""
    global get_adapter, register_adapter, OAuth2ServiceLite, GoogleCalendarAdapter
    global get_api_call_logger, APICallTracker

    if get_adapter is None:
        try:
            from ..services.api_adapters.base import get_adapter, register_adapter
            from ..services.api_adapters.google_calendar import GoogleCalendarAdapter
            from ..services.api_call_logger import APICallTracker, get_api_call_logger
            from ..services.oauth2_service_lite import OAuth2ServiceLite
        except ImportError as e:
            logging.warning(f"Failed to import API adapters or logger: {e}")
            # Keep them as None


# Import new shared SDKs
try:
    from shared.sdks import ApiCallSDK, EmailSDK, GitHubSDK, GoogleCalendarSDK, NotionSDK, SlackSDK

    SDK_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Failed to import shared SDKs: {e}")
    GoogleCalendarSDK = None
    GitHubSDK = None
    SlackSDK = None
    EmailSDK = None
    ApiCallSDK = None
    NotionSDK = None
    SDK_AVAILABLE = False


class ExternalActionNodeExecutor(BaseNodeExecutor):
    """Executor for EXTERNAL_ACTION_NODE type."""

    def __init__(
        self, oauth2_service: Optional["OAuth2ServiceLite"] = None, subtype: Optional[str] = None
    ):
        """Initialize the external action executor.

        Args:
            oauth2_service: OAuth2 service for credential management
            subtype: The specific subtype of external action (e.g., GITHUB, SLACK, etc.)
        """
        super().__init__(subtype=subtype)
        self.oauth2_service = oauth2_service
        self.logger = logging.getLogger(__name__)

        # Initialize new shared SDKs
        self._sdks = {}
        if SDK_AVAILABLE:
            try:
                # Only initialize available SDKs
                if GoogleCalendarSDK is not None:
                    self._sdks["google_calendar"] = GoogleCalendarSDK()
                if GitHubSDK is not None:
                    self._sdks["github"] = GitHubSDK()
                if SlackSDK is not None:
                    self._sdks["slack"] = SlackSDK()
                if EmailSDK is not None:
                    self._sdks["email"] = EmailSDK()
                if ApiCallSDK is not None:
                    self._sdks["api_call"] = ApiCallSDK()
                if NotionSDK is not None:
                    self._sdks["notion"] = NotionSDK()

                self.logger.info(
                    f"Initialized {len(self._sdks)} shared SDKs for external actions: {list(self._sdks.keys())}"
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize shared SDKs: {e}")
                self._sdks = {}

        # Fallback to old adapters if SDKs not available
        self._adapters = {}
        if not self._sdks and GoogleCalendarAdapter:
            try:
                self._adapters = {
                    "google_calendar": GoogleCalendarAdapter(),
                }
                self.logger.info("Initialized fallback API adapters for external actions")
            except Exception as e:
                self.logger.error(f"Failed to initialize API adapters: {e}")
                self._adapters = {}

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for external action nodes."""
        if node_spec_registry and self._subtype:
            # Return the specific spec for current subtype
            return node_spec_registry.get_spec(NodeType.EXTERNAL_ACTION.value, self._subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported external action subtypes."""
        return [subtype.value for subtype in ExternalActionSubtype]

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

        if subtype == ExternalActionSubtype.GITHUB.value:
            errors.extend(self._validate_required_parameters(node, ["action", "repository"]))

        elif subtype == ExternalActionSubtype.GOOGLE_CALENDAR.value:
            errors.extend(self._validate_required_parameters(node, ["action", "calendar_id"]))

        elif subtype == ExternalActionSubtype.TRELLO.value:
            errors.extend(self._validate_required_parameters(node, ["action", "board_id"]))

        elif subtype == ExternalActionSubtype.EMAIL.value:
            errors.extend(self._validate_required_parameters(node, ["action"]))
            if hasattr(node, "parameters") and node.parameters.get("action") == "send":
                errors.extend(self._validate_required_parameters(node, ["recipients", "subject"]))

        elif subtype == ExternalActionSubtype.SLACK.value:
            errors.extend(self._validate_required_parameters(node, ["action", "channel"]))

        elif subtype == ExternalActionSubtype.API_CALL.value:
            errors.extend(self._validate_required_parameters(node, ["method", "url"]))
            if hasattr(node, "parameters"):
                method = node.parameters.get("method", "").upper()
                if method and method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    errors.append(f"Invalid HTTP method: {method}")

        elif subtype == ExternalActionSubtype.WEBHOOK.value:
            errors.extend(self._validate_required_parameters(node, ["url", "payload"]))

        elif subtype == ExternalActionSubtype.NOTIFICATION.value:
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

    async def _call_sdk_api(
        self,
        provider: str,
        operation: str,
        parameters: Dict[str, Any],
        credentials: Dict[str, str],
        user_id: str,
        workflow_execution_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call external API using the new shared SDK system."""
        _ensure_api_adapters()
        api_logger = get_api_call_logger()
        start_time = time.time()

        # Check if operation is valid
        if not operation:
            error_message = f"No operation specified for provider {provider}"
            self.logger.error(error_message)

            if api_logger:
                await api_logger.log_api_call(
                    user_id=user_id,
                    provider=provider,
                    operation=operation or "unknown",
                    api_endpoint="N/A",
                    http_method="N/A",
                    success=False,
                    status_code=400,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    workflow_execution_id=workflow_execution_id,
                    node_id=node_id,
                    request_data=parameters,
                    error_type="InvalidOperation",
                    error_message=error_message,
                )

            return {
                "success": False,
                "error": error_message,
                "provider": provider,
                "operation": operation,
            }

        # Check if we have the SDK
        if provider not in self._sdks:
            error_message = f"Provider {provider} not available in shared SDKs"
            self.logger.error(error_message)

            if api_logger:
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
            }

        try:
            # Use the shared SDK
            sdk = self._sdks[provider]
            api_response = await sdk.call_operation(operation, parameters, credentials)

            # Log the API call
            if api_logger:
                await api_logger.log_api_call(
                    user_id=user_id,
                    provider=provider,
                    operation=operation,
                    api_endpoint=f"{provider}://{operation}",
                    http_method="POST",
                    success=api_response.success,
                    status_code=api_response.status_code or (200 if api_response.success else 500),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    workflow_execution_id=workflow_execution_id,
                    node_id=node_id,
                    request_data=parameters,
                    response_data=api_response.data if api_response.success else None,
                    error_type=None if api_response.success else "APIError",
                    error_message=api_response.error if not api_response.success else None,
                )

            # Convert APIResponse to dict format expected by existing code
            if api_response.success:
                result = api_response.data or {}
                result.update(
                    {
                        "success": True,
                        "provider": provider,
                        "operation": operation,
                        "real_api_call": True,
                        "executed_at": datetime.now().isoformat(),
                        "sdk_used": True,
                    }
                )
                return result
            else:
                return {
                    "success": False,
                    "error": api_response.error,
                    "provider": provider,
                    "operation": operation,
                    "sdk_used": True,
                }

        except Exception as e:
            self.logger.error(f"SDK API call failed for {provider}: {e}")

            if api_logger:
                await api_logger.log_api_call(
                    user_id=user_id,
                    provider=provider,
                    operation=operation,
                    api_endpoint=f"{provider}://{operation}",
                    http_method="POST",
                    success=False,
                    status_code=500,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    workflow_execution_id=workflow_execution_id,
                    node_id=node_id,
                    request_data=parameters,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )

            return {
                "success": False,
                "error": str(e),
                "provider": provider,
                "operation": operation,
                "sdk_error": True,
            }

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute external action node."""
        start_time = time.time()
        logs = []

        try:
            self.logger.info(f"🔧 ExternalActionNodeExecutor.execute() called")
            self.logger.info(f"📋 Node type: {context.node.type}, subtype: {context.node.subtype}")
            self.logger.info(f"🔐 Credentials available: {bool(context.credentials)}")
            self.logger.info(
                f"📥 Input data keys: {list(context.input_data.keys()) if context.input_data else 'None'}"
            )
            self.logger.info(f"⚙️ Node parameters: {context.node.parameters}")
            self.logger.info(f"🛠️ SDKs initialized: {bool(self._sdks)}")

            # Log SDK details if available
            if self._sdks:
                self.logger.info(
                    f"📦 Available SDKs: {list(self._sdks.keys()) if hasattr(self._sdks, 'keys') else 'SDK object available'}"
                )

            subtype = context.node.subtype
            if context.credentials:
                self.logger.info(
                    f"Available credential providers: {list(context.credentials.keys())}"
                )

            subtype = context.node.subtype
            logs.append(f"Executing external action node with subtype: {subtype}")

            # Try new shared SDK approach first
            sdk_supported_subtypes = [
                ExternalActionSubtype.GITHUB.value,
                ExternalActionSubtype.GOOGLE_CALENDAR.value,
                ExternalActionSubtype.SLACK.value,
                ExternalActionSubtype.EMAIL.value,
                ExternalActionSubtype.API_CALL.value,
                ExternalActionSubtype.NOTION.value,
            ]

            self.logger.info(f"🔍 Checking execution path for subtype: {subtype}")
            self.logger.info(f"🎯 SDK supported subtypes: {sdk_supported_subtypes}")
            self.logger.info(f"🧪 Subtype in SDK list: {subtype in sdk_supported_subtypes}")

            if self._sdks and subtype in sdk_supported_subtypes:
                self.logger.info(f"🚀 Using SDK execution path for {subtype}")
                return await self._execute_with_sdk(context, logs, start_time)
            # Fallback to original implementation
            else:
                self.logger.info(f"🔄 Using fallback execution path for {subtype}")

                if subtype == ExternalActionSubtype.GITHUB.value:
                    self.logger.info(f"📦 Executing GitHub action")
                    return self._execute_github_action(context, logs, start_time)
                elif subtype == ExternalActionSubtype.GOOGLE_CALENDAR.value:
                    self.logger.info(f"📅 Executing Google Calendar action")
                    return await self._execute_google_calendar_action(context, logs, start_time)
                elif subtype == ExternalActionSubtype.TRELLO.value:
                    self.logger.info(f"📋 Executing Trello action")
                    return self._execute_trello_action(context, logs, start_time)
                elif subtype == ExternalActionSubtype.EMAIL.value:
                    self.logger.info(f"📧 Executing Email action")
                    return await self._execute_email_action(context, logs, start_time)
                elif subtype == ExternalActionSubtype.SLACK.value:
                    self.logger.info(f"💬 Executing Slack action")
                    return self._execute_slack_action(context, logs, start_time)
                elif subtype == ExternalActionSubtype.API_CALL.value:
                    self.logger.info(f"🌐 Executing API Call action")
                    return await self._execute_api_call_action(context, logs, start_time)
                elif subtype == ExternalActionSubtype.WEBHOOK.value:
                    self.logger.info(f"🔗 Executing Webhook action")
                    return self._execute_webhook_action(context, logs, start_time)
                elif subtype == ExternalActionSubtype.NOTIFICATION.value:
                    self.logger.info(f"🔔 Executing Notification action")
                    return self._execute_notification_action(context, logs, start_time)
                else:
                    self.logger.error(f"❌ Unsupported external action subtype: {subtype}")
                    return self._create_error_result(
                        f"Unsupported external action subtype: {subtype}",
                        execution_time=time.time() - start_time,
                        logs=logs,
                    )

        except Exception as e:
            self.logger.error(f"💥 ExternalActionNodeExecutor exception details:")
            self.logger.error(f"   - Exception type: {type(e).__name__}")
            self.logger.error(f"   - Exception message: {str(e)}")
            self.logger.error(f"   - Node subtype: {context.node.subtype}")
            self.logger.error(f"   - Node parameters: {context.node.parameters}")
            self.logger.error(f"   - SDKs available: {bool(self._sdks)}")
            self.logger.exception("Full stack trace:")

            return self._create_error_result(
                f"Error executing external action: {str(e)}",
                error_details={
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                    "subtype": context.node.subtype,
                    "sdks_available": bool(self._sdks),
                },
                execution_time=time.time() - start_time,
                logs=logs,
            )

    async def _execute_with_sdk(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute external action using new shared SDK system."""
        subtype = context.node.subtype
        self.logger.info(f"🛠️ _execute_with_sdk called for subtype: {subtype}")

        user_id = getattr(context, "user_id", None) or context.metadata.get(
            "user_id", "00000000-0000-0000-0000-000000000123"
        )
        self.logger.info(f"👤 User ID for SDK: {user_id}")

        # Map subtypes to provider names and operations
        subtype_mapping = {
            ExternalActionSubtype.GITHUB.value: ("github", self._prepare_github_operation),
            ExternalActionSubtype.GOOGLE_CALENDAR.value: (
                "google_calendar",
                self._prepare_google_calendar_operation,
            ),
            ExternalActionSubtype.SLACK.value: ("slack", self._prepare_slack_operation),
            ExternalActionSubtype.EMAIL.value: ("email", self._prepare_email_operation),
            ExternalActionSubtype.API_CALL.value: ("api_call", self._prepare_api_call_operation),
            ExternalActionSubtype.NOTION.value: ("notion", self._prepare_notion_operation),
        }

        if subtype not in subtype_mapping:
            self.logger.error(
                f"❌ Subtype {subtype} not in SDK mapping: {list(subtype_mapping.keys())}"
            )
            return self._create_error_result(
                f"SDK not available for subtype: {subtype}",
                execution_time=time.time() - start_time,
                logs=logs,
            )

        provider, operation_preparer = subtype_mapping[subtype]
        self.logger.info(f"📦 Mapped to provider: {provider}")

        try:
            # Prepare operation and parameters
            self.logger.info(f"🔧 Preparing operation with {operation_preparer.__name__}")
            operation, parameters = operation_preparer(context)
            self.logger.info(f"✅ Prepared {provider} operation: {operation}")
            self.logger.info(f"⚙️ Parameters: {parameters}")
            logs.append(f"Prepared {provider} operation: {operation}")

            # Get credentials from OAuth2 service (N8N-style automatic querying)
            credentials = await self._get_credentials_for_sdk(context, provider, user_id)

            # Check if credentials are available (N8N-style error handling)
            if not credentials:
                # Return standardized error for missing authorization (referencing N8N pattern)
                logs.append(f"No credentials found for {provider} - authorization required")
                return self._create_error_result(
                    f"Missing credentials for {provider}. Please authorize this provider first.",
                    error_details={
                        "error_type": "MISSING_CREDENTIALS",
                        "provider": provider,
                        "user_id": user_id,
                        "requires_auth": True,
                        "auth_provider": provider,
                    },
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

            # Call SDK
            result = await self._call_sdk_api(
                provider=provider,
                operation=operation,
                parameters=parameters,
                credentials=credentials,
                user_id=user_id,
                workflow_execution_id=context.execution_id,
                node_id=context.metadata.get("node_id"),
            )

            logs.append(f"SDK call completed for {provider}: {result.get('success', False)}")

            return self._create_success_result(
                output_data=result, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            logs.append(f"SDK execution failed: {str(e)}")
            return self._create_error_result(
                f"SDK execution failed for {subtype}: {str(e)}",
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _prepare_github_operation(
        self, context: NodeExecutionContext
    ) -> tuple[str, Dict[str, Any]]:
        """Prepare GitHub operation and parameters."""
        # Use get_resolved_parameters to resolve all template variables at once
        resolved_params = context.get_resolved_parameters()

        action = resolved_params.get("action", "")
        repository = resolved_params.get("repository", "")
        owner = resolved_params.get("owner", "")

        parameters = {"repository": repository, "owner": owner}

        # Add action-specific parameters
        if action == "create_issue":
            parameters.update(
                {
                    "title": resolved_params.get("title", ""),
                    "body": resolved_params.get("body", ""),
                    "labels": resolved_params.get("labels", []),
                    "assignees": resolved_params.get("assignees", []),
                }
            )
        elif action == "create_pull_request":
            parameters.update(
                {
                    "title": resolved_params.get("title", ""),
                    "head": resolved_params.get("head", ""),
                    "base": resolved_params.get("base", ""),
                    "body": resolved_params.get("body", ""),
                }
            )
        elif action == "add_comment":
            # Ensure issue_number is resolved from template
            issue_number = resolved_params.get("issue_number")
            if issue_number is not None:
                parameters["issue_number"] = issue_number
            parameters["body"] = resolved_params.get("body", "")
        elif action == "close_issue":
            # Ensure issue_number is resolved from template
            issue_number = resolved_params.get("issue_number")
            if issue_number is not None:
                parameters["issue_number"] = issue_number
        elif action == "list_issues":
            parameters.update(
                {
                    "state": resolved_params.get("state", "open"),
                    "labels": resolved_params.get("labels", []),
                    "sort": resolved_params.get("sort", "created"),
                }
            )

        return action, parameters

    def _prepare_google_calendar_operation(
        self, context: NodeExecutionContext
    ) -> tuple[str, Dict[str, Any]]:
        """Prepare Google Calendar operation and parameters."""
        action = self.get_parameter_with_spec(context, "action") or context.get_parameter("action")
        calendar_id = self.get_parameter_with_spec(context, "calendar_id") or context.get_parameter(
            "calendar_id", "primary"
        )

        parameters = {"calendar_id": calendar_id}

        # Add action-specific parameters
        if action == "create_event":
            event_data = context.get_parameter("event_data", {})
            parameters.update(
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
            parameters.update(
                {
                    "time_min": context.get_parameter("time_min"),
                    "time_max": context.get_parameter("time_max"),
                    "max_results": context.get_parameter("max_results", 10),
                    "single_events": context.get_parameter("single_events", True),
                    "order_by": context.get_parameter("order_by", "startTime"),
                }
            )
        elif action == "update_event":
            parameters.update(
                {
                    "event_id": context.get_parameter("event_id", ""),
                    "summary": context.get_parameter("summary", ""),
                    "description": context.get_parameter("description", ""),
                    "start": context.get_parameter("start"),
                    "end": context.get_parameter("end"),
                }
            )

        return action, parameters

    def _prepare_slack_operation(self, context: NodeExecutionContext) -> tuple[str, Dict[str, Any]]:
        """Prepare Slack operation and parameters."""
        self.logger.info(f"🔧 _prepare_slack_operation called")
        action = self.get_parameter_with_spec(context, "action") or context.get_parameter("action")
        channel = self.get_parameter_with_spec(context, "channel") or context.get_parameter(
            "channel"
        )

        self.logger.info(f"💬 Slack action: {action}")
        self.logger.info(f"📢 Slack channel: {channel}")

        # Provide default action if none specified
        if not action:
            action = "send_message"  # Default to send_message
            self.logger.warning(f"❌ No Slack action specified, defaulting to: {action}")

        # Handle channel validation and fallbacks
        if not channel:
            self.logger.error(f"❌ No Slack channel specified")
        elif channel.startswith("example-value-"):
            # Replace example/placeholder values with a test channel or better error
            self.logger.warning(
                f"⚠️ Placeholder channel '{channel}' detected. This needs to be replaced with a real Slack channel ID."
            )
            # For demo purposes, we can either:
            # 1. Use a test channel (if available): channel = "C1234567890"
            # 2. Or provide a clear error message
            channel = None  # This will cause a clear error message

        parameters = {"channel": channel}

        # Add action-specific parameters
        if action == "send_message":
            message_data = context.get_parameter("message_data", {})

            # Get text and blocks with proper parameter resolution
            text = message_data.get("text", context.get_parameter("text", ""))

            # Also check for 'message' parameter (common in workflow definitions)
            if not text:
                text = context.get_parameter("message", "")
                self.logger.info(f"📝 Found 'message' parameter: {text}")

                # Check if this is a placeholder value that should be replaced
                if text and text.startswith("example-value-"):
                    self.logger.warning(
                        f"⚠️ Detected placeholder message value: {text}, will look for AI response"
                    )
                    text = ""  # Clear placeholder so we check input data

            # Check for input data from connected nodes (AI agent response)
            if not text and context.input_data:
                # Try to extract AI response from input data
                if "ai_response" in context.input_data:
                    ai_response = context.input_data["ai_response"]
                    self.logger.info(f"🤖 Found AI response in input data: {ai_response}")

                    # Parse AI response if it's JSON
                    try:
                        if isinstance(ai_response, str):
                            import json

                            ai_data = json.loads(ai_response)
                            # Extract the actual response content, not the wrapper
                            if "response" in ai_data:
                                text = ai_data["response"]
                                # If response is still JSON-like, extract further
                                if isinstance(text, str) and text.startswith('{"'):
                                    try:
                                        inner_data = json.loads(text)
                                        if "response" in inner_data:
                                            text = inner_data["response"]
                                    except:
                                        pass  # Use outer response if inner parsing fails
                            else:
                                text = str(ai_data)
                        else:
                            text = str(ai_response)
                        self.logger.info(f"✅ Extracted AI response content: {text}")
                    except (json.JSONDecodeError, Exception) as e:
                        self.logger.warning(f"⚠️ Failed to parse AI response, using raw: {e}")
                        text = str(ai_response)

                # Also check for general response or output from upstream nodes
                elif "response" in context.input_data:
                    text = str(context.input_data["response"])
                    self.logger.info(f"✅ Using upstream response as message: {text}")
                elif "output" in context.input_data:
                    text = str(context.input_data["output"])
                    self.logger.info(f"✅ Using upstream output as message: {text}")

            blocks = message_data.get("blocks", context.get_parameter("blocks", []))

            # Provide default text if both text and blocks are empty
            if not text and not blocks:
                # Use contextual message based on trigger data or generic message
                trigger_data = context.metadata.get("trigger_data", {})
                trigger_type = trigger_data.get("trigger_type", "workflow")
                text = f"🤖 Workflow executed via {trigger_type} trigger"
                self.logger.info(f"✅ Using default Slack message: {text}")

            parameters.update(
                {
                    "text": text,
                    "blocks": blocks,
                    "attachments": message_data.get(
                        "attachments", context.get_parameter("attachments", [])
                    ),
                    "username": context.get_parameter("username"),
                    "icon_emoji": context.get_parameter("icon_emoji"),
                    "icon_url": context.get_parameter("icon_url"),
                    "thread_ts": self._clean_thread_ts(context.get_parameter("thread_ts")),
                    "reply_broadcast": context.get_parameter("reply_broadcast", False),
                }
            )
        elif action == "list_channels":
            parameters.update(
                {
                    "types": context.get_parameter("types", "public_channel,private_channel"),
                    "exclude_archived": context.get_parameter("exclude_archived", True),
                    "limit": context.get_parameter("limit", 100),
                }
            )
        elif action == "upload_file":
            parameters.update(
                {
                    "file_content": context.get_parameter("file_content", ""),
                    "file_name": context.get_parameter("file_name", ""),
                    "title": context.get_parameter("title"),
                    "initial_comment": context.get_parameter("initial_comment"),
                    "channels": channel,
                }
            )

        self.logger.info(f"✅ Returning Slack operation: action='{action}', parameters={parameters}")
        return action, parameters

    def _clean_thread_ts(self, thread_ts: str) -> str:
        """Clean thread_ts parameter, removing placeholder values."""
        if not thread_ts:
            return None

        # Remove placeholder values
        if thread_ts.startswith("example-value-"):
            self.logger.info(f"🧹 Removing placeholder thread_ts: {thread_ts}")
            return None

        return thread_ts

    def _prepare_email_operation(self, context: NodeExecutionContext) -> tuple[str, Dict[str, Any]]:
        """Prepare Email operation and parameters."""
        action = self.get_parameter_with_spec(context, "action") or "send"

        parameters = {}

        if action == "send":
            parameters.update(
                {
                    "recipients": self.get_parameter_with_spec(context, "recipients"),
                    "subject": self.get_parameter_with_spec(context, "subject"),
                    "body": context.get_parameter("body", context.get_parameter("message", "")),
                    "from_email": context.get_parameter("from_email"),
                }
            )

        return action, parameters

    def _prepare_api_call_operation(
        self, context: NodeExecutionContext
    ) -> tuple[str, Dict[str, Any]]:
        """Prepare API Call operation and parameters."""
        parameters = {
            "method": self.get_parameter_with_spec(context, "method"),
            "url": self.get_parameter_with_spec(context, "url"),
            "headers": self.get_parameter_with_spec(context, "headers") or {},
            "query_params": self.get_parameter_with_spec(context, "query_params") or {},
            "body": self.get_parameter_with_spec(context, "body"),
            "timeout": self.get_parameter_with_spec(context, "timeout") or 30,
            "authentication": self.get_parameter_with_spec(context, "authentication") or "none",
        }

        # Add authentication parameters
        if parameters["authentication"] != "none":
            auth_token = self.get_parameter_with_spec(context, "auth_token")
            api_key_header = self.get_parameter_with_spec(context, "api_key_header")
            username = self.get_parameter_with_spec(context, "username")
            password = self.get_parameter_with_spec(context, "password")

            if auth_token:
                parameters["auth_token"] = auth_token
            if api_key_header:
                parameters["api_key_header"] = api_key_header
            if username:
                parameters["username"] = username
            if password:
                parameters["password"] = password

        return "generic_call", parameters

    def _prepare_notion_operation(
        self, context: NodeExecutionContext
    ) -> tuple[str, Dict[str, Any]]:
        """Prepare Notion operation and parameters."""
        # Use get_resolved_parameters to resolve all template variables at once
        resolved_params = context.get_resolved_parameters()

        action_type = resolved_params.get("action_type", "")

        parameters = {
            "action_type": action_type,
            "query": resolved_params.get("query"),
            "page_id": resolved_params.get("page_id"),
            "database_id": resolved_params.get("database_id"),
            "parent_id": resolved_params.get("parent_id"),
            "parent_type": resolved_params.get("parent_type", "page"),
            "properties": resolved_params.get("properties", {}),
            "content": resolved_params.get("content", {}),
            "block_operations": resolved_params.get("block_operations", []),
            "search_filter": resolved_params.get("search_filter", {}),
            "database_query": resolved_params.get("database_query", {}),
            "include_content": resolved_params.get("include_content", False),
            "limit": resolved_params.get("limit", 10),
        }

        # Remove None values to keep parameters clean
        parameters = {k: v for k, v in parameters.items() if v is not None}

        return action_type, parameters

    async def _get_credentials_for_sdk(
        self, context: NodeExecutionContext, provider: str, user_id: str
    ) -> Dict[str, str]:
        """Get credentials for SDK from OAuth2 service (N8N-style automatic credential querying).

        This method implements the N8N-style approach where:
        1. Credentials are automatically queried from database, not passed in requests
        2. Missing credentials result in structured error responses
        3. Frontend handles authorization flow based on error responses
        """
        # Always query stored credentials from database (N8N style)
        # Don't check context.credentials - this enforces the N8N pattern
        return await self._get_user_credentials(user_id, provider) or {}

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
        _ensure_api_adapters()
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

        # Always query stored credentials from database (N8N style)
        credentials = await self._get_user_credentials(user_id, provider)

        # Debug logging
        self.logger.info(f"Calling external API for provider={provider}, operation={operation}")
        self.logger.info(
            f"Auto-queried credentials for user {user_id}, provider {provider}: {bool(credentials)}"
        )

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

            # Check if this is an N8N-style error response (missing credentials)
            if not output_data.get("success", True) and output_data.get("requires_auth"):
                logs.append(f"Missing credentials for github - authorization required")
                return self._create_error_result(
                    f"Missing credentials for github. Please authorize this provider first.",
                    error_details={
                        "error_type": "MISSING_CREDENTIALS",
                        "provider": "github",
                        "user_id": user_id,
                        "requires_auth": True,
                        "auth_provider": "github",
                    },
                    execution_time=time.time() - start_time,
                    logs=logs,
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
            output_data = await self._call_external_api(
                "google_calendar",
                action,
                api_parameters,
                user_id,
                context.metadata.get("workflow_execution_id"),
                context.metadata.get("node_id"),
                context,
            )

            # Check if this is an N8N-style error response (missing credentials)
            if not output_data.get("success", True) and output_data.get("requires_auth"):
                logs.append(f"Missing credentials for google_calendar - authorization required")
                return self._create_error_result(
                    f"Missing credentials for google_calendar. Please authorize this provider first.",
                    error_details={
                        "error_type": "MISSING_CREDENTIALS",
                        "provider": "google_calendar",
                        "user_id": user_id,
                        "requires_auth": True,
                        "auth_provider": "google_calendar",
                    },
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

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

    async def _execute_email_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute email action."""
        # Use spec-based parameter retrieval with fallback
        action = self.get_parameter_with_spec(context, "action") or "send"
        user_id = getattr(context, "user_id", None) or context.metadata.get(
            "user_id", "00000000-0000-0000-0000-000000000123"
        )

        logs.append(f"Email action: {action}")

        # Prepare parameters for Email API
        api_parameters = {}

        if action == "send":
            api_parameters.update(
                {
                    "recipients": self.get_parameter_with_spec(context, "recipients"),
                    "subject": self.get_parameter_with_spec(context, "subject"),
                    "body": context.get_parameter("body", context.get_parameter("message", "")),
                    "from_email": context.get_parameter("from_email"),
                }
            )

        # Call real Email API
        try:
            # Direct async call since method is now async
            output_data = await self._call_external_api(
                "email",
                action,
                api_parameters,
                user_id,
                context.metadata.get("workflow_execution_id"),
                context.metadata.get("node_id"),
                context,
            )

            # Check if this is an N8N-style error response (missing credentials)
            if not output_data.get("success", True) and output_data.get("requires_auth"):
                logs.append(f"Missing credentials for email - authorization required")
                return self._create_error_result(
                    f"Missing credentials for email. Please authorize this provider first.",
                    error_details={
                        "error_type": "MISSING_CREDENTIALS",
                        "provider": "email",
                        "user_id": user_id,
                        "requires_auth": True,
                        "auth_provider": "email",
                    },
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            logs.append(f"Failed to call Email API: {str(e)}")
            # Fallback to mock data with error info
            output_data = {
                "provider": "email",
                "action": action,
                "result": f"Mock email {action} result (API call failed: {str(e)})",
                "executed_at": datetime.now().isoformat(),
                "fallback_mode": True,
                "api_error": str(e),
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

        # Use trigger channel if parameter channel is a placeholder or empty
        trigger_channel = context.metadata.get("trigger_channel_id")
        if trigger_channel and (not channel or channel.startswith("example-value")):
            channel = trigger_channel
            logs.append(f"Using trigger channel: {channel} (parameter was placeholder/empty)")
        elif not channel:
            logs.append("Warning: No channel specified and no trigger channel available")
        user_id = getattr(context, "user_id", None) or context.metadata.get(
            "user_id", "00000000-0000-0000-0000-000000000123"
        )

        logs.append(f"Slack action: {action} in channel: {channel}")

        # Prepare parameters for Slack API
        api_parameters = {"channel": channel}

        # Add action-specific parameters
        if action == "send_message":
            message_data = context.get_parameter("message_data", {})

            # Get message text with fallback for placeholder values
            message_text = message_data.get("text", context.get_parameter("text", ""))
            if not message_text or message_text.startswith("example-value"):
                # Use a contextual message based on trigger data
                trigger_data = context.metadata.get("trigger_data", {})
                trigger_type = trigger_data.get("trigger_type", "unknown")
                message_text = f"🤖 Workflow triggered by {trigger_type} event"
                logs.append(f"Using default message (parameter was placeholder): {message_text}")

            api_parameters.update(
                {
                    "text": message_text,
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

            # Check if this is an N8N-style error response (missing credentials)
            if not output_data.get("success", True) and output_data.get("requires_auth"):
                logs.append(f"Missing credentials for slack - authorization required")
                return self._create_error_result(
                    f"Missing credentials for slack. Please authorize this provider first.",
                    error_details={
                        "error_type": "MISSING_CREDENTIALS",
                        "provider": "slack",
                        "user_id": user_id,
                        "requires_auth": True,
                        "auth_provider": "slack",
                    },
                    execution_time=time.time() - start_time,
                    logs=logs,
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
            "authentication": authentication,
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
        user_id = getattr(context, "user_id", None) or context.metadata.get(
            "user_id", "00000000-0000-0000-0000-000000000123"
        )
        credentials = {}

        # Call real API using the api_call adapter
        try:
            # Direct async call using the new shared API system
            output_data = await self._call_external_api(
                "api_call",
                "generic_call",
                api_parameters,
                user_id,
                context.metadata.get("workflow_execution_id"),
                context.metadata.get("node_id"),
                context,
            )

            # Check if this is an N8N-style error response (missing credentials)
            if not output_data.get("success", True) and output_data.get("requires_auth"):
                logs.append(f"Missing credentials for api_call - authorization required")
                return self._create_error_result(
                    f"Missing credentials for api_call. Please authorize this provider first.",
                    error_details={
                        "error_type": "MISSING_CREDENTIALS",
                        "provider": "api_call",
                        "user_id": user_id,
                        "requires_auth": True,
                        "auth_provider": "api_call",
                    },
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

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
                "api_error": str(e),
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
