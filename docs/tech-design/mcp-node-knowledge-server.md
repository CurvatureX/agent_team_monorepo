# MCP Node Knowledge Server - Tech Design

## Overview

This document outlines the technical design for an MCP (Model Context Protocol) server that provides workflow agent access to comprehensive node specifications knowledge. The server enables LLMs to query detailed information about available workflow nodes, including their parameters, input/output schemas, examples, and usage patterns.

## Problem Statement

The workflow agent needs access to detailed knowledge about available node types to generate accurate workflows from natural language descriptions. Currently, this information is stored in the `@apps/backend/shared/node_specs/` directory but is not easily accessible to the LLM during workflow generation.

## Architecture Overview

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Workflow Agent │───▶│ API Gateway     │───▶│ Node Knowledge  │
│   (LangGraph)   │    │  MCP Server     │    │   Repository    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────┐         ┌─────────────┐
                       │ MCP Tools   │         │ Node Specs  │
                       │ - get_nodes │         │ Registry    │
                       │ - get_node  │         │             │
                       │ - search    │         └─────────────┘
                       └─────────────┘
```

### Components

1. **MCP Server** - Extends existing API Gateway MCP implementation
2. **Node Knowledge Service** - Business logic for node spec queries
3. **Node Registry Integration** - Interface with existing node spec registry
4. **MCP Tools** - Specific tools for node knowledge access

## Detailed Design

### 1. MCP Tools Specification

#### Tool: `get_node_types`
**Purpose**: Get all available node types and their subtypes
```json
{
  "name": "get_node_types",
  "description": "Get all available workflow node types and their subtypes",
  "parameters": {
    "type": "object",
    "properties": {
      "type_filter": {
        "type": "string",
        "enum": ["ACTION_NODE", "TRIGGER_NODE", "AI_AGENT_NODE", "FLOW_NODE", "TOOL_NODE", "MEMORY_NODE", "HUMAN_LOOP_NODE", "EXTERNAL_ACTION_NODE"],
        "description": "Filter by node type (optional)"
      }
    }
  }
}
```

#### Tool: `get_node_details`
**Purpose**: Get comprehensive details for specific nodes
```json
{
  "name": "get_node_details",
  "description": "Get detailed specifications for one or more workflow nodes",
  "parameters": {
    "type": "object",
    "properties": {
      "nodes": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "node_type": {"type": "string"},
            "subtype": {"type": "string"}
          },
          "required": ["node_type", "subtype"]
        },
        "description": "List of nodes to get details for"
      },
      "include_examples": {
        "type": "boolean",
        "default": true,
        "description": "Include usage examples in response"
      },
      "include_schemas": {
        "type": "boolean",
        "default": true,
        "description": "Include input/output schemas"
      }
    },
    "required": ["nodes"]
  }
}
```

#### Tool: `search_nodes`
**Purpose**: Search nodes by capabilities or description
```json
{
  "name": "search_nodes",
  "description": "Search workflow nodes by functionality, description, or capabilities",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query (e.g., 'HTTP request', 'send email', 'process data')"
      },
      "max_results": {
        "type": "integer",
        "default": 10,
        "description": "Maximum number of results to return"
      },
      "include_details": {
        "type": "boolean",
        "default": false,
        "description": "Include full node specifications in results"
      }
    },
    "required": ["query"]
  }
}
```

### 2. Service Implementation

#### Node Knowledge Service
```python
# apps/backend/api-gateway/app/services/node_knowledge_service.py

from typing import List, Dict, Any, Optional
from apps.backend.shared.node_specs.registry import node_spec_registry
from apps.backend.shared.node_specs.base import NodeSpec

