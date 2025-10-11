# Node-to-Node Communication Protocol

## 1. Executive Summary

This document describes the data flow and communication protocol between different node types in the workflow engine v2. The protocol is **implicit rather than standardized**, relying on dictionary-based data passing with flexible field extraction patterns. The engine uses conversion functions on connections to transform data between nodes when explicit mapping is required.

### Key Architectural Decisions

- **No Standardized Message Format**: Unlike the original design concept, the implementation does **not** use a `StandardMessage` dataclass
- **Dictionary-Based Communication**: Nodes communicate via Python dictionaries passed through the `{"result": data}` structure
- **Flexible Field Extraction**: Nodes extract data using multiple fallback field names (e.g., "message", "user_message", "content", etc.)
- **Connection-Level Conversion**: Data transformation happens via optional `conversion_function` on Connection objects
- **JSON Response Parsing**: AI agents automatically parse JSON responses to make structured data accessible to downstream nodes

### Technology Stack

- **Execution Engine**: Custom Python execution engine with dependency graph resolution
- **Data Flow**: Dictionary-based parameter passing through `pending_inputs` tracking
- **Conversion Functions**: Dynamic Python code execution with restricted namespace for security
- **Graph Structure**: `WorkflowGraph` with adjacency lists tracking connections and conversion functions

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Trigger    │────▶│    AI Agent      │────▶│ External Action  │
│   Node       │     │  (Gemini/OpenAI) │     │  (Slack/Email)   │
└──────────────┘     └──────────────────┘     └──────────────────┘
       │                      │                         │
       └──────────── pending_inputs tracking ───────────┘
                    {"result": data_dict}
```

**Key Components:**
- **ExecutionEngine**: Manages workflow execution, node scheduling, and data flow
- **WorkflowGraph**: Directed graph representing workflow structure with conversion functions
- **NodeRunner**: Base interface for node execution (no standardized output format)
- **Connection**: Edges with optional `conversion_function` for data transformation

### 2.2 Component Architecture

**Workflow Execution Flow:**
1. Graph construction with cycle detection
2. Topological ordering for dependency resolution
3. Node readiness checking (at least one predecessor has provided data)
4. Data propagation through `pending_inputs` dictionary
5. Optional conversion function execution on connection edges
6. Output shaping according to node spec `output_params`

## 3. Data Architecture

### 3.1 Data Flow Model

**Core Data Passing Structure:**
```python
# Data passed between nodes via "result" key
runner_output = {"result": output_data}

# Output data structure (varies by node type)
output_data = {
    "field1": value1,
    "field2": value2,
    # ... node-specific fields
}
```

**No Unified Message Format:**
- **AI Agent Output**: `{"result": {"response": str, "model": str, "parsed_json": dict, ...}}`
- **External Action Output**: `{"result": {"success": bool, "message_ts": str, "error_message": str, ...}}`
- **Memory Node Output**: `{"result": {"success": bool, "context": str, "messages": list, ...}}`
- **Tool Node Output**: `{"result": {"success": bool, "functions": list, ...}}`

### 3.2 Connection-Based Data Transformation

**Connection Structure:**
```python
@dataclass
class Connection:
    from_node: str
    to_node: str
    output_key: str = "result"  # Which output port to use
    conversion_function: Optional[str] = None  # Python code as string
```

**Conversion Function Format:**
```python
# Lambda function
"lambda input_data: {'transformed_field': input_data.get('original_field')}"

# Named function
"""
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'message': input_data.get('response') or input_data.get('content'),
        'channel': input_data.get('channel_override') or '#general'
    }
"""
```

## 4. Implementation Details

### 4.1 AI Agent Output Format

**OpenAI/Gemini/Anthropic Runners:**
```python
# Output structure from ai_openai.py, ai_gemini.py
output = {
    "content": ai_response,              # Clean AI text response
    "metadata": {                        # Provider metadata
        "model": "gpt-5-nano",
        "finish_reason": "stop",
        "system_fingerprint": "..."
    },
    "format_type": "text",               # text, json, schema
    "source_node": node.id,              # Tracing
    "timestamp": "2025-01-28T10:30:00Z", # ISO timestamp
    "token_usage": {                     # Token tracking
        "prompt_tokens": 50,
        "completion_tokens": 100,
        "total_tokens": 150
    },
    "function_calls": []                 # MCP tool invocations
}

