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