class NodeKnowledgeService:
    def __init__(self):
        self.registry = node_spec_registry

    def get_node_types(self, type_filter: Optional[str] = None) -> Dict[str, List[str]]:
        """Get all node types and subtypes, optionally filtered by type."""
        all_types = self.registry.get_node_types()

        if type_filter:
            return {k: v for k, v in all_types.items() if k == type_filter}

        return all_types

    def get_node_details(self, nodes: List[Dict[str, str]],
                        include_examples: bool = True,
                        include_schemas: bool = True) -> List[Dict[str, Any]]:
        """Get detailed specifications for requested nodes."""
        results = []

        for node_req in nodes:
            spec = self.registry.get_spec(node_req["node_type"], node_req["subtype"])
            if spec:
                result = self._serialize_node_spec(spec, include_examples, include_schemas)
                results.append(result)
            else:
                results.append({
                    "node_type": node_req["node_type"],
                    "subtype": node_req["subtype"],
                    "error": "Node specification not found"
                })

        return results

    def search_nodes(self, query: str, max_results: int = 10,
                    include_details: bool = False) -> List[Dict[str, Any]]:
        """Search nodes by description and capabilities."""
        all_specs = self.registry.list_all_specs()
        query_lower = query.lower()

        # Simple text search in description and parameter names
        matches = []
        for spec in all_specs:
            score = 0

            # Search in description
            if query_lower in spec.description.lower():
                score += 10

            # Search in parameter names and descriptions
            for param in spec.parameters:
                if query_lower in param.name.lower():
                    score += 5
                if query_lower in param.description.lower():
                    score += 3

            # Search in port names and descriptions
            for port in spec.input_ports + spec.output_ports:
                if query_lower in port.name.lower():
                    score += 3
                if query_lower in port.description.lower():
                    score += 2

            if score > 0:
                matches.append((spec, score))

        # Sort by relevance score and limit results
        matches.sort(key=lambda x: x[1], reverse=True)
        matches = matches[:max_results]

        # Format results
        results = []
        for spec, score in matches:
            if include_details:
                result = self._serialize_node_spec(spec, True, True)
                result["relevance_score"] = score
            else:
                result = {
                    "node_type": spec.node_type,
                    "subtype": spec.subtype,
                    "description": spec.description,
                    "relevance_score": score
                }
            results.append(result)

        return results

    def _serialize_node_spec(self, spec: NodeSpec, include_examples: bool,
                           include_schemas: bool) -> Dict[str, Any]:
        """Convert NodeSpec to serializable dictionary."""
        result = {
            "node_type": spec.node_type,
            "subtype": spec.subtype,
            "version": spec.version,
            "description": spec.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "required": p.required,
                    "default_value": p.default_value,
                    "description": p.description,
                    "enum_values": p.enum_values,
                    "validation_pattern": p.validation_pattern
                }
                for p in spec.parameters
            ],
            "input_ports": [
                {
                    "name": port.name,
                    "type": port.type,
                    "required": port.required,
                    "description": port.description,
                    "max_connections": port.max_connections,
                    "data_format": {
                        "mime_type": port.data_format.mime_type,
                        "schema": port.data_format.schema,
                        "examples": port.data_format.examples
                    } if port.data_format and include_schemas else None,
                    "validation_schema": port.validation_schema if include_schemas else None
                }
                for port in spec.input_ports
            ],
            "output_ports": [
                {
                    "name": port.name,
                    "type": port.type,
                    "description": port.description,
                    "max_connections": port.max_connections,
                    "data_format": {
                        "mime_type": port.data_format.mime_type,
                        "schema": port.data_format.schema,
                        "examples": port.data_format.examples
                    } if port.data_format and include_schemas else None,
                    "validation_schema": port.validation_schema if include_schemas else None
                }
                for port in spec.output_ports
            ]
        }

        if include_examples and spec.examples:
            result["examples"] = spec.examples

        return result
```

### 3. MCP Integration

#### Enhanced MCP Service
```python
# apps/backend/api-gateway/app/api/mcp/tools.py (enhancement)

from app.services.node_knowledge_service import NodeKnowledgeService

