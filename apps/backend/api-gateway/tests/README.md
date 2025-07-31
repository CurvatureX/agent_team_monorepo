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