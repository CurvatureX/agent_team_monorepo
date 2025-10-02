# Workflow Engine V2 Test Suite

This directory contains comprehensive tests for the workflow_engine_v2 implementation, covering all newly implemented features and existing functionality.

## Test Structure

```
tests/
├── README.md                      # This file
├── conftest.py                    # Pytest configuration and shared fixtures
├── requirements-test.txt          # Testing dependencies
├── run_tests.py                   # Test runner script
├── test_basic.py                  # Existing basic functionality tests
├── test_flow_wait_and_foreach.py  # Existing flow control tests
├── test_oauth2_service.py         # OAuth2 and credential management tests
├── test_external_actions.py       # External action implementation tests
├── test_memory_implementations.py # Memory system tests
├── test_hil_services.py           # Human-in-the-Loop service tests
├── test_services.py               # Service layer component tests
└── test_api_endpoints.py          # API endpoint tests
```

## New Features Tested

### 🔐 OAuth2 & Credential Management
- **File**: `test_oauth2_service.py`
- **Coverage**: Token exchange, refresh, storage, encryption
- **Providers**: Google, GitHub, Slack, Notion
- **Features**: AES-256 encryption, automatic token refresh, secure storage

### 🔌 External Actions
- **File**: `test_external_actions.py`
- **Coverage**: All external action implementations
- **Integrations**:
  - Slack (send message, list channels, list users)
  - GitHub (create issue, create PR, get repo, list issues)
  - Google Calendar (create event, list events, update event)
  - Notion (search, create page, update page)

### 🧠 Memory Implementations
- **File**: `test_memory_implementations.py`
- **Coverage**: Advanced memory system with multiple types
- **Types**:
  - Key-Value Store Memory
  - Conversation Buffer Memory
  - Conversation Summary Memory
  - Entity Memory
  - Vector Database Memory
  - Working Memory
  - Memory Orchestrator

### 👥 Human-in-the-Loop (HIL)
- **File**: `test_hil_services.py`
- **Coverage**: Advanced HIL features and AI-powered classification
- **Features**:
  - Response relevance classification
  - Multi-channel support (Slack, webhook)
  - Timeout handling
  - Interaction statistics

### 🛠️ Service Layer
- **File**: `test_services.py`
- **Coverage**: Service layer components
- **Components**:
  - Workflow validation service
  - Unified logging service
  - Workflow status manager
  - Enhanced database repository

### 🌐 API Endpoints
- **File**: `test_api_endpoints.py`
- **Coverage**: New API endpoints
- **Endpoints**:
  - Credential management (`/api/v2/credentials/*`)
  - Node specifications (`/api/v2/node-specs`)
  - Workflow validation (`/api/v2/workflows/*/validate`)
  - Enhanced execution logging

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Or if using the existing workflow engine setup
cd workflow_engine_v2
pip install -e .
```

### Quick Start

```bash
# Run all tests
python tests/run_tests.py all

# Run specific test categories
python tests/run_tests.py oauth      # OAuth2 tests
python tests/run_tests.py external  # External action tests
python tests/run_tests.py memory    # Memory implementation tests
python tests/run_tests.py hil       # HIL service tests
python tests/run_tests.py services  # Service layer tests
python tests/run_tests.py api       # API endpoint tests
```

### Coverage Reporting

```bash
# Run with coverage
python tests/run_tests.py coverage

# View HTML coverage report
open htmlcov/index.html
```

### Performance Testing

```bash
# Run performance tests
python tests/run_tests.py performance

# Run tests in parallel
python tests/run_tests.py parallel
```

### Direct pytest Usage

```bash
# Run all tests
pytest

# Run specific test file
pytest test_oauth2_service.py -v

# Run tests with specific markers
pytest -m "oauth" -v
pytest -m "not slow" -v
pytest -m "unit" -v

# Run with coverage
pytest --cov=workflow_engine_v2 --cov-report=html

# Run specific test function
pytest test_oauth2_service.py::test_google_token_exchange -v
```

## Test Configuration

### Pytest Markers

Tests are organized with the following markers:

- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.oauth` - OAuth-related tests
- `@pytest.mark.memory` - Memory implementation tests
- `@pytest.mark.hil` - HIL functionality tests
- `@pytest.mark.api` - API endpoint tests

### Environment Variables

Tests use the following environment variables (set automatically in `conftest.py`):

