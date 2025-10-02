# Workflow Engine Integration Test Plan

## Overview

Comprehensive integration testing strategy for the workflow engine to ensure all node types work correctly, data flows properly between nodes, and logging is accurately captured in the database. Tests run independently without Docker dependencies using .env configuration.

## Test Architecture

### Framework & Dependencies
- **pytest** with async support
- **httpx** for API testing
- **python-dotenv** for environment loading
- **Supabase** for database operations
- Automatic cleanup after each test

### Environment Setup
```bash
# Required .env variables
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
WORKFLOW_ENGINE_URL=http://localhost:8002
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=test_password

# Optional external API variables
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key
SLACK_BOT_TOKEN=xoxb-your-token
```

## Test Structure

```
tests/integration/
├── conftest.py                     # Test fixtures and setup
├── test_individual_nodes/          # Single node tests
│   ├── test_trigger_node.py
│   ├── test_ai_agent_node.py
│   ├── test_action_node.py
│   ├── test_external_action_node.py
│   ├── test_flow_node.py
│   ├── test_human_loop_node.py
│   ├── test_tool_node.py
│   └── test_memory_node.py
├── test_multi_node_workflows/      # Multi-node workflow tests
│   ├── test_linear_workflows.py
│   ├── test_branching_workflows.py
│   └── test_complex_workflows.py
├── test_database_integration/      # Database and logging tests
│   ├── test_execution_tracking.py
│   ├── test_execution_logs.py
│   └── test_data_flow_logging.py
└── utils/                          # Test utilities
    ├── workflow_factory.py
    ├── assertions.py
    └── cleanup.py
```

## 1. Individual Node Type Tests

### 1.1 TRIGGER Node Tests
```python
class TestTriggerNode:
    async def test_manual_trigger_basic(self):
        """Test basic manual workflow trigger with simple data"""

    async def test_manual_trigger_with_user_context(self):
        """Test manual trigger includes user context in output"""

    async def test_webhook_trigger_simulation(self):
        """Test webhook trigger with GitHub-style payload"""

    async def test_scheduled_trigger_simulation(self):
        """Test scheduled trigger with cron expression"""

    async def test_trigger_data_passthrough_complex(self):
        """Test complex nested data preservation through trigger"""

    async def test_trigger_parameter_validation(self):
        """Test trigger node parameter validation"""

    async def test_trigger_error_handling(self):
        """Test trigger node error scenarios"""

    async def test_trigger_metadata_generation(self):
        """Test trigger metadata is properly generated"""
```

### 1.2 AI_AGENT Node Tests
```python
class TestAIAgentNode:
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"))
    async def test_openai_integration_real(self):
        """Test OpenAI API integration with real API key"""

    async def test_openai_integration_mock(self):
        """Test OpenAI fallback behavior without API key"""

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"))
    async def test_anthropic_integration_real(self):
        """Test Anthropic Claude API integration"""

    async def test_parameter_validation_missing_system_prompt(self):
        """Test validation failure when system_prompt is missing"""

    async def test_parameter_validation_missing_user_message(self):
        """Test validation failure when user_message is missing"""

    async def test_input_data_sources(self):
        """Test AI agent accepts user_message from multiple input sources"""

    async def test_model_name_mapping(self):
        """Test model name mapping (gpt-4-mini → gpt-4o-mini)"""

    async def test_error_handling_api_failure(self):
        """Test graceful handling of API failures"""

    async def test_token_usage_tracking(self):
        """Test token usage is accurately tracked"""

    async def test_concurrent_requests(self):
        """Test multiple concurrent AI requests"""
```

### 1.3 ACTION Node Tests
```python
class TestActionNode:
    async def test_http_request_get(self):
        """Test HTTP GET request to external API"""

    async def test_http_request_post_with_json(self):
        """Test HTTP POST with JSON payload"""

    async def test_http_request_error_handling(self):
        """Test HTTP request error handling (404, timeout)"""

    async def test_data_transformation_jq_style(self):
        """Test JQ-style data transformations"""

    async def test_data_transformation_field_mapping(self):
        """Test field mapping transformations"""

    async def test_data_transformation_python_safe(self):
        """Test safe Python expression transformations"""

    async def test_data_transformation_jsonpath(self):
        """Test JSONPath transformations"""

    async def test_parameter_validation(self):
        """Test action node parameter validation"""
```

### 1.4 EXTERNAL_ACTION Node Tests
```python
class TestExternalActionNode:
    async def test_slack_integration_mock(self):
        """Test Slack integration with mock token"""

    @pytest.mark.skipif(not os.getenv("SLACK_BOT_TOKEN"))
    async def test_slack_integration_real(self):
        """Test Slack integration with real token"""

    async def test_webhook_posting(self):
        """Test webhook posting functionality"""

    async def test_email_sending_mock(self):
        """Test email sending with mock SMTP"""

    async def test_channel_parameter_validation(self):
        """Test Slack channel parameter requirements"""

    async def test_integration_error_handling(self):
        """Test error handling for failed external integrations"""
```

