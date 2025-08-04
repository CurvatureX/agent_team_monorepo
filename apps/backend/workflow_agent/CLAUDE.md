# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- **Install dependencies:** `uv pip install --system -e .` (requires Python 3.11+)
- **Run main service:** `python main.py` (starts FastAPI server on port 8001)
- **Run debug server:** `python debug_server.py` (for LangGraph Studio integration)
- **Run tests:** `pytest tests/` or `pytest tests/test_specific.py::test_function`
- **Start LangGraph:** `langgraph up` (uses langgraph.json config)

### Docker Operations
- **Build image:** `docker build -f Dockerfile -t workflow-agent .`
- **Run container:** `docker run -p 8001:8001 --env-file .env workflow-agent`
- **Start with docker-compose:** `./start_docker.sh`
- **Stop containers:** `./stop_docker.sh`

### RAG System Management
- **Initialize node knowledge:** `python scripts/insert_node_knowledge.py`
- **Test RAG search:** `python scripts/insert_node_knowledge.py test`

## Architecture Overview

The Workflow Agent is an AI-powered consultant that transforms natural language requirements into executable workflow DSL through a sophisticated multi-stage process.

### Core Flow: Request → Analysis → Negotiation → Design → DSL

1. **Entry Point** (`main.py` → `services/fastapi_server.py`)
   - FastAPI server receives workflow generation requests
   - Handles streaming responses for real-time interaction

2. **State Machine** (`agents/workflow_agent.py`)
   - LangGraph-based orchestration with 4 core nodes
   - Dynamic routing based on workflow stage
   - Maintains conversation history and context

3. **Intelligence Layer** (`agents/nodes.py`)
   - **Clarification Node**: Analyzes requirements, identifies gaps using RAG
   - **Gap Analysis Node**: Evaluates feasibility and suggests alternatives
   - **Workflow Generation Node**: Creates final DSL output
   - **Debug Node**: Validates and optimizes the workflow

4. **RAG System** (`core/vector_store.py` + `agents/tools.py`)
   - Supabase pgvector for semantic search
   - Pre-populated with node capabilities and best practices
   - Enhances all intelligence nodes with contextual knowledge

5. **State Management** (`agents/state.py` + `services/state_manager.py`)
   - Pydantic models for type-safe state handling
   - Supabase persistence for session continuity
   - Tracks workflow evolution through all stages

## Workflow DSL

The system outputs a human-readable YAML-like DSL (`dsl/` directory):
- **Node Types**: Triggers, AI Agents, External Actions, Flow Control, Human-in-Loop, Tools, Memory
- **Connection Types**: Define execution flow between nodes
- **See `dsl/README.md`** for complete specification

## Key Design Patterns

### 1. Defensive Workflow Generation
The agent doesn't blindly generate workflows. It:
- Identifies capability gaps early
- Negotiates feasible solutions with users
- Suggests alternatives when direct implementation isn't possible

### 2. RAG-Enhanced Intelligence
Every decision is informed by:
- Historical node usage patterns
- Best practices from the knowledge base
- Capability matching algorithms

### 3. Stateful Multi-Turn Interaction
- Maintains full conversation context
- Allows iterative refinement
- Supports backtracking to previous stages

## Environment Configuration

Required environment variables:
```bash
# Core Service
FASTAPI_PORT=8001
HOST=0.0.0.0

# AI Models
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4

# Supabase (RAG)
SUPABASE_URL=your_url
SUPABASE_SECRET_KEY=your_key

# RAG Configuration
EMBEDDING_MODEL=text-embedding-ada-002
RAG_SIMILARITY_THRESHOLD=0.3
RAG_MAX_RESULTS=5
```

## Testing Strategy

The test suite (`tests/` directory) covers progressively complex scenarios:

1. **Simple Requirements** - Direct capability mapping
2. **AI Coordination** - Multi-agent workflows
3. **Cross-System Integration** - Complex data flows
4. **Alternative Solutions** - Handling capability gaps
5. **Ambiguous Requests** - Natural language understanding

Run specific test scenarios:
```bash
pytest tests/test_simplified_nodes.py::test_clarification_node_needs_more_info
```

## Critical Implementation Notes

### State Transitions
The workflow always follows this progression:
```
CLARIFICATION → GAP_ANALYSIS → WORKFLOW_GENERATION → DEBUG → END
```

Each node can route back to previous stages if issues are found.

### RAG Integration Points
- **Clarification**: Retrieves similar workflows and capabilities
- **Gap Analysis**: Searches for alternative node combinations
- **Workflow Generation**: Fetches best practices and patterns

### Error Handling
- Graceful degradation when RAG is unavailable
- Fallback to basic capability matching
- Always maintains conversation continuity

## Common Development Tasks

### Adding New Node Types
1. Update `dsl/workflow-dsl.yaml` with node definition
2. Add knowledge entry in `scripts/insert_node_knowledge.py`
3. Run knowledge insertion script
4. Test with example workflows

### Debugging Workflows
1. Use `debug_server.py` for interactive testing
2. Check logs for stage transitions
3. Examine state at each node using breakpoints

### Modifying Intelligence Logic
1. Edit specific node methods in `agents/nodes.py`
2. Update prompts in `shared/prompts/workflow_agent/`
3. Test with scenarios from `tests/README.md`