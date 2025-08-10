<<<<<<< HEAD
# API Gateway Integration Tests

This directory contains integration tests for the API Gateway service, testing real endpoints with actual Supabase authentication.

## Test Coverage

### `test_integration.py`
Integration tests that use real Supabase authentication to test:

1. **Session Management** (`/api/v1/app/sessions`)
   - Create new session
   - List user sessions
   - Get session by ID
   - Update session

2. **Chat Streaming** (`/api/v1/app/chat/stream`)
   - Send chat messages with SSE streaming
   - Verify event structure and types
   - Test concurrent chat streams
   - Get chat history

3. **Authentication**
   - Verify endpoints require valid JWT tokens
   - Test unauthorized access handling
   - Test invalid token rejection

### `test_basic.py`
Basic unit tests covering:
- Public endpoints (health, version, docs)
- Authentication requirements
- Middleware functionality
- Application configuration

## Running the Tests

### Prerequisites

1. **Environment Variables**: Ensure the `.env` file exists at `../.env` with:
   ```env
   # Supabase Configuration
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your_anon_key
   SUPABASE_SECRET_KEY=your_service_key
   
   # Test Credentials
   TEST_USER_EMAIL=test@example.com
   TEST_USER_PASSWORD=testpassword123
   ```

2. **Services Running**: Ensure all backend services are running:
   ```bash
   cd ../
   docker-compose up
   ```

### Running Integration Tests

#### Method 1: Using the test script
```bash
./run_integration_tests.sh
```

#### Method 2: Direct pytest command
```bash
# Load environment variables first
export $(grep -v '^#' ../.env | xargs)

# Run integration tests
uv run pytest tests/test_integration.py -v
```

#### Method 3: Run specific tests
```bash
# Run only session tests
uv run pytest tests/test_integration.py::TestIntegration::test_create_session -v

# Run only chat tests
uv run pytest tests/test_integration.py::TestIntegration::test_chat_stream -v
```

### Running Basic Tests

```bash
# Run all basic tests
uv run pytest tests/test_basic.py -v

# Run with coverage
uv run pytest tests/test_basic.py --cov=app
```

## CI Environment

Integration tests are automatically skipped in CI environments (when `CI=true`). This is because:
- CI may not have access to real Supabase credentials
- Integration tests require actual backend services running
- They're designed for local development and staging environments

To force run in CI:
```bash
unset CI
./run_integration_tests.sh
```

## Test Structure

```
tests/
├── __init__.py
├── README.md               # This file
├── test_basic.py          # Basic unit tests
└── test_integration.py    # Integration tests with real auth
```

## Troubleshooting

### Authentication Failures
- Verify `TEST_USER_EMAIL` and `TEST_USER_PASSWORD` are correct
- Ensure the test user exists in Supabase Auth
- Check that `SUPABASE_URL` and `SUPABASE_ANON_KEY` are valid

### Connection Errors
- Ensure all services are running: `docker-compose ps`
- Check service health: `curl http://localhost:8000/api/v1/public/health`
- Verify network connectivity to Supabase

### Test Failures
- Run with detailed output: `pytest -vvs tests/test_integration.py`
- Check service logs: `docker-compose logs api-gateway`
- Verify environment variables are loaded correctly

## Adding New Tests

When adding new integration tests:

1. Follow the existing test class structure
2. Use `self.auth_headers` for authenticated requests
3. Clean up test data when possible
4. Add appropriate assertions for response structure
5. Document any special requirements in test docstrings

Example:
```python
def test_new_endpoint(self):
    """Test description with any special requirements"""
    response = self.client.post(
        "/api/v1/app/new-endpoint",
        json={"key": "value"},
        headers=self.auth_headers
    )
    assert response.status_code == 200
    # Add specific assertions
```
=======
# API Gateway Test Suite

This directory contains comprehensive tests for the API Gateway's MCP Node Knowledge Server implementation.

## Test Structure

### Core Test Files

- **`test_basic.py`** - Basic functionality and integration tests
  - Application startup and configuration
  - Basic HTTP endpoint tests
  - Authentication requirement verification
  - Middleware functionality
  - MCP Node Knowledge integration test

- **`test_node_knowledge_service.py`** - Unit tests for NodeKnowledgeService
  - Service initialization with/without registry
  - Node type retrieval and filtering
  - Node details retrieval with various options
  - Node search functionality with relevance scoring
  - Error handling and edge cases
  - Serialization testing

