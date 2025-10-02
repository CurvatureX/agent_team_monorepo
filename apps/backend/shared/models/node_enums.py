"""
Node Type and Subtype Enums - Single Source of Truth

This module defines the authoritative enums for all node types and subtypes
used across the entire system. All services MUST use these enums directly.

NO conversion functions - these ARE the standard.
"""

from enum import Enum
from typing import Any, Dict, List, Set


class NodeType(str, Enum):
    """
    Core Node Types - Based on database schema constraints

    These are the 8 fundamental node categories in the workflow engine.

    🎯 WORKFLOW GENERATION GUIDANCE:
    - HUMAN_IN_THE_LOOP: Has built-in AI response analysis - DO NOT add separate IF/AI_AGENT nodes
    - AI_AGENT: For general AI processing - NOT needed for HIL response analysis
    - FLOW (IF): For business logic conditions - NOT needed for HIL response classification
    """

    TRIGGER = "TRIGGER"
    AI_AGENT = "AI_AGENT"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    ACTION = "ACTION"
    FLOW = "FLOW"
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"  # 🤖 Built-in AI response analysis capabilities
    TOOL = "TOOL"
    MEMORY = "MEMORY"


class TriggerSubtype(str, Enum):
    """Trigger Node Subtypes - All supported trigger mechanisms"""

    MANUAL = "MANUAL"
    WEBHOOK = "WEBHOOK"
    CRON = "CRON"
    EMAIL = "EMAIL"
    GITHUB = "GITHUB"
    SLACK = "SLACK"


class AIAgentSubtype(str, Enum):
    """AI Agent Node Subtypes - All AI model integrations"""

    # OpenAI Models
    OPENAI_CHATGPT = "OPENAI_CHATGPT"

    # Anthropic Models
    ANTHROPIC_CLAUDE = "ANTHROPIC_CLAUDE"

    # Google Models
    GOOGLE_GEMINI = "GOOGLE_GEMINI"


class OpenAIModel(str, Enum):
    """OpenAI Model Versions for OPENAI_CHATGPT subtype"""

    # GPT-5 Models (2025 - Latest)
    GPT_5 = "gpt-5"  # $1.25 input, $0.125 cached, $10.00 output
    GPT_5_MINI = "gpt-5-mini"  # $0.25 input, $0.025 cached, $2.00 output
    GPT_5_NANO = "gpt-5-nano"  # $0.05 input, $0.005 cached, $0.40 output
    GPT_5_MINI_0807 = "gpt-5-mini-2025-08-07"
    GPT_5_CHAT_LATEST = "gpt-5-chat-latest"  # $1.25 input, $0.125 cached, $10.00 output

    # GPT-4.1 Models
    GPT_4_1 = "gpt-4.1"  # $2.00 input, $0.50 cached, $8.00 output
    GPT_4_1_MINI = "gpt-4.1-mini"  # $0.40 input, $0.10 cached, $1.60 output


class AnthropicModel(str, Enum):
    """Anthropic Claude Model Versions for ANTHROPIC_CLAUDE subtype"""

    # Claude Sonnet 4 - Optimal balance of intelligence, cost, and speed
    # Output: ≤200K $15/MTok, >200K $22.50/MTok
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"

    # Claude Haiku 3.5 - Fastest, most cost-effective model
    # Output: $4/MTok
    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-20241022"


class GoogleGeminiModel(str, Enum):
    """Google Gemini Model Versions for GOOGLE_GEMINI subtype"""

    # Gemini 2.5 Pro - State-of-the-art multipurpose model, excels at coding and complex reasoning
    # Input: ≤200k $1.25/MTok, >200k $2.50/MTok | Output: ≤200k $10.00/MTok, >200k $15.00/MTok
    # Caching: ≤200k $0.31/MTok, >200k $0.625/MTok | Storage: $4.50/MTok/hour
    GEMINI_2_5_PRO = "gemini-2.5-pro"

    # Gemini 2.5 Flash - First hybrid reasoning model, 1M context, thinking budgets
    # Input: $0.30 text/image/video, $1.00 audio | Output: $2.50/MTok
    # Caching: $0.075 text/image/video, $0.25 audio | Storage: $1.00/MTok/hour
    GEMINI_2_5_FLASH = "gemini-2.5-flash"

    # Gemini 2.5 Flash-Lite - Smallest, most cost-effective, built for scale
    # Input: $0.10 text/image/video, $0.30 audio | Output: $0.40/MTok
    # Caching: $0.025 text/image/video, $0.125 audio | Storage: $1.00/MTok/hour
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"


