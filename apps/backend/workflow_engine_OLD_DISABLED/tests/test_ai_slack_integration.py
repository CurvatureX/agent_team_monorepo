"""
Test file to debug AI node to Slack node data flow issue.

The issue: AI node outputs data in one format, but Slack node expects a different format.
"""

import json
import logging
from datetime import datetime

# Set up logging to see debug messages
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Simulate AI node output format
ai_node_output = {
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
    "metadata": {"provider": "openai", "model": "gpt-4", "executed_at": datetime.now().isoformat()},
    "format_type": "text",
    "source_node": "ai_extract_meeting",
    "timestamp": datetime.now().isoformat(),
}

logger.info("=== AI Node Output ===")
logger.info(f"AI output keys: {list(ai_node_output.keys())}")
logger.info(f"Content type: {type(ai_node_output['content'])}")
logger.info(f"Content preview: {ai_node_output['content'][:100]}...")

# What the Slack node receives as context.input_data
slack_input_data = ai_node_output

logger.info("\n=== Slack Node Processing ===")
logger.info(f"Input data keys: {list(slack_input_data.keys())}")

# Simulate Slack node's logic for extracting message
if slack_input_data and "content" in slack_input_data:
    content_value = slack_input_data["content"]
    logger.info(f"Found content: {type(content_value)}")

    # Check if content is a JSON string
    if isinstance(content_value, str) and content_value.strip().startswith("{"):
        try:
            parsed_content = json.loads(content_value)
            logger.info(f"Parsed JSON keys: {list(parsed_content.keys())}")

            # The Slack node looks for specific keys
            slack_keys = ["message", "channel", "bot_token"]
            has_slack_keys = any(key in parsed_content for key in slack_keys)
            logger.info(f"Has Slack-specific keys? {has_slack_keys}")

            if has_slack_keys:
                text = parsed_content.get("message", "")
                logger.info(f"✅ Extracted message: {text}")
            else:
                # Not Slack-specific JSON, use as text
                text = content_value
                logger.info(f"❌ No 'message' key found, using raw content as text")
                logger.info(f"This will send the raw JSON as the Slack message!")
        except json.JSONDecodeError:
            text = content_value
            logger.info(f"Failed to parse JSON, using as text")
    else:
        text = content_value
        logger.info(f"Content is not JSON, using as text")

# SOLUTION 1: Modify AI prompt to include 'message' key
logger.info("\n=== SOLUTION 1: AI outputs Slack-ready format ===")
ai_output_slack_ready = {
    "content": json.dumps(
        {
            "message": "📅 **Team Meeting Agenda**\n\n"
            "🕘 9:00 AM - Project Updates (30 min)\n"
            "🕘 9:30 AM - Technical Discussion (45 min)\n"
            "🕘 10:15 AM - Q&A (15 min)\n\n"
            "Summary: Team meeting discussing project progress and technical challenges",
            "channel": "#general",  # Optional, will be overridden by node config
        }
    ),
    "metadata": ai_node_output["metadata"],
    "format_type": "text",
    "source_node": "ai_extract_meeting",
    "timestamp": datetime.now().isoformat(),
}

content = json.loads(ai_output_slack_ready["content"])
logger.info(f"AI output with 'message' key: {content['message'][:100]}...")

# SOLUTION 2: Use data transformation in workflow
logger.info("\n=== SOLUTION 2: Transform data between nodes ===")
logger.info(
    "The _transform_node_data method in execution_engine.py should handle this transformation"
)
logger.info("Source type: AI_AGENT.GEMINI, Target type: EXTERNAL_ACTION.SLACK")

# SOLUTION 3: Modify Slack node to better handle AI output
logger.info("\n=== SOLUTION 3: Enhance Slack node logic ===")
logger.info("The Slack node could check for common AI output patterns:")
logger.info("- If 'agenda' key exists, format it as a message")
logger.info("- If 'summary' key exists, use it as the message")
logger.info("- Better handling of structured data")