```bash
SUPABASE_URL=https://test.supabase.co
SUPABASE_SECRET_KEY=test_secret_key
SUPABASE_ANON_KEY=test_anon_key
OPENAI_API_KEY=test_openai_key
ANTHROPIC_API_KEY=test_anthropic_key
ENCRYPTION_KEY=test_encryption_key_32_chars_long
```

### Fixtures

Common fixtures available in all tests:

- `mock_supabase_client` - Mock Supabase database client
- `mock_oauth_service` - Mock OAuth2 service
- `mock_event_bus` - Mock event bus
- `sample_execution_context` - Sample node execution context
- `workflow_factory` - Factory for creating test workflows
- `execution_factory` - Factory for creating test executions

## Test Categories

### Unit Tests
- Test individual components in isolation
- Use mocks for external dependencies
- Fast execution (< 1s per test)
- Run with: `pytest -m "unit"`

### Integration Tests
- Test component interactions
- May use real database connections (with test data)
- Slower execution (1-10s per test)
- Run with: `pytest -m "integration"`

### API Tests
- Test HTTP endpoints using TestClient
- Mock external service dependencies
- Test request/response validation
- Run with: `pytest -m "api"`

### Performance Tests
- Test execution time and resource usage
- Marked as slow tests
- Run with: `pytest -m "slow"`

## Mocking Strategy

### External Services
- **OAuth Providers**: Mock HTTP requests to Google, GitHub, Slack, Notion APIs
- **Supabase**: Mock database operations and responses
- **AI Services**: Mock OpenAI and Anthropic API calls
- **HTTP Requests**: Use `aioresponses` for async HTTP mocking

### Database Operations
- Use `mock_supabase_client` fixture for database mocking
- Test both success and failure scenarios
- Verify correct query construction and parameter passing

### Async Operations
- All async tests use `@pytest.mark.asyncio`
- Mock async methods with `AsyncMock`
- Test timeout and cancellation scenarios

## Continuous Integration

### GitHub Actions Integration

```yaml
# Example CI configuration
- name: Run Tests
  run: |
    cd apps/backend/workflow_engine_v2
    pip install -r tests/requirements-test.txt
    python tests/run_tests.py all

- name: Upload Coverage
  run: |
    cd apps/backend/workflow_engine_v2
    python tests/run_tests.py coverage
    # Upload to codecov or similar
```

### Test Reports

- **Coverage**: HTML reports generated in `htmlcov/`
- **JUnit**: XML reports for CI integration
- **Performance**: Benchmark results for performance tests

## Best Practices

### Writing Tests

1. **Test Naming**: Use descriptive names that explain what is being tested
2. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
3. **Mock External Dependencies**: Always mock external API calls and database operations
4. **Test Error Cases**: Include tests for error scenarios and edge cases
5. **Async Testing**: Use proper async fixtures and assertions

### Test Data

1. **Factories**: Use factories for creating test data consistently
2. **Fixtures**: Share common setup through pytest fixtures
3. **Isolation**: Each test should be independent and not affect others
4. **Cleanup**: Use fixtures for automatic cleanup of test data

### Performance

1. **Fast Tests**: Keep unit tests under 1 second
2. **Parallel Execution**: Use pytest-xdist for parallel test execution
3. **Selective Running**: Use markers to run specific test subsets
4. **Mocking**: Mock expensive operations (API calls, database queries)

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure proper Python path setup in test files
2. **Async Test Failures**: Use `@pytest.mark.asyncio` and `AsyncMock` properly
3. **Mock Issues**: Verify mock setup and patch targets
4. **Environment Variables**: Check test environment variable configuration

### Debugging Tests

```bash
# Run with debugging
pytest --pdb --pdbcls=IPython.terminal.debugger:Pdb

# Verbose output
pytest -v -s

# Run specific test with debugging
pytest test_oauth2_service.py::test_google_token_exchange -v -s --pdb
```

## Contributing

### Adding New Tests

1. **New Features**: Add corresponding test files for new features
2. **Existing Features**: Enhance existing test files with new test cases
3. **Test Coverage**: Maintain >80% code coverage for new code
4. **Documentation**: Update this README when adding new test categories

### Test Review Checklist

- [ ] All new features have corresponding tests
- [ ] Tests cover both success and error scenarios
- [ ] External dependencies are properly mocked
- [ ] Tests are properly categorized with markers
- [ ] Test names are descriptive and clear
- [ ] Code coverage meets requirements (>80%)
- [ ] Tests run in reasonable time (<5 minutes for full suite)

---

**Total Test Coverage**: This test suite provides comprehensive coverage of all workflow_engine_v2 features, ensuring reliability and maintainability of the codebase.