class ExternalActionSubtype(str, Enum):
    """External Action Node Subtypes - Third-party integrations"""

    # Generic Actions
    API_CALL = "API_CALL"
    WEBHOOK = "WEBHOOK"
    NOTIFICATION = "NOTIFICATION"

    # Communication
    SLACK = "SLACK"
    DISCORD_ACTION = "DISCORD_ACTION"
    TELEGRAM_ACTION = "TELEGRAM_ACTION"
    EMAIL = "EMAIL"

    # Development
    GITHUB = "GITHUB"
    GITLAB_ACTION = "GITLAB_ACTION"
    JIRA_ACTION = "JIRA_ACTION"

    # Productivity
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    TRELLO = "TRELLO"
    NOTION = "NOTION"

    # Web Scraping & Data Extraction
    FIRECRAWL = "FIRECRAWL"

    # Cloud Services
    AWS_ACTION = "AWS_ACTION"
    GCP_ACTION = "GCP_ACTION"
    AZURE_ACTION = "AZURE_ACTION"

    # Databases
    POSTGRES_ACTION = "POSTGRES_ACTION"
    MYSQL_ACTION = "MYSQL_ACTION"
    MONGODB_ACTION = "MONGODB_ACTION"


class ActionSubtype(str, Enum):
    """Action Node Subtypes - Core system actions"""

    # Code Execution
    RUN_CODE = "RUN_CODE"
    EXECUTE_SCRIPT = "EXECUTE_SCRIPT"

    # Data Operations
    DATA_TRANSFORMATION = "DATA_TRANSFORMATION"
    DATA_VALIDATION = "DATA_VALIDATION"
    DATA_FORMATTING = "DATA_FORMATTING"

    # File Operations
    FILE_OPERATION = "FILE_OPERATION"
    FILE_UPLOAD = "FILE_UPLOAD"
    FILE_DOWNLOAD = "FILE_DOWNLOAD"

    # HTTP Operations
    HTTP_REQUEST = "HTTP_REQUEST"
    WEBHOOK_CALL = "WEBHOOK_CALL"

    # Database Operations
    DATABASE_QUERY = "DATABASE_QUERY"
    DATABASE_OPERATION = "DATABASE_OPERATION"

    WEB_SEARCH = "WEB_SEARCH"


class FlowSubtype(str, Enum):
    """Flow Control Node Subtypes - Logic and control flow"""

    # Conditional Logic
    IF = "IF"

    # Loops
    LOOP = "LOOP"
    FOR_EACH = "FOR_EACH"
    WHILE = "WHILE"

    # Data Flow
    MERGE = "MERGE"
    SPLIT = "SPLIT"
    FILTER = "FILTER"
    SORT = "SORT"

    # Timing
    WAIT = "WAIT"
    DELAY = "DELAY"
    TIMEOUT = "TIMEOUT"


