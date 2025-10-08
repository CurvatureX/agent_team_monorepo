# Node Spec Naming Conventions

## ⚠️ IMPORTANT: Use "options" not "enum" in Node Specs

### The Rule

**In backend node specifications (`node_specs/`), ALWAYS use `"options"` for dropdown choices, NOT `"enum"`.**

```python
# ✅ CORRECT - Use "options"
"action_type": {
    "type": "string",
    "default": "send_message",
    "description": "Slack operation type",
    "required": True,
    "options": [
        "send_message",
        "send_file",
        "create_channel"
    ],
}

# ❌ WRONG - Don't use "enum"
"action_type": {
    "type": "string",
    "enum": ["send_message", "send_file"],  # Don't do this!
}
```

---

## Why This Matters

### 1. **Backend Node Specs** (`node_specs/*.py`)
- Use **`"options"`** field for dropdown choices
- This is our internal standard for node configuration schemas

### 2. **API Layer** (`node_specs_api_service.py`)
- Automatically converts `"options"` → `"enum"` for JSON Schema
- Supports legacy `"enum"` for backward compatibility (but prefer `"options"`)

### 3. **Frontend** (`node-template.ts`)
- Receives `"enum"` from API (JSON Schema format)
- The `enum` field comes from backend `"options"` after conversion

### 4. **MCP Tools** (`api-gateway/app/api/mcp/*.py`)
- Use `"enum"` because they follow **JSON Schema** standard
- This is correct for MCP tools (they're not node specs)

---

## Data Flow

```
Backend Node Spec          API Conversion           Frontend Type
─────────────────────────────────────────────────────────────────
"options": [               →  "enum": [          →  enum?: string[]
  "option1",                     "option1",
  "option2"                      "option2"
]                              ]
```

---

## Verification

### Check Node Specs Use "options"
```bash
# Should return results (correct usage)
grep -r '"options":' apps/backend/shared/node_specs --include="*.py"

# Should return NOTHING (no incorrect usage)
grep -r '"enum":' apps/backend/shared/node_specs --include="*.py" | grep -v base.py
```

### Examples of Correct Usage

**SLACK Node Spec:**
```python
"action_type": {
    "type": "string",
    "options": ["send_message", "send_file", "create_channel"],
}
```

**GitHub Node Spec:**
```python
"action_type": {
    "type": "string",
    "options": ["create_issue", "create_pr", "add_comment"],
}
```

**Google Calendar Node Spec:**
```python
"action": {
    "type": "string",
    "options": ["list", "create", "update", "delete", "get"],
}
```

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Using "enum" in Node Specs
```python
# WRONG - in node_specs/EXTERNAL_ACTION/SLACK.py
"action_type": {
    "type": "string",
    "enum": ["send_message", "send_file"],  # Should be "options"
}
```

### ❌ Mistake 2: Confusing with JSON Schema
```python
# This is OK in MCP tools (they use JSON Schema)
# But NOT in node specs
{
    "type": "string",
    "enum": ["value1", "value2"]
}
```

### ✅ Correct Pattern
```python
# In node specs, ALWAYS use "options"
"field_name": {
    "type": "string",
    "options": ["value1", "value2"],
    "default": "value1",
    "description": "Choose an option",
}
```

---

## Summary

| Location | Use | Reason |
|----------|-----|--------|
| **Node Specs** | `"options"` | Internal node schema standard |
| **API Service** | Converts `"options"` → `"enum"` | JSON Schema compatibility |
| **Frontend** | `enum?: string[]` | Receives JSON Schema format |
| **MCP Tools** | `"enum"` | Follows JSON Schema standard |

**Remember:** When writing node specs, think **"options"** not "enum"!
