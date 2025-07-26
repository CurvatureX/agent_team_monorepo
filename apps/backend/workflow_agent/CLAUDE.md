# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- **Project uses uv package manager** - backend directory has existing venv
- **Install dependencies:** `uv sync --group dev` (uses uv package manager, requires Python 3.13 compatible versions)
- **Activate environment:** `source venv/bin/activate` (or use uv commands directly)
- **Run tests:** `pytest` or `pytest tests/` (uses pytest with asyncio support)
- **Run single test:** `pytest tests/test_specific.py::test_function`
- **Code formatting:** `black .` (line length 100)
- **Import sorting:** `isort .` (black profile, line length 100)
- **Type checking:** `mypy .` (strict mode enabled)
- **Linting:** `flake8 .`

### LangGraph Development
- **Start LangGraph server:** `langgraph up` (uses langgraph.json config)
- **Debug server:** `python debug_server.py`
- **Main application:** `python main.py` (starts gRPC server)

### RAG System
- **Initialize node knowledge:** `python scripts/insert_node_knowledge.py`
- **Test RAG functionality:** `python scripts/insert_node_knowledge.py test`

## Architecture Overview

This is a sophisticated **AI workflow consultant** that transforms natural language requirements into executable workflow DSL through a multi-stage LangGraph state machine.

### Core Architecture Components

**1. Entry Points:**
- `main.py` - gRPC server startup
- `services/grpc_server.py` - gRPC service implementation (GenerateWorkflow, RefineWorkflow)

**2. Orchestration Layer:**
- `agents/workflow_agent.py` - LangGraph state machine definition
- `graph.py` - Graph configuration and state flow management

**3. State Management:**
- `agents/state.py` - Pydantic models for agent state
- Core state model: `MVPWorkflowState` tracks entire session lifecycle

**4. Intelligence Engines (the "brain"):**
- `IntelligentAnalyzer` - Parses requests and identifies capability gaps
- `IntelligentNegotiator` - Multi-turn dialogue for requirement clarification
- `IntelligentDesigner` - Generates technical architecture and workflow DSL

**5. RAG Knowledge System:**
- `core/vector_store.py` - Supabase pgvector integration for node knowledge
- `NodeKnowledgeRAG` - Retrieval-augmented generation for workflow recommendations
- RAG enhances all intelligence engines with best practices and examples

**6. Configuration & Infrastructure:**
- `core/config.py` - Environment and system configuration
- `core/prompt_engine.py` - Template management for AI prompts

### Workflow Generation Process

1. **Request Reception** → gRPC service receives natural language workflow request
2. **Intelligent Analysis** → `IntelligentAnalyzer` + RAG identifies capabilities and gaps
3. **Requirement Negotiation** → `IntelligentNegotiator` clarifies ambiguities via dialogue
4. **Technical Design** → `IntelligentDesigner` creates architecture and generates DSL
5. **Validation & Output** → Returns validated workflow DSL with optimization suggestions

### Key Technologies
- **LangGraph:** State machine orchestration
- **LangChain:** LLM integration (OpenAI, Anthropic)
- **Supabase + pgvector:** RAG knowledge base
- **gRPC:** Service interface
- **FastAPI:** Optional HTTP interface
- **Pydantic:** Data validation and state management

## Workflow DSL

The system outputs a custom YAML-like Domain Specific Language located in `dsl/`:
- Human-readable workflow definitions
- Extensive node type library (triggers, AI agents, external integrations, flow control)
- Maps to protobuf schema for execution
- See `dsl/README.md` and `dsl/examples.yaml` for detailed documentation

## Environment Configuration

Required environment variables:
```bash
# Supabase (RAG system)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SECRET_KEY=your_secret_key

# LLM APIs
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# RAG Configuration
EMBEDDING_MODEL=text-embedding-ada-002
RAG_SIMILARITY_THRESHOLD=0.3
RAG_MAX_RESULTS=5
```

## Testing Strategy

- Test files in `tests/` directory
- Manual testing scenarios documented in `tests/manual_prompting*.md`
- Test cases cover simple to complex workflows with capability gap handling
- RAG system has dedicated test scripts

## Code Style Requirements

- **Python 3.11+** required
- **Black formatting** (100 character line length)
- **Type hints required** (mypy strict mode)
- **Async/await patterns** throughout
- **Pydantic models** for all data structures
- **Structured logging** with structlog

## Important Implementation Notes

- The system is designed for **defensive workflow generation** - it identifies gaps and negotiates feasible solutions rather than generating potentially broken workflows
- RAG integration is critical - always consider existing node knowledge when making recommendations
- LangGraph state transitions are carefully designed - maintain state consistency across nodes
- Error handling includes graceful degradation when RAG services are unavailable
