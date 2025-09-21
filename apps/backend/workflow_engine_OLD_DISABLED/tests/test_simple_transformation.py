"""
Simple test to demonstrate the AI to Slack transformation issue and solution.
"""

import json
from datetime import datetime


# Simulate the transformation logic
def transform_text_to_slack_fixed(text_output):
    """Fixed transformation that handles AI output with agenda/summary."""
    content = text_output.get("content", "")

    # Check if content is a JSON string with structured data
    if isinstance(content, str) and content.strip().startswith("{"):
        try:
            parsed_content = json.loads(content)

            # Handle different structured formats from AI
            if isinstance(parsed_content, dict):
                # Check for agenda format
                if "agenda" in parsed_content and isinstance(parsed_content["agenda"], list):
                    message_parts = ["📅 **Meeting Agenda**\n"]

                    for item in parsed_content["agenda"]:
                        if isinstance(item, dict):
                            time = item.get("time", "")
                            topic = item.get("topic", "")
                            duration = item.get("duration", "")
                            if time and topic:
                                line = f"🕘 {time} - {topic}"
                                if duration:
                                    line += f" ({duration})"
                                message_parts.append(line)

                    # Add summary if present
                    if "summary" in parsed_content:
                        message_parts.append(f"\n**Summary:** {parsed_content['summary']}")

                    content = "\n".join(message_parts)

                # Check for summary-only format
                elif "summary" in parsed_content and "agenda" not in parsed_content:
                    content = parsed_content["summary"]

                # Check if it already has Slack-specific format
                elif "message" in parsed_content:
                    content = parsed_content["message"]

        except json.JSONDecodeError:
            # If JSON parsing fails, use content as-is
            pass

    return {
        "content": content,
        "blocks": [],
        "mentions": [],
        "metadata": text_output.get("metadata", {}),
    }


# Test the AI output
ai_output = {
    "content": json.dumps(
        {
            "agenda": [
                {"time": "9:00 AM", "topic": "Project Updates", "duration": "30 min"},
                {"time": "9:30 AM", "topic": "Technical Discussion", "duration": "45 min"},
                {"time": "10:15 AM", "topic": "Q&A", "duration": "15 min"},
            ],
            "summary": "Team meeting discussing project progress and technical challenges",
        }
    ),
    "metadata": {"provider": "gemini", "model": "gemini-pro"},
    "format_type": "text",
    "source_node": "ai_extract_meeting",
    "timestamp": datetime.now().isoformat(),
}

print("=== BEFORE TRANSFORMATION ===")
print("AI output content (raw JSON string):")
print(ai_output["content"])
print("\nThis would be sent as raw JSON to Slack without transformation!")

print("\n=== AFTER TRANSFORMATION ===")
transformed = transform_text_to_slack_fixed(ai_output)
print("Slack-ready content:")
print(transformed["content"])

print("\n✅ The transformation converts structured AI output into a readable Slack message!")