### 1.5 FLOW Node Tests
```python
class TestFlowNode:
    async def test_conditional_flow_true_path(self):
        """Test IF condition evaluating to true"""

    async def test_conditional_flow_false_path(self):
        """Test IF condition evaluating to false"""

    async def test_multi_branch_if_flow(self):
        """Test multi-branch flow using chained IF nodes (SWITCH removed)"""

    async def test_for_each_loop_array(self):
        """Test FOR_EACH loop over array data"""

    async def test_while_loop_with_condition(self):
        """Test WHILE loop with dynamic condition"""

    async def test_merge_multiple_inputs(self):
        """Test data merging from multiple sources"""

    async def test_split_parallel_execution(self):
        """Test data splitting for parallel execution"""

    async def test_filter_array_data(self):
        """Test array filtering with conditions"""

    async def test_complex_nested_conditions(self):
        """Test complex nested conditional expressions"""
```

### 1.6 HUMAN_LOOP Node Tests
```python
class TestHumanLoopNode:
    async def test_approval_request_creation(self):
        """Test approval request creation and storage"""

    async def test_input_request_with_form_fields(self):
        """Test input request with multiple form fields"""

    async def test_selection_request_with_options(self):
        """Test selection request with multiple options"""

    async def test_review_request_with_criteria(self):
        """Test review request with specific criteria"""

    async def test_timeout_handling(self):
        """Test HIL request timeout behavior"""

    async def test_hil_request_database_storage(self):
        """Test HIL requests are properly stored in database"""

    async def test_parameter_validation(self):
        """Test HIL node parameter validation"""
```

### 1.7 TOOL Node Tests
```python
class TestToolNode:
    async def test_mcp_tool_execution_mock(self):
        """Test MCP tool execution with mock responses"""

    async def test_utility_tool_timestamp(self):
        """Test utility tool timestamp generation"""

    async def test_utility_tool_uuid_generation(self):
        """Test utility tool UUID generation"""

    async def test_utility_tool_hash_functions(self):
        """Test utility tool hash functions (md5, sha256)"""

    async def test_file_operations_read_write(self):
        """Test file read/write operations"""

    async def test_api_tool_http_requests(self):
        """Test API tool HTTP request functionality"""

    async def test_tool_parameter_validation(self):
        """Test tool-specific parameter validation"""
```

### 1.8 MEMORY Node Tests
```python
class TestMemoryNode:
    async def test_key_value_store_operations(self):
        """Test key-value storage and retrieval"""

    async def test_vector_database_operations(self):
        """Test vector database storage and similarity search"""

    async def test_conversation_buffer_management(self):
        """Test conversation buffer memory management"""

    async def test_entity_memory_storage(self):
        """Test entity-based memory storage"""

    async def test_working_memory_operations(self):
        """Test working memory operations"""

    async def test_context_generation(self):
        """Test context generation from stored memory"""

    async def test_memory_parameter_validation(self):
        """Test memory node parameter validation"""
```

## 2. Multi-Node Workflow Tests

### 2.1 Linear Workflows
```python
class TestLinearWorkflows:
    async def test_trigger_to_ai_to_slack(self):
        """
        Test: TRIGGER → AI_AGENT → EXTERNAL_ACTION(Slack)
        Verify: AI response flows to Slack message
        """

    async def test_http_to_transform_to_store(self):
        """
        Test: TRIGGER → ACTION(HTTP) → ACTION(transform) → MEMORY(store)
        Verify: HTTP response is transformed and stored
        """

    async def test_trigger_to_validation_to_action(self):
        """
        Test: TRIGGER → FLOW(validation) → ACTION
        Verify: Data validation and conditional execution
        """
```

### 2.2 Branching Workflows
```python
class TestBranchingWorkflows:
    async def test_conditional_branching_if_else(self):
        """
        Test: TRIGGER → FLOW(IF) → [AI_AGENT | ACTION(HTTP)]
        Verify: Correct branch taken based on condition
        """

    async def test_multi_branching_with_if_chain(self):
        """
        Test: TRIGGER → FLOW(IF) chained → [Multiple branches]
        Verify: Correct branch executed based on evaluated conditions
        """

    async def test_parallel_execution_merge(self):
        """
        Test: TRIGGER → FLOW(SPLIT) → [Parallel paths] → FLOW(MERGE)
        Verify: Parallel execution and data merging
        """
```

