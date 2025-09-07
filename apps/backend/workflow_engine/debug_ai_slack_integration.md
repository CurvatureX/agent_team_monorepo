# AI Node to Slack Node Integration Issue

## Problem Summary
The `slack_post_agenda` node is not receiving properly formatted data from the `ai_extract_meeting` node. The AI node outputs structured JSON data, but the Slack node receives it as raw JSON string instead of a formatted message.

## Root Cause Analysis

### 1. Data Flow Path
```
AI Node (ai_extract_meeting) 
    ↓ outputs
{
  "content": "{\"agenda\": [...], \"summary\": \"...\"}",  // JSON string
  "metadata": {...},
  "format_type": "text",
  "source_node": "ai_extract_meeting"
}
    ↓ flows via connections to
Slack Node (slack_post_agenda)
    ↓ receives as context.input_data
```

### 2. Transformation System Issue

The workflow engine has a data transformation system in `_transform_node_data()` that should convert data between nodes:

- Source type: `AI_AGENT.GEMINI` (includes subtype)
- Target type: `EXTERNAL_ACTION.SLACK` 
- Registry key: `("AI_AGENT", "EXTERNAL_ACTION.SLACK")` (without subtype)

The mismatch in type patterns caused the transformation to be skipped.

### 3. Slack Node Behavior

The Slack node (`external_action_node.py`) does check for input data:
```python
if context.input_data and "content" in context.input_data:
    content_value = context.input_data["content"]
    # Tries to parse JSON and look for "message" key
```

But the AI output has `agenda` and `summary` keys, not `message`, so it sends the raw JSON.

## Solutions Implemented

### 1. Fixed Communication Protocol (`shared/node_specs/communication_protocol.py`)

Enhanced `get_transformation_function()` to handle subtypes:
```python
def get_transformation_function(source_type: str, target_type: str):
    # Try exact match first
    # Then try without source subtype (AI_AGENT instead of AI_AGENT.GEMINI)
    # Then try without target subtype
    # Finally try base types only
```

### 2. Enhanced Slack Transformation (`transform_text_to_slack()`)

Added logic to handle AI-specific output formats:
```python
def transform_text_to_slack(text_output: Dict[str, Any]) -> Dict[str, Any]:
    # Check if content is JSON with agenda/summary
    # Format agenda items into readable Slack message
    # Handle summary-only format
    # Preserve pre-formatted messages
```

## Result

Before fix:
```
{"agenda": [{"time": "9:00 AM", "topic": "Project Updates"}, ...]}
```

After fix:
```
📅 **Meeting Agenda**

🕘 9:00 AM - Project Updates (30 min)
🕘 9:30 AM - Technical Discussion (45 min)
🕘 10:15 AM - Q&A (15 min)

**Summary:** Team meeting discussing project progress
```

## Alternative Solutions

1. **Modify AI Prompt**: Have the AI output include a `message` key with formatted text
2. **Add Transform Node**: Insert a dedicated transformation node between AI and Slack
3. **Update Slack Node**: Make it smarter about handling different input formats

## Testing

Run the test files to verify the fix:
```bash
python3 tests/test_ai_slack_integration.py
python3 tests/test_simple_transformation.py
```

## Files Modified

1. `/apps/backend/shared/node_specs/communication_protocol.py` - Enhanced transformation logic
2. Created test files in `/apps/backend/workflow_engine/tests/`

## Next Steps

1. Test the workflow execution with these changes
2. Consider adding more transformation patterns for other node combinations
3. Add logging to verify transformations are applied during execution