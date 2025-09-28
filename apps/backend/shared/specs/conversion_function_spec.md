# Conversion Function Specification

## Overview

The `conversion_function` field in workflow connections enables data transformation between nodes. This specification defines the consistent format and supported transformation types.

## Format Structure

The `conversion_function` field should be a JSON string with the following structure:

```json
{
  "type": "transformation_type",
  "script": "transformation_logic",
  "options": {}
}
```

## Supported Transformation Types

### 1. Pass-Through (`passthrough`)
No transformation - data passes through unchanged.

```json
{
  "type": "passthrough"
}
```

### 2. Field Mapping (`mapping`)
Maps input fields to output fields with optional transformations.

```json
{
  "type": "mapping",
  "script": {
    "output_field": "input_field",
    "message": "text",
    "channel": "#general"
  }
}
```

### 3. JQ Transformation (`jq`)
Uses JQ-style queries for complex data manipulation.

```json
{
  "type": "jq",
  "script": ".data | {message: .content, timestamp: now}"
}
```

### 4. JSONPath (`jsonpath`)
Extracts data using JSONPath expressions.

```json
{
  "type": "jsonpath",
  "script": "$.response.data[*].message"
}
```

### 5. Python Expression (`python`)
Limited Python expressions for calculations (security-restricted).

```json
{
  "type": "python",
  "script": "{'formatted_message': f'🎭 {data.get(\"output\", \"\")} 🎭'}"
}
```

## Implementation in Workflow Engine

The workflow engine executor should:

1. Parse the `conversion_function` JSON string
2. Identify the transformation type
3. Apply the appropriate transformation method
4. Return the transformed data

### Example Implementation

```python
async def apply_conversion_function(self, data: Dict[str, Any], conversion_function: str) -> Dict[str, Any]:
    """Apply conversion function to transform data between nodes."""
    if not conversion_function:
        return data

    try:
        conversion_spec = json.loads(conversion_function)
        transform_type = conversion_spec.get("type", "passthrough")
        script = conversion_spec.get("script", "")

        if transform_type == "passthrough":
            return data
        elif transform_type == "mapping":
            return await self._apply_field_mapping(data, script)
        elif transform_type == "jq":
            return await self._apply_jq_transform(data, script)
        elif transform_type == "jsonpath":
            return await self._apply_jsonpath_transform(data, script)
        elif transform_type == "python":
            return await self._apply_python_transform(data, script)
        else:
            logger.warning(f"Unknown conversion function type: {transform_type}")
            return data

    except Exception as e:
        logger.error(f"Conversion function failed: {e}")
        return data  # Fallback to original data
```

## Usage Examples

### Example 1: AI Agent to Slack
Transform AI output to Slack message format:

```json
{
  "id": "conn_ai_to_slack",
  "from_node": "ai_agent_1",
  "to_node": "slack_1",
  "from_port": "output",
  "to_port": "input",
  "conversion_function": "{\"type\": \"mapping\", \"script\": {\"text\": \"output\", \"channel\": \"#general\", \"username\": \"JokeBot\"}}"
}
```

### Example 2: Trigger to AI Agent
Add context to trigger data:

```json
{
  "id": "conn_trigger_to_ai",
  "from_node": "trigger_1",
  "to_node": "ai_agent_1",
  "from_port": "output",
  "to_port": "input",
  "conversion_function": "{\"type\": \"python\", \"script\": \"{'user_input': data.get('message', 'Tell me a joke'), 'context': 'joke_generation'}\"}"
}
```

### Example 3: Complex Data Extraction
Extract specific fields from API response:

```json
{
  "id": "conn_api_to_process",
  "from_node": "api_call_1",
  "to_node": "process_1",
  "from_port": "output",
  "to_port": "input",
  "conversion_function": "{\"type\": \"jq\", \"script\": \".response.data | {items: map({id: .id, name: .name, status: .status})}\"}"
}
```

## Security Considerations

- **Python expressions**: Restricted to safe operations, no imports, no file access
- **Input validation**: All conversion functions should validate input data
- **Error handling**: Graceful fallback to original data on conversion errors
- **Timeout protection**: Long-running conversions should have timeouts

## Integration with Current Workflow Engine

This specification builds on the existing transformation logic in `workflow_engine/nodes/action_node.py`. The conversion function execution should be integrated into the executor's data flow logic between nodes.
