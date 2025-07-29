# Node Specification System

## Overview

The Node Specification System provides a clean, extensible framework for defining workflow node types with complete type safety, validation, and documentation. The system focuses on **simplicity and flexibility**, with AI agents defined by their provider (Gemini, OpenAI, Claude) where functionality is determined by system prompts rather than hardcoded roles.

## 🏗️ Architecture

```
apps/backend/shared/node_specs/
├── __init__.py              # Main exports and public API
├── base.py                  # Core data structures and types
├── registry.py              # Specification registry with auto-loading
├── validator.py             # Parameter and port validation
├── definitions/             # Node specifications by category
│   ├── __init__.py
│   ├── trigger_nodes.py     # Event and schedule triggers
│   ├── ai_agent_nodes.py    # AI provider nodes (NEW APPROACH)
│   ├── action_nodes.py      # Actions and integrations
│   └── flow_nodes.py        # Flow control and logic
└── README.md               # This documentation
```

## 🤖 AI Agent Revolution

### New Provider-Based Approach

Instead of hardcoded AI roles like "REPORT_GENERATOR" or "TASK_ANALYZER", we now have **provider-based AI agents** where functionality is determined by system prompts:

```python
# OLD: Rigid, predefined roles
"AI_AGENT_NODE.REPORT_GENERATOR"
"AI_AGENT_NODE.TASK_ANALYZER"

# NEW: Flexible, prompt-driven providers
"AI_AGENT_NODE.GEMINI_NODE"
"AI_AGENT_NODE.OPENAI_NODE"
"AI_AGENT_NODE.CLAUDE_NODE"
```

### AI Node Types

| Provider | Description | Key Features |
|----------|-------------|--------------|
| **GEMINI_NODE** | Google Gemini AI | Vision support, safety filters, multi-modal |
| **OPENAI_NODE** | OpenAI GPT models | Advanced reasoning, function calling, structured output |
| **CLAUDE_NODE** | Anthropic Claude | Long context, helpful and harmless, precise control |

### System Prompt Examples

```python
# Data Analysis Agent
system_prompt = """
You are a data analysis expert. Analyze the provided data for trends,
anomalies, and insights. Always provide:
1. Executive summary
2. Key findings with confidence scores
3. Actionable recommendations
4. Data quality assessment
"""

# Customer Service Router
system_prompt = """
You are a customer service routing assistant. Based on the customer's
message, determine the appropriate department:
- "billing" for payment/invoice issues
- "technical" for product problems
- "sales" for new purchases
- "general" for everything else

Respond with JSON: {"department": "...", "confidence": 0.95, "reason": "..."}
"""

# Code Review Agent
system_prompt = """
You are a senior software engineer reviewing code. Analyze for:
- Security vulnerabilities
- Performance issues
- Code style and best practices
- Potential bugs

Provide specific feedback with line numbers and improvement suggestions.
"""
```

## 📊 Complete Node Types

### TRIGGER_NODE (Event Sources)
| Subtype | Description | Use Cases |
|---------|-------------|-----------|
| **MANUAL** | User-initiated triggers | Manual workflow execution, testing |
| **CRON** | Scheduled execution | Daily reports, cleanup tasks, backups |
| **WEBHOOK** | HTTP endpoint triggers | API integrations, external events |
| **CHAT** | Messaging platform events | Slack bots, Discord commands |
| **EMAIL** | Email-based triggers | Support tickets, form submissions |
| **FORM** | Web form submissions | Lead capture, feedback collection |
| **CALENDAR** | Calendar event triggers | Meeting reminders, event automation |

### AI_AGENT_NODE (AI Providers) 🆕
| Provider | Models | Specialties |
|----------|--------|-------------|
| **GEMINI_NODE** | gemini-pro, gemini-pro-vision, gemini-ultra | Multi-modal, vision, safety |
| **OPENAI_NODE** | gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o | Reasoning, structured output |
| **CLAUDE_NODE** | claude-3-haiku, claude-3-sonnet, claude-3-opus | Long context, helpfulness |

### ACTION_NODE (Operations)
| Subtype | Description | Capabilities |
|---------|-------------|--------------|
| **RUN_CODE** | Multi-language code execution | Python, JavaScript, SQL, R, Julia |
| **HTTP_REQUEST** | API calls and web requests | REST APIs, GraphQL, webhooks |
| **PARSE_IMAGE** | OCR and image analysis | Text extraction, object detection |
| **WEB_SEARCH** | Search engine queries | Google, Bing, DuckDuckGo |
| **DATABASE_OPERATION** | Database interactions | PostgreSQL, MySQL, MongoDB |
| **FILE_OPERATION** | File system operations | Read, write, copy, transform |
| **DATA_TRANSFORMATION** | Data processing | Filter, map, reduce, aggregate |

### FLOW_NODE (Control Flow)
| Subtype | Description | Logic Type |
|---------|-------------|------------|
| **IF** | Conditional branching | Boolean conditions, routing |
| **FILTER** | Data filtering | Include/exclude based on criteria |
| **LOOP** | Iteration and repetition | ForEach, While, Until loops |
| **MERGE** | Data stream combination | Union, intersection, join |
| **SWITCH** | Multi-way routing | Case-based routing |
| **WAIT** | Delays and pausing | Time delays, condition waiting |

## 🚀 Quick Start

### Basic AI Agent Usage

