# Workflow DSL (Domain Specific Language)

An elegant YAML-like intermediate representation for AI Agent workflows that focuses on human and AI readability while maintaining composability and extensibility.

## Overview

The Workflow DSL serves as a bridge between human workflow design and the underlying protobuf data model. It provides:

- **Human-readable syntax** for defining workflows
- **Composable structure** for building complex workflows
- **Concise representation** of nodes and connections
- **Extensible design** for future enhancements
- **Type-safe mapping** to workflow.proto

## Key Features

### 🎯 **Focused Design**
- Declares nodes (name, type, role) clearly
- Connects nodes with simple edge definitions
- Omits verbose internal configuration unless critical
- Supports extension through metadata and parameters

### 🧩 **Composable & Extendable**
- Modular node definitions
- Flexible connection system
- Parameter-based customization
- Metadata support for tooling

### 📖 **Human & AI Readable**
- Clean YAML-like syntax
- Descriptive node roles
- Intuitive connection definitions
- Self-documenting structure

## Core Structure

```yaml
workflow:
  name: "My Workflow"
  description: "What this workflow does"
  version: "1.0.0"
  tags: ["category", "purpose"]

  settings:
    timezone: "UTC"
    timeout: 300
    error_policy: STOP_WORKFLOW

  nodes:
    - name: "unique_node_id"
      type: TRIGGER_NODE
      subtype: TRIGGER_CHAT
      role: "Human-readable description"
      parameters:
        key: "value"

  connections:
    - from: "source_node"
      to: "target_node"
      type: MAIN
      index: 0
```

## Node Types

### 🚀 **Trigger Nodes**
Entry points for workflow execution
- `TRIGGER_CHAT` - Chat message triggers
- `TRIGGER_WEBHOOK` - HTTP webhook triggers
- `TRIGGER_CRON` - Scheduled triggers
- `TRIGGER_MANUAL` - Manual execution
- `TRIGGER_EMAIL` - Email-based triggers
- `TRIGGER_FORM` - Form submission triggers
- `TRIGGER_CALENDAR` - Calendar event triggers

### 🤖 **AI Agent Nodes**
Provider-based AI processing nodes (functionality defined by system prompts)
- `AI_GEMINI_NODE` - Google Gemini AI agent
- `AI_OPENAI_NODE` - OpenAI GPT AI agent
- `AI_CLAUDE_NODE` - Anthropic Claude AI agent

### 🔌 **External Action Nodes**
External service integrations
- `EXTERNAL_GITHUB` - GitHub operations
- `EXTERNAL_GOOGLE_CALENDAR` - Calendar integration
- `EXTERNAL_TRELLO` - Project management
- `EXTERNAL_EMAIL` - Email operations
- `EXTERNAL_SLACK` - Slack integration
- `EXTERNAL_API_CALL` - Generic API calls
- `EXTERNAL_WEBHOOK` - Webhook calls
- `EXTERNAL_NOTIFICATION` - Notifications

### ⚡ **Action Nodes**
Internal processing actions
- `ACTION_RUN_CODE` - Code execution
- `ACTION_SEND_HTTP_REQUEST` - HTTP requests
- `ACTION_PARSE_IMAGE` - Image processing
- `ACTION_WEB_SEARCH` - Web search
- `ACTION_DATABASE_OPERATION` - Database ops
- `ACTION_FILE_OPERATION` - File handling
- `ACTION_DATA_TRANSFORMATION` - Data processing

### 🔄 **Flow Nodes**
Workflow control flow
- `FLOW_IF` - Conditional branching
- `FLOW_FILTER` - Data filtering
- `FLOW_LOOP` - Iteration
- `FLOW_MERGE` - Data merging
- `FLOW_SWITCH` - Multi-way branching
- `FLOW_WAIT` - Delays/waiting

### 👥 **Human-in-the-Loop Nodes**
Human interaction points
- `HUMAN_GMAIL` - Gmail interactions
- `HUMAN_SLACK` - Slack interactions
- `HUMAN_DISCORD` - Discord interactions
- `HUMAN_TELEGRAM` - Telegram interactions
- `HUMAN_APP` - App-based interactions

### 🛠️ **Tool Nodes**
External tool integrations
- `TOOL_GOOGLE_CALENDAR_MCP` - Calendar tools
- `TOOL_NOTION_MCP` - Notion integration
- `TOOL_CALENDAR` - Generic calendar
- `TOOL_EMAIL` - Email tools
- `TOOL_HTTP` - HTTP utilities
- `TOOL_CODE_EXECUTION` - Code runners

### 💾 **Memory Nodes**
Data persistence and retrieval
- `MEMORY_SIMPLE` - Simple storage
- `MEMORY_BUFFER` - Buffer memory
- `MEMORY_KNOWLEDGE` - Knowledge base
- `MEMORY_VECTOR_STORE` - Vector storage
- `MEMORY_DOCUMENT` - Document storage
- `MEMORY_EMBEDDING` - Embeddings

## Connection Types

Defines how nodes are linked together:

- `MAIN` - Primary execution flow
- `AI_AGENT` - AI agent connections
- `AI_CHAIN` - AI processing chains
- `AI_DOCUMENT` - Document processing
- `AI_EMBEDDING` - Embedding operations
- `AI_LANGUAGE_MODEL` - Language model connections
- `AI_MEMORY` - Memory system connections
- `AI_OUTPUT_PARSER` - Output parsing
- `AI_RETRIEVER` - Information retrieval
- `AI_RERANKER` - Result reranking
- `AI_TEXT_SPLITTER` - Text processing
- `AI_TOOL` - Tool integrations
- `AI_VECTOR_STORE` - Vector storage

## Usage Examples

See `examples.yaml` for detailed examples including:

1. **Simple Chat-to-Email Workflow** - Basic message forwarding
2. **Complex Data Processing Pipeline** - Multi-source report generation
3. **Human-in-the-Loop Approval Process** - Document review workflow

## Design Principles

### ✨ **Elegance Over Verbosity**
- Minimal required fields
- Sensible defaults
- Clear, concise syntax
- Focused on essential workflow logic

### 🔧 **Extensibility Without Complexity**
- Parameter-based customization
- Metadata support for tooling
- Version-aware design
- Forward compatibility

### 🎯 **Purpose-Driven**
- Workflow-first design
- Node roles over implementation details
- Connection clarity
- Human-centric naming

## Integration

The DSL maps directly to the protobuf schema in `workflow.proto`:

- `workflow` → `Workflow` message
- `nodes` → `Node` messages
- `connections` → `ConnectionsMap` structure
- `settings` → `WorkflowSettings` message

This ensures type safety and seamless integration with the workflow engine while maintaining the DSL's readability and ease of use.

## File Structure

```
dsl/
├── workflow-dsl.yaml    # DSL specification
├── examples.yaml        # Usage examples
└── README.md           # This documentation
```
