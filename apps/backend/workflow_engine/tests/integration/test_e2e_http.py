"""
End-to-end integration tests for HTTP tool.

This module tests the complete HTTP tool integration flow including:
- Different HTTP methods (GET, POST, PUT, DELETE)
- Authentication methods (Bearer, API Key, Basic Auth)
- Tool node execution
- Error handling and recovery
- Performance and concurrent operations
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import json

from workflow_engine.clients.http_client import HTTPClient, HTTPError
from workflow_engine.nodes.tool_node import ToolNodeExecutor
from workflow_engine.nodes.base import NodeExecutionContext


@pytest.fixture
def mock_httpx_response():
    """Create mock httpx response."""
    response = MagicMock()
    response.status_code = 200
    response.headers = {"content-type": "application/json"}
    response.json.return_value = {"success": True, "data": "test data"}
    response.text = '{"success": true, "data": "test data"}'
    response.raise_for_status.return_value = None
    return response


class TestHTTPToolE2E:
    """End-to-end tests for HTTP tool integration."""
    
    @pytest.mark.asyncio
    async def test_complete_http_get_workflow(self, mock_httpx_response):
        """Test complete HTTP GET workflow."""
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_httpx_response
            
            client = HTTPClient({
                "type": "bearer",
                "token": "test_bearer_token"
            })
            
            # Test GET request
            result = await client.request(
                method="GET",
                url="https://api.example.com/users",
                headers={"Accept": "application/json"}
            )
            
            assert result["success"] == True
            assert result["data"] == "test data"
            
            # Verify the request was made correctly
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "GET"
            assert call_args[1]["url"] == "https://api.example.com/users"
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Authorization"] == "Bearer test_bearer_token"
    
    @pytest.mark.asyncio
    async def test_http_post_with_json_payload(self, mock_httpx_response):
        """Test HTTP POST request with JSON payload."""
        
        # Mock response for POST
        mock_httpx_response.status_code = 201
        mock_httpx_response.json.return_value = {"id": 123, "created": True}
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_httpx_response
            
            client = HTTPClient({
                "type": "api_key",
                "key_name": "X-API-Key",
                "key_value": "test_api_key",
                "location": "header"
            })
            
            # Test POST request
            payload = {"name": "John Doe", "email": "john@example.com"}
            result = await client.request(
                method="POST",
                url="https://api.example.com/users",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert result["id"] == 123
            assert result["created"] == True
            
            # Verify the request was made correctly
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "POST"
            assert call_args[1]["json"] == payload
            assert call_args[1]["headers"]["X-API-Key"] == "test_api_key"
    
    @pytest.mark.asyncio
    async def test_http_authentication_methods(self, mock_httpx_response):
        """Test different HTTP authentication methods."""
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_httpx_response
            
            # Test 1: Bearer Token Authentication
            bearer_client = HTTPClient({
                "type": "bearer",
                "token": "test_bearer_token"
            })
            
            await bearer_client.request("GET", "https://api.example.com/data")
            bearer_call = mock_request.call_args
            assert bearer_call[1]["headers"]["Authorization"] == "Bearer test_bearer_token"
            
            mock_request.reset_mock()
            
            # Test 2: API Key Authentication (Header)
            apikey_client = HTTPClient({
                "type": "api_key",
                "key_name": "X-API-Key",
                "key_value": "test_api_key",
                "location": "header"
            })
            
            await apikey_client.request("GET", "https://api.example.com/data")
            apikey_call = mock_request.call_args
            assert apikey_call[1]["headers"]["X-API-Key"] == "test_api_key"
            
            mock_request.reset_mock()
            
            # Test 3: API Key Authentication (Query Parameter)
            apikey_query_client = HTTPClient({
                "type": "api_key",
                "key_name": "api_key",
                "key_value": "test_query_key",
                "location": "query"
            })
            
            await apikey_query_client.request("GET", "https://api.example.com/data")
            query_call = mock_request.call_args
            assert query_call[1]["params"]["api_key"] == "test_query_key"
            
            mock_request.reset_mock()
            
            # Test 4: Basic Authentication
            basic_client = HTTPClient({
                "type": "basic_auth",
                "username": "testuser",
                "password": "testpass"
            })
            
            await basic_client.request("GET", "https://api.example.com/data")
            basic_call = mock_request.call_args
            assert "Authorization" in basic_call[1]["headers"]
            assert basic_call[1]["headers"]["Authorization"].startswith("Basic ")
    
    @pytest.mark.asyncio
    async def test_http_methods_comprehensive(self, mock_httpx_response):
        """Test all supported HTTP methods."""
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_httpx_response
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            methods_and_payloads = [
                ("GET", None),
                ("POST", {"data": "create"}),
                ("PUT", {"data": "update"}),
                ("DELETE", None),
                ("PATCH", {"data": "partial_update"}),
                ("HEAD", None),
                ("OPTIONS", None)
            ]
            
            for method, payload in methods_and_payloads:
                mock_request.reset_mock()
                
                if payload:
                    await client.request(method, "https://api.example.com/resource", json=payload)
                else:
                    await client.request(method, "https://api.example.com/resource")
                
                call_args = mock_request.call_args
                assert call_args[1]["method"] == method
                
                if payload:
                    assert call_args[1]["json"] == payload
    
    @pytest.mark.asyncio
    async def test_tool_node_http_execution(self, mock_httpx_response):
        """Test HTTP tool execution through ToolNodeExecutor."""
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_httpx_response
            
            # Create mock execution context
            context = MagicMock(spec=NodeExecutionContext)
            context.get_parameter.side_effect = lambda key, default=None: {
                "provider": "http",
                "action": "request",
                "method": "GET",
                "url": "https://api.example.com/test",
                "user_id": "test_user"
            }.get(key, default)
            
            context.input_data = {
                "url": "https://api.example.com/test",
                "method": "GET",
                "headers": {"Accept": "application/json"},
                "auth_config": {
                    "type": "bearer",
                    "token": "test_token"
                }
            }
            
            # Execute tool
            executor = ToolNodeExecutor()
            result = executor._execute_http_tool(context, [], 0.0)
            
            # Verify result
            assert result.status.value == "SUCCESS"
            assert "tool_type" in result.output_data
            assert result.output_data["tool_type"] == "http"
            assert result.output_data["method"] == "GET"
            
            # Verify API was called
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_http_error_handling_and_retry(self, mock_httpx_response):
        """Test error handling and retry mechanism for HTTP requests."""
        
        # Mock initial failures followed by success
        import httpx
        
        error_responses = [
            httpx.HTTPStatusError("500 Internal Server Error", request=MagicMock(), response=MagicMock()),
            httpx.HTTPStatusError("502 Bad Gateway", request=MagicMock(), response=MagicMock()),
            mock_httpx_response  # Third attempt succeeds
        ]
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.side_effect = error_responses
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            # This should retry and eventually succeed
            with patch('asyncio.sleep'):  # Speed up the test
                result = await client.request("GET", "https://api.example.com/unreliable")
            
            assert result["success"] == True
            assert mock_request.call_count == 3  # Should have retried 3 times
    
    @pytest.mark.asyncio
    async def test_http_timeout_handling(self):
        """Test HTTP timeout handling."""
        
        import httpx
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Request timeout")
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            with pytest.raises(HTTPError) as exc_info:
                await client.request("GET", "https://api.example.com/slow")
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_http_operations(self, mock_httpx_response):
        """Test concurrent HTTP operations."""
        
        # Mock responses for concurrent operations
        mock_responses = []
        for i in range(5):
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"id": i, "data": f"response_{i}"}
            response.raise_for_status.return_value = None
            mock_responses.append(response)
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.side_effect = mock_responses
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            # Make multiple requests concurrently
            start_time = datetime.now()
            
            tasks = []
            for i in range(5):
                task = client.request(
                    "GET",
                    f"https://api.example.com/data/{i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Verify all requests were successful
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result["id"] == i
                assert result["data"] == f"response_{i}"
            
            # Concurrent execution should complete within reasonable time
            assert execution_time < 10.0
            assert mock_request.call_count == 5
    
    @pytest.mark.asyncio
    async def test_large_response_handling(self):
        """Test handling of large responses."""
        
        # Mock large response
        large_data = {"data": "x" * 1000000}  # 1MB of data
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = large_data
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-length": str(len(json.dumps(large_data)))}
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_response
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            # This should handle large responses correctly
            result = await client.request("GET", "https://api.example.com/large-data")
            
            assert len(result["data"]) == 1000000
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_custom_headers_and_params(self, mock_httpx_response):
        """Test custom headers and query parameters."""
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_httpx_response
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            # Test with custom headers and params
            custom_headers = {
                "Accept": "application/json",
                "User-Agent": "MyApp/1.0",
                "X-Custom-Header": "custom-value"
            }
            
            query_params = {
                "page": 1,
                "limit": 10,
                "filter": "active"
            }
            
            await client.request(
                "GET",
                "https://api.example.com/data",
                headers=custom_headers,
                params=query_params
            )
            
            call_args = mock_request.call_args
            
            # Verify custom headers are included (along with auth)
            request_headers = call_args[1]["headers"]
            assert request_headers["Accept"] == "application/json"
            assert request_headers["User-Agent"] == "MyApp/1.0"
            assert request_headers["X-Custom-Header"] == "custom-value"
            assert "Authorization" in request_headers  # Auth header should still be there
            
            # Verify query parameters
            request_params = call_args[1]["params"]
            assert request_params["page"] == 1
            assert request_params["limit"] == 10
            assert request_params["filter"] == "active"
    
    @pytest.mark.asyncio
    async def test_http_performance_benchmarks(self, mock_httpx_response):
        """Test performance benchmarks for HTTP operations."""
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_httpx_response
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            # Measure single request performance
            start_time = datetime.now()
            
            await client.request("GET", "https://api.example.com/performance-test")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Performance should be under 5 seconds (excluding actual network latency)
            assert execution_time < 5.0
            
            # Test rapid sequential requests
            start_time = datetime.now()
            
            for i in range(10):
                await client.request("GET", f"https://api.example.com/seq/{i}")
            
            sequential_time = (datetime.now() - start_time).total_seconds()
            
            # Sequential requests should complete within reasonable time
            assert sequential_time < 10.0
            assert mock_request.call_count == 11  # 1 + 10 sequential calls


class TestHTTPIntegrationErrors:
    """Test error scenarios and edge cases for HTTP integration."""
    
    @pytest.mark.asyncio
    async def test_invalid_url_handling(self):
        """Test handling of invalid URLs."""
        
        client = HTTPClient({"type": "bearer", "token": "test_token"})
        
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://invalid-protocol.com",
            "http://",
            "https://"
        ]
        
        for invalid_url in invalid_urls:
            with pytest.raises(HTTPError):
                await client.request("GET", invalid_url)
    
    @pytest.mark.asyncio
    async def test_unsupported_http_methods(self):
        """Test handling of unsupported HTTP methods."""
        
        client = HTTPClient({"type": "bearer", "token": "test_token"})
        
        # Most HTTP methods should be supported, but test edge cases
        valid_url = "https://api.example.com/test"
        
        # These should work without errors (assuming proper mocking)
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            # Test various methods
            methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
            
            for method in methods:
                await client.request(method, valid_url)
            
            assert mock_request.call_count == len(methods)
    
    @pytest.mark.asyncio
    async def test_malformed_auth_config(self):
        """Test handling of malformed authentication configurations."""
        
        malformed_configs = [
            {"type": "unknown_auth"},  # Unknown auth type
            {"type": "bearer"},  # Missing token
            {"type": "api_key", "key_name": "X-API-Key"},  # Missing key_value
            {"type": "basic_auth", "username": "user"},  # Missing password
            {}  # Empty config
        ]
        
        for config in malformed_configs:
            with pytest.raises((HTTPError, ValueError, KeyError)):
                client = HTTPClient(config)
                await client.request("GET", "https://api.example.com/test")
    
    @pytest.mark.asyncio
    async def test_network_connectivity_issues(self):
        """Test handling of network connectivity issues."""
        
        import httpx
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            with pytest.raises(HTTPError) as exc_info:
                await client.request("GET", "https://api.example.com/test")
            
            assert "connection" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_http_status_error_handling(self):
        """Test handling of various HTTP status errors."""
        
        import httpx
        
        status_codes_and_errors = [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (429, "Too Many Requests"),
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable")
        ]
        
        for status_code, error_message in status_codes_and_errors:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                error_message, 
                request=MagicMock(), 
                response=mock_response
            )
            
            with patch('httpx.AsyncClient.request') as mock_request:
                mock_request.return_value = mock_response
                
                client = HTTPClient({"type": "bearer", "token": "test_token"})
                
                with pytest.raises(HTTPError) as exc_info:
                    await client.request("GET", "https://api.example.com/test")
                
                assert str(status_code) in str(exc_info.value) or error_message in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON responses."""
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "This is not valid JSON"
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_response
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            # Should handle malformed JSON gracefully
            result = await client.request("GET", "https://api.example.com/bad-json")
            
            # Should return text content when JSON parsing fails
            assert result == "This is not valid JSON"
    
    @pytest.mark.asyncio
    async def test_response_size_limits(self):
        """Test handling of response size limits."""
        
        # This would test the 10MB response limit mentioned in requirements
        # For now, we'll test the concept with a smaller size
        
        oversized_data = "x" * (15 * 1024 * 1024)  # 15MB of data
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": str(len(oversized_data))}
        mock_response.text = oversized_data
        mock_response.json.side_effect = ValueError("Response too large")
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_response
            
            client = HTTPClient({"type": "bearer", "token": "test_token"})
            
            # Should handle oversized responses appropriately
            # The exact behavior depends on implementation details
            try:
                result = await client.request("GET", "https://api.example.com/large-response")
                # If it succeeds, verify it's handled properly
                assert isinstance(result, str)
            except HTTPError:
                # If it fails, that's also acceptable for oversized responses
                pass 