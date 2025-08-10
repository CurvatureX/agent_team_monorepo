"""
Workflow Agent State Model
Explicit model for managing workflow_agent_states table
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing_extensions import Literal


class WorkflowStageEnum(str, Enum):
    """Workflow stages"""
    CLARIFICATION = "clarification"
    GAP_ANALYSIS = "gap_analysis"
    WORKFLOW_GENERATION = "workflow_generation"
    DEBUG = "debug"
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
        json_encoders={
            UUID: str,
            datetime: lambda v: int(v.timestamp() * 1000)
        }
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
    
    # Workflow result
    current_workflow: Optional[Dict[str, Any]] = None
    
    # Debug state
    debug_loop_count: int = Field(default=0, ge=0, le=2)  # Max 2 retries
    
    # Failure state
    final_error_message: Optional[str] = None
    
    # Validators
    @field_validator('stage', 'previous_stage')
    @classmethod
    def validate_stage(cls, v: Optional[str]) -> Optional[str]:
        """Validate stage values"""
        if v is not None and v not in WorkflowStageEnum.__members__.values():
            raise ValueError(f"Invalid stage: {v}")
        return v
    
    @field_validator('conversations', mode='before')
    @classmethod
    def validate_conversations(cls, v: Any) -> List[ConversationMessage]:
        """Convert raw conversation data to ConversationMessage objects"""
        if isinstance(v, str):
            import json
            v = json.loads(v)
        
        if isinstance(v, list):
            return [
                ConversationMessage(**msg) if isinstance(msg, dict) else msg
                for msg in v
            ]
        return v
    
    @field_validator('current_workflow', mode='before')
    @classmethod
    def validate_workflow(cls, v: Any) -> Optional[Dict[str, Any]]:
        """Validate and parse workflow JSON"""
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
            metadata=metadata or {}
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
        data = self.model_dump(mode='json')
        
        # Convert conversations to JSON string for database
        data['conversations'] = [
            msg.model_dump() if isinstance(msg, ConversationMessage) else msg
            for msg in self.conversations
        ]
        
        return data
    
    def to_workflow_state(self) -> Dict[str, Any]:
        """
        Convert to WorkflowState format for LangGraph.
        Adds derived fields that are not stored in DB.
        """
        state = self.to_db_dict()
        
        # Add derived fields for runtime use
        state['clarification_context'] = self._derive_clarification_context()
        state['gap_status'] = self._derive_gap_status()
        state['identified_gaps'] = self._derive_gaps()
        
        return state
    
    def _derive_clarification_context(self) -> Dict[str, Any]:
        """Derive clarification context from conversations"""
        # Extract pending questions from recent assistant messages
        pending_questions = []
        for msg in reversed(self.conversations):
            if msg.role == "assistant" and "?" in msg.text:
                # Simple heuristic - extract questions
                lines = msg.text.split('\n')
                questions = [line.strip() for line in lines if line.strip().endswith('?')]
                pending_questions.extend(questions)
                break  # Only look at most recent assistant message
        
        return {
            "purpose": "initial_intent",
            "collected_info": {},
            "pending_questions": pending_questions,
            "origin": "create"
        }
    
    def _derive_gap_status(self) -> str:
        """Derive gap status from conversation context"""
        # Look for gap-related keywords in recent conversations
        for msg in reversed(self.conversations[-5:]):  # Check last 5 messages
            text_lower = msg.text.lower()
            if "gap" in text_lower or "missing" in text_lower or "alternative" in text_lower:
                if "resolved" in text_lower or "fixed" in text_lower:
                    return "gap_resolved"
                elif "found" in text_lower or "identified" in text_lower:
                    return "has_gap"
        return "no_gap"
    
    def _derive_gaps(self) -> List[Dict[str, Any]]:
        """Derive identified gaps from conversation"""
        # This would need more sophisticated parsing in production
        # For now, return empty list as gaps are computed at runtime
        return []
    
    @classmethod
    def from_workflow_state(cls, state: Dict[str, Any]) -> "WorkflowAgentStateModel":
        """Create model from WorkflowState dict"""
        # Extract only the fields we persist
        return cls(
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            created_at=state.get("created_at", int(datetime.now().timestamp() * 1000)),
            updated_at=state.get("updated_at", int(datetime.now().timestamp() * 1000)),
            stage=state.get("stage", WorkflowStageEnum.CLARIFICATION),
            previous_stage=state.get("previous_stage"),
            intent_summary=state.get("intent_summary", ""),
            conversations=state.get("conversations", []),
            current_workflow=state.get("current_workflow"),
            debug_loop_count=state.get("debug_loop_count", 0),
            final_error_message=state.get("final_error_message")
        )