return {"result": output}
```

**Legacy AI Runner (ai.py):**
```python
# Output structure from ai.py
output = {
    "input": inputs.get("result", inputs),
    "model": model_name,
    "response": ai_response,             # Main response text
    "output": ai_response,               # Standardized field
    "parsed_json": {...},                # If response is valid JSON
    "provider_result": {...},            # Full provider response
    "memory_enhanced": True/False,
    "tools_available": True/False,
    "_details": {...},                   # Execution metadata
    "_tokens": {...}                     # Token usage
}

return {"result": output}
```

**No Unified Response Parsing:**
- OpenAI/Gemini runners return raw `content` field
- Legacy AI runner attempts JSON parsing and merges fields into top-level output
- **No `_parse_ai_response()` method** in OpenAI/Gemini runners
- Downstream nodes must handle various field name variations

### 4.2 External Action Input Handling

**Slack External Action (slack_external_action.py):**
```python
# Input extraction from context.input_data
def _send_message(self, context):
    # Extract message from input_data
    message = context.input_data.get("message", "")
    blocks = context.input_data.get("blocks", [])
    channel = self._get_channel(context)

    # No standardized format - direct field access
    kwargs = {
        "channel": channel,
        "text": message,
        "blocks": blocks if blocks else None,
        # ...
    }
```

**Input Field Priority:**
```python
# Channel extraction with fallbacks
channel = (
    context.input_data.get("channel_override") or
    context.input_data.get("channel") or
    context.node.configurations.get("channel", "#general")
)
```

**External Action Output:**
```python
# Slack success output
{
    "success": True,
    "message_ts": "1234567890.123456",
    "channel_id": "C123456",
    "response_data": {...},  # Full Slack API response
    "error_message": "",
    "api_response": {...}
}

# Slack error output
{
    "success": False,
    "message_ts": "",
    "channel_id": "",
    "response_data": {},
    "error_message": "Clear error description",
    "api_response": {}
}
```

### 4.3 Field Extraction Patterns

**AI Agent User Message Extraction:**
```python
# From ai_openai.py, ai_gemini.py, ai.py
def _extract_user_prompt(self, main_input):
    if isinstance(main_input, str):
        return main_input

    # Try common field names in priority order
    for key in ["user_prompt", "message", "user_message", "user_input",
                "input", "query", "text", "content"]:
        if key in main_input and main_input[key]:
            return str(main_input[key])

    # Fallback to dict string representation
    if isinstance(main_input, dict) and main_input:
        return str(main_input)

    return ""
```

**Trigger Data Extraction:**
```python
def _extract_message_from_trigger(self, trigger):
    if not trigger or not trigger.trigger_data:
        return ""

    data = trigger.trigger_data

    # Try direct fields
    for key in ["message", "user_message", "user_input", "text", "content"]:
        if key in data and isinstance(data[key], str) and data[key].strip():
            return data[key].strip()

    # Slack event structure
    event = data.get("event")
    if isinstance(event, dict):
        text = event.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()

    return ""
