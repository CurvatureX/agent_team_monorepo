# Agent Development Guide

## Overview

This guide helps team members develop AI agents using LangGraph in our monorepo.

## 🚀 Quick Start

1. **Navigate to backend directory**: `cd apps/backend`
2. **Create environment file**: Copy `.env.example` to `.env` and add your API keys
3. **Navigate to agent directory**: `cd workflow_agent`
4. **Install dependencies**: `uv sync --frozen`
5. **Start development server**: `langgraph dev --port 8125`
6. **Open LangGraph Studio**: Visit `http://localhost:8123` in your browser

## 📚 LangGraph Basics

### What is LangGraph?

LangGraph is a framework for building stateful, multi-step AI agents as graphs. Think of it as a workflow engine for LLM-powered applications.

### Core Concepts

**1. State (`AgentState`)**

- Shared data structure that flows through your agent
- Defined as a TypedDict with required and optional fields
- Located in: `agents/state.py`

```python
class AgentState(TypedDict):
    user_input: str                    # Required input
    workflow: NotRequired[Dict]        # Optional output
    current_step: NotRequired[str]     # Track progress
```

**2. Nodes (Functions)**

- Individual processing steps in your agent
- Each node receives state and returns updated state
- Located in: `agents/nodes.py`

```python
async def analyze_requirement(state: AgentState) -> AgentState:
    # Process user input and update state
    return {"requirements": parsed_data, **state}
```

**3. Edges (Connections)**

- Define the flow between nodes
- Can be conditional (if/else logic)
- Set in: `agents/workflow_agent.py`

```python
# Simple edge: always go from A to B
workflow.add_edge("analyze_requirement", "generate_plan")

# Conditional edge: decide next step based on logic
workflow.add_conditional_edges(
    "check_knowledge",
    should_continue_function,
    {"ask_questions": END, "generate": "generate_workflow"}
)
```

### Project Structure

```
workflow_agent/
├── agents/
│   ├── state.py          # State definitions
│   ├── nodes.py          # Node implementations
│   └── workflow_agent.py # Graph setup and orchestration
├── core/
│   ├── config.py         # Configuration settings
│   └── models.py         # Data models
├── services/
│   └── grpc_server.py    # External API interface
├── langgraph.json        # LangGraph configuration
└── pyproject.toml        # Python dependencies
```

## 🔧 Development Workflow

### 1. Setting Up Your Environment

```bash
# Navigate to backend directory
cd apps/backend

# Create .env file from example (if it exists) or create new one
cp .env.example .env  # or touch .env if no example exists

# Add your API keys to .env file:
# OPENAI_API_KEY=your_openai_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_if_needed
# LANGSMITH_API_KEY=your_langsmith_key_here (optional, for monitoring)

# Install dependencies
cd workflow_agent
uv sync --frozen

# If you get dependency conflicts, use:
uv add --frozen package-name
```

### 2. Defining Your Agent State

Edit `agents/state.py`:

- Add fields your agent needs
- Use `NotRequired[Type]` for optional fields
- Keep required fields minimal (usually just user input)

### 3. Implementing Nodes

Edit `agents/nodes.py`:

- Each node is an async function
- Receives `AgentState`, returns updated `AgentState`
- Add logging for debugging: `logger.info("Processing step", data=value)`

### 4. Connecting the Graph

Edit `agents/workflow_agent.py`:

- Add your nodes: `workflow.add_node("node_name", self.nodes.your_function)`
- Connect with edges: `workflow.add_edge("start_node", "end_node")`
- Set entry point: `workflow.set_entry_point("first_node")`

### 5. Setting Up LangSmith (Optional but Recommended)

LangSmith provides powerful monitoring, debugging, and evaluation tools for your LangGraph agents.

**Creating a LangSmith Account:**

