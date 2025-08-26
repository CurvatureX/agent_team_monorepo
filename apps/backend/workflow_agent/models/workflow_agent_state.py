"""
Workflow Agent State Model
Explicit model for managing workflow_agent_states table
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import Literal


class WorkflowStageEnum(str, Enum):
    """Workflow stages"""

    CLARIFICATION = "clarification"
    WORKFLOW_GENERATION = "workflow_generation"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationMessage(BaseModel):
    """Conversation message structure"""

    role: Literal["user", "assistant", "system"]
    text: str
    timestamp: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowAgentStateModel(BaseModel):
    """
    Pydantic model for workflow_agent_states table.
    Provides validation, serialization, and type safety.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={UUID: str, datetime: lambda v: int(v.timestamp() * 1000)},
    )

    # Primary key
    id: UUID = Field(default_factory=uuid4)

    # Core identity
    session_id: str = Field(..., min_length=1, max_length=255)
    user_id: Optional[str] = Field(None, max_length=255)

    # Timestamps (stored as milliseconds)
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))

    # Stage tracking
    stage: WorkflowStageEnum = Field(default=WorkflowStageEnum.CLARIFICATION)
    previous_stage: Optional[WorkflowStageEnum] = None

    # Core persistent data
    intent_summary: str = Field(default="")
    conversations: List[ConversationMessage] = Field(default_factory=list)

    # Debug state (matches DDL: debug_result as text, debug_loop_count as int)
    debug_result: Optional[str] = None  # Stored as text in DB
    debug_loop_count: int = Field(default=0, ge=0, le=2)  # Max 2 retries

    # Workflow data (matches DDL)
    template_workflow: Optional[Dict[str, Any]] = None  # Future use for templates
    workflow_id: Optional[str] = None  # ID of created workflow in workflow_engine

    # Failure state
    final_error_message: Optional[str] = None

    # Validators
    @field_validator("stage", "previous_stage")
    @classmethod
    def validate_stage(cls, v: Optional[str]) -> Optional[str]:
        """Validate stage values"""
        if v is not None and v not in WorkflowStageEnum.__members__.values():
            raise ValueError(f"Invalid stage: {v}")
        return v

    @field_validator("conversations", mode="before")
    @classmethod
    def validate_conversations(cls, v: Any) -> List[ConversationMessage]:
        """Convert raw conversation data to ConversationMessage objects"""
        if isinstance(v, str):
            import json

            v = json.loads(v)

        if isinstance(v, list):
            return [ConversationMessage(**msg) if isinstance(msg, dict) else msg for msg in v]
        return v

    @field_validator("template_workflow", mode="before")
    @classmethod
    def validate_template_workflow(cls, v: Any) -> Optional[Dict[str, Any]]:
        """Validate and parse template workflow JSON"""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            return json.loads(v)
        return v

    # Helper methods
    def add_conversation(self, role: str, text: str, metadata: Optional[Dict] = None):
        """Add a conversation message"""
        msg = ConversationMessage(
            role=role,
            text=text,
            timestamp=int(datetime.now().timestamp() * 1000),
            metadata=metadata or {},
        )
        self.conversations.append(msg)
        self.updated_at = int(datetime.now().timestamp() * 1000)

    def update_stage(self, new_stage: WorkflowStageEnum):
        """Update stage and track previous stage"""
        if new_stage != self.stage:
            self.previous_stage = self.stage
            self.stage = new_stage
            self.updated_at = int(datetime.now().timestamp() * 1000)

    def mark_failed(self, error_message: str):
        """Mark workflow as failed with error message"""
        self.stage = WorkflowStageEnum.FAILED
        self.final_error_message = error_message
        self.updated_at = int(datetime.now().timestamp() * 1000)

    def increment_debug_count(self) -> bool:
        """Increment debug count, return False if max reached"""
        if self.debug_loop_count >= 2:
            return False
        self.debug_loop_count += 1
        self.updated_at = int(datetime.now().timestamp() * 1000)
        return True

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion"""
        data = self.model_dump(mode="json")

        # Convert conversations to JSON string for database
        data["conversations"] = [
            msg.model_dump() if isinstance(msg, ConversationMessage) else msg
            for msg in self.conversations
        ]

        return data

    def to_workflow_state(self) -> Dict[str, Any]:
        """
        Convert to WorkflowState format for LangGraph.
        Adds derived fields that are not stored in DB but needed at runtime.
        """
        state = self.to_db_dict()

        # Add derived fields for runtime use
        state["clarification_context"] = self._derive_clarification_context()

        # current_workflow is NOT stored in DB - it's a runtime field
        # It gets populated during workflow generation and passed to debug node in memory
        # We don't initialize it here since it's transient data

        # Convert debug_result from text to dict if needed (for LangGraph compatibility)
        if state.get("debug_result") and isinstance(state["debug_result"], str):
            try:
                import json

                state["debug_result"] = json.loads(state["debug_result"])
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, convert to simple dict format
                state["debug_result"] = {
                    "success": False,
                    "error": state["debug_result"],
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }

        return state

    def _derive_clarification_context(self) -> Dict[str, Any]:
        """Derive clarification context from conversations"""
        # Extract pending questions from recent assistant messages
        pending_questions = []
        for msg in reversed(self.conversations):
            if msg.role == "assistant" and "?" in msg.text:
                # Simple heuristic - extract questions
                lines = msg.text.split("\n")
                questions = [line.strip() for line in lines if line.strip().endswith("?")]
                pending_questions.extend(questions)
                break  # Only look at most recent assistant message

        return {
            "purpose": "initial_intent",
            "collected_info": {},
            "pending_questions": pending_questions,
            "origin": "create",
        }

    @classmethod
    def from_workflow_state(cls, state: Dict[str, Any]) -> "WorkflowAgentStateModel":
        """Create model from WorkflowState dict - only persist fields that belong in DB"""
        # Convert debug_result to text if it's a dict (for DB storage)
        debug_result = state.get("debug_result")
        if isinstance(debug_result, dict):
            import json

            debug_result = json.dumps(debug_result)

        return cls(
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            created_at=state.get("created_at", int(datetime.now().timestamp() * 1000)),
            updated_at=state.get("updated_at", int(datetime.now().timestamp() * 1000)),
            stage=state.get("stage", WorkflowStageEnum.CLARIFICATION),
            previous_stage=state.get("previous_stage"),
            intent_summary=state.get("intent_summary", ""),
            conversations=state.get("conversations", []),
            debug_result=debug_result,
            debug_loop_count=state.get("debug_loop_count", 0),
            template_workflow=state.get("template_workflow"),  # For future template support
            workflow_id=state.get("workflow_id"),  # Critical: persist the workflow_id
            final_error_message=state.get("final_error_message")
            # NOTE: current_workflow is NOT persisted - it's transient runtime data
        )