class HumanLoopSubtype(str, Enum):
    """
    Human-in-the-Loop Node Subtypes - Human interaction points with built-in AI response analysis

    🎯 IMPORTANT FOR WORKFLOW GENERATION:
    All HIL nodes have integrated AI-powered response analysis capabilities that:
    - Automatically classify user responses as confirmed/rejected/unrelated
    - Eliminate the need for separate IF nodes or AI_AGENT nodes for response analysis
    - Provide multiple output ports based on AI classification (confirmed, rejected, unrelated, timeout)
    - Handle response messaging automatically based on classification results

    ❌ DO NOT CREATE: Separate IF nodes, AI_AGENT nodes, or EXTERNAL_ACTION nodes for HIL response handling
    ✅ USE INSTEAD: Single HIL node with built-in response analysis and integrated messaging
    """

    # Email Interactions - with AI response analysis for email replies
    GMAIL_INTERACTION = "GMAIL_INTERACTION"
    OUTLOOK_INTERACTION = "OUTLOOK_INTERACTION"

    # Chat Interactions - with AI response analysis for chat messages
    SLACK_INTERACTION = "SLACK_INTERACTION"
    DISCORD_INTERACTION = "DISCORD_INTERACTION"
    TELEGRAM_INTERACTION = "TELEGRAM_INTERACTION"
    TEAMS_INTERACTION = "TEAMS_INTERACTION"

    # App Interactions - with AI response analysis for in-app interactions
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ToolSubtype(str, Enum):
    """Tool Node Subtypes - External tools and utilities"""

    # MCP Tools
    NOTION_MCP_TOOL = "NOTION_MCP_TOOL"
    SLACK_MCP_TOOL = "SLACK_MCP_TOOL"
    DISCORD_MCP_TOOL = "DISCORD_MCP_TOOL"
    GOOGLE_CALENDAR_MCP_TOOL = "GOOGLE_CALENDAR_MCP_TOOL"
    FIRECRAWL_MCP_TOOL = "FIRECRAWL_MCP_TOOL"

    # Calendar Tools
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR_TOOL"
    OUTLOOK_CALENDAR = "OUTLOOK_CALENDAR_TOOL"
    CALENDAR_GENERIC = "CALENDAR_GENERIC_TOOL"

    # Email Tools
    EMAIL_TOOL = "EMAIL_TOOL"
    GMAIL_TOOL = "GMAIL_TOOL"

    # HTTP Tools
    HTTP_CLIENT = "HTTP_CLIENT"

    # File Tools
    FILE_PROCESSOR = "FILE_PROCESSOR"
    IMAGE_PROCESSOR = "IMAGE_PROCESSOR"

    CODE_TOOL = "CODE_TOOL"


class MemorySubtype(str, Enum):
    """Memory Node Subtypes - Memory storage types for LLM context"""

    # Conversation Memory Types
    CONVERSATION_BUFFER = "CONVERSATION_BUFFER"
    CONVERSATION_SUMMARY = "CONVERSATION_SUMMARY"

    # Vector Database Memory
    VECTOR_DATABASE = "VECTOR_DATABASE"

    # Key-Value Memory
    KEY_VALUE_STORE = "KEY_VALUE_STORE"

    # Document Memory
    DOCUMENT_STORE = "DOCUMENT_STORE"

    # Advanced Memory Types
    ENTITY_MEMORY = "ENTITY_MEMORY"
    EPISODIC_MEMORY = "EPISODIC_MEMORY"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    GRAPH_MEMORY = "GRAPH_MEMORY"


# Validation mapping - defines which subtypes are valid for each node type
VALID_SUBTYPES: Dict[NodeType, Set[str]] = {
    NodeType.TRIGGER: {s.value for s in TriggerSubtype},
    NodeType.AI_AGENT: {s.value for s in AIAgentSubtype},
    NodeType.EXTERNAL_ACTION: {s.value for s in ExternalActionSubtype},
    NodeType.ACTION: {s.value for s in ActionSubtype},
    NodeType.FLOW: {s.value for s in FlowSubtype},
    NodeType.HUMAN_IN_THE_LOOP: {s.value for s in HumanLoopSubtype},
    NodeType.TOOL: {s.value for s in ToolSubtype},
    NodeType.MEMORY: {s.value for s in MemorySubtype},
}

# AI Agent Model Validation - defines which models are valid for each AI agent subtype
VALID_AI_MODELS: Dict[str, Set[str]] = {
    AIAgentSubtype.OPENAI_CHATGPT.value: {m.value for m in OpenAIModel},
    AIAgentSubtype.ANTHROPIC_CLAUDE.value: {m.value for m in AnthropicModel},
    AIAgentSubtype.GOOGLE_GEMINI.value: {m.value for m in GoogleGeminiModel},
}


def get_valid_subtypes(node_type: NodeType) -> List[str]:
    """Get list of valid subtypes for a given node type"""
    return sorted(list(VALID_SUBTYPES.get(node_type, set())))


def is_valid_node_subtype_combination(node_type: str, subtype: str) -> bool:
    """Validate if a node_type/subtype combination is valid"""
    try:
        node_type_enum = NodeType(node_type)
        return subtype in VALID_SUBTYPES[node_type_enum]
    except ValueError:
        return False


def get_all_node_types() -> List[str]:
    """Get all valid node types"""
    return [t.value for t in NodeType]


def get_all_subtypes() -> Dict[str, List[str]]:
    """Get all subtypes organized by node type"""
    return {node_type.value: get_valid_subtypes(node_type) for node_type in NodeType}