```

## 5. Data Transformation System

### 5.1 Conversion Function Execution

**Location**: `workflow_engine_v2/core/engine.py`

```python
def execute_conversion_function_flexible(
    conversion_function: str,
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute conversion function with security restrictions."""

    # Create restricted namespace (safe builtins only)
    namespace = {
        "Dict": Dict, "Any": Any,
        "__builtins__": {
            "len": len, "str": str, "int": int, "float": float,
            "bool": bool, "list": list, "dict": dict, "range": range,
            "enumerate": enumerate, "zip": zip, "max": max, "min": min,
            "sum": sum, "abs": abs, "round": round, "sorted": sorted,
            "any": any, "all": all, "isinstance": isinstance, "type": type
        }
    }

    # Execute function (lambda or def)
    if conversion_function.strip().startswith("lambda"):
        func = eval(conversion_function, namespace)
        result = func(input_data)
    else:
        exec(conversion_function, namespace)
        # Find the function in namespace
        func = next(obj for name, obj in namespace.items()
                    if callable(obj) and not name.startswith("_"))
        result = func(input_data)

    # Ensure dict result
    return result if isinstance(result, dict) else {"converted_data": result}
```

**Conversion Application in Data Propagation:**
```python
# From engine.py line 862-876
for successor_node, output_key, conversion_function in graph.successors(current_node_id):
    value = shaped_outputs.get(output_key)

    # Apply conversion function if provided
    if conversion_function and isinstance(conversion_function, str):
        try:
            raw_value = raw_outputs.get(output_key)
            converted_data = execute_conversion_function_flexible(
                conversion_function,
                {"value": raw_value, "data": raw_value, "output": raw_value}
            )
            value = converted_data
        except Exception as e:
            print(f"Conversion function failed: {e}")
            # Keep original value on error

    # Propagate to successor's pending_inputs
    successor_node_inputs[input_key] = value
```

### 5.2 Output Shaping

**Node Spec Output Enforcement:**
```python
# From engine.py line 628-651
def _shape_payload(payload: Any) -> Dict[str, Any]:
    """Enforce output matches node spec output_params."""

    # Get allowed fields from node spec
    spec = get_spec(node.type, node.subtype)
    allowed_defaults = getattr(spec, "output_params", {}) or {}

    if not isinstance(allowed_defaults, dict):
        return payload if isinstance(payload, dict) else {}

    shaped = {}
    if isinstance(payload, dict):
        # Only include fields defined in spec with defaults
        for k, default_val in allowed_defaults.items():
            shaped[k] = payload.get(k, default_val)
    else:
        # Primitive payload goes to 'data' field if defined
        if "data" in allowed_defaults:
            shaped = {k: (payload if k == "data" else v)
                     for k, v in allowed_defaults.items()}
        else:
            shaped = dict(allowed_defaults)

    return shaped

# Apply shaping to all output ports
shaped_outputs = {
    port: _shape_payload(payload)
    for port, payload in sanitized_outputs.items()
}
```

## 6. Data Flow Examples

### 6.1 AI Agent → Slack Integration

**Scenario**: AI generates response, Slack node sends message

**Step 1: AI Agent Execution**
```python
# AI agent output (from ai_openai.py)
{
    "content": "Customer issue has been resolved. Ticket #12345 is now closed.",
    "metadata": {
        "model": "gpt-5-nano",
        "finish_reason": "stop"
    },
    "format_type": "text",
    "source_node": "ai_agent_1",
    "timestamp": "2025-01-28T14:30:00Z",
    "token_usage": {
        "prompt_tokens": 45,
        "completion_tokens": 20,
        "total_tokens": 65
    }
}
```

**Step 2: Conversion Function (if needed)**
```python
# Connection conversion_function to map AI output to Slack input
"""
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'message': input_data.get('content') or input_data.get('response'),
        'channel': '#support',
        'blocks': []
    }