1. **Visit LangSmith**: Go to [https://smith.langchain.com/](https://smith.langchain.com/)
2. **Sign Up**: Click "Sign Up" and create an account using:
   - Email and password, or
   - GitHub/Google authentication
3. **Verify Email**: Check your email and verify your account if required

**Getting Your API Key:**

1. **Login** to your LangSmith account
2. **Navigate to Settings**: Click on your profile icon → Settings
3. **API Keys Section**: Go to the "API Keys" tab
4. **Create New Key**: Click "Create API Key"
   - Give it a descriptive name (e.g., "Local Development")
   - Copy the generated API key immediately (you won't see it again)
5. **Add to .env**: Add the key to your `apps/backend/.env` file:

```bash
# apps/backend/.env
LANGSMITH_API_KEY=lsv2_pt_your_actual_api_key_here
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=workflow-agent-dev
```

**Benefits of LangSmith Integration:**

- **Trace Visualization**: See detailed execution traces of your agent runs
- **Performance Monitoring**: Track latency, token usage, and costs
- **Error Debugging**: Detailed error logs and stack traces
- **Prompt Engineering**: Test and iterate on prompts
- **Evaluation**: Run automated tests on your agent behavior

**Accessing LangSmith Dashboard:**

After adding the API key and running your agent:

1. Visit [https://smith.langchain.com/](https://smith.langchain.com/)
2. Navigate to your project (e.g., "workflow-agent-dev")
3. View real-time traces as your agent executes

## 🐛 Debugging with LangGraph Studio

### Starting the Debug Server

```bash
# From workflow_agent directory
langgraph dev --port 8125

# Server starts on:
# - Studio UI: http://localhost:8123
# - API: http://localhost:8124
```

**Environment Setup**
Make sure you have a `.env` file in the `apps/backend/` directory with your API keys:

```bash
# apps/backend/.env
OPENAI_API_KEY=your_actual_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_key_if_needed
LANGSMITH_API_KEY=your_langsmith_api_key
# Add other secrets as needed
```

### Using LangGraph Studio

**1. Studio Interface**

- **Left Panel**: Your agent configurations and threads
- **Center Panel**: Conversation interface and graph visualization
- **Right Panel**: State inspection and debugging tools

**2. Testing Your Agent**

- Click "New Thread" to start a conversation
- Enter test input in the chat interface
- Watch the graph execute step by step
- Inspect state changes in real-time

**3. State Inspection**

- Click on any node in the graph to see its state
- View input/output for each step
- Check for errors or unexpected values
- Monitor state evolution through the workflow

**4. Graph Visualization**

- See your workflow as a visual graph
- Track execution path in real-time
- Identify bottlenecks or errors
- Understand data flow

### Debug Tips

**Console Logging**

```python
import structlog
logger = structlog.get_logger()

# In your nodes:
logger.info("Processing user input", input=state["user_input"])
logger.error("Validation failed", errors=validation_errors)
```

**State Debugging**

```python
# Add debug info to state
return {
    **state,
    "debug_info": {
        "step": "validation",
        "timestamp": datetime.now().isoformat(),
        "processed_data": cleaned_data
    }
}
```

**Testing Specific Nodes**

- Use Studio to test individual node behavior
- Create minimal test states
- Verify each node's input/output

## 🛠️ Common Patterns

### Error Handling

```python
async def safe_node(state: AgentState) -> AgentState:
    try:
        result = await process_data(state["user_input"])
        return {"result": result, **state}
    except Exception as e:
        logger.error("Node failed", error=str(e))
        return {"errors": [str(e)], **state}
```

### Conditional Logic

```python
def should_continue(state: AgentState) -> str:
    if state.get("errors"):
        return "handle_error"
    elif state.get("missing_info"):
        return "ask_questions"
    else:
        return "continue_processing"
```

### State Validation

```python
def validate_state(state: AgentState) -> AgentState:
    errors = []
    if not state.get("user_input"):
        errors.append("Missing user input")

    return {"validation_errors": errors, **state}
```

## 🚨 Troubleshooting

### Common Issues

**1. Import Errors**

```bash
# Use absolute imports
from agents.state import AgentState  # ✅ Good
from .state import AgentState        # ❌ Bad
```

**2. Dependency Conflicts**

```bash
# Force install with frozen dependencies
uv sync --frozen
uv add --frozen package-name
```

**3. State Type Errors**

- Make sure state fields match TypedDict definition
- Use `NotRequired[Type]` for optional fields
- Initialize all required fields in your entry node

**4. Graph Compilation Errors**

```python
# Check that all referenced nodes are added
workflow.add_node("missing_node", self.nodes.missing_function)

# Verify conditional edge return values match defined paths
def router(state):
    return "valid_path_name"  # Must match edge definition
```

**5. Studio Connection Issues**

- Check port availability (8123, 8124, 8125)
- Verify `langgraph.json` configuration
- Ensure `.env` file exists in `apps/backend/` with required API keys
- Check that environment variables are loaded correctly

### Debug Commands

```bash
# Check server status
curl http://localhost:8124/health

# View available assistants
curl http://localhost:8124/assistants

# Check configuration
cat langgraph.json
```

## 📋 Development Checklist

Before submitting your agent:

- [ ] State is properly defined with minimal required fields
- [ ] All nodes have error handling and logging
- [ ] Graph compiles without errors
- [ ] Agent works in LangGraph Studio
- [ ] Edge conditions cover all possible states
- [ ] Documentation updated for new functionality
- [ ] Tests added for new nodes (if applicable)

## 🔗 Resources

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **LangSmith Platform**: https://smith.langchain.com/ (monitoring & debugging)
- **LangSmith Documentation**: https://docs.smith.langchain.com/
- **Project Architecture**: `docs/tech-design/workflow-agent-architecture.md`
- **API Documentation**: `docs/tech-design/api-doc.md`

## 💡 Pro Tips

1. **Start Simple**: Begin with a linear workflow, add complexity gradually
2. **Use Studio Early**: Test each node as you build it
3. **Log Everything**: Add structured logging for easier debugging
4. **State Hygiene**: Keep state minimal and clean, avoid nested complexity
5. **Error Recovery**: Always plan for failure cases and provide meaningful errors
6. **Version Control**: Commit working states frequently during development
