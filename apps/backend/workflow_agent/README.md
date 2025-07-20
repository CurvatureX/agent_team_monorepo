# Workflow Agent

## Overview

The `workflow_agent` is an advanced AI system designed to act as an **intelligent workflow consultant**. It transforms natural language user requirements into a complete, executable workflow DSL (Domain Specific Language). This is achieved through a multi-stage, stateful process managed by a `langgraph` state machine, which orchestrates a series of specialized intelligent engines.

The system moves beyond simple code generation by first negotiating a feasible set of requirements with the user before designing and generating the final workflow.

## Core Components & Flow

The agent's architecture is composed of several key components that work together to deliver an intelligent and interactive workflow design experience.

### 1. Entrypoint (`main.py`, `services/grpc_server.py`)
The service is exposed via a gRPC server.
- **`main.py`**: Starts the gRPC server.
- **`services/grpc_server.py`**: Implements the gRPC service methods (`GenerateWorkflow`, `RefineWorkflow`), handling the translation between protobuf messages and the system's internal data models.

### 2. Orchestration (`agents/workflow_agent.py`, `core/design_engine.py`)
- **`WorkflowAgent`**: Defines the high-level `langgraph` state machine, outlining the major stages of the generation process (e.g., `initialize_session`, `requirement_negotiation`, `design`) and the transitions between them.
- **`WorkflowOrchestrator`**: The central coordinator, directed by the `WorkflowAgent`. It manages the session state and invokes the appropriate intelligent engines for the current stage.

### 3. State Management (`agents/state.py`, `core/mvp_models.py`)
These files define the Pydantic data models for the agent's state.
- **`MVPWorkflowState`**: The primary model that holds all information for a session, including negotiation history, design artifacts, and final results.

### 4. Intelligence Engines (`core/intelligence.py`, `core/design_engine.py`)
This is the "brain" of the agent, composed of three distinct engines:
- **`IntelligentAnalyzer`**: The "ears." It parses the initial user request to understand intent and uses the `LLMCapabilityScanner` to perform a detailed analysis of required vs. available capabilities, identifying any gaps.
- **`IntelligentNegotiator`**: The "mouth." If gaps or ambiguities are found, this engine engages in a multi-turn dialogue with the user to clarify requirements, present tradeoffs, and guide them to a feasible solution.
- **`IntelligentDesigner`**: The "creator." Once requirements are finalized, this engine designs the technical architecture, decomposes the work into a task tree, applies relevant design patterns, and generates the final, optimized workflow DSL.

### 5. Knowledge & RAG (`core/vector_store.py`)
The agent's long-term memory and knowledge base.
- **`SupabaseVectorStore`**: A client for `pgvector` in Supabase, used to store and retrieve "node knowledge"—information about different workflow components, their capabilities, and best practices.
- **`NodeKnowledgeRAG`**: A Retrieval-Augmented Generation (RAG) service that enhances the intelligence engines by providing them with relevant context, examples, and best practices from the vector store.

### 6. Output (`dsl/`)
The final output is a human-readable workflow defined in a custom Domain Specific Language (DSL). The `dsl` directory contains the specification and examples of this language.

## How It Works: The Generation Process

1.  A user request to generate a workflow is received by the **gRPC server**.
2.  The **`WorkflowAgent`** state machine is invoked, and the **`WorkflowOrchestrator`** initializes a new session.
3.  **Negotiation Stage**: The `IntelligentAnalyzer` parses the request, and the `LLMCapabilityScanner` (powered by the RAG system) identifies any gaps between the user's needs and the system's capabilities. If gaps exist, the `IntelligentNegotiator` starts a dialogue to resolve them.
4.  **Design Stage**: Once requirements are confirmed, the `IntelligentDesigner` takes over to create the technical design, task tree, and final architecture.
5.  **Validation & Completion**: The generated workflow DSL is validated, and the final result, along with any optimization suggestions, is returned to the user.
