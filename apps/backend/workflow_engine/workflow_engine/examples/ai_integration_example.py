"""
Example: AI Node Integration in Workflows

This example demonstrates how AI nodes can be smoothly integrated into workflows
using the n8n-inspired expression system.
"""

from workflow_engine.utils.ai_response_formatter import AIResponseFormatter, WorkflowDataAccessor
from workflow_engine.utils.expression_parser import ExpressionParser, WorkflowDataProxy


def example_sunday_planning_workflow():
    """
    Example of a Sunday planning workflow with proper AI integration.
    """
    
    # Step 1: AI Planning Facilitator executes
    ai_planning_response = """
    {
        "tasks": [
            {
                "title": "Complete AI provider refactoring",
                "priority": "high",
                "assignee": "Alice",
                "due_date": "2025-01-10"
            },
            {
                "title": "Review Q1 roadmap",
                "priority": "medium",
                "assignee": "Bob",
                "due_date": "2025-01-15"
            }
        ],
        "summary": "Focus on completing the AI refactoring this week before the roadmap review.",
        "category": "planning",
        "priority": "high"
    }
    """
    
    # Format the AI response
    formatted_planning = AIResponseFormatter.format_response(
        raw_response=ai_planning_response,
        provider="openai",
        model="gpt-5-mini",
        input_text="Plan the week for Engineering Team",
        system_prompt="You review past work and plan upcoming tasks for Sunday planning."
    )
    
    # Create node output
    planning_node_output = WorkflowDataAccessor.create_node_output(formatted_planning)
    
    print("AI Planning Facilitator Output:")
    print(f"  Text: {planning_node_output['text'][:50]}...")
    print(f"  Task Count: {planning_node_output['json']['extracted']['task_count']}")
    print(f"  Priority: {planning_node_output['json']['priority']}")
    print()
    
    # Step 2: Slack Action Node uses AI output
    # In the Slack node configuration, the message parameter would use expressions:
    slack_message_template = """
Weekly Planning Summary:
{{ $node["ai_planning_facilitator"].json.summary }}

Priority: {{ $node["ai_planning_facilitator"].json.priority }}

Tasks for this week:
{{ $node["ai_planning_facilitator"].json.extracted.task_count }} tasks created
    """
    
    # Create workflow execution context
    workflow_data = {
        "node_outputs": {
            "ai_planning_facilitator": planning_node_output
        }
    }
    
    # Parse the Slack message
    parser = ExpressionParser(workflow_data, "action_slack_post_planning")
    slack_message = parser.evaluate_template(slack_message_template)
    
    print("Slack Message (parsed from template):")
    print(slack_message)
    print()
    
    # Step 3: Task Management AI uses planning output
    task_management_template = {
        "action": "create_tasks",
        "tasks": "{{ $node[\"ai_planning_facilitator\"].json.tasks }}",
        "team_context": {
            "summary": "{{ $node[\"ai_planning_facilitator\"].json.summary }}",
            "priority": "{{ $node[\"ai_planning_facilitator\"].json.priority }}"
        }
    }
    
    # The Task Management AI would receive parsed data
    task_input = {
        "action": "create_tasks",
        "tasks": parser.evaluate('$node["ai_planning_facilitator"].json.tasks'),
        "team_context": {
            "summary": parser.evaluate('$node["ai_planning_facilitator"].json.summary'),
            "priority": parser.evaluate('$node["ai_planning_facilitator"].json.priority')
        }
    }
    
    print("Task Management AI Input (parsed):")
    print(f"  Action: {task_input['action']}")
    print(f"  Tasks: {len(task_input['tasks'])} tasks")
    print(f"  First task: {task_input['tasks'][0]['title']}")
    print()
    
    # Step 4: Calendar Integration uses structured data
    calendar_event = {
        "title": "Weekly Planning - {{ $node[\"ai_planning_facilitator\"].json.priority }} Priority",
        "description": "{{ $node[\"ai_planning_facilitator\"].json.summary }}",
        "tasks": "{{ $node[\"ai_planning_facilitator\"].json.extracted.task_count }} tasks"
    }
    
    # Parse calendar event
    parsed_calendar = {
        "title": parser.evaluate_template(calendar_event["title"]),
        "description": parser.evaluate_template(calendar_event["description"]),
        "tasks": parser.evaluate_template(calendar_event["tasks"])
    }
    
    print("Calendar Event (parsed):")
    print(f"  Title: {parsed_calendar['title']}")
    print(f"  Description: {parsed_calendar['description']}")
    print()


