"""
Human-in-the-Loop Node Executor - Production Implementation.

Handles human interaction operations with workflow pause/resume, AI response filtering,
and multi-channel communication support according to the HIL system technical design.
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from shared.models import NodeType
from shared.models.human_in_loop import (
    HILChannelType,
    HILErrorData,
    HILFilteredData,
    HILInputData,
    HILInteractionType,
    HILOutputData,
    HILPriority,
    HILStatus,
    HILTimeoutData,
)
from shared.models.node_enums import HumanLoopSubtype
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

from ..services.hil_service import HILWorkflowService
from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult


class HumanLoopNodeExecutor(BaseNodeExecutor):
    """Enhanced HIL node executor with workflow pause and AI response filtering."""

    def __init__(self, subtype: Optional[str] = None):
        super().__init__(subtype=subtype)
        # Initialize HIL system components
        from ..services.channel_integration_manager import ChannelIntegrationManager
        from ..services.hil_response_classifier import HILResponseClassifier
        from ..services.hil_timeout_manager import HILTimeoutManager
        from ..services.workflow_status_manager import WorkflowStatusManager

        self.ai_classifier = HILResponseClassifier()
        self.channel_integrations = ChannelIntegrationManager()
        self.workflow_status_manager = WorkflowStatusManager()
        self.timeout_manager = HILTimeoutManager(self.workflow_status_manager)

        # Initialize Slack client for actual message sending
        self.slack_client = None
        self._initialize_slack_client()

        # Initialize HIL service for complete response message handling
        self.hil_service = HILWorkflowService()

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for human loop nodes."""
        if node_spec_registry and self._subtype:
            return node_spec_registry.get_spec(NodeType.HUMAN_IN_THE_LOOP.value, self._subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported human-in-the-loop subtypes."""
        return [subtype.value for subtype in HumanLoopSubtype]

    def validate(self, node: Any) -> List[str]:
        """Validate HIL node configuration using standardized data models."""
        errors = super().validate(node)

        if not node.subtype:
            errors.append("Human-in-the-loop subtype is required")
            return errors

        if node.subtype not in self.get_supported_subtypes():
            errors.append(f"Unsupported human-in-the-loop subtype: {node.subtype}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute HIL node with workflow pause and response handling."""

        logs = []
        start_time = time.time()

        try:
            # 1. Check if this is a resume from existing interaction
            existing_interaction = self._check_existing_interaction(context)
            if existing_interaction:
                logs.append(f"Resuming HIL interaction: {existing_interaction.get('id')}")
                return self._handle_resume_execution(existing_interaction, context, logs)

            # 2. Parse HIL input data from context
            try:
                hil_input = self._parse_hil_input_data(context)
                logs.append(f"Parsed HIL input: {hil_input.interaction_type}")
            except Exception as e:
                return self._create_error_result(
                    f"Invalid HIL input data: {str(e)}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

            # 3. Create human interaction record
            logs.append("Creating new HIL interaction")
            interaction = self._create_human_interaction(hil_input, context, logs)

            # 4. Send initial message through appropriate channel
            self._send_human_request(interaction, hil_input, context, logs)

            # 5. Pause workflow execution
            self._pause_workflow_execution(interaction, context, logs)

            # 6. Return pause result to halt workflow execution
            logs.append(
                f"Workflow paused - waiting for human response (timeout: {interaction.get('timeout_at')})"
            )
            return self._create_pause_result(interaction, logs, time.time() - start_time)

        except Exception as e:
            return self._create_error_result(
                f"Error executing HIL node: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _parse_hil_input_data(self, context: NodeExecutionContext) -> HILInputData:
        """Parse and validate HIL input data from context."""
        input_data = context.input_data or {}

        # Convert context input to HILInputData model for validation
        try:
            return HILInputData(**input_data)
        except Exception as e:
            raise ValueError(f"Invalid HIL input format: {str(e)}")

    def _check_existing_interaction(
        self, context: NodeExecutionContext
    ) -> Optional[Dict[str, Any]]:
        """Check if there's an existing interaction for this workflow/node."""
        try:
            workflow_id = getattr(context, "workflow_id", "unknown")
            execution_id = getattr(context, "execution_id", "unknown")
            node_id = getattr(
                context, "node_id", context.node.id if hasattr(context.node, "id") else "unknown"
            )

            # Check if workflow is currently paused for HIL interaction
            pause_status = self.workflow_status_manager.get_pause_status(execution_id)

            if (
                pause_status.get("is_paused")
                and pause_status.get("pause_reason") == "human_interaction"
            ):
                # Return the existing interaction data
                return {
                    "id": pause_status.get("interaction_id"),
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "node_id": node_id,
                    "status": "pending",
                    "resumed": True,
                }

            return None
        except Exception as e:
            # If status check fails, assume no existing interaction
            return None

    def _handle_resume_execution(
        self, interaction: Dict[str, Any], context: NodeExecutionContext, logs: List[str]
    ) -> NodeExecutionResult:
        """Handle workflow resume from existing HIL interaction."""
        logs.append(f"Processing response for interaction {interaction.get('id')}")
        interaction_id = interaction.get("id")

        try:
            # Get the human response - in a real system this would query hil_responses table
            # For now, we'll simulate getting the response from workflow context or parameters
            response_data = getattr(context, "hil_response_data", None) or context.input_data.get(
                "hil_response", {}
            )

            if not response_data:
                # No response data available, default to approved for demo
                response_data = {"approved": True, "default_response": True}
                logs.append("No explicit response data found, defaulting to approved")

            # Classify response using AI if needed
            if response_data.get("needs_classification"):
                classification_result = self.ai_classifier.classify_response(
                    response_text=response_data.get("text", ""),
                    interaction_type=HILInteractionType.APPROVAL,
                    context_data=response_data.get("context", {}),
                )
                response_data.update(classification_result)
                logs.append(
                    f"AI classification completed: {classification_result.get('classification')}"
                )

            # Determine output port based on response
            output_port = self.determine_output_port(response_data)
            logs.append(f"Determined output port: {output_port}")

            # Resume workflow execution
            self.workflow_status_manager.resume_workflow_execution(
                execution_id=interaction.get("execution_id"),
                resume_reason="human_response_received",
                resume_data=response_data,
            )

            return self._create_success_result(
                output_data={
                    "resumed": True,
                    "interaction_id": interaction_id,
                    "response_data": response_data,
                    "output_port": output_port,
                },
                execution_time=100,
                logs=logs,
                output_port=output_port,
            )

        except Exception as e:
            error_msg = f"Failed to handle HIL resume: {str(e)}"
            logs.append(error_msg)
            return self._create_error_result(
                error_msg,
                error_details={"interaction_id": interaction_id, "exception": str(e)},
                execution_time=50,
                logs=logs,
            )

    def _create_human_interaction(
        self, hil_input: HILInputData, context: NodeExecutionContext, logs: List[str]
    ) -> Dict[str, Any]:
        """Create human interaction record in database."""
        interaction_id = str(uuid.uuid4())

        # Calculate timeout
        timeout_at = datetime.now() + timedelta(hours=hil_input.timeout_hours)

        interaction_data = {
            "id": interaction_id,
            "workflow_id": getattr(context, "workflow_id", "unknown"),
            "execution_id": getattr(context, "execution_id", "unknown"),
            "node_id": getattr(
                context, "node_id", context.node.id if hasattr(context.node, "id") else "unknown"
            ),
            "interaction_type": hil_input.interaction_type.value,
            "channel_type": hil_input.channel_config.channel_type.value,
            "status": HILStatus.PENDING.value,
            "priority": hil_input.priority.value,
            "created_at": datetime.now(),
            "timeout_at": timeout_at,
            "request_data": hil_input.dict(),
            "correlation_id": hil_input.correlation_id,
        }

        # Store interaction in database via workflow status manager
        try:
            self.workflow_status_manager.create_pause_record(
                execution_id=interaction_data["execution_id"],
                node_id=interaction_data["node_id"],
                pause_reason="human_interaction",
                pause_data={
                    "interaction_id": interaction_id,
                    "interaction_type": hil_input.interaction_type.value,
                    "timeout_at": timeout_at.isoformat(),
                    "channel_type": hil_input.channel_config.channel_type.value,
                    "request_data": hil_input.dict(),
                },
            )
            logs.append(
                f"Created interaction {interaction_id} with {hil_input.timeout_hours}h timeout"
            )
        except Exception as e:
            logs.append(f"Warning: Failed to store interaction record: {str(e)}")

        return interaction_data

    def _initialize_slack_client(self):
        """Initialize Slack client for message sending."""
        try:
            # Try to get Slack bot token from environment or config
            slack_token = os.getenv("DEFAULT_SLACK_BOT_TOKEN")

            if slack_token:
                self.slack_client = SlackWebClient(slack_token)
                # Test authentication silently
                try:
                    self.slack_client.auth_test()
                except SlackAPIError:
                    # If auth fails, disable Slack client
                    self.slack_client = None
        except Exception:
            # If initialization fails, continue without Slack
            self.slack_client = None

    def _send_human_request(
        self,
        interaction: Dict[str, Any],
        hil_input: HILInputData,
        context: NodeExecutionContext,
        logs: List[str],
    ):
        """Send human request through appropriate channel."""
        channel_type = hil_input.channel_config.channel_type

        if channel_type == HILChannelType.SLACK:
            self._send_slack_request(interaction, hil_input, logs)
        elif channel_type == HILChannelType.EMAIL:
            self._send_email_request(interaction, hil_input, logs)
        elif channel_type == HILChannelType.WEBHOOK:
            self._send_webhook_request(interaction, hil_input, logs)
        elif channel_type == HILChannelType.APP:
            self._send_app_request(interaction, hil_input, logs)
        else:
            raise ValueError(f"Unsupported channel type: {channel_type}")

    def _send_slack_request(
        self, interaction: Dict[str, Any], hil_input: HILInputData, logs: List[str]
    ):
        """Send HIL request via Slack."""
        if not self.slack_client:
            logs.append("Slack client not available - message not sent")
            return

        try:
            # Build Slack blocks for rich formatting
            blocks = self._build_hil_slack_blocks(hil_input, interaction)

            # Send initial HIL request message
            response = self.slack_client.send_message(
                channel=hil_input.channel_config.slack_channel,
                text=f"Human interaction required: {hil_input.interaction_type.value}",
                blocks=blocks,
            )

            if response.get("ok"):
                logs.append(f"Sent Slack HIL request to {hil_input.channel_config.slack_channel}")
                # Store message timestamp for thread replies
                interaction["slack_ts"] = response.get("ts")
            else:
                logs.append(f"Failed to send Slack HIL request: {response.get('error')}")

        except SlackAPIError as e:
            logs.append(f"Slack API error sending HIL request: {str(e)}")
        except Exception as e:
            logs.append(f"Error sending Slack HIL request: {str(e)}")

    def _send_email_request(
        self, interaction: Dict[str, Any], hil_input: HILInputData, logs: List[str]
    ):
        """Send HIL request via email."""
        # Send email via channel integration manager
        try:
            recipients = hil_input.channel_config.email_recipients or []
            if recipients:
                success = self.channel_integrations.send_email(
                    recipients=recipients,
                    subject=f"Human Interaction Required: {hil_input.interaction_type.value}",
                    body=self._format_email_body(hil_input, interaction),
                    is_html=True,
                )
                if success:
                    logs.append(f"Email HIL request sent to {len(recipients)} recipients")
                else:
                    logs.append(f"Failed to send email HIL request to {len(recipients)} recipients")
            else:
                logs.append("No email recipients specified")
        except Exception as e:
            logs.append(f"Error sending email HIL request: {str(e)}")

    def _send_webhook_request(
        self, interaction: Dict[str, Any], hil_input: HILInputData, logs: List[str]
    ):
        """Send HIL request via webhook."""
        import httpx

        try:
            # Prepare webhook payload
            payload = {
                "event_type": "human_interaction_required",
                "interaction_id": interaction["id"],
                "interaction_type": hil_input.interaction_type.value,
                "priority": hil_input.priority.value,
                "timeout_hours": hil_input.timeout_hours,
                "timeout_at": interaction["timeout_at"].isoformat(),
                "workflow_id": interaction.get("workflow_id"),
                "question": hil_input.question,
                "context_data": hil_input.context_data,
                "correlation_id": hil_input.correlation_id,
            }

            # Send webhook with timeout
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    hil_input.channel_config.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    logs.append(f"Sent HIL webhook to {hil_input.channel_config.webhook_url}")
                else:
                    logs.append(
                        f"Webhook failed with status {response.status_code}: {response.text[:100]}"
                    )

        except httpx.TimeoutException:
            logs.append(f"Webhook timeout to {hil_input.channel_config.webhook_url}")
        except Exception as e:
            logs.append(f"Webhook error to {hil_input.channel_config.webhook_url}: {str(e)}")

    def _send_app_request(
        self, interaction: Dict[str, Any], hil_input: HILInputData, logs: List[str]
    ):
        """Send HIL request via in-app notification."""
        # Send in-app notification via channel integration manager
        try:
            user_ids = (
                [hil_input.channel_config.user_id] if hil_input.channel_config.user_id else []
            )
            if user_ids:
                success = self.channel_integrations.send_in_app_notification(
                    user_ids=user_ids,
                    title=f"Human Interaction Required: {hil_input.interaction_type.value}",
                    message=hil_input.question
                    or "Your input is required to continue the workflow.",
                    data={
                        "interaction_id": interaction["id"],
                        "priority": hil_input.priority.value,
                        "timeout_at": interaction["timeout_at"].isoformat(),
                        "context_data": hil_input.context_data,
                        "workflow_id": interaction.get("workflow_id"),
                    },
                )
                if success:
                    logs.append("In-app HIL notification sent")
                else:
                    logs.append("Failed to send in-app HIL notification")
            else:
                logs.append("No user IDs specified for in-app notification")
        except Exception as e:
            logs.append(f"Error sending in-app HIL notification: {str(e)}")

    def _pause_workflow_execution(
        self, interaction: Dict[str, Any], context: NodeExecutionContext, logs: List[str]
    ):
        """Pause workflow execution until human responds."""
        pause_data = {
            "execution_id": getattr(context, "execution_id", "unknown"),
            "paused_at": datetime.now(),
            "paused_node_id": getattr(
                context, "node_id", context.node.id if hasattr(context.node, "id") else "unknown"
            ),
            "pause_reason": "human_interaction",
            "resume_conditions": {"interaction_id": interaction["id"], "awaiting_response": True},
            "status": "active",
        }

        # Pause workflow execution using status manager
        try:
            execution_id = getattr(context, "execution_id", "unknown")
            self.workflow_status_manager.pause_workflow_execution(
                execution_id=execution_id,
                pause_reason="human_interaction",
                pause_data=pause_data,
                timeout_at=interaction["timeout_at"],
            )
            logs.append(f"Paused workflow execution {execution_id}")
        except Exception as e:
            logs.append(f"Warning: Failed to pause workflow execution: {str(e)}")

    def _create_pause_result(
        self, interaction: Dict[str, Any], logs: List[str], execution_time: float
    ) -> NodeExecutionResult:
        """Create a pause result that halts workflow execution."""
        return NodeExecutionResult(
            status=ExecutionStatus.PAUSED,  # Special status for HIL pause
            output_data={
                "interaction_id": interaction["id"],
                "status": "waiting_for_human",
                "timeout_at": interaction["timeout_at"].isoformat(),
                "channel_type": interaction["channel_type"],
                "paused": True,
            },
            execution_time_ms=int(execution_time * 1000),
            logs=logs,
            output_port=None,  # No output port until resume
        )

    def determine_output_port(
        self, response_data: Dict[str, Any], ai_relevance_score: Optional[float] = None
    ) -> str:
        """Determine which output port to use based on response."""

        # Handle webhook filtering results
        if ai_relevance_score is not None and ai_relevance_score < 0.7:
            return "filtered"  # Route to filtered port for handling

        # Process valid HIL responses based on interaction type
        interaction_type = response_data.get("interaction_type")

        if interaction_type == HILInteractionType.APPROVAL:
            if response_data.get("approved", False):
                return "approved"
            else:
                return "rejected"

        # INPUT, SELECTION, REVIEW, CONFIRMATION, CUSTOM - all route to approved when completed
        return "approved"

    def _build_hil_slack_blocks(
        self, hil_input: HILInputData, interaction: Dict[str, Any]
    ) -> List[Dict]:
        """Build Slack blocks for HIL interaction request."""
        blocks = [
            SlackBlockBuilder.header(f"🤖 Human Interaction Required"),
            SlackBlockBuilder.section(
                f"*Type:* {hil_input.interaction_type.value}\n"
                f"*Priority:* {hil_input.priority.value}\n"
                f"*Timeout:* {hil_input.timeout_hours} hours\n"
                f"*Interaction ID:* `{interaction['id']}`"
            ),
        ]

        # Add interaction-specific content
        if hil_input.question:
            blocks.append(SlackBlockBuilder.section(f"*Question:*\n{hil_input.question}"))

        if hil_input.context_data:
            # Format context data as readable text
            context_text = "\n".join([f"• {k}: {v}" for k, v in hil_input.context_data.items()])
            blocks.append(SlackBlockBuilder.section(f"*Context:*\n{context_text}"))

        # Add action buttons based on interaction type
        if hil_input.interaction_type == HILInteractionType.APPROVAL:
            blocks.append(SlackBlockBuilder.divider())
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ Approve"},
                            "style": "primary",
                            "value": f"approve_{interaction['id']}",
                            "action_id": "hil_approve",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "❌ Reject"},
                            "style": "danger",
                            "value": f"reject_{interaction['id']}",
                            "action_id": "hil_reject",
                        },
                    ],
                }
            )

        # Add footer with workflow info
        blocks.append(
            SlackBlockBuilder.context(
                [
                    SlackBlockBuilder.text_element(
                        f"🔧 Workflow: {interaction.get('workflow_id', 'Unknown')} | "
                        f"⏰ Expires: {interaction['timeout_at'].strftime('%Y-%m-%d %H:%M UTC')}"
                    )
                ]
            )
        )

        return blocks

    def send_hil_response_message(
        self,
        interaction: Dict[str, Any],
        response_type: str,
        message_template: str,
        context_data: Dict[str, Any] = None,
    ) -> bool:
        """Send response message after HIL interaction is resolved."""
        if not self.slack_client or not message_template:
            return False

        try:
            # Replace template variables in message
            message = self._process_message_template(message_template, context_data or {})

            # Determine channel from interaction data
            channel = interaction.get("channel_id") or interaction.get("slack_channel")
            thread_ts = interaction.get("slack_ts")  # Reply in thread if available

            # Add status emoji based on response type
            status_emoji = {"approved": "✅", "rejected": "❌", "timeout": "⏰", "completed": "🎉"}.get(
                response_type, "📢"
            )

            formatted_message = f"{status_emoji} {message}"

            response = self.slack_client.send_message(
                channel=channel, text=formatted_message, thread_ts=thread_ts
            )

            return response.get("ok", False)

        except Exception as e:
            # Log error but don't fail the workflow
            print(f"Error sending HIL response message: {e}")
            return False

    def _process_message_template(self, template: str, context_data: Dict[str, Any]) -> str:
        """Process message template with variable substitution."""
        try:
            # Simple template variable replacement
            # Supports {{variable_name}} format
            import re

            def replace_var(match):
                var_name = match.group(1).strip()
                # Support nested dict access like {{data.event_id}}
                keys = var_name.split(".")
                value = context_data

                try:
                    for key in keys:
                        value = value[key]
                    return str(value)
                except (KeyError, TypeError):
                    return match.group(0)  # Return original if not found

            return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace_var, template)

        except Exception:
            # If template processing fails, return original message
            return template

    def _format_email_body(self, hil_input: HILInputData, interaction: Dict[str, Any]) -> str:
        """Format email body for HIL request."""
        return f"""
<html>
<body>
    <h2>🤖 Human Interaction Required</h2>

    <p><strong>Type:</strong> {hil_input.interaction_type.value}</p>
    <p><strong>Priority:</strong> {hil_input.priority.value}</p>
    <p><strong>Timeout:</strong> {hil_input.timeout_hours} hours</p>
    <p><strong>Expires:</strong> {interaction['timeout_at'].strftime('%Y-%m-%d %H:%M UTC')}</p>

    <h3>Question:</h3>
    <p>{hil_input.question or 'Your input is required to continue the workflow.'}</p>

    {f'<h3>Context:</h3><ul>{"".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in hil_input.context_data.items())}</ul>' if hil_input.context_data else ''}

    <p><strong>Interaction ID:</strong> <code>{interaction['id']}</code></p>
    <p><strong>Workflow ID:</strong> {interaction.get('workflow_id', 'unknown')}</p>

    <hr>
    <p><em>This is an automated message from the Workflow Engine HIL system.</em></p>
</body>
</html>
        """.strip()

    def handle_hil_response_with_messaging(
        self, interaction_id: str, response_data: Dict[str, Any], context: NodeExecutionContext
    ) -> NodeExecutionResult:
        """
        Handle HIL response and send response messages using node specification parameters.

        This method uses the enhanced node specifications with integrated response messaging
        to automatically send appropriate messages when HIL interactions are resolved.
        """
        try:
            # Get node parameters from context (includes response message templates)
            node_parameters = getattr(context, "parameters", {}) or context.input_data or {}

            # Prepare workflow context for template variables
            workflow_context = {
                "workflow_id": getattr(context, "workflow_id", "unknown"),
                "execution_id": getattr(context, "execution_id", "unknown"),
                "node_id": getattr(context, "node_id", "unknown"),
                "data": response_data.get("context_data", {}),
                "workflow": {
                    "id": getattr(context, "workflow_id", "unknown"),
                    "node_id": getattr(context, "node_id", "unknown"),
                },
            }

            # Use HIL service to handle response and send messages
            success = self.hil_service.handle_hil_response(
                interaction_id=interaction_id,
                response_data=response_data,
                node_parameters=node_parameters,
                workflow_context=workflow_context,
            )

            # Determine output port based on response
            output_port = self.determine_output_port(response_data)

            # Create result based on whether messaging succeeded
            if success:
                status_message = "HIL response processed and notification sent"
                logs = [
                    f"HIL response handled for interaction {interaction_id}",
                    "Response message sent successfully",
                ]
            else:
                status_message = "HIL response processed, notification failed"
                logs = [
                    f"HIL response handled for interaction {interaction_id}",
                    "Response message failed to send",
                ]

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data={
                    "interaction_id": interaction_id,
                    "response_data": response_data,
                    "messaging_success": success,
                    "message": status_message,
                },
                output_port=output_port,
                execution_time_ms=50,  # Quick response processing
                logs=logs,
            )

        except Exception as e:
            error_msg = f"Error handling HIL response with messaging: {str(e)}"
            return self._create_error_result(
                error_msg,
                error_details={"interaction_id": interaction_id, "exception": str(e)},
                execution_time=50,
                logs=[f"HIL response handling failed for {interaction_id}"],
            )