"""
```

**Step 3: Slack Node Receives Input**
```python
# Slack node context.input_data after conversion
{
    "message": "Customer issue has been resolved. Ticket #12345 is now closed.",
    "channel": "#support",
    "blocks": []
}
```

**Step 4: Slack Node Output**
```python
{
    "success": True,
    "message_ts": "1234567890.123456",
    "channel_id": "C123456",
    "response_data": {"ok": True, "ts": "...", "channel": "..."},
    "error_message": "",
    "api_response": {...}
}
```

### 6.2 Multi-Node Data Flow

**Without Conversion Functions:**
```
[Trigger] → {"result": {"message": "Hello"}}
    ↓
[AI Agent] → {"result": {"content": "AI response", "metadata": {...}}}
    ↓
[Slack] → Extracts: input_data.get("content") or input_data.get("message")
    ↓
[Slack Output] → {"result": {"success": True, "message_ts": "..."}}
```

**With Conversion Functions:**
```
[AI Agent] → {"result": {"response": "..."}}
    ↓ [conversion_function on connection]
    λ input_data: {"message": input_data.get("response")}
    ↓
[Email] → {"result": {"message": "...", "channel": "..."}}
```

## 7. System Interactions

### 7.1 Internal Data Flow Mechanism

**Pending Inputs Tracking:**
```python
# From engine.py initialization
pending_inputs: Dict[str, Dict[str, Any]] = {
    node_id: {} for node_id in graph.nodes.keys()
}

# Data propagation (line 859-889)
for successor_node, output_key, conversion_function in graph.successors(current_node_id):
    value = shaped_outputs.get(output_key)

    # Apply conversion if provided
    if conversion_function:
        value = execute_conversion_function_flexible(conversion_function,
                                                      {"value": value, "data": value})

    # Accumulate inputs for successor
    successor_node_inputs = pending_inputs.setdefault(successor_node, {})
    input_key = "result"  # Default input key

    if input_key in successor_node_inputs:
        # Multiple inputs: convert to list
        existing = successor_node_inputs[input_key]
        if isinstance(existing, list):
            existing.append(value)
        else:
            successor_node_inputs[input_key] = [existing, value]
    else:
        successor_node_inputs[input_key] = value
```

**Node Readiness Check:**
```python
def _is_node_ready(self, graph, node_id, pending_inputs):
    """Node is ready when at least one predecessor provided data."""
    predecessors = list(graph.predecessors(node_id))

    # No predecessors = ready (e.g., trigger nodes)
    if not predecessors:
        return True

    # Check if any input has been provided
    provided = pending_inputs.get(node_id, {})
    return len(provided) > 0
```

### 7.2 Graph Structure

**WorkflowGraph Implementation:**
```python
class WorkflowGraph:
    """Directed graph with conversion functions on edges."""

    def __init__(self, workflow: Workflow):
        # Adjacency list: node_id -> [(to_node, output_key, conversion_fn)]
        self.adjacency_list: Dict[str, List[Tuple[str, str, Optional[str]]]]
        self.reverse_adjacency_list: Dict[str, List[Tuple[str, str, Optional[str]]]]

        # Build from connections
        for c in workflow.connections:
            output_key = getattr(c, "output_key", "result")
            self.adjacency_list[c.from_node].append(
                (c.to_node, output_key, c.conversion_function)
            )
```

**Topological Execution Order:**
```python
def topo_order(self) -> List[str]:
    """Kahn's algorithm with cycle detection."""
    in_degree_map = dict(self._in_degree)
    queue = deque([node_id for node_id, deg in in_degree_map.items() if deg == 0])
    order = []

    while queue:
        current_node = queue.popleft()
        order.append(current_node)

        for successor, _output_key, _conversion in self.adjacency_list[current_node]:
            in_degree_map[successor] -= 1
            if in_degree_map[successor] == 0:
                queue.append(successor)

    if len(order) != len(self.nodes):
        raise CycleError("Workflow graph contains a cycle")

    return order
```

## 8. Non-Functional Requirements

### 8.1 Performance

**Performance Characteristics:**
- **Conversion Function Execution**: \<1ms for typical transformations
- **Output Shaping**: O(n) where n = number of output fields
- **Graph Construction**: O(V + E) where V = nodes, E = connections
- **Topological Sort**: O(V + E) with cycle detection

**Optimization Strategies:**
- Node outputs cached in `execution_context.node_outputs[node_id]`
- Graph structure pre-computed before execution
- Conversion functions executed once per connection edge
- Restricted namespace reduces overhead in function execution

### 8.2 Security

**Conversion Function Sandboxing:**
- Restricted `__builtins__` with safe operations only
- No file system access (`open`, `file`, etc. blocked)
- No network access (`urllib`, `requests`, etc. blocked)
- No subprocess execution (`os.system`, `subprocess` blocked)
- No import capabilities (all modules must be pre-loaded)

**Security Measures:**
```python
# Allowed builtins
allowed_builtins = {
    "len", "str", "int", "float", "bool",
    "list", "dict", "range", "enumerate", "zip",
    "max", "min", "sum", "abs", "round",
    "sorted", "any", "all", "isinstance", "type"
}

