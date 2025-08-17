"""
Node Type and Subtype Enums - Single Source of Truth

This module defines the authoritative enums for all node types and subtypes
used across the entire system. All services MUST use these enums directly.

NO conversion functions - these ARE the standard.
"""

from enum import Enum
from typing import Dict, List, Set


class NodeType(str, Enum):
    """
    Core Node Types - Based on database schema constraints

    These are the 8 fundamental node categories in the workflow engine.
    """

    TRIGGER = "TRIGGER"
    AI_AGENT = "AI_AGENT"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    ACTION = "ACTION"
    FLOW = "FLOW"
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"
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


class ExternalActionSubtype(str, Enum):
    """External Action Node Subtypes - Third-party integrations"""

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

    # Generic Actions
    API_CALL = "API_CALL"
    WEBHOOK = "WEBHOOK"
    NOTIFICATION = "NOTIFICATION"

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
    SWITCH = "SWITCH"

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
    """Human-in-the-Loop Node Subtypes - Human interaction points"""

    # Email Interactions
    GMAIL_INTERACTION = "GMAIL_INTERACTION"
    OUTLOOK_INTERACTION = "OUTLOOK_INTERACTION"

    # Chat Interactions
    SLACK_INTERACTION = "SLACK_INTERACTION"
    DISCORD_INTERACTION = "DISCORD_INTERACTION"
    TELEGRAM_INTERACTION = "TELEGRAM_INTERACTION"
    TEAMS_INTERACTION = "TEAMS_INTERACTION"

    # App Interactions
    IN_APP_APPROVAL = "IN_APP_APPROVAL"
    FORM_SUBMISSION = "FORM_SUBMISSION"
    MANUAL_REVIEW = "MANUAL_REVIEW"

    # Legacy (for backward compatibility)
    GMAIL = "GMAIL"
    SLACK = "SLACK"
    DISCORD = "DISCORD"
    TELEGRAM = "TELEGRAM"
    APP = "APP"


class ToolSubtype(str, Enum):
    """Tool Node Subtypes - External tools and utilities"""

    # MCP Tools
    MCP_TOOL = "MCP_TOOL"

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
    """Memory Node Subtypes - Data storage and retrieval"""

    # Vector Databases
    VECTOR_DATABASE = "VECTOR_DATABASE"
    PINECONE = "PINECONE"
    WEAVIATE = "WEAVIATE"
    QDRANT = "QDRANT"

    # Key-Value Stores
    KEY_VALUE_STORE = "KEY_VALUE_STORE"
    REDIS_CACHE = "REDIS_CACHE"

    # Document Stores
    DOCUMENT_STORE = "DOCUMENT_STORE"
    ELASTICSEARCH = "ELASTICSEARCH"

    # Traditional Databases
    SQL_DATABASE = "SQL_DATABASE"
    NOSQL_DATABASE = "NOSQL_DATABASE"

    SIMPLE_MEMORY = "SIMPLE_MEMORY"

    # Legacy (for backward compatibility)
    VECTOR_DB = "VECTOR_DB"
    KEY_VALUE = "KEY_VALUE"
    DOCUMENT = "DOCUMENT"


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


# Export all enums for easy importing
__all__ = [
    "NodeType",
    "TriggerSubtype",
    "AIAgentSubtype",
    "ExternalActionSubtype",
    "ActionSubtype",
    "FlowSubtype",
    "HumanLoopSubtype",
    "ToolSubtype",
    "MemorySubtype",
    "VALID_SUBTYPES",
    "get_valid_subtypes",
    "is_valid_node_subtype_combination",
    "get_all_node_types",
    "get_all_subtypes",
    "resolve_legacy_api_type",
]
