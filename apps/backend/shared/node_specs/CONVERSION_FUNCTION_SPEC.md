# Conversion Function Specification

## Overview

The `conversion_function` field in workflow connections enables data transformation between nodes using strictly defined Python anonymous functions stored as strings in the database.

**IMPORTANT: `conversion_function` is a REQUIRED field for all connections. Even when no transformation is needed, you must provide a passthrough function.**

## Required Format

**Strict Function Signature:**
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return transformed_data
```

## Rules and Constraints

### 1. Function Structure
- **Function Name**: Must be exactly `convert`
- **Parameter**: Single parameter `input_data` with type `Dict[str, Any]`
- **Return Type**: Must return `Dict[str, Any]`
- **Storage**: String format that can be saved to database

### 2. Security Restrictions
- **No imports allowed**: Function must use only built-in Python functions
- **Restricted namespace**: Only safe built-ins are available
- **No file system access**: Cannot read/write files
- **No network access**: Cannot make HTTP requests
- **No external libraries**: Only pure Python syntax

### 3. Available Built-ins
```python
# Available functions in conversion functions:
len, str, int, float, bool, list, dict, range, enumerate, zip,
max, min, sum, abs, round
```

## Examples

### 1. Pass-through (No Transformation)
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return input_data
```

### 2. AI Agent to Slack Formatting
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": f"🎭 {input_data.get('output', '')} 🎭",
        "channel": "#general",
        "username": "JokeBot"
    }
```

### 3. Trigger to AI Agent Input
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_input": input_data.get("message", "Tell me a joke"),
        "context": "joke_generation"
    }
```

### 4. Extract Specific Fields
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message": input_data.get("output", ""),
        "timestamp": str(input_data.get("timestamp", "")),
        "status": "processed"
    }
```

### 5. Data Validation and Defaults
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "email": input_data.get("email", "").lower().strip(),
        "priority": "high" if input_data.get("urgent", False) else "normal",
        "tags": input_data.get("tags", [])[:5]  # Limit to 5 tags
    }
```

## Implementation in Workflow Engine

### Execution Flow
1. **Validation**: Check function format using `validate_conversion_function()`
2. **Compilation**: Compile the function string to verify syntax
3. **Execution**: Run the function in a restricted namespace
4. **Error Handling**: Return original data if conversion fails

### Integration Example
```python
# In workflow executor
def apply_connection_conversion(self, connection: Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    if connection.conversion_function:
        from shared.node_specs.base import execute_conversion_function
        return execute_conversion_function(connection.conversion_function, data)
    return data
```

## Validation and Testing

### Valid Function Examples
```python
# ✅ Valid - correct signature and return type
"def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return input_data"

# ✅ Valid - transformation with safe operations
"def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return {'result': str(input_data)}"

# ✅ Valid - conditional logic
"def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return {'message': input_data['text'] if 'text' in input_data else 'No message'}"
```

### Invalid Function Examples
```python
# ❌ Invalid - wrong function name
"def transform(input_data: Dict[str, Any]) -> Dict[str, Any]: return input_data"

# ❌ Invalid - wrong parameter type
"def convert(data: str) -> Dict[str, Any]: return {'data': data}"

# ❌ Invalid - wrong return type
"def convert(input_data: Dict[str, Any]) -> str: return 'transformed'"

# ❌ Invalid - imports not allowed
"import json\ndef convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return json.loads(input_data)"

# ❌ Invalid - file access not allowed
"def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: open('file.txt', 'w').write('data'); return input_data"
```

## Database Storage

The conversion function is stored as a `TEXT` field in the database:

```sql
-- Example database schema
CREATE TABLE workflow_connections (
    id UUID PRIMARY KEY,
    from_node VARCHAR(255) NOT NULL,
    to_node VARCHAR(255) NOT NULL,
    from_port VARCHAR(255) NOT NULL,
    to_port VARCHAR(255) NOT NULL,
    conversion_function TEXT NULL  -- Stores the Python function as string
);
```

## Error Handling

### Execution Failures
- **Syntax Errors**: Function compilation fails → return original data
- **Runtime Errors**: Function execution throws exception → return original data
- **Type Errors**: Function returns wrong type → wrap in `{'converted_data': result}`
- **Security Violations**: Restricted operation attempted → return original data

### Logging
All conversion function errors should be logged but not break workflow execution:

```python
try:
    result = execute_conversion_function(func_string, input_data)
except Exception as e:
    logger.warning(f"Conversion function failed: {e}")
    return input_data
```

## Best Practices

### 1. Keep Functions Simple
- Single responsibility principle
- Avoid complex nested logic
- Use clear variable names

### 2. Handle Missing Data
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": input_data.get("message", "No message provided"),
        "priority": input_data.get("priority", "normal")
    }
```

### 3. Validate Input Data
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(input_data.get("count"), int):
        return {"error": "Invalid count value"}
    return {"processed_count": input_data["count"] * 2}
```

### 4. Use Type-Safe Operations
```python
def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "email": str(input_data.get("email", "")).lower(),
        "age": int(input_data.get("age", 0)) if input_data.get("age") else 0
    }
```

## Migration Guide

### From Legacy Conversion Functions
If upgrading from other conversion function formats:

1. **JSON-based transformations** → Convert to Python function
2. **JQ expressions** → Rewrite as Python dict operations
3. **Template strings** → Use f-string formatting in Python function

### Example Migration
```python
# Legacy format (JSON mapping)
{"text": "{{output}}", "channel": "#general"}

# New format (Python function)
"def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return {'text': input_data.get('output', ''), 'channel': '#general'}"
```

This specification ensures consistency, security, and maintainability across all workflow conversion functions.