# Namespace isolation
namespace = {
    "__builtins__": {k: builtins[k] for k in allowed_builtins}
}
```

### 8.3 Reliability

**Error Handling:**
```python
# Conversion function failure handling
try:
    converted_data = execute_conversion_function_flexible(
        conversion_function, input_data
    )
    value = converted_data
except Exception as e:
    print(f"Conversion function failed: {e}")
    # Keep original value on error
    value = original_value
```

**Fail-Fast Node Execution:**
```python
# Check for node failures via success field (line 668-718)
for port_data in shaped_outputs.values():
    if isinstance(port_data, dict) and port_data.get("success") is False:
        error_msg = port_data.get("error_message", "Node execution failed")

        # Mark node and workflow as failed
        node_execution.status = NodeExecutionStatus.FAILED
        workflow_execution.status = ExecutionStatus.ERROR

        # Stop execution immediately
        break
```

### 8.4 Testing & Observability

#### Testing Strategy

**Unit Testing:**
- Test conversion function execution with valid/invalid inputs
- Test output shaping with various node spec configurations
- Test field extraction patterns with multiple fallback scenarios
- Test graph construction and topological ordering

**Integration Testing:**
- Test end-to-end data flow AI → External Action
- Test conversion function transformations in real workflows
- Test error propagation and fail-fast behavior
- Test multiple input accumulation (fan-in scenarios)

**Example Test Patterns:**
```python
def test_ai_to_slack_data_flow():
    """Test AI agent output flows to Slack correctly."""
    # AI agent produces output
    ai_output = {
        "content": "Test message",
        "metadata": {"model": "gpt-5-nano"}
    }

    # Conversion function transforms
    conversion = "lambda data: {'message': data.get('content')}"
    result = execute_conversion_function_flexible(conversion, ai_output)

    assert result["message"] == "Test message"
```

#### Observability

**Logging Strategy:**
```python
# Backend developer logs (verbose, with emoji)
logger.info("=" * 80)
logger.info(f"🚀 Executing Node: {node.name}")
logger.info(f"   Type: {node.type}, Subtype: {node.subtype}")
logger.info(f"📥 Input Parameters: {clean_inputs}")
logger.info("=" * 80)

# Structured logging for production
logger.info(
    "node_execution_start",
    extra={
        "node_id": node_id,
        "node_type": node.type,
        "input_size": len(str(inputs))
    }
)
```

**Key Metrics:**
- Node execution duration (`node_execution.duration_ms`)
- Token usage tracking (`workflow_execution.tokens_used`)
- Credits consumed (`node_execution.credits_consumed`)
- Conversion function failures (logged but not tracked as metric)

**Distributed Tracing:**
- Execution ID tracking across all nodes
- Node activation IDs for parallel execution tracking
- Parent activation IDs for fan-out lineage tracking
- Execution sequence array preserves order

#### Monitoring & Alerting

**Dashboard Metrics:**
- Workflow execution success rate
- Average node execution time by type
- Conversion function failure rate
- Output shaping validation failures

**Alert Thresholds:**
- Conversion function failure rate \> 5%
- Node execution timeout rate \> 10%
- Memory exhaustion during execution
- Cycle detection in workflow graph

**SLIs and SLOs:**
- **SLI**: 95th percentile workflow execution time \< 30s
- **SLI**: Conversion function execution success rate \>= 98%
- **SLO**: 99.9% uptime for workflow execution engine
- **SLO**: Data loss rate = 0% (all execution state persisted)

## 9. Technical Debt and Future Considerations

### 9.1 Known Limitations

**No Standardized Communication Protocol:**
- Each node type uses different output field names
- Downstream nodes must implement flexible field extraction
- Conversion functions required for most cross-node-type connections
- Difficult to validate data contracts at design time

**Conversion Function Limitations:**
- No type checking or validation before execution
- Error messages are minimal (just prints to console)
- No debugging capabilities for conversion functions
- Limited to synchronous transformations only

**Field Extraction Brittleness:**
- Multiple fallback field names create maintenance burden
- No schema validation for node inputs/outputs
- Different runners use inconsistent field names
- AI response parsing is inconsistent across providers

### 9.2 Areas for Improvement

**Standardized Message Format:**
- Implement true `StandardMessage` dataclass for node communication
- Enforce consistent field names across all node types
- Add schema validation using Pydantic models
- Provide automatic migration from legacy formats

**Enhanced Conversion Functions:**
- Add conversion function validation before workflow execution
- Provide better error messages with line numbers
- Implement conversion function testing/debugging tools
- Support async conversion functions for I/O operations

**Type Safety:**
- Add Pydantic models for all node inputs/outputs
- Implement compile-time type checking for conversions
- Generate TypeScript types for frontend integration
- Validate data contracts at workflow save time

### 9.3 Planned Enhancements

**Q2 2025:**
- Implement `StandardMessage` dataclass for core node types
- Add conversion function validation with detailed error reporting
- Migrate AI agent runners to consistent output format

**Q3 2025:**
- Add schema validation for all node inputs/outputs
- Implement conversion function debugging tools
- Provide auto-generated conversion function templates

**Q4 2025:**
- Complete migration to standardized communication protocol
- Add GraphQL-style schema introspection for nodes
- Implement visual conversion function editor in frontend

### 9.4 Migration Paths

**Phase 1: Standardization (Q2 2025)**
```python
@dataclass
class StandardMessage:
    """Unified message format for node communication."""
    content: Any                                # Primary payload
    metadata: Dict[str, Any] = field(default_factory=dict)
    format_type: str = "text"                  # text, json, binary
    source_node: Optional[str] = None
    timestamp: Optional[str] = None