def get_valid_ai_models(ai_subtype: str) -> List[str]:
    """Get list of valid models for a given AI agent subtype"""
    return sorted(list(VALID_AI_MODELS.get(ai_subtype, set())))


def is_valid_ai_model(ai_subtype: str, model_version: str) -> bool:
    """Validate if an AI subtype/model combination is valid"""
    return model_version in VALID_AI_MODELS.get(ai_subtype, set())


def get_all_ai_models() -> Dict[str, List[str]]:
    """Get all AI models organized by subtype"""
    return {subtype: get_valid_ai_models(subtype) for subtype in VALID_AI_MODELS.keys()}


def validate_ai_node_config(subtype: str, model_version: str) -> Dict[str, Any]:
    """
    Validate AI agent node configuration

    Returns:
        Dict with 'valid' boolean and 'message' with details
    """
    if subtype not in VALID_AI_MODELS:
        return {
            "valid": False,
            "message": f"Invalid AI subtype: {subtype}. Valid options: {list(VALID_AI_MODELS.keys())}",
        }

    if not is_valid_ai_model(subtype, model_version):
        valid_models = get_valid_ai_models(subtype)
        return {
            "valid": False,
            "message": f"Invalid model {model_version} for {subtype}. Valid options: {valid_models}",
        }

    return {"valid": True, "message": f"Valid configuration: {subtype} with {model_version}"}


# Legacy API Gateway compatibility mapping
# This allows gradual migration from legacy API formats
API_GATEWAY_COMPATIBILITY = {
    "trigger": NodeType.TRIGGER,
    "action": NodeType.ACTION,
    "condition": NodeType.FLOW,
    "loop": NodeType.FLOW,
    "webhook": NodeType.TRIGGER,
    "api_call": NodeType.EXTERNAL_ACTION,
    "email": NodeType.EXTERNAL_ACTION,
    "delay": NodeType.FLOW,
}


def resolve_legacy_api_type(legacy_type: str) -> NodeType:
    """
    Resolve legacy API Gateway types to unified NodeType
    This function should be removed once API Gateway is fully migrated
    """
    return API_GATEWAY_COMPATIBILITY.get(legacy_type.lower(), NodeType.ACTION)


# ============================================================================
# WORKFLOW SCHEDULER SPECIFIC ENUMS
# ============================================================================


class IntegrationProvider(str, Enum):
    """Integration providers for OAuth and external services"""

    GITHUB = "github"
    SLACK = "slack"
    NOTION = "notion"
    GOOGLE_CALENDAR = "google_calendar"
    DISCORD = "discord"
    FIRECRAWL = "firecrawl"


class SlackEventType(str, Enum):
    """Slack event types for trigger configuration"""

    MESSAGE = "message"
    APP_MENTION = "app_mention"
    REACTION_ADDED = "reaction_added"
    CHANNEL_MESSAGE = "channel_message"


class ValidationResult(str, Enum):
    """Standard validation result statuses"""

    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"
    ERROR = "error"


class ServiceName(str, Enum):
    """Service names in the monorepo"""

    WORKFLOW_SCHEDULER = "workflow_scheduler"
    WORKFLOW_ENGINE = "workflow_engine"
    WORKFLOW_AGENT = "workflow_agent"
    API_GATEWAY = "api_gateway"


# Export all enums for easy importing
__all__ = [
    # Core Node Enums
    "NodeType",
    "TriggerSubtype",
    "AIAgentSubtype",
    "ExternalActionSubtype",
    "ActionSubtype",
    "FlowSubtype",
    "HumanLoopSubtype",
    "ToolSubtype",
    "MemorySubtype",
    # AI Model Enums
    "OpenAIModel",
    "AnthropicModel",
    "GoogleGeminiModel",
    # Workflow Scheduler Enums
    "IntegrationProvider",
    "SlackEventType",
    "ValidationResult",
    "ServiceName",
    # Validation Maps
    "VALID_SUBTYPES",
    "VALID_AI_MODELS",
    # Node Type Validation Functions
    "get_valid_subtypes",
    "is_valid_node_subtype_combination",
    "get_all_node_types",
    "get_all_subtypes",
    # AI Model Validation Functions
    "get_valid_ai_models",
    "is_valid_ai_model",
    "get_all_ai_models",
    "validate_ai_node_config",
    # Legacy Support
    "resolve_legacy_api_type",
]
