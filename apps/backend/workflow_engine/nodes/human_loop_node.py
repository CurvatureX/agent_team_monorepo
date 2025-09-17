"""Human Loop Node Executor."""
from datetime import datetime
from typing import Any, Dict, Optional

from shared.models.node_enums import HumanLoopSubtype, NodeType

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.HUMAN_IN_THE_LOOP.value)
class HumanLoopNodeExecutor(BaseNodeExecutor):
    """Executor for Human-in-the-Loop nodes."""

    def __init__(self, node_type: str = NodeType.HUMAN_IN_THE_LOOP.value, subtype: str = None):
        super().__init__(node_type, subtype)

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute human-in-the-loop node."""
        interaction_type = self.subtype or context.get_parameter("interaction_type", "approval")
        timeout_seconds_param = context.get_parameter("timeout_seconds", 300)  # 5 minutes default
        timeout_seconds = (
            int(timeout_seconds_param)
            if isinstance(timeout_seconds_param, str)
            else timeout_seconds_param
        )

        self.log_execution(context, f"Executing HIL node: {interaction_type}")

        try:
            # Handle different interaction types using enum values
            if (
                interaction_type == HumanLoopSubtype.IN_APP_APPROVAL.value
                or interaction_type.lower() == "approval"
            ):
                return await self._handle_approval_request(context, timeout_seconds)
            elif (
                interaction_type == HumanLoopSubtype.FORM_SUBMISSION.value
                or interaction_type.lower() == "input"
            ):
                return await self._handle_input_request(context, timeout_seconds)
            elif interaction_type.lower() == "selection":
                return await self._handle_selection_request(context, timeout_seconds)
            elif (
                interaction_type == HumanLoopSubtype.MANUAL_REVIEW.value
                or interaction_type.lower() == "review"
            ):
                return await self._handle_review_request(context, timeout_seconds)
            else:
                return await self._handle_generic_interaction(
                    context, interaction_type, timeout_seconds
                )

        except Exception as e:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Human-in-the-loop execution failed: {str(e)}",
                error_details={"interaction_type": interaction_type},
            )

    async def _handle_approval_request(
        self, context: NodeExecutionContext, timeout_seconds: int
    ) -> NodeExecutionResult:
        """Handle approval request interaction."""
        title = context.get_parameter("title", "Approval Required")
        description = context.get_parameter("description", "Please review and approve this request")
        approval_options = context.get_parameter("approval_options", ["Approve", "Reject"])
        reason_required = context.get_parameter("reason_required", False)

        # Create HIL request
        hil_request = await self._create_hil_request(
            context=context,
            interaction_type="approval",
            title=title,
            description=description,
            timeout_seconds=timeout_seconds,
            additional_data={
                "approval_options": approval_options,
                "reason_required": reason_required,
                "workflow_data": context.input_data,
            },
        )

        # For real implementation, this would:
        # 1. Store the request in database
        # 2. Send notifications via configured channels (Slack, email, etc.)
        # 3. Wait for response or timeout
        # 4. Return the human response

        self.log_execution(context, f"Created approval request: {hil_request['id']}")

        # Simulate approval response (in real implementation, this would wait for actual human response)
        mock_response = {
            "approved": True,
            "selected_option": "Approve",
            "reason": "Automated approval for testing",
            "responded_by": "system",
            "responded_at": datetime.now().isoformat(),
        }

        output_data = {
            "interaction_type": "approval",
            "hil_request_id": hil_request["id"],
            "title": title,
            "description": description,
            "timeout_seconds": timeout_seconds,
            "human_response": mock_response,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "human_in_the_loop",
                "interaction_type": "approval",
                "hil_request_id": hil_request["id"],
            },
        )

    async def _handle_input_request(
        self, context: NodeExecutionContext, timeout_seconds: int
    ) -> NodeExecutionResult:
        """Handle input request interaction."""
        title = context.get_parameter("title", "Input Required")
        description = context.get_parameter(
            "description", "Please provide the requested information"
        )
        input_fields = context.get_parameter(
            "input_fields",
            [{"name": "response", "label": "Response", "type": "text", "required": True}],
        )

        # Create HIL request
        hil_request = await self._create_hil_request(
            context=context,
            interaction_type="input",
            title=title,
            description=description,
            timeout_seconds=timeout_seconds,
            additional_data={"input_fields": input_fields, "workflow_data": context.input_data},
        )

        self.log_execution(context, f"Created input request: {hil_request['id']}")

        # Simulate input response
        mock_response = {
            "inputs": {field["name"]: f"Mock {field['label'].lower()}" for field in input_fields},
            "responded_by": "system",
            "responded_at": datetime.now().isoformat(),
        }

        output_data = {
            "interaction_type": "input",
            "hil_request_id": hil_request["id"],
            "title": title,
            "description": description,
            "input_fields": input_fields,
            "timeout_seconds": timeout_seconds,
            "human_response": mock_response,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "human_in_the_loop",
                "interaction_type": "input",
                "hil_request_id": hil_request["id"],
            },
        )

    async def _handle_selection_request(
        self, context: NodeExecutionContext, timeout_seconds: int
    ) -> NodeExecutionResult:
        """Handle selection request interaction."""
        title = context.get_parameter("title", "Selection Required")
        description = context.get_parameter(
            "description", "Please select from the available options"
        )
        options = context.get_parameter(
            "options",
            [{"value": "option1", "label": "Option 1"}, {"value": "option2", "label": "Option 2"}],
        )
        multiple_selection = context.get_parameter("multiple_selection", False)

        # Create HIL request
        hil_request = await self._create_hil_request(
            context=context,
            interaction_type="selection",
            title=title,
            description=description,
            timeout_seconds=timeout_seconds,
            additional_data={
                "options": options,
                "multiple_selection": multiple_selection,
                "workflow_data": context.input_data,
            },
        )

        self.log_execution(context, f"Created selection request: {hil_request['id']}")

        # Simulate selection response
        if multiple_selection:
            selected = (
                [options[0]["value"], options[1]["value"]]
                if len(options) > 1
                else [options[0]["value"]]
            )
        else:
            selected = options[0]["value"] if options else None

        mock_response = {
            "selected": selected,
            "responded_by": "system",
            "responded_at": datetime.now().isoformat(),
        }

        output_data = {
            "interaction_type": "selection",
            "hil_request_id": hil_request["id"],
            "title": title,
            "description": description,
            "options": options,
            "multiple_selection": multiple_selection,
            "timeout_seconds": timeout_seconds,
            "human_response": mock_response,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "human_in_the_loop",
                "interaction_type": "selection",
                "hil_request_id": hil_request["id"],
            },
        )

    async def _handle_review_request(
        self, context: NodeExecutionContext, timeout_seconds: int
    ) -> NodeExecutionResult:
        """Handle review request interaction."""
        title = context.get_parameter("title", "Review Required")
        description = context.get_parameter("description", "Please review the following content")
        content_to_review = context.get_parameter("content_to_review", context.input_data)
        review_criteria = context.get_parameter("review_criteria", [])

        # Create HIL request
        hil_request = await self._create_hil_request(
            context=context,
            interaction_type="review",
            title=title,
            description=description,
            timeout_seconds=timeout_seconds,
            additional_data={
                "content_to_review": content_to_review,
                "review_criteria": review_criteria,
                "workflow_data": context.input_data,
            },
        )

        self.log_execution(context, f"Created review request: {hil_request['id']}")

        # Simulate review response
        mock_response = {
            "approved": True,
            "review_comments": "Content looks good, approved for processing",
            "rating": 4,
            "responded_by": "system",
            "responded_at": datetime.now().isoformat(),
        }

        output_data = {
            "interaction_type": "review",
            "hil_request_id": hil_request["id"],
            "title": title,
            "description": description,
            "content_to_review": content_to_review,
            "review_criteria": review_criteria,
            "timeout_seconds": timeout_seconds,
            "human_response": mock_response,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "human_in_the_loop",
                "interaction_type": "review",
                "hil_request_id": hil_request["id"],
            },
        )

    async def _handle_generic_interaction(
        self, context: NodeExecutionContext, interaction_type: str, timeout_seconds: int
    ) -> NodeExecutionResult:
        """Handle generic/unknown interaction types."""
        title = context.get_parameter("title", f"{interaction_type.title()} Required")
        description = context.get_parameter(
            "description", f"Please complete the {interaction_type} interaction"
        )

        # Create HIL request
        hil_request = await self._create_hil_request(
            context=context,
            interaction_type=interaction_type,
            title=title,
            description=description,
            timeout_seconds=timeout_seconds,
            additional_data={"workflow_data": context.input_data},
        )

        self.log_execution(context, f"Created {interaction_type} request: {hil_request['id']}")

        # Simulate generic response
        mock_response = {
            "completed": True,
            "result": f"Generic {interaction_type} interaction completed",
            "responded_by": "system",
            "responded_at": datetime.now().isoformat(),
        }

        output_data = {
            "interaction_type": interaction_type,
            "hil_request_id": hil_request["id"],
            "title": title,
            "description": description,
            "timeout_seconds": timeout_seconds,
            "human_response": mock_response,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "human_in_the_loop",
                "interaction_type": interaction_type,
                "hil_request_id": hil_request["id"],
            },
        )

    async def _create_hil_request(
        self,
        context: NodeExecutionContext,
        interaction_type: str,
        title: str,
        description: str,
        timeout_seconds: int,
        additional_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create HIL request record."""
        import uuid

        # In real implementation, this would:
        # 1. Store in database (execution_logs or hil_requests table)
        # 2. Send notifications via ChannelIntegrationManager
        # 3. Set up timeout handling
        # 4. Return the stored request with ID

        hil_request_id = str(uuid.uuid4())

        hil_request = {
            "id": hil_request_id,
            "execution_id": context.execution_id,
            "workflow_id": context.workflow_id,
            "node_id": context.node_id,
            "interaction_type": interaction_type,
            "title": title,
            "description": description,
            "timeout_seconds": timeout_seconds,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "expires_at": datetime.now().isoformat(),  # Add timeout_seconds
            "channels": context.get_parameter("channels", ["email"]),  # Default to email
            "priority": context.get_parameter("priority", "medium"),
            "additional_data": additional_data,
        }

        # In real implementation, save to database here
        self.log_execution(context, f"HIL request created: {hil_request_id}")

        return hil_request

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate HIL node parameters."""
        interaction_type = self.subtype or context.get_parameter("interaction_type", "approval")

        # Validate specific interaction types
        if interaction_type == "selection":
            options = context.get_parameter("options", [])
            if not options or not isinstance(options, list):
                return False, "Selection interactions require 'options' parameter (list of options)"

        elif interaction_type == "input":
            input_fields = context.get_parameter("input_fields", [])
            if not input_fields or not isinstance(input_fields, list):
                return (
                    False,
                    "Input interactions require 'input_fields' parameter (list of field definitions)",
                )

        # Check timeout
        timeout_seconds_param = context.get_parameter("timeout_seconds", 300)
        try:
            timeout_seconds = (
                int(timeout_seconds_param)
                if isinstance(timeout_seconds_param, str)
                else timeout_seconds_param
            )
            if timeout_seconds <= 0:
                return False, "timeout_seconds must be a positive number"
        except (ValueError, TypeError):
            return False, "timeout_seconds must be a valid number"

        return True, ""