```python
from node_specs import node_spec_registry

# Get Gemini AI agent specification
gemini_spec = node_spec_registry.get_spec("AI_AGENT_NODE", "GEMINI_NODE")

# Create a data analysis node
class DataAnalysisNode:
    def __init__(self):
        self.type = "AI_AGENT_NODE"
        self.subtype = "GEMINI_NODE"
        self.parameters = {
            "system_prompt": """You are a data analyst. Analyze the provided
                               dataset and identify key trends, outliers, and
                               actionable insights. Format your response as a
                               structured JSON report.""",
            "model_version": "gemini-pro",
            "temperature": "0.3",
            "max_tokens": "2048",
            "response_format": "json"
        }

# Validate the node
errors = node_spec_registry.validate_node(DataAnalysisNode())
if not errors:
    print("✅ Node configuration is valid!")
```

### Creating Custom Workflows

```python
# 1. Trigger: Manual start
trigger = {
    "type": "TRIGGER_NODE",
    "subtype": "MANUAL",
    "parameters": {"trigger_name": "Data Analysis Pipeline"}
}

# 2. AI Agent: Data analysis
analyzer = {
    "type": "AI_AGENT_NODE",
    "subtype": "CLAUDE_NODE",
    "parameters": {
        "system_prompt": "Analyze sales data for trends and recommendations",
        "model_version": "claude-3-sonnet",
        "temperature": "0.2"
    }
}

# 3. Action: Generate report file
file_writer = {
    "type": "ACTION_NODE",
    "subtype": "FILE_OPERATION",
    "parameters": {
        "operation": "write",
        "file_path": "/reports/analysis.md",
        "encoding": "utf-8"
    }
}
```

## 🔧 Advanced Features

### Parameter Validation

```python
# Automatic validation with detailed error messages
node = MockNode("AI_AGENT_NODE", "OPENAI_NODE", {
    "system_prompt": "Analyze data",
    "temperature": "1.5",  # Invalid: > 1.0
    "model_version": "gpt-5"  # Invalid: not in enum
})

errors = node_spec_registry.validate_node(node)
# Returns: [
#   "Parameter temperature must be between 0.0 and 1.0",
#   "Parameter model_version must be one of: ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o']"
# ]
```

### Connection Compatibility

```python
# Validate port connections between nodes
source = MockNode("TRIGGER_NODE", "WEBHOOK", {})
target = MockNode("AI_AGENT_NODE", "GEMINI_NODE", {})

errors = node_spec_registry.validate_connection(
    source, "main",  # source port
    target, "main"   # target port
)

if not errors:
    print("✅ Ports are compatible!")
```

### Provider-Specific Parameters

```python
# OpenAI-specific parameters
openai_node = {
    "type": "AI_AGENT_NODE",
    "subtype": "OPENAI_NODE",
    "parameters": {
        "system_prompt": "You are a helpful assistant",
        "model_version": "gpt-4",
        "temperature": "0.7",
        "presence_penalty": "0.1",     # OpenAI-specific
        "frequency_penalty": "0.2"     # OpenAI-specific
    }
}

# Gemini-specific parameters
gemini_node = {
    "type": "AI_AGENT_NODE",
    "subtype": "GEMINI_NODE",
    "parameters": {
        "system_prompt": "Analyze this image and data",
        "model_version": "gemini-pro-vision",  # Vision model
        "safety_settings": {               # Gemini-specific
            "harassment": "BLOCK_MEDIUM_AND_ABOVE",
            "hate_speech": "BLOCK_ONLY_HIGH"
        }
    }
}
```

## 🧪 Testing & Validation

```bash
# Run comprehensive tests
cd apps/backend/shared/node_specs
python -m pytest tests/

# Quick validation test
python simple_test.py
```

## 📈 Benefits of New Approach

### 🎯 For AI Agents
| Old Approach | New Approach |
|--------------|--------------|
| ❌ Hardcoded roles (REPORT_GENERATOR) | ✅ Flexible system prompts |
| ❌ Limited to predefined functions | ✅ Unlimited functionality via prompts |
| ❌ Difficult to customize behavior | ✅ Easy prompt customization |
| ❌ Need new code for new roles | ✅ Just change the prompt |
| ❌ Provider capabilities ignored | ✅ Provider-specific optimizations |

### 🚀 For Developers
- **Flexibility**: Any AI task possible through prompts
- **Simplicity**: Three providers instead of dozens of subtypes
- **Maintainability**: No hardcoded business logic in specs
- **Extensibility**: Easy to add new providers
- **Optimization**: Leverage provider-specific features

### 👥 For Users
- **Clarity**: Know exactly which AI provider they're using
- **Control**: Full control over AI behavior via prompts
- **Choice**: Pick the best provider for their use case
- **Transparency**: Clear understanding of capabilities and costs

## 🔄 Migration Guide

### From Old AI Agents
```python
# OLD: Hardcoded role
{
    "type": "AI_AGENT_NODE",
    "subtype": "REPORT_GENERATOR",
    "parameters": {
        "report_type": "executive_summary",
        "target_audience": "stakeholder"
    }
}

# NEW: Prompt-driven provider
{
    "type": "AI_AGENT_NODE",
    "subtype": "CLAUDE_NODE",
    "parameters": {
        "system_prompt": """You are an executive report generator.
                           Create concise summaries for stakeholders focusing on
                           key metrics, decisions needed, and business impact.""",
        "model_version": "claude-3-sonnet",
        "temperature": "0.3"
    }
}
```

## 🎉 What's Next

1. **Tool Nodes**: Database connectors, API integrations
2. **Memory Nodes**: Vector stores, knowledge bases
3. **Human Loop Nodes**: Approval workflows, manual input
4. **Advanced Validation**: Cross-parameter validation, schema evolution
5. **Visual Builder**: Drag-and-drop workflow designer
6. **Performance Analytics**: Node execution metrics and optimization

---

**🔄 Status**: Revamped with provider-based AI agents
**📝 Version**: 2.0.0
**📅 Updated**: 2025-01-28
**🎯 Focus**: Flexibility through system prompts, not hardcoded roles
