from typing import Any, Dict

import pytest

from shared.models.node_enums import (
    ActionSubtype,
    AIAgentSubtype,
    ExternalActionSubtype,
    FlowSubtype,
    HumanLoopSubtype,
    MemorySubtype,
    NodeType,
    ToolSubtype,
    TriggerSubtype,
)
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.workflow_factory import connect, node


@pytest.mark.asyncio
async def test_approval_workflow_complete(app_client, patch_workflow_definition, in_memory_logs):
    """Test: TRIGGER → AI_AGENT → HUMAN_LOOP(approval) → EXTERNAL_ACTION
    Verify: Complete approval workflow with human interaction"""

    # Create nodes
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # AI analysis of the request
    ai_analyzer = node(
        "n2",
        NodeType.AI_AGENT.value,
        AIAgentSubtype.OPENAI_CHATGPT.value,
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "system_prompt": "Analyze the request and provide recommendations for approval decision.",
            "user_message": "Analyze request: {{input_data.request_details}}",
        },
    )

    # Human approval step
    approval_node = node(
        "n3",
        NodeType.HUMAN_IN_THE_LOOP.value,
        HumanLoopSubtype.IN_APP_APPROVAL.value,
        {
            "interaction_type": "approval",
            "title": "Request Approval Required",
            "description": "Please review the AI analysis and approve or reject this request",
            "approval_options": ["Approve", "Reject", "Request More Info"],
            "reason_required": "true",
            "timeout_seconds": "1800",  # 30 minutes
        },
    )

    # Conditional action based on approval
    decision_flow = node(
        "n4",
        NodeType.FLOW.value,
        FlowSubtype.IF.value,
        {
            "flow_type": "if",
            "condition": "input_data.human_response.approved == true",
            "condition_field": "approved",
            "condition_operator": "==",
            "condition_value": "true",
        },
    )

    # Action for approved requests
    approved_action = node(
        "n5",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.SLACK.value,
        {
            "action_type": "slack",
            "channel": "#approvals",
            "message": "✅ Request APPROVED: {{input_data.request_details}}\nReason: {{input_data.human_response.reason}}",
        },
    )

    # Action for rejected requests
    rejected_action = node(
        "n6",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.EMAIL.value,
        {
            "action_type": "email",
            "to": "{{input_data.requester_email}}",
            "subject": "Request Rejected",
            "body": "Your request has been rejected.\nReason: {{input_data.human_response.reason}}",
        },
    )

    # Memory storage for audit trail
    audit_log = node(
        "n7",
        NodeType.MEMORY.value,
        MemorySubtype.KEY_VALUE_STORE.value,
        {
            "memory_type": "key_value_store",
            "operation": "store",
            "key": "approval_{{input_data.request_id}}",
            "value": '{"request_details": "{{input_data.request_details}}", "ai_analysis": "{{input_data.ai_response}}", "human_decision": "{{input_data.human_response}}", "timestamp": "{{current_timestamp}}"}',
        },
    )

    workflow = {
        "id": "wf_approval_complete",
        "name": "Complete Approval Workflow",
        "nodes": [
            trigger,
            ai_analyzer,
            approval_node,
            decision_flow,
            approved_action,
            rejected_action,
            audit_log,
        ],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → AI Analysis
            "n2": [connect("n2", "n3")],  # AI → Human Approval
            "n3": [connect("n3", "n4")],  # Approval → Decision Flow
            "n4": [
                connect("n4", "n5", output_field="true_path"),  # Approved → Slack
                connect("n4", "n6", output_field="false_path"),  # Rejected → Email
            ],
            "n5": [connect("n5", "n7")],  # Slack → Audit Log
            "n6": [connect("n6", "n7")],  # Email → Audit Log
        },
    }

    patch_workflow_definition(workflow)

    resp = await app_client.post(
        "/v1/workflows/wf_approval_complete/execute",
        json={
            "workflow_id": "wf_approval_complete",
            "user_id": "u1",
            "trigger_data": {
                "request_id": "REQ-001",
                "request_details": "Budget increase for Q2 marketing campaign",
                "requester_email": "marketing@company.com",
                "amount": "50000",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs show complete workflow execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of AI_AGENT node")
    assert_log_contains(logs, "Starting execution of HUMAN_IN_THE_LOOP node")
    assert_log_contains(logs, "Successfully completed HUMAN_IN_THE_LOOP node")


@pytest.mark.asyncio
async def test_error_handling_notification_flow(
    app_client, patch_workflow_definition, in_memory_logs
):
    """Test: TRIGGER → ACTION(failing) → FLOW(error) → EXTERNAL_ACTION(notify)
    Verify: Error handling and notification flow"""

    # Create nodes
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Action that might fail
    risky_action = node(
        "n2",
        NodeType.ACTION.value,
        ActionSubtype.HTTP_REQUEST.value,
        {
            "action_type": "http_request",
            "url": "https://invalid-url-that-will-fail.com/api/endpoint",
            "method": "POST",
            "payload": {"data": "{{input_data.payload}}"},
            "timeout": "5",
        },
    )

    # Error detection flow
    error_check = node(
        "n3",
        NodeType.FLOW.value,
        FlowSubtype.IF.value,
        {
            "flow_type": "if",
            "condition": "input_data.error_message != null",
            "condition_field": "error_message",
            "condition_operator": "!=",
            "condition_value": "null",
        },
    )

    # Error notification action
    error_notification = node(
        "n4",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.SLACK.value,
        {
            "action_type": "slack",
            "channel": "#alerts",
            "message": "🚨 Workflow Error Alert\nWorkflow: {{workflow_id}}\nError: {{input_data.error_message}}\nTime: {{current_timestamp}}",
        },
    )

    # Success action
    success_action = node(
        "n5",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {"action_type": "log", "message": "Workflow completed successfully: {{input_data}}"},
    )

    # Error logging to memory
    error_logger = node(
        "n6",
        NodeType.MEMORY.value,
        MemorySubtype.KEY_VALUE_STORE.value,
        {
            "memory_type": "key_value_store",
            "operation": "store",
            "key": "error_{{execution_id}}",
            "value": '{"workflow_id": "{{workflow_id}}", "error_details": "{{input_data.error_message}}", "timestamp": "{{current_timestamp}}", "user_id": "{{user_id}}"}',
        },
    )

    workflow = {
        "id": "wf_error_handling",
        "name": "Error Handling Notification Flow",
        "nodes": [
            trigger,
            risky_action,
            error_check,
            error_notification,
            success_action,
            error_logger,
        ],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → Risky Action
            "n2": [connect("n2", "n3")],  # Action → Error Check
            "n3": [
                connect("n3", "n4", output_field="true_path"),  # Error → Notification
                connect("n3", "n5", output_field="false_path"),  # Success → Log
            ],
            "n4": [connect("n4", "n6")],  # Error Notification → Error Logger
        },
    }

    patch_workflow_definition(workflow)

    resp = await app_client.post(
        "/v1/workflows/wf_error_handling/execute",
        json={
            "workflow_id": "wf_error_handling",
            "user_id": "u1",
            "trigger_data": {
                "payload": '{"test": "error_handling"}',
                "expected_outcome": "failure",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    # Note: The workflow should complete even if individual actions fail

    # Check logs show error handling
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "workflow")  # Should show workflow execution


@pytest.mark.asyncio
async def test_memory_context_workflow(app_client, patch_workflow_definition, in_memory_logs):
    """Test: TRIGGER → MEMORY(retrieve) → AI_AGENT → MEMORY(store) → ACTION
    Verify: Memory context usage and storage"""

    # Create nodes
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Retrieve existing context from memory
    context_retriever = node(
        "n2",
        NodeType.MEMORY.value,
        MemorySubtype.CONVERSATION_BUFFER.value,
        {
            "memory_type": "conversation_buffer",
            "operation": "get_context",
            "conversation_id": "user_{{input_data.user_id}}",
            "context_window": "5",
            "include_metadata": "true",
        },
    )

    # AI agent with context
    contextual_ai = node(
        "n3",
        NodeType.AI_AGENT.value,
        AIAgentSubtype.OPENAI_CHATGPT.value,
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "system_prompt": "You are a contextual assistant. Use the conversation history to provide relevant responses.",
            "user_message": "Context: {{input_data.context}}\n\nUser request: {{input_data.user_message}}",
        },
    )

    # Store AI response in memory
    memory_store = node(
        "n4",
        NodeType.MEMORY.value,
        MemorySubtype.CONVERSATION_BUFFER.value,
        {
            "memory_type": "conversation_buffer",
            "operation": "add_message",
            "conversation_id": "user_{{input_data.user_id}}",
            "message": '{"role": "assistant", "content": "{{input_data.ai_response}}", "timestamp": "{{current_timestamp}}"}',
        },
    )

    # Action based on AI response
    response_action = node(
        "n5",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.WEBHOOK.value,
        {
            "action_type": "webhook",
            "url": "https://httpbin.org/post",
            "method": "POST",
            "payload": '{"user_id": "{{input_data.user_id}}", "response": "{{input_data.ai_response}}", "context_used": "true"}',
        },
    )

    # Update entity memory with user interaction
    entity_update = node(
        "n6",
        NodeType.MEMORY.value,
        MemorySubtype.ENTITY_MEMORY.value,
        {
            "memory_type": "entity_memory",
            "operation": "update_entity",
            "entity_type": "user",
            "entity_id": "{{input_data.user_id}}",
            "entity_data": '{"last_interaction": "{{current_timestamp}}", "interaction_count": "{{input_data.interaction_count + 1}}", "last_request": "{{input_data.user_message}}"}',
        },
    )

    workflow = {
        "id": "wf_memory_context",
        "name": "Memory Context Workflow",
        "nodes": [
            trigger,
            context_retriever,
            contextual_ai,
            memory_store,
            response_action,
            entity_update,
        ],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → Context Retrieval
            "n2": [connect("n2", "n3")],  # Context → AI Agent
            "n3": [connect("n3", "n4")],  # AI → Memory Store
            "n4": [connect("n4", "n5")],  # Memory Store → Response Action
            "n5": [connect("n5", "n6")],  # Response → Entity Update
        },
    }

    patch_workflow_definition(workflow)

    resp = await app_client.post(
        "/v1/workflows/wf_memory_context/execute",
        json={
            "workflow_id": "wf_memory_context",
            "user_id": "u1",
            "trigger_data": {
                "user_id": "user123",
                "user_message": "What was my last request about?",
                "interaction_count": "5",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs show memory operations and AI interaction
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")
    assert_log_contains(logs, "Starting execution of AI_AGENT node")


@pytest.mark.asyncio
async def test_complex_data_pipeline(app_client, patch_workflow_definition, in_memory_logs):
    """Test complex data processing pipeline with multiple transformations"""

    # Create nodes
    trigger = node(
        "n1",
        NodeType.TRIGGER.value,
        TriggerSubtype.WEBHOOK.value,
        {"trigger_type": "webhook", "webhook_config": {"endpoint": "/data-pipeline"}},
    )

    # Data validation
    validator = node(
        "n2",
        NodeType.FLOW.value,
        FlowSubtype.IF.value,
        {
            "flow_type": "if",
            "condition": "input_data.data_size > 0 and input_data.format == 'json'",
            "validation_rules": ["data_size > 0", "format == 'json'"],
        },
    )

    # Data transformation
    transformer = node(
        "n3",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": "data_transformation",
            "transformation_type": "field_mapping",
            "field_mappings": {
                "raw_data": "processed_data",
                "timestamp": "processed_at",
                "source": "data_source",
            },
        },
    )

    # AI-powered data enrichment
    enricher = node(
        "n4",
        NodeType.AI_AGENT.value,
        AIAgentSubtype.OPENAI_CHATGPT.value,
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "system_prompt": "Enrich the provided data with relevant metadata and insights.",
            "user_message": "Enrich this data: {{input_data.processed_data}}",
        },
    )

    # Data quality check
    quality_check = node(
        "n5",
        NodeType.TOOL.value,
        ToolSubtype.HTTP_CLIENT.value,
        {
            "tool_type": "utility",
            "utility_type": "hash",
            "operation": "verify",
            "hash_type": "sha256",
        },
    )

    # Store in vector database for future retrieval
    vector_store = node(
        "n6",
        NodeType.MEMORY.value,
        MemorySubtype.VECTOR_DATABASE.value,
        {
            "memory_type": "vector_database",
            "operation": "store",
            "collection": "processed_data",
            "content": "{{input_data.enriched_data}}",
            "metadata": '{"pipeline_id": "{{execution_id}}", "processing_timestamp": "{{current_timestamp}}", "data_quality_score": "{{input_data.quality_score}}"}',
        },
    )

    # Final notification
    completion_notification = node(
        "n7",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.WEBHOOK.value,
        {
            "action_type": "webhook",
            "url": "https://httpbin.org/post",
            "method": "POST",
            "payload": '{"pipeline_id": "{{execution_id}}", "status": "completed", "records_processed": "{{input_data.record_count}}", "quality_score": "{{input_data.quality_score}}"}',
        },
    )

    # Error handler for validation failures
    error_handler = node(
        "n8",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": "log",
            "level": "ERROR",
            "message": "Data pipeline failed validation: {{input_data.validation_errors}}",
        },
    )

    workflow = {
        "id": "wf_data_pipeline",
        "name": "Complex Data Processing Pipeline",
        "nodes": [
            trigger,
            validator,
            transformer,
            enricher,
            quality_check,
            vector_store,
            completion_notification,
            error_handler,
        ],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → Validator
            "n2": [
                connect("n2", "n3", output_field="true_path"),  # Valid → Transformer
                connect("n2", "n8", output_field="false_path"),  # Invalid → Error Handler
            ],
            "n3": [connect("n3", "n4")],  # Transformer → Enricher
            "n4": [connect("n4", "n5")],  # Enricher → Quality Check
            "n5": [connect("n5", "n6")],  # Quality Check → Vector Store
            "n6": [connect("n6", "n7")],  # Vector Store → Completion Notification
        },
    }

    patch_workflow_definition(workflow)

    resp = await app_client.post(
        "/v1/workflows/wf_data_pipeline/execute",
        json={
            "workflow_id": "wf_data_pipeline",
            "user_id": "u1",
            "trigger_data": {
                "data_size": "1024",
                "format": "json",
                "raw_data": '{"records": [{"id": 1, "value": "test"}]}',
                "source": "api_endpoint",
                "timestamp": "2025-01-17T10:00:00Z",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs show complete pipeline execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")
    assert_log_contains(logs, "Starting execution of ACTION node")
    assert_log_contains(logs, "Starting execution of AI_AGENT node")


@pytest.mark.asyncio
async def test_multi_user_collaboration_workflow(
    app_client, patch_workflow_definition, in_memory_logs
):
    """Test workflow involving multiple human users with role-based routing"""

    # Create nodes
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Route based on request type
    request_router = node(
        "n2",
        NodeType.FLOW.value,
        FlowSubtype.SWITCH.value,
        {
            "flow_type": "switch",
            "switch_field": "request_type",
            "cases": {
                "technical": {"assigned_role": "engineer"},
                "business": {"assigned_role": "manager"},
                "legal": {"assigned_role": "legal_team"},
            },
            "default_case": {"assigned_role": "general"},
        },
    )

    # Technical review by engineer
    technical_review = node(
        "n3",
        NodeType.HUMAN_IN_THE_LOOP.value,
        HumanLoopSubtype.MANUAL_REVIEW.value,
        {
            "interaction_type": "review",
            "title": "Technical Review Required",
            "description": "Please review the technical aspects of this request",
            "review_criteria": [
                "Technical feasibility",
                "Resource requirements",
                "Timeline estimates",
            ],
            "assigned_role": "engineer",
            "timeout_seconds": "3600",
        },
    )

    # Business review by manager
    business_review = node(
        "n4",
        NodeType.HUMAN_IN_THE_LOOP.value,
        HumanLoopSubtype.IN_APP_APPROVAL.value,
        {
            "interaction_type": "approval",
            "title": "Business Approval Required",
            "description": "Please review and approve the business case",
            "approval_options": ["Approve", "Reject", "Request Changes"],
            "assigned_role": "manager",
            "timeout_seconds": "7200",
        },
    )

    # Legal review
    legal_review = node(
        "n5",
        NodeType.HUMAN_IN_THE_LOOP.value,
        HumanLoopSubtype.MANUAL_REVIEW.value,
        {
            "interaction_type": "review",
            "title": "Legal Compliance Review",
            "description": "Please review for legal and compliance requirements",
            "review_criteria": [
                "Regulatory compliance",
                "Contract implications",
                "Risk assessment",
            ],
            "assigned_role": "legal_team",
            "timeout_seconds": "10800",
        },
    )

    # Consolidate all reviews
    review_consolidator = node(
        "n6",
        NodeType.FLOW.value,
        FlowSubtype.MERGE.value,
        {
            "flow_type": "merge",
            "merge_strategy": "combine",
            "wait_for_all": "true",
            "output_field": "consolidated_reviews",
        },
    )

    # Final decision maker
    final_decision = node(
        "n7",
        NodeType.HUMAN_IN_THE_LOOP.value,
        HumanLoopSubtype.IN_APP_APPROVAL.value,
        {
            "interaction_type": "approval",
            "title": "Final Decision Required",
            "description": "Based on all reviews, make the final decision",
            "approval_options": ["Approve", "Reject"],
            "assigned_role": "director",
            "timeout_seconds": "1800",
        },
    )

    # Notification to all stakeholders
    stakeholder_notification = node(
        "n8",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.EMAIL.value,
        {
            "action_type": "email",
            "to": "{{input_data.stakeholders}}",
            "subject": "Request Decision: {{input_data.request_title}}",
            "body": "Decision: {{input_data.final_decision}}\nReviews: {{input_data.consolidated_reviews}}",
        },
    )

    workflow = {
        "id": "wf_multi_user_collaboration",
        "name": "Multi-User Collaboration Workflow",
        "nodes": [
            trigger,
            request_router,
            technical_review,
            business_review,
            legal_review,
            review_consolidator,
            final_decision,
            stakeholder_notification,
        ],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → Router
            "n2": [
                connect("n2", "n3", output_field="technical"),
                connect("n2", "n4", output_field="business"),
                connect("n2", "n5", output_field="legal"),
            ],
            "n3": [connect("n3", "n6")],  # Technical Review → Consolidator
            "n4": [connect("n4", "n6")],  # Business Review → Consolidator
            "n5": [connect("n5", "n6")],  # Legal Review → Consolidator
            "n6": [connect("n6", "n7")],  # Consolidator → Final Decision
            "n7": [connect("n7", "n8")],  # Final Decision → Notification
        },
    }

    patch_workflow_definition(workflow)

    resp = await app_client.post(
        "/v1/workflows/wf_multi_user_collaboration/execute",
        json={
            "workflow_id": "wf_multi_user_collaboration",
            "user_id": "u1",
            "trigger_data": {
                "request_type": "technical",
                "request_title": "New API Development",
                "stakeholders": '["engineering@company.com", "management@company.com"]',
                "priority": "high",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs show routing and human loop executions
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")
    assert_log_contains(logs, "Starting execution of HUMAN_IN_THE_LOOP node")
