import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from shared.models.node_enums import TriggerSubtype
from shared.models.trigger import ExecutionResult, TriggerStatus
from workflow_scheduler.core.config import settings
from workflow_scheduler.triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class WebhookTrigger(BaseTrigger):
    """Webhook trigger for HTTP-based workflow execution"""

    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        super().__init__(workflow_id, trigger_config)

        self.webhook_path = trigger_config.get("webhook_path", f"/webhook/{workflow_id}")
        self.methods = trigger_config.get("methods", ["POST"])
        self.require_auth = trigger_config.get("require_auth", False)

        # Ensure webhook path starts with /
        if not self.webhook_path.startswith("/"):
            self.webhook_path = f"/{self.webhook_path}"

    @property
    def trigger_type(self) -> str:
        return TriggerSubtype.WEBHOOK.value

    async def start(self) -> bool:
        """Start the webhook trigger (mark as active)"""
        try:
            if not self.enabled:
                logger.info(f"Webhook trigger for workflow {self.workflow_id} is disabled")
                self.status = TriggerStatus.PAUSED
                return True

            self.status = TriggerStatus.ACTIVE
            webhook_url = self.get_webhook_url()

            logger.info(f"Webhook trigger started for workflow {self.workflow_id}: {webhook_url}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to start webhook trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            self.status = TriggerStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the webhook trigger"""
        try:
            self.status = TriggerStatus.STOPPED
            logger.info(f"Webhook trigger stopped for workflow {self.workflow_id}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to stop webhook trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            return False

    def get_webhook_url(self) -> str:
        """Get the full webhook URL"""
        base_url = settings.api_gateway_url.rstrip("/")
        return f"{base_url}{self.webhook_path}"

    async def process_webhook(self, request_data: Dict[str, Any]) -> ExecutionResult:
        """
        Process webhook request and trigger workflow

        Args:
            request_data: HTTP request data containing headers, body, etc.

        Returns:
            ExecutionResult with execution details
        """
        try:
            if not self.enabled:
                return ExecutionResult(
                    status="failed",
                    message="Webhook trigger is disabled",
                    trigger_data=request_data,
                )

            if self.status != TriggerStatus.ACTIVE:
                return ExecutionResult(
                    status="failed",
                    message=f"Webhook trigger is not active (status: {self.status.value})",
                    trigger_data=request_data,
                )

            # Validate HTTP method
            method = request_data.get("method", "POST").upper()
            if method not in [m.upper() for m in self.methods]:
                return ExecutionResult(
                    status="failed",
                    message=f"HTTP method {method} not allowed. Allowed methods: {self.methods}",
                    trigger_data=request_data,
                )

            # Validate authentication if required
            if self.require_auth:
                auth_result = await self._validate_webhook_auth(request_data)
                if not auth_result["valid"]:
                    return ExecutionResult(
                        status="failed",
                        message=f"Authentication failed: {auth_result['error']}",
                        trigger_data=request_data,
                    )

            # Prepare trigger data
            trigger_data = {
                "trigger_type": "webhook",
                "method": method,
                "path": request_data.get("path", self.webhook_path),
                "headers": request_data.get("headers", {}),
                "query_params": request_data.get("query_params", {}),
                "body": request_data.get("body"),
                "remote_addr": request_data.get("remote_addr"),
                "user_agent": request_data.get("headers", {}).get("user-agent"),
                "content_type": request_data.get("headers", {}).get("content-type"),
                "triggered_at": datetime.utcnow().isoformat(),
                "execution_id": f"exec_{uuid.uuid4()}",
                "webhook_path": self.webhook_path,
            }

            # Execute workflow
            result = await self._trigger_workflow(trigger_data)

            if result.status == "started":
                logger.info(
                    f"Webhook trigger executed successfully for workflow {self.workflow_id}: {result.execution_id}"
                )
            else:
                logger.warning(
                    f"Webhook trigger execution had issues for workflow {self.workflow_id}: {result.message}"
                )

            return result

        except Exception as e:
            error_msg = f"Error processing webhook for workflow {self.workflow_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return ExecutionResult(status="error", message=error_msg, trigger_data=request_data)

    async def _validate_webhook_auth(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate webhook authentication

        Args:
            request_data: HTTP request data

        Returns:
            Dict with validation result
        """
        try:
            headers = request_data.get("headers", {})

            # Check for Authorization header
            auth_header = headers.get("authorization") or headers.get("Authorization")
            if not auth_header:
                return {"valid": False, "error": "Missing Authorization header"}

            # Simple bearer token validation (can be extended)
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                # TODO: Implement actual token validation
                # For now, just check if token exists and is not empty
                if token:
                    return {"valid": True, "error": None}
                else:
                    return {"valid": False, "error": "Empty bearer token"}

            # Check for API key in headers
            api_key = headers.get("x-api-key") or headers.get("X-API-Key")
            if api_key:
                # TODO: Implement actual API key validation
                return {"valid": True, "error": None}

            return {"valid": False, "error": "Invalid authentication method"}

        except Exception as e:
            logger.error(f"Error validating webhook auth: {e}", exc_info=True)
            return {"valid": False, "error": f"Authentication validation error: {str(e)}"}

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of the webhook trigger"""
        base_health = await super().health_check()

        webhook_health = {
            **base_health,
            "webhook_path": self.webhook_path,
            "webhook_url": self.get_webhook_url(),
            "methods": self.methods,
            "require_auth": self.require_auth,
            "ready_for_webhooks": self.enabled and self.status == TriggerStatus.ACTIVE,
        }

        return webhook_health
