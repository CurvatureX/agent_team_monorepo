"""
Basic tests for HTTP client functionality.

Simple tests to verify core HTTPClient functionality works correctly.
"""

import pytest
from unittest.mock import patch, MagicMock
import json

from workflow_engine.clients.http_client import (
    HTTPClient,
    HTTPClientError,
    AuthenticationError,
)


class TestHTTPClientBasic:
    """Basic test cases for HTTPClient class."""
    
    def test_client_initialization(self):
        """Test HTTPClient can be initialized."""
        client = HTTPClient()
        
        assert client.timeout.connect == 5.0
        assert client.timeout.read == 30.0
        assert client.max_response_size == 10 * 1024 * 1024  # 10MB
        assert client.max_retries == 3
        assert client.retry_delays == [2, 4, 8]
        assert "User-Agent" in client.default_headers
        assert "Accept" in client.default_headers
    
    def test_bearer_token_auth(self):
        """Test Bearer token authentication header generation."""
        client = HTTPClient()
        auth_config = {"type": "bearer", "token": "abc123xyz"}
        
        headers = client._apply_auth(auth_config)
        assert headers["Authorization"] == "Bearer abc123xyz"
    
    def test_api_key_auth(self):
        """Test API key authentication header generation."""
        client = HTTPClient()
        auth_config = {
            "type": "api_key",
            "key_name": "X-API-Key",
            "key_value": "secret-key-123",
            "location": "header"
        }
        
        headers = client._apply_auth(auth_config)
        assert headers["X-API-Key"] == "secret-key-123"
    
    def test_basic_auth(self):
        """Test Basic authentication header generation."""
        client = HTTPClient()
        auth_config = {
            "type": "basic_auth",
            "username": "testuser",
            "password": "testpass"
        }
        
        headers = client._apply_auth(auth_config)
        
        # Verify Authorization header exists and is correct format
        auth_header = headers["Authorization"]
        assert auth_header.startswith("Basic ")
        
        # Decode and verify credentials
        import base64
        encoded_creds = auth_header.split(" ", 1)[1]
        decoded_creds = base64.b64decode(encoded_creds).decode()
        assert decoded_creds == "testuser:testpass"
    
    def test_invalid_auth_type(self):
        """Test invalid authentication type raises error."""
        client = HTTPClient()
        auth_config = {"type": "invalid_type"}
        
        with pytest.raises(AuthenticationError, match="Unsupported authentication type"):
            client._apply_auth(auth_config)
    
    def test_missing_bearer_token(self):
        """Test missing Bearer token raises error."""
        client = HTTPClient()
        auth_config = {"type": "bearer"}
        
        with pytest.raises(AuthenticationError, match="Bearer token is required"):
            client._apply_auth(auth_config)
    
    def test_missing_api_key_values(self):
        """Test missing API key values raises error."""
        client = HTTPClient()
        auth_config = {"type": "api_key", "key_name": "X-API-Key"}
        
        with pytest.raises(AuthenticationError, match="API key name and value are required"):
            client._apply_auth(auth_config)
    
    def test_invalid_http_method(self):
        """Test invalid HTTP method raises error."""
        client = HTTPClient()
        
        with pytest.raises(HTTPClientError, match="Unsupported HTTP method"):
            client.request("INVALID", "https://api.example.com")
    
    def test_json_response_parsing(self):
        """Test JSON response parsing."""
        client = HTTPClient()
        
        # Mock JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"key": "value"}
        mock_response.content = b'{"key": "value"}'
        mock_response.text = '{"key": "value"}'
        mock_response.url = "https://api.example.com"
        mock_response.request.method = "GET"
        mock_response.elapsed.total_seconds.return_value = 0.3
        
        result = client._handle_response(mock_response)
        
        assert result["status_code"] == 200
        assert result["data"] == {"key": "value"}
        assert result["success"] is True
        assert result["response_time"] == 0.3
        assert "timestamp" in result
    
    def test_text_response_parsing(self):
        """Test text response parsing."""
        client = HTTPClient()
        
        # Mock text response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = b'plain text response'
        mock_response.text = 'plain text response'
        mock_response.url = "https://api.example.com"
        mock_response.request.method = "GET"
        mock_response.elapsed.total_seconds.return_value = 0.2
        
        result = client._handle_response(mock_response)
        
        assert result["status_code"] == 200
        assert result["data"] == "plain text response"
        assert result["success"] is True 