- **`test_mcp_tools.py`** - Unit tests for MCP service layer
  - MCP service initialization
  - Tool availability and structure validation
  - Tool invocation for all three tools (get_node_types, get_node_details, search_nodes)
  - Parameter validation and default handling
  - Error handling and invalid tool requests
  - Health checks and service status
  - Concurrent operations testing

- **`test_mcp_endpoints.py`** - Integration tests for HTTP API endpoints
  - Authentication requirement verification
  - Successful tool invocations via HTTP
  - Error responses and status codes
  - Request/response metadata handling
  - Timeout validation
  - Service exception handling
  - Malformed request handling

- **`test_mcp_error_handling.py`** - Comprehensive error handling tests
  - Registry failure scenarios
  - Partial operation failures
  - Malformed requests and parameters
  - Edge cases with large data sets
  - Concurrent operation failures
  - Parameter and port serialization edge cases

- **`test_mcp_performance.py`** - Performance and scalability tests
  - Large registry handling (500+ node specs)
  - Search performance with many results
  - Bulk node details retrieval
  - Concurrent operation performance
  - Memory usage efficiency
  - Response time consistency

### Support Files

- **`conftest.py`** - Shared test fixtures and configuration
  - Mock node registry with comprehensive test data
  - Authentication mocking utilities
  - Warning suppression for cleaner test output
  - Sample data fixtures

## Test Coverage

### Functionality Coverage
- ✅ **Node Type Discovery** - Get all available node types with filtering
- ✅ **Node Details Retrieval** - Comprehensive node specifications with examples/schemas
- ✅ **Node Search** - Intelligent search with relevance scoring
- ✅ **Error Handling** - Graceful degradation and error reporting
- ✅ **Authentication** - API key validation and scope checking
- ✅ **Performance** - Scalability with large node registries
- ✅ **Concurrency** - Multiple simultaneous operations

### Edge Cases Covered
- ✅ Registry import failures
- ✅ Partial operation failures
- ✅ Malformed requests
- ✅ Large data sets
- ✅ Network timeouts
- ✅ Invalid parameters
- ✅ Missing node specifications
- ✅ Serialization errors

## Running Tests

### Quick Tests
```bash
python run_mcp_tests.py --quick
```

### Full Test Suite
```bash
python run_mcp_tests.py
```

### Individual Test Files
```bash
# Unit tests
python -m pytest tests/test_node_knowledge_service.py -v
python -m pytest tests/test_mcp_tools.py -v

# Integration tests
python -m pytest tests/test_mcp_endpoints.py -v

# Error handling tests
python -m pytest tests/test_mcp_error_handling.py -v

# Performance tests
python -m pytest tests/test_mcp_performance.py -v

# Basic functionality
python -m pytest tests/test_basic.py -v
```

### Test with Coverage
```bash
python -m pytest tests/ --cov=app --cov-report=html
```

## Test Statistics

- **Total Test Files**: 6
- **Total Test Cases**: ~80 tests
- **Coverage Areas**:
  - Unit tests: 40+ tests
  - Integration tests: 20+ tests
  - Error handling: 15+ tests
  - Performance tests: 10+ tests
  - Basic functionality: 10+ tests

## Key Testing Principles

1. **Isolation** - Each test is independent and uses mocked dependencies
2. **Comprehensiveness** - Tests cover happy path, edge cases, and error conditions
3. **Performance** - Performance tests ensure scalability
4. **Real-world scenarios** - Tests simulate actual usage patterns
5. **Error resilience** - Extensive error handling validation

## Mock Strategy

- **Node Registry** - Comprehensive mock with 500+ test specs
- **Authentication** - Mocked API key validation
- **HTTP Requests** - FastAPI TestClient for integration tests
- **Async Operations** - Full async/await testing support
- **Warning Suppression** - Clean test output without registry warnings

## Continuous Integration

These tests are designed to run in CI/CD environments with:
- No external dependencies (all mocked)
- Fast execution (complete suite < 5 seconds)
- Clear failure reporting
- Deterministic results

## Future Test Enhancements

- [ ] Load testing with very large registries (10,000+ specs)
- [ ] Memory leak detection in long-running scenarios
- [ ] Network failure simulation
- [ ] Database persistence testing
- [ ] Real-time performance monitoring
>>>>>>> 9d01ca06259e01482a9566540300517a68f80f8b