def example_message_classification_workflow():
    """
    Example of a message classification workflow.
    """
    
    # Slack message comes in
    slack_message = "URGENT: Production server is down! Need immediate assistance."
    
    # AI Classifier processes it
    ai_classification_response = """
    {
        "category": "incident",
        "priority": "urgent",
        "sentiment": "negative",
        "action_required": true,
        "suggested_action": "escalate_to_oncall",
        "keywords": ["production", "server", "down", "urgent"],
        "confidence": 0.95
    }
    """
    
    # Format AI response
    formatted_classification = AIResponseFormatter.format_response(
        raw_response=ai_classification_response,
        provider="openai",
        model="gpt-5-mini",
        input_text=slack_message,
        system_prompt="Classify the message and extract priority."
    )
    
    classification_output = WorkflowDataAccessor.create_node_output(formatted_classification)
    
    # Create workflow context
    workflow_data = {
        "node_outputs": {
            "ai_message_classification": classification_output
        }
    }
    
    # Conditional routing based on classification
    proxy = WorkflowDataProxy({"node_results": {"ai_message_classification": {"output_data": classification_output}}})
    
    priority = proxy.get_node_parameter("ai_message_classification", "priority")
    category = proxy.resolve_expression_for_node("router", '$node["ai_message_classification"].json.category')
    
    print("Message Classification Results:")
    print(f"  Category: {category}")
    print(f"  Priority: {priority}")
    print(f"  Should escalate: {priority == 'urgent'}")
    
    # Route to appropriate action based on classification
    if priority == "urgent":
        print("  → Routing to: High Priority Slack Channel")
    else:
        print("  → Routing to: Normal Priority Notion Log")


def example_data_transformation():
    """
    Example of how AI output can be transformed for different uses.
    """
    
    # AI generates a report
    ai_report = """
## Weekly Summary
- Completed 15 tasks
- 3 blockers identified
- Team velocity: 85%

### Key Achievements:
1. Launched new feature X
2. Fixed critical bug Y
3. Improved performance by 20%

### Next Steps:
- Review architecture for feature Z
- Plan Q2 roadmap
- Hire 2 new engineers
    """
    
    # Format for workflow use
    formatted_report = AIResponseFormatter.format_response(
        raw_response=ai_report,
        provider="openai",
        model="gpt-5-mini",
        input_text="Generate weekly report",
        system_prompt="Create a comprehensive weekly summary."
    )
    
    report_output = WorkflowDataAccessor.create_node_output(formatted_report)
    
    print("AI Report Analysis:")
    print(f"  Bullet points found: {len(report_output['json']['extracted'].get('bullet_points', []))}")
    print(f"  Numbered items: {len(report_output['json']['extracted'].get('numbered_items', []))}")
    print(f"  Has urgent items: {report_output['json']['extracted'].get('has_urgent', False)}")
    
    # Different nodes can use different parts
    print("\nHow different nodes would use this:")
    print("  Email Node: Would use the full text")
    print("  Task Creator: Would use the numbered items as tasks")
    print("  Metrics Dashboard: Would extract the '85%' velocity")


if __name__ == "__main__":
    print("=== Sunday Planning Workflow Example ===\n")
    example_sunday_planning_workflow()
    
    print("\n=== Message Classification Workflow Example ===\n")
    example_message_classification_workflow()
    
    print("\n=== Data Transformation Example ===\n")
    example_data_transformation()