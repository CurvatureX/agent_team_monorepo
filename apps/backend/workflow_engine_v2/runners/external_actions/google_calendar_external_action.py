"""
Google Calendar external action for workflow_engine_v2 using Google Calendar SDK.

This implementation uses the shared Google Calendar SDK for all operations,
strictly following the node specification in shared/node_specs/EXTERNAL_ACTION/GOOGLE_CALENDAR.py.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult
from shared.sdks.google_calendar_sdk.client import GoogleCalendarSDK
from shared.sdks.google_calendar_sdk.exceptions import (
    GoogleCalendarAuthError,
    GoogleCalendarError,
    GoogleCalendarNotFoundError,
    GoogleCalendarPermissionError,
    GoogleCalendarRateLimitError,
    GoogleCalendarValidationError,
)
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction


class GoogleCalendarExternalAction(BaseExternalAction):
    """
    Google Calendar external action handler using Google Calendar SDK.

    Follows node spec output format (11 fields):
    - success: boolean
    - google_response: object (parsed Google API response)
    - event: object (single event when applicable)
    - events: array (list of events when listing)
    - calendars: array (list of calendars when listing)
    - next_page_token: string
    - next_sync_token: string
    - html_link: string
    - event_id: string
    - event_url: string/calendar_url: string
    - meeting_link: string
    - error_message: string
    - execution_metadata: object
    """

    def __init__(self):
        super().__init__("google")

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle Google Calendar-specific operations using SDK."""
        try:
            # Get Google OAuth token from oauth_tokens table
            google_token = await self.get_oauth_token(context)

            if not google_token:
                return self._create_spec_error_result(
                    "No Google authentication token found. Please connect your Google account in integrations settings.",
                    operation,
                    {
                        "reason": "missing_oauth_token",
                        "solution": "Connect Google account in integrations settings",
                    },
                )

            # Initialize SDK
            sdk = GoogleCalendarSDK()
            credentials = {"access_token": google_token}

            # Build parameters from input_data (highest priority) and configurations (fallback)
            parameters = self._build_parameters(context)

            # Execute operation via SDK
            self.log_execution(context, f"Executing Google Calendar operation: {operation}")
            start_time = datetime.now()

            response = await sdk.call_operation(operation, parameters, credentials)

            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if response.success:
                self.log_execution(context, f"✅ Google Calendar {operation} succeeded")
                return self._create_spec_success_result(operation, response.data, execution_time_ms)
            else:
                self.log_execution(
                    context, f"❌ Google Calendar {operation} failed: {response.error}", "ERROR"
                )
                return self._create_spec_error_result(
                    response.error or "Unknown error",
                    operation,
                    {
                        "reason": "api_error",
                        "status_code": response.status_code,
                    },
                )

        except GoogleCalendarAuthError as e:
            self.log_execution(context, f"Google Calendar authentication error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Google Calendar authentication failed: {str(e)}",
                operation,
                {
                    "reason": "authentication_error",
                    "solution": "Check Google OAuth token validity and refresh if needed",
                },
            )
        except GoogleCalendarPermissionError as e:
            self.log_execution(context, f"Google Calendar permission error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Insufficient permissions: {str(e)}",
                operation,
                {
                    "reason": "permission_error",
                    "solution": "Grant required Google Calendar permissions in OAuth consent",
                },
            )
        except GoogleCalendarRateLimitError as e:
            self.log_execution(context, f"Google Calendar rate limit exceeded: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Rate limit exceeded: {str(e)}",
                operation,
                {"reason": "rate_limit_exceeded", "solution": "Wait before retrying"},
            )
        except GoogleCalendarNotFoundError as e:
            self.log_execution(context, f"Google Calendar resource not found: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Resource not found: {str(e)}",
                operation,
                {"reason": "resource_not_found", "solution": "Verify calendar_id/event_id"},
            )
        except GoogleCalendarValidationError as e:
            self.log_execution(context, f"Google Calendar validation error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Validation error: {str(e)}",
                operation,
                {"reason": "validation_error", "solution": "Check required parameters"},
            )
        except GoogleCalendarError as e:
            self.log_execution(context, f"Google Calendar API error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Google Calendar API error: {str(e)}",
                operation,
                {"reason": "api_error"},
            )
        except Exception as e:
            self.log_execution(context, f"Unexpected error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Google Calendar action failed: {str(e)}",
                operation,
                {"exception_type": type(e).__name__, "exception": str(e)},
            )

    def _build_parameters(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """
        Build parameters from input_data and configurations.

        Priority: input_data (highest) > configurations (fallback)
        Per node spec input_params schema.
        """
        # Start with configurations as base
        params = dict(context.node.configurations)

        # Override with input_data (highest priority)
        if context.input_data:
            params.update(context.input_data)

        # Handle nested 'data' object from node spec input_params
        if "data" in params and isinstance(params["data"], dict):
            # Merge data object into parameters
            data = params.pop("data")
            for key, value in data.items():
                if key not in params or params[key] is None:
                    params[key] = value

        return params

    def _create_spec_error_result(
        self, message: str, operation: str, error_details: Dict[str, Any] = None
    ) -> NodeExecutionResult:
        """
        Create error result following node spec output format.

        Spec output_params (11 fields):
        - success: false
        - google_response: {}
        - event: {}
        - events: []
        - calendars: []
        - next_page_token: ""
        - next_sync_token: ""
        - html_link: ""
        - event_id: ""
        - event_url/calendar_url: ""
        - meeting_link: ""
        - error_message: string
        - execution_metadata: object
        """
        return NodeExecutionResult(
            status=ExecutionStatus.ERROR,
            error_message=message,
            error_details={
                "integration": self.integration_name,
                "operation": operation,
                **(error_details or {}),
            },
            output_data={
                "success": False,
                "google_response": {},
                "event": {},
                "events": [],
                "calendars": [],
                "next_page_token": "",
                "next_sync_token": "",
                "html_link": "",
                "event_id": "",
                "event_url": "",
                "calendar_url": "",
                "meeting_link": "",
                "error_message": message,
                "execution_metadata": {
                    "integration_type": self.integration_name,
                    "operation": operation,
                    "timestamp": datetime.now().isoformat(),
                },
            },
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )

    def _create_spec_success_result(
        self, operation: str, response_data: Any, execution_time_ms: int = 0
    ) -> NodeExecutionResult:
        """
        Create success result following node spec output format.

        Spec output_params (11 fields):
        - success: true
        - google_response: object (parsed Google API response)
        - event: object (single event when applicable)
        - events: array (list of events when listing)
        - calendars: array (list of calendars when listing)
        - next_page_token: string
        - next_sync_token: string
        - html_link: string
        - event_id: string
        - event_url/calendar_url: string
        - meeting_link: string
        - error_message: ""
        - execution_metadata: object
        """
        # Initialize all fields with defaults
        output = {
            "success": True,
            "google_response": response_data if isinstance(response_data, dict) else {},
            "event": {},
            "events": [],
            "calendars": [],
            "next_page_token": "",
            "next_sync_token": "",
            "html_link": "",
            "event_id": "",
            "event_url": "",
            "calendar_url": "",
            "meeting_link": "",
            "error_message": "",
            "execution_metadata": {
                "integration_type": self.integration_name,
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                "execution_time_ms": execution_time_ms,
            },
        }

        # Populate fields based on response structure
        if isinstance(response_data, dict):
            # Single event operations (create_event, update_event, get_event)
            if "event" in response_data:
                event = response_data["event"]
                output["event"] = event
                output["event_id"] = event.get("id", "")
                output["html_link"] = event.get("htmlLink", "") or event.get("html_link", "")
                output["event_url"] = output["html_link"]
                # Extract meeting link (Google Meet, Zoom, etc.)
                output["meeting_link"] = event.get("hangoutLink", "") or event.get(
                    "conferenceData", {}
                ).get("entryPoints", [{}])[0].get("uri", "")

            # List events operations
            if "events" in response_data:
                output["events"] = response_data["events"]
                output["next_page_token"] = response_data.get("next_page_token", "")
                output["next_sync_token"] = response_data.get("next_sync_token", "")

            # List calendars operations
            if "calendars" in response_data:
                output["calendars"] = response_data["calendars"]

            # Calendar operations
            if "calendar" in response_data:
                calendar = response_data["calendar"]
                output["google_response"] = calendar
                output["calendar_url"] = calendar.get("id", "")

            # Direct fields
            if "event_id" in response_data:
                output["event_id"] = response_data["event_id"]
            if "html_link" in response_data:
                output["html_link"] = response_data["html_link"]
                output["event_url"] = response_data["html_link"]

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output,
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )


__all__ = ["GoogleCalendarExternalAction"]