```

**Phase 2: Backward Compatibility (Q3 2025)**
- Implement adapter layer for legacy field extraction
- Provide automatic wrapping/unwrapping of StandardMessage
- Maintain support for direct dictionary passing

**Phase 3: Full Migration (Q4 2025)**
- Deprecate legacy field extraction patterns
- Enforce StandardMessage for all new workflows
- Migrate existing workflows through automated tools

## 10. Appendices

### A. Glossary

- **Conversion Function**: Python code (lambda or def) executed on connection edges to transform data
- **Output Shaping**: Process of enforcing node spec output_params on raw node output
- **Pending Inputs**: Dictionary tracking accumulated inputs for each node awaiting execution
- **Field Extraction**: Pattern of trying multiple field names to find data (e.g., "message", "content", "text")
- **Graph Successor**: Node that receives data from current node via connection edge
- **Output Key**: Connection parameter specifying which output port to use (default: "result")
- **Shaped Outputs**: Node outputs after enforcing spec-defined fields with defaults
- **Raw Outputs**: Original node output before shaping (used for conversion functions)

### B. References

**Source Code:**
- `/apps/backend/workflow_engine_v2/core/engine.py` - Main execution engine
- `/apps/backend/workflow_engine_v2/core/graph.py` - Graph structure and traversal
- `/apps/backend/workflow_engine_v2/runners/ai_openai.py` - OpenAI runner implementation
- `/apps/backend/workflow_engine_v2/runners/ai_gemini.py` - Gemini runner implementation
- `/apps/backend/workflow_engine_v2/runners/ai.py` - Legacy AI runner
- `/apps/backend/workflow_engine_v2/runners/external_actions/slack_external_action.py` - Slack integration

**Related Documentation:**
- `/docs/tech-design/new_workflow_spec.md` - Complete workflow data models
- `/docs/tech-design/node-structure.md` - Node architecture specification
- `/docs/tech-design/workflow-engine-architecture.md` - Engine architecture overview
- `/apps/backend/CLAUDE.md` - Backend development guide

**External Resources:**
- Python `exec()` and `eval()` security best practices
- Kahn's algorithm for topological sorting
- Directed acyclic graph (DAG) execution patterns

---

**Document Version**: 2.0
**Created**: 2025-01-28
**Last Updated**: 2025-10-11
**Author**: Claude Code (Technical Design Documentation Specialist)
**Status**: Implementation Analysis Complete
**Next Review**: 2025-11-11