### 2.3 Complex Workflows
```python
class TestComplexWorkflows:
    async def test_approval_workflow_complete(self):
        """
        Test: TRIGGER → AI_AGENT → HUMAN_LOOP(approval) → EXTERNAL_ACTION
        Verify: Complete approval workflow with human interaction
        """

    async def test_error_handling_notification_flow(self):
        """
        Test: TRIGGER → ACTION(failing) → FLOW(error) → EXTERNAL_ACTION(notify)
        Verify: Error handling and notification flow
        """

    async def test_memory_context_workflow(self):
        """
        Test: TRIGGER → MEMORY(retrieve) → AI_AGENT → MEMORY(store) → ACTION
        Verify: Memory context usage and storage
        """
```

## 3. Database Integration Tests

### 3.1 Execution Tracking
```python
class TestExecutionTracking:
    async def test_execution_record_creation(self):
        """Test execution records created with correct metadata"""

    async def test_execution_status_transitions(self):
        """Test status transitions: NEW → RUNNING → SUCCESS/ERROR"""

    async def test_execution_timing_accuracy(self):
        """Test execution timing tracking accuracy"""

    async def test_async_execution_tracking(self):
        """Test async execution status tracking"""
```

### 3.2 Execution Logs
```python
class TestExecutionLogs:
    async def test_node_execution_logging_completeness(self):
        """Test all node executions generate complete logs"""

    async def test_user_friendly_log_messages(self):
        """Test logs contain user-friendly messages"""

    async def test_error_log_detail_capture(self):
        """Test error logs capture detailed information"""

    async def test_sensitive_data_masking(self):
        """Test sensitive data is masked in logs"""
```

### 3.3 Data Flow Logging
```python
class TestDataFlowLogging:
    async def test_input_output_data_logging(self):
        """Test input/output data logged for each node"""

    async def test_parameter_logging_accuracy(self):
        """Test node parameters logged accurately"""

    async def test_data_flow_integrity_verification(self):
        """Test data flow integrity between nodes"""
```

## 4. Test Utilities (Design Only)

### 4.1 Workflow Factory
```python
async def create_single_node_workflow(test_context, node_type, subtype, parameters):
    """Create single-node workflow for testing"""

async def create_multi_node_workflow(test_context, nodes, connections):
    """Create multi-node workflow with connections"""

async def execute_workflow(client, workflow_id, trigger_data, async_execution):
    """Execute workflow and return response"""

async def get_execution_details(client, execution_id):
    """Get detailed execution information"""

async def get_execution_logs(client, execution_id):
    """Get execution logs"""
```

### 4.2 Test Assertions
```python
def assert_execution_success(execution):
    """Assert execution completed successfully"""

def assert_node_output_structure(output_data, expected_fields):
    """Assert node output contains expected fields"""

def assert_data_flow_integrity(source_output, target_input):
    """Assert data flows correctly between nodes"""

def assert_log_completeness(logs, expected_node_count):
    """Assert logs are complete for all nodes"""

def assert_user_friendly_messages(logs):
    """Assert logs contain user-friendly messages"""
```

### 4.3 Cleanup Management
```python
async def cleanup_test_data(test_context):
    """Clean up all test data after test completion"""

async def verify_cleanup_success(test_context):
    """Verify all test data has been removed"""
```

## 5. Test Execution

### Running Tests
```bash
# All integration tests
pytest tests/integration/ -v

# Specific categories
pytest tests/integration/test_individual_nodes/ -v
pytest tests/integration/test_multi_node_workflows/ -v
pytest tests/integration/test_database_integration/ -v

# With external APIs (requires API keys)
pytest tests/integration/ -m "external_api" -v

# Mock external services
pytest tests/integration/ -m "not external_api" -v

# Performance tests
pytest tests/integration/ -m "performance" -v
```

### Test Configuration
```ini
# pytest.ini
[tool:pytest]
asyncio_mode = auto
markers =
    external_api: requires external API keys
    database: requires database access
    performance: performance tests
    slow: slow running tests
testpaths = tests/integration
```

## Success Criteria

### Coverage Requirements
- ✅ All 8 node types tested individually
- ✅ Linear, branching, and complex workflows tested
- ✅ All API endpoints tested
- ✅ Database operations validated
- ✅ Error scenarios covered

### Quality Gates
- ✅ All workflows execute without errors
- ✅ Data flows correctly between nodes
- ✅ Complete logs generated for all executions
- ✅ No test data remains after completion
- ✅ Performance within acceptable limits

### Performance Targets
- Single node execution: < 500ms
- Multi-node workflow (5 nodes): < 2s
- Database operations: < 100ms
- API responses: < 1s

This focused test plan ensures comprehensive validation of the workflow engine while maintaining clarity and avoiding implementation details.
