"""
Test and solution for AI node to Slack node data transformation issue.

The root cause: The transformation registry doesn't match the exact source type pattern.
"""

import json
from datetime import datetime

# The issue: Source type includes subtype, but registry doesn't
source_type = "AI_AGENT.GEMINI"  # What execution engine generates
target_type = "EXTERNAL_ACTION.SLACK"

# Current registry only has:
registry_key = ("AI_AGENT", "EXTERNAL_ACTION.SLACK")  # Missing .GEMINI

print(f"Source type from execution: {source_type}")
print(f"Target type from execution: {target_type}")
print(f"Registry key pattern: {registry_key}")
print(f"Match? {(source_type, target_type) == registry_key}")  # False!

# SOLUTION: Update the communication protocol to handle AI subtypes
def enhanced_get_transformation(source_type: str, target_type: str):
    """Enhanced transformation lookup that handles subtypes."""
    # First try exact match
    transform_fn = TRANSFORMATION_REGISTRY.get((source_type, target_type))
    if transform_fn:
        return transform_fn
    
    # Try without source subtype
    source_base = source_type.split('.')[0]
    transform_fn = TRANSFORMATION_REGISTRY.get((source_base, target_type))
    if transform_fn:
        return transform_fn
    
    # Try without target subtype
    target_base = target_type.split('.')[0]
    transform_fn = TRANSFORMATION_REGISTRY.get((source_type, target_base))
    if transform_fn:
        return transform_fn
    
    # Try base types only
    transform_fn = TRANSFORMATION_REGISTRY.get((source_base, target_base))
    if transform_fn:
        return transform_fn
    
    return None

# Simulate the transformation
TRANSFORMATION_REGISTRY = {
    ("AI_AGENT", "EXTERNAL_ACTION.SLACK"): lambda data: {
        "content": data.get("content", ""),
        "blocks": [],
        "mentions": [],
        "metadata": data.get("metadata", {}),
    }
}

# Test with AI output
ai_output = {
    "content": json.dumps({
        "agenda": [
            {"time": "9:00 AM", "topic": "Project Updates"},
            {"time": "9:30 AM", "topic": "Technical Discussion"}
        ],
        "summary": "Team meeting"
    }),
    "metadata": {"provider": "gemini"},
    "format_type": "text",
    "source_node": "ai_extract_meeting",
    "timestamp": datetime.now().isoformat()
}

# Try enhanced transformation
transform_fn = enhanced_get_transformation("AI_AGENT.GEMINI", "EXTERNAL_ACTION.SLACK")
if transform_fn:
    transformed = transform_fn(ai_output)
    print("\nTransformed data:")
    print(f"Keys: {list(transformed.keys())}")
    print(f"Content: {transformed['content'][:100]}...")
else:
    print("\nNo transformation found!")