"""
Human-in-the-Loop (HIL) Node Data Models

This module defines the standard input and output data formats for Human-in-the-Loop nodes.
These models ensure consistent data exchange between HIL nodes and other workflow components.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class HILInteractionType(str, Enum):
    """Types of human interactions supported by HIL nodes."""

    APPROVAL = "approval"  # Binary approve/reject decisions
    INPUT = "input"  # Request specific data input from human
    REVIEW = "review"  # Request human review/feedback
    CONFIRMATION = "confirmation"  # Request confirmation of an action
    SELECTION = "selection"  # Choose from multiple options
    CUSTOM = "custom"  # Custom interaction type


class HILChannelType(str, Enum):
    """Communication channels supported for HIL interactions."""

    SLACK = "slack"  # Slack channel or direct message
    EMAIL = "email"  # Email notification with response links
    APP = "app"  # In-app notification/modal
    WEBHOOK = "webhook"  # Generic webhook-based interaction
    DISCORD = "discord"  # Discord channel interaction
    TELEGRAM = "telegram"  # Telegram bot interaction
    TEAMS = "teams"  # Microsoft Teams interaction


class HILPriority(str, Enum):
    """Priority levels for HIL interactions."""

    LOW = "low"  # Non-urgent, can wait days
    NORMAL = "normal"  # Standard business priority
    HIGH = "high"  # Urgent, needs attention within hours
    CRITICAL = "critical"  # Mission-critical, immediate attention


class HILStatus(str, Enum):
    """Status of HIL interactions."""

    PENDING = "pending"  # Waiting for human response
    RESPONDED = "responded"  # Human has provided response
    TIMEOUT = "timeout"  # Interaction timed out without response
    ERROR = "error"  # Error occurred during processing
    CANCELLED = "cancelled"  # Interaction was cancelled


# Input Data Models


class HILApprovalRequest(BaseModel):
    """Request data for approval-type HIL interactions."""

    title: str = Field(..., description="Title/subject of the approval request")
    description: str = Field(..., description="Detailed description of what needs approval")
    approval_options: List[str] = Field(
        default=["Approve", "Reject"], description="Available approval options"
    )
    approval_reason_required: bool = Field(
        default=False, description="Whether reason is required for the decision"
    )
    approval_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context data for approval"
    )


class HILInputField(BaseModel):
    """Definition of a required input field."""

    name: str = Field(..., description="Field name/identifier")
    label: str = Field(..., description="Human-readable field label")
    field_type: str = Field(
        default="text", description="Field type: text, number, email, date, select, etc."
    )
    required: bool = Field(default=True, description="Whether field is required")
    options: Optional[List[str]] = Field(default=None, description="Options for select-type fields")
    validation: Optional[Dict[str, Any]] = Field(
        default=None, description="Validation rules for the field"
    )
    placeholder: Optional[str] = Field(default=None, description="Placeholder text for the field")


class HILInputRequest(BaseModel):
    """Request data for input-type HIL interactions."""

    title: str = Field(..., description="Title of the input request")
    description: str = Field(..., description="Description of required input")
    fields: List[HILInputField] = Field(..., description="Required input fields")
    submit_button_text: str = Field(default="Submit", description="Text for submit button")


class HILSelectionOption(BaseModel):
    """Option for selection-type HIL interactions."""

    value: str = Field(..., description="Option value")
    label: str = Field(..., description="Human-readable option label")
    description: Optional[str] = Field(
        default=None, description="Detailed description of the option"
    )


class HILSelectionRequest(BaseModel):
    """Request data for selection-type HIL interactions."""

    title: str = Field(..., description="Title of the selection request")
    description: str = Field(..., description="Description of what to select")
    options: List[HILSelectionOption] = Field(..., description="Available options")
    multiple_selection: bool = Field(default=False, description="Allow multiple selections")
    min_selections: int = Field(default=1, description="Minimum number of selections required")
    max_selections: Optional[int] = Field(
        default=None, description="Maximum number of selections allowed"
    )


class HILChannelConfig(BaseModel):
    """Channel-specific configuration for HIL interactions."""

    channel_type: HILChannelType = Field(..., description="Type of communication channel")

    # Slack configuration
    slack_channel: Optional[str] = Field(default=None, description="Slack channel ID or name")
    slack_user_ids: Optional[List[str]] = Field(
        default=None, description="Specific Slack user IDs to notify"
    )

    # Email configuration
    email_recipients: Optional[List[str]] = Field(
        default=None, description="Email addresses to send notification"
    )
    email_subject: Optional[str] = Field(default=None, description="Email subject line")

    # App notification configuration
    app_notification_users: Optional[List[str]] = Field(
        default=None, description="User IDs to send in-app notifications"
    )

    # Generic webhook configuration
    webhook_url: Optional[str] = Field(
        default=None, description="Webhook URL for response callbacks"
    )
    webhook_headers: Optional[Dict[str, str]] = Field(
        default=None, description="Custom headers for webhook requests"
    )


class HILInputData(BaseModel):
    """Standard input data format for HIL nodes."""

    interaction_type: HILInteractionType = Field(
        ..., description="Type of human interaction required"
    )
    channel_config: HILChannelConfig = Field(..., description="Communication channel configuration")

    # Request-specific data (one of these will be populated based on interaction_type)
    approval_request: Optional[HILApprovalRequest] = Field(
        default=None, description="Approval request data"
    )
    input_request: Optional[HILInputRequest] = Field(default=None, description="Input request data")
    selection_request: Optional[HILSelectionRequest] = Field(
        default=None, description="Selection request data"
    )

    # Generic request data for custom interactions
    custom_request: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom request data for non-standard interactions"
    )

    # Workflow execution control
    workflow_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context from previous workflow nodes"
    )
    timeout_hours: int = Field(default=24, description="Hours to wait for response before timeout")
    continue_on_timeout: bool = Field(
        default=True, description="Whether to continue workflow execution on timeout"
    )
    timeout_default_response: Optional[Dict[str, Any]] = Field(
        default=None, description="Default response to use when timeout occurs"
    )

    # Configuration
    priority: HILPriority = Field(
        default=HILPriority.NORMAL, description="Priority level of the interaction"
    )

    # Metadata
    correlation_id: Optional[str] = Field(
        default=None, description="Correlation ID for tracking related requests"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="Tags for categorizing the interaction"
    )

    @field_validator("interaction_type", mode="before")
    @classmethod
    def validate_interaction_type_data(cls, v):
        """Ensure appropriate request data is provided for interaction type."""
        # This validation will be expanded in the actual implementation
        return v


# Output Data Models


class HILResponder(BaseModel):
    """Information about who responded to the HIL interaction."""

    user_id: Optional[str] = Field(default=None, description="User identifier")
    username: Optional[str] = Field(default=None, description="Username")
    display_name: Optional[str] = Field(default=None, description="Display name")
    email: Optional[str] = Field(default=None, description="Email address")
    platform: str = Field(..., description="Platform/channel where response came from")
    platform_user_id: Optional[str] = Field(default=None, description="Platform-specific user ID")


class HILApprovalResponse(BaseModel):
    """Response data for approval-type HIL interactions."""

    approved: bool = Field(..., description="Whether the request was approved")
    approval_option: str = Field(..., description="Selected approval option")
    reason: Optional[str] = Field(default=None, description="Reason provided for the decision")


class HILInputResponse(BaseModel):
    """Response data for input-type HIL interactions."""

    field_values: Dict[str, Any] = Field(..., description="Values for requested fields")
    additional_notes: Optional[str] = Field(
        default=None, description="Additional notes provided by user"
    )


class HILSelectionResponse(BaseModel):
    """Response data for selection-type HIL interactions."""

    selected_values: List[str] = Field(..., description="Selected option values")
    selected_labels: List[str] = Field(..., description="Selected option labels")


class HILResponseData(BaseModel):
    """Container for response data based on interaction type."""

    # Response-specific data (one of these will be populated)
    approval_response: Optional[HILApprovalResponse] = Field(
        default=None, description="Approval response data"
    )
    input_response: Optional[HILInputResponse] = Field(
        default=None, description="Input response data"
    )
    selection_response: Optional[HILSelectionResponse] = Field(
        default=None, description="Selection response data"
    )

    # Generic response data for custom interactions
    custom_response: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom response data"
    )

    # Raw response data for debugging/auditing
    raw_response: Optional[Dict[str, Any]] = Field(
        default=None, description="Raw response data from the channel"
    )


class HILOutputData(BaseModel):
    """Standard output data format for HIL nodes."""

    # Interaction metadata
    interaction_id: str = Field(..., description="Unique interaction identifier")
    interaction_type: HILInteractionType = Field(..., description="Type of interaction")
    status: HILStatus = Field(..., description="Final status of the interaction")

    # Response data
    response_data: HILResponseData = Field(..., description="Response data from human")
    responder: Optional[HILResponder] = Field(
        default=None, description="Information about who responded"
    )

    # Timing information
    requested_at: datetime = Field(..., description="When interaction was requested")
    responded_at: Optional[datetime] = Field(default=None, description="When response was received")
    timeout_at: datetime = Field(..., description="When interaction would timeout")
    processing_time_ms: Optional[int] = Field(
        default=None, description="Processing time in milliseconds"
    )

    # Channel information
    channel_type: HILChannelType = Field(..., description="Channel used for interaction")
    channel_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Channel-specific metadata"
    )

    # AI classification metadata (for webhook responses)
    ai_confidence_score: Optional[float] = Field(
        default=None, description="AI confidence score for response relevance (0.0-1.0)"
    )
    ai_reasoning: Optional[str] = Field(
        default=None, description="AI explanation of response relevance"
    )

    # Workflow context
    workflow_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Context passed through from input"
    )

    # Metadata
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracking")
    tags: Optional[List[str]] = Field(default=None, description="Tags associated with interaction")


class HILTimeoutData(BaseModel):
    """Output data for timed-out HIL interactions."""

    interaction_id: str = Field(..., description="Unique interaction identifier")
    interaction_type: HILInteractionType = Field(..., description="Type of interaction")
    timeout: bool = Field(default=True, description="Indicates this is a timeout")
    timeout_hours: float = Field(..., description="Hours waited before timeout")

    # Timing information
    requested_at: datetime = Field(..., description="When interaction was requested")
    timeout_at: datetime = Field(..., description="When timeout occurred")

    # Channel information
    channel_type: HILChannelType = Field(..., description="Channel used for interaction")

    # Original request context
    original_request: Optional[Dict[str, Any]] = Field(
        default=None, description="Original request data for reference"
    )

    # Metadata
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracking")


class HILErrorData(BaseModel):
    """Output data for HIL interactions that encountered errors."""

    interaction_id: Optional[str] = Field(
        default=None, description="Interaction identifier if available"
    )
    interaction_type: Optional[HILInteractionType] = Field(
        default=None, description="Type of interaction if known"
    )
    error: bool = Field(default=True, description="Indicates this is an error")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )

    # Channel information if available
    channel_type: Optional[HILChannelType] = Field(
        default=None, description="Channel where error occurred"
    )

    # Timestamp
    error_timestamp: datetime = Field(
        default_factory=datetime.now, description="When error occurred"
    )

    # Metadata
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracking")


class HILFilteredData(BaseModel):
    """Output data for webhook messages filtered as unrelated."""

    interaction_id: Optional[str] = Field(
        default=None, description="HIL interaction ID if available"
    )
    webhook_id: str = Field(..., description="Webhook response identifier")
    filtered: bool = Field(default=True, description="Indicates this message was filtered")

    # AI classification results
    ai_relevance_score: float = Field(..., description="AI confidence score (0.0-1.0)")
    ai_reasoning: str = Field(..., description="AI explanation for filtering decision")

    # Original webhook data
    raw_webhook_payload: Dict[str, Any] = Field(..., description="Original webhook payload")
    source_channel: str = Field(..., description="Channel where message originated")

    # Timing
    filtered_at: datetime = Field(
        default_factory=datetime.now, description="When message was filtered"
    )

    # Context
    workflow_id: Optional[str] = Field(default=None, description="Associated workflow ID")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracking")


# HIL Response Processing Models


class HILIncomingResponseData(BaseModel):
    """Data structure for incoming HIL responses from webhooks."""

    response_id: str = Field(..., description="Unique HIL response identifier")
    workflow_id: str = Field(..., description="Associated workflow identifier")
    source_channel: str = Field(..., description="Source channel of the response")
    raw_payload: Dict[str, Any] = Field(..., description="Complete response payload")
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="HTTP headers from response request"
    )

    # Processing metadata
    received_at: datetime = Field(
        default_factory=datetime.now, description="When response was received"
    )
    processed_at: Optional[datetime] = Field(
        default=None, description="When response was processed"
    )
    processing_status: str = Field(default="unprocessed", description="Processing status")

    # AI classification results
    matched_interaction_id: Optional[str] = Field(
        default=None, description="ID of matched HIL interaction"
    )
    ai_relevance_score: Optional[float] = Field(
        default=None, description="AI confidence score for relevance"
    )
    ai_reasoning: Optional[str] = Field(
        default=None, description="AI explanation of relevance decision"
    )


# Utility Types

HILOutput = Union[HILOutputData, HILTimeoutData, HILErrorData, HILFilteredData]
"""Union type for all possible HIL node outputs."""

HILRequest = Union[HILApprovalRequest, HILInputRequest, HILSelectionRequest]
"""Union type for all HIL request types."""

HILResponse = Union[HILApprovalResponse, HILInputResponse, HILSelectionResponse]
"""Union type for all HIL response types."""
