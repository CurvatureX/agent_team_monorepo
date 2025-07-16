"""
Unit tests for HTTP client functionality.

Tests HTTP request methods, authentication, retry mechanisms, and error handling.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import httpx

from workflow_engine.clients.http_client import (
    HTTPClient,
    HTTPClientError,
    AuthenticationError,
    RateLimitError,
    ResponseSizeError,
    get, post, put, delete
)


class TestHTTPClient:
    """Test cases for HTTPClient class."""
    
    def test_init(self):
        """Test HTTPClient initialization."""
        client = HTTPClient()
        
        assert client.timeout.connect == 5.0
        assert client.timeout.read == 30.0
        assert client.max_response_size == 10 * 1024 * 1024  # 10MB
        assert client.max_retries == 3
        assert client.retry_delays == [2, 4, 8]
        assert "User-Agent" in client.default_headers
        assert "Accept" in client.default_headers
    
    @patch('workflow_engine.clients.http_client.httpx.Client')
    def test_successful_get_request(self, mock_client_class):
        """Test successful GET request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"status": "success"}
        mock_response.text = '{"status": "success"}'
        mock_response.content = b'{"status": "success"}'
        mock_response.url = "https://api.example.com/data"
        mock_response.request.method = "GET"
        mock_response.elapsed.total_seconds.return_value = 0.5
        
        # Mock client
        mock_client = Mock()
        mock_client.request.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        # Test request
        client = HTTPClient()
        result = client.request("GET", "https://api.example.com/data")
        
        assert result["status_code"] == 200
        assert result["data"] == {"status": "success"}
        assert result["success"] is True
        assert result["response_time"] == 0.5
        assert "timestamp" in result
        
        # Verify call
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[0] == ("GET", "https://api.example.com/data")
    
    @patch('workflow_engine.clients.http_client.httpx.Client')
    def test_post_request_with_json_data(self, mock_client_class):
        """Test POST request with JSON data."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"id": 123, "created": True}
        mock_response.text = '{"id": 123, "created": true}'
        mock_response.content = b'{"id": 123, "created": true}'
        mock_response.url = "https://api.example.com/items"
        mock_response.request.method = "POST"
        mock_response.elapsed.total_seconds.return_value = 0.8
        
        # Mock client
        mock_client = Mock()
        mock_client.request.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        # Test request
        client = HTTPClient()
        json_data = {"name": "test item", "value": 42}
        result = client.request("POST", "https://api.example.com/items", json_data=json_data)
        
        assert result["status_code"] == 201
        assert result["data"] == {"id": 123, "created": True}
        
        # Verify JSON data was passed
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["json"] == json_data
    
    def test_bearer_token_auth(self):
        """Test Bearer token authentication."""
        client = HTTPClient()
        auth_config = {"type": "bearer", "token": "abc123xyz"}
        
        headers = client._apply_auth(auth_config)
        assert headers["Authorization"] == "Bearer abc123xyz"
    
    def test_api_key_auth(self):
        """Test API key authentication."""
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
        """Test Basic authentication."""
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
        """Test invalid authentication type."""
        client = HTTPClient()
        auth_config = {"type": "invalid_type"}
        
        with pytest.raises(AuthenticationError, match="Unsupported authentication type"):
            client._apply_auth(auth_config)
    
    def test_missing_bearer_token(self):
        """Test missing Bearer token."""
        client = HTTPClient()
        auth_config = {"type": "bearer"}
        
        with pytest.raises(AuthenticationError, match="Bearer token is required"):
            client._apply_auth(auth_config)
    
    def test_missing_api_key_values(self):
        """Test missing API key values."""
        client = HTTPClient()
        auth_config = {"type": "api_key", "key_name": "X-API-Key"}
        
        with pytest.raises(AuthenticationError, match="API key name and value are required"):
            client._apply_auth(auth_config)
    
    def test_missing_basic_auth_credentials(self):
        """Test missing Basic auth credentials."""
        client = HTTPClient()
        auth_config = {"type": "basic_auth", "username": "testuser"}
        
        with pytest.raises(AuthenticationError, match="Username and password are required"):
            client._apply_auth(auth_config)
    
    def test_invalid_http_method(self):
        """Test invalid HTTP method."""
        client = HTTPClient()
        
        with pytest.raises(HTTPClientError, match="Unsupported HTTP method"):
            client.request("INVALID", "https://api.example.com")
    
    @patch('workflow_engine.clients.http_client.httpx.Client')
    def test_rate_limit_retry(self, mock_client_class):
        """Test rate limit handling with retry."""
        # Mock client to return 429 on first call, 200 on second
        mock_client = Mock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        # First response: rate limit
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.text = "Rate limit exceeded"
        
        # Second response: success
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {"content-type": "application/json"}
        success_response.json.return_value = {"status": "success"}
        success_response.text = '{"status": "success"}'
        success_response.content = b'{"status": "success"}'
        success_response.url = "https://api.example.com/data"
        success_response.request.method = "GET"
        success_response.elapsed.total_seconds.return_value = 0.5
        
        mock_client.request.side_effect = [rate_limit_response, success_response]
        
        # Mock time.sleep to speed up test
        with patch('time.sleep') as mock_sleep:
            client = HTTPClient()
            result = client.request("GET", "https://api.example.com/data")
            
            assert result["status_code"] == 200
            assert result["data"] == {"status": "success"}
            
            # Verify retry was attempted
            assert mock_client.request.call_count == 2
            mock_sleep.assert_called_once_with(2)  # First retry delay
    
    @patch('workflow_engine.clients.http_client.httpx.Client')
    def test_rate_limit_max_retries_exceeded(self, mock_client_class):
        """Test rate limit with max retries exceeded."""
        # Mock client to always return 429
        mock_client = Mock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.text = "Rate limit exceeded"
        
        mock_client.request.return_value = rate_limit_response
        
        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            client = HTTPClient()
            
            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                client.request("GET", "https://api.example.com/data")
            
            # Should have tried max_retries + 1 times
            assert mock_client.request.call_count == 4  # 3 retries + initial attempt
    
    @patch('workflow_engine.clients.http_client.httpx.Client')
    def test_authentication_error(self, mock_client_class):
        """Test authentication error handling."""
        # Mock client to return 401
        mock_client = Mock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        auth_error_response = Mock()
        auth_error_response.status_code = 401
        auth_error_response.text = "Unauthorized"
        
        mock_client.request.return_value = auth_error_response
        
        client = HTTPClient()
        
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            client.request("GET", "https://api.example.com/data")
    
    @patch('workflow_engine.clients.http_client.httpx.Client')
    def test_network_error_retry(self, mock_client_class):
        """Test network error retry mechanism."""
        # Mock client to raise ConnectError on first call, succeed on second
        mock_client = Mock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        # Success response
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {"content-type": "application/json"}
        success_response.json.return_value = {"status": "success"}
        success_response.text = '{"status": "success"}'
        success_response.content = b'{"status": "success"}'
        success_response.url = "https://api.example.com/data"
        success_response.request.method = "GET"
        success_response.elapsed.total_seconds.return_value = 0.5
        
        mock_client.request.side_effect = [
            httpx.ConnectError("Connection failed"),
            success_response
        ]
        
        # Mock time.sleep to speed up test
        with patch('time.sleep') as mock_sleep:
            client = HTTPClient()
            result = client.request("GET", "https://api.example.com/data")
            
            assert result["status_code"] == 200
            assert result["data"] == {"status": "success"}
            
            # Verify retry was attempted
            assert mock_client.request.call_count == 2
            mock_sleep.assert_called_once_with(2)  # First retry delay
    
    @patch('workflow_engine.clients.http_client.httpx.Client')
    def test_network_error_max_retries_exceeded(self, mock_client_class):
        """Test network error with max retries exceeded."""
        # Mock client to always raise ConnectError
        mock_client = Mock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        mock_client.request.side_effect = httpx.ConnectError("Connection failed")
        
        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            client = HTTPClient()
            
            with pytest.raises(HTTPClientError, match="Network error after 3 retries"):
                client.request("GET", "https://api.example.com/data")
            
            # Should have tried max_retries + 1 times
            assert mock_client.request.call_count == 4  # 3 retries + initial attempt
    
    def test_response_size_limit(self):
        """Test response size limit checking."""
        client = HTTPClient()
        
        # Mock response with large content
        mock_response = Mock()
        mock_response.headers = {"content-length": str(20 * 1024 * 1024)}  # 20MB
        
        with pytest.raises(ResponseSizeError, match="exceeds limit"):
            client._handle_response(mock_response)
    
    def test_json_response_parsing(self):
        """Test JSON response parsing."""
        client = HTTPClient()
        
        # Mock JSON response
        mock_response = Mock()
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
    
    def test_text_response_parsing(self):
        """Test text response parsing."""
        client = HTTPClient()
        
        # Mock text response
        mock_response = Mock()
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
    
    def test_json_decode_error_fallback(self):
        """Test JSON decode error fallback to text."""
        client = HTTPClient()
        
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.content = b'invalid json content'
        mock_response.text = 'invalid json content'
        mock_response.url = "https://api.example.com"
        mock_response.request.method = "GET"
        mock_response.elapsed.total_seconds.return_value = 0.1
        
        result = client._handle_response(mock_response)
        
        assert result["status_code"] == 200
        assert result["data"] == "invalid json content"
        assert result["success"] is True


class TestConvenienceFunctions:
    """Test convenience functions for HTTP methods."""
    
    @patch('workflow_engine.clients.http_client.HTTPClient')
    def test_get_function(self, mock_http_client_class):
        """Test GET convenience function."""
        mock_client = Mock()
        mock_client.request.return_value = {"status": "success"}
        mock_http_client_class.return_value = mock_client
        
        result = get("https://api.example.com/data")
        
        assert result == {"status": "success"}
        mock_client.request.assert_called_once_with(
            "GET", "https://api.example.com/data", auth_config=None
        )
    
    @patch('workflow_engine.clients.http_client.HTTPClient')
    def test_post_function(self, mock_http_client_class):
        """Test POST convenience function."""
        mock_client = Mock()
        mock_client.request.return_value = {"id": 123}
        mock_http_client_class.return_value = mock_client
        
        auth_config = {"type": "bearer", "token": "abc123"}
        result = post("https://api.example.com/items", auth_config=auth_config, json_data={"name": "test"})
        
        assert result == {"id": 123}
        mock_client.request.assert_called_once_with(
            "POST", "https://api.example.com/items", auth_config=auth_config, json_data={"name": "test"}
        )
    
    @patch('workflow_engine.clients.http_client.HTTPClient')
    def test_put_function(self, mock_http_client_class):
        """Test PUT convenience function."""
        mock_client = Mock()
        mock_client.request.return_value = {"updated": True}
        mock_http_client_class.return_value = mock_client
        
        result = put("https://api.example.com/items/123")
        
        assert result == {"updated": True}
        mock_client.request.assert_called_once_with(
            "PUT", "https://api.example.com/items/123", auth_config=None
        )
    
    @patch('workflow_engine.clients.http_client.HTTPClient')
    def test_delete_function(self, mock_http_client_class):
        """Test DELETE convenience function."""
        mock_client = Mock()
        mock_client.request.return_value = {"deleted": True}
        mock_http_client_class.return_value = mock_client
        
        result = delete("https://api.example.com/items/123")
        
        assert result == {"deleted": True}
        mock_client.request.assert_called_once_with(
            "DELETE", "https://api.example.com/items/123", auth_config=None
        ) 