class EnhancedMCPService:
    def __init__(self):
        self.node_knowledge = NodeKnowledgeService()

    def get_available_tools(self) -> MCPToolsResponse:
        """Enhanced to include node knowledge tools."""
        tools = [
            # ... existing tools ...
            MCPTool(
                name="get_node_types",
                description="Get all available workflow node types and their subtypes",
                parameters={
                    "type": "object",
                    "properties": {
                        "type_filter": {
                            "type": "string",
                            "enum": ["ACTION_NODE", "TRIGGER_NODE", "AI_AGENT_NODE",
                                   "FLOW_NODE", "TOOL_NODE", "MEMORY_NODE",
                                   "HUMAN_LOOP_NODE", "EXTERNAL_ACTION_NODE"],
                            "description": "Filter by node type (optional)"
                        }
                    }
                },
                category="workflow",
                tags=["nodes", "workflow", "specifications"]
            ),
            MCPTool(
                name="get_node_details",
                description="Get detailed specifications for workflow nodes including parameters, ports, and examples",
                parameters={
                    "type": "object",
                    "properties": {
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "node_type": {"type": "string"},
                                    "subtype": {"type": "string"}
                                },
                                "required": ["node_type", "subtype"]
                            },
                            "description": "List of nodes to get details for"
                        },
                        "include_examples": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include usage examples"
                        },
                        "include_schemas": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include input/output schemas"
                        }
                    },
                    "required": ["nodes"]
                },
                category="workflow",
                tags=["nodes", "specifications", "details"]
            ),
            MCPTool(
                name="search_nodes",
                description="Search workflow nodes by functionality, description, or capabilities",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query describing desired functionality"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 10,
                            "description": "Maximum number of results"
                        },
                        "include_details": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include full specifications"
                        }
                    },
                    "required": ["query"]
                },
                category="workflow",
                tags=["search", "nodes", "discovery"]
            )
        ]
        # ... rest of method

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """Enhanced to handle node knowledge tools."""
        start_time = time.time()

        if tool_name == "get_node_types":
            type_filter = params.get("type_filter")
            result = self.node_knowledge.get_node_types(type_filter)

        elif tool_name == "get_node_details":
            nodes = params.get("nodes", [])
            include_examples = params.get("include_examples", True)
            include_schemas = params.get("include_schemas", True)
            result = self.node_knowledge.get_node_details(
                nodes, include_examples, include_schemas
            )

        elif tool_name == "search_nodes":
            query = params.get("query", "")
            max_results = params.get("max_results", 10)
            include_details = params.get("include_details", False)
            result = self.node_knowledge.search_nodes(
                query, max_results, include_details
            )

        else:
            # ... existing tool handling ...

        return MCPInvokeResponse(
            success=True,
            tool_name=tool_name,
            result=result,
            execution_time_ms=round((time.time() - start_time) * 1000, 2),
            timestamp=datetime.now(timezone.utc)
        )
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. **Create NodeKnowledgeService** in `apps/backend/api-gateway/app/services/`
2. **Update MCP tools** in `apps/backend/api-gateway/app/api/mcp/tools.py`
3. **Add dependency injection** for node registry access
4. **Create unit tests** for the service

### Phase 2: Tool Implementation
1. **Implement get_node_types tool** with category filtering
2. **Implement get_node_details tool** with comprehensive spec serialization
3. **Implement search_nodes tool** with relevance scoring
4. **Add integration tests** for MCP endpoints

### Phase 3: Optimization & Enhancement
1. **Add caching** for frequently accessed node specifications
2. **Implement semantic search** using embeddings for better node discovery
3. **Add node compatibility checking** tools
4. **Performance optimization** for large node registries

## Usage Examples

### Example 1: Get all available node types
```python
# MCP Tool call
{
  "tool_name": "get_node_types",
  "params": {}
}

# Response
{
  "ACTION_NODE": ["RUN_CODE", "HTTP_REQUEST", "PARSE_IMAGE", "WEB_SEARCH", "DATABASE_OPERATION", "FILE_OPERATION", "DATA_TRANSFORMATION"],
  "TRIGGER_NODE": ["TRIGGER_MANUAL", "TRIGGER_CRON", "TRIGGER_WEBHOOK", "TRIGGER_CHAT", "TRIGGER_EMAIL", "TRIGGER_FORM", "TRIGGER_CALENDAR"],
  "AI_AGENT_NODE": ["GEMINI_NODE", "OPENAI_NODE", "CLAUDE_NODE"],
  "FLOW_NODE": ["IF", "FILTER", "LOOP", "MERGE", "SWITCH", "WAIT"],
  "TOOL_NODE": ["TOOL_GOOGLE_CALENDAR_MCP", "CALENDAR", "EMAIL", "HTTP"],
  "MEMORY_NODE": ["MEMORY_VECTOR_STORE", "MEMORY_SIMPLE", "MEMORY_DOCUMENT", "MEMORY_BUFFER", "MEMORY_KNOWLEDGE", "MEMORY_EMBEDDING"],
  "HUMAN_LOOP_NODE": ["HUMAN_GMAIL", "HUMAN_SLACK", "HUMAN_DISCORD", "HUMAN_TELEGRAM", "HUMAN_APP"],
  "EXTERNAL_ACTION_NODE": ["EXTERNAL_GITHUB", "EXTERNAL_GOOGLE_CALENDAR", "EXTERNAL_TRELLO", "EXTERNAL_EMAIL", "EXTERNAL_SLACK", "EXTERNAL_API_CALL", "EXTERNAL_WEBHOOK", "EXTERNAL_NOTIFICATION"]
}
```

### Example 2: Get details for specific nodes
```python
# MCP Tool call
{
  "tool_name": "get_node_details",
  "params": {
    "nodes": [
      {"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"},
      {"node_type": "AI_AGENT_NODE", "subtype": "OPENAI_NODE"}
    ],
    "include_examples": true
  }
}

# Response includes full specifications with parameters, ports, examples
```

### Example 3: Search for nodes by functionality
```python
# MCP Tool call
{
  "tool_name": "search_nodes",
  "params": {
    "query": "send email notification",
    "max_results": 5
  }
}

# Response returns relevant nodes ranked by relevance score
```

## Security & Performance Considerations

### Security
- **Scope-based access control** using existing MCP authentication
- **No sensitive data exposure** in node specifications
- **Rate limiting** on search operations to prevent abuse

### Performance
- **Lazy loading** of node specifications
- **Response size optimization** with optional detail inclusion
- **Caching strategy** for frequently accessed specifications
- **Search index** for efficient node discovery

## Testing Strategy

### Unit Tests
- **NodeKnowledgeService** methods with mock node registry
- **Serialization accuracy** for complex node specifications
- **Search relevance** scoring validation
- **Error handling** for invalid requests

### Integration Tests
- **MCP tool invocation** end-to-end workflows
- **Large registry performance** with all node types loaded
- **Authentication and authorization** with API keys
- **Error responses** for malformed requests

## Monitoring & Observability

### Metrics
- **Tool invocation frequency** by tool type
- **Response times** for different query types
- **Cache hit rates** for node specifications
- **Search query patterns** and effectiveness

### Logging
- **Tool usage tracking** with anonymized query patterns
- **Performance monitoring** for slow queries
- **Error tracking** with detailed context
- **Cache performance** metrics

## Future Enhancements

### Semantic Search
- **Embedding-based search** for better node discovery
- **Natural language queries** for complex node requirements
- **Similarity recommendations** for related nodes

### Advanced Features
- **Node compatibility validation** tools
- **Workflow template generation** based on available nodes
- **Usage analytics** and recommendation engine
- **Custom node specification** support

## Conclusion

This MCP Node Knowledge Server design provides a comprehensive solution for giving workflow agents access to detailed node specifications. The implementation leverages existing infrastructure while adding powerful discovery and query capabilities through well-defined MCP tools.

The phased implementation approach ensures incremental value delivery while maintaining system stability. The design supports future enhancements like semantic search and advanced analytics while providing immediate value through basic node discovery and specification access.
