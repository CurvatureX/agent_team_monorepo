"""
Integration tests for Tool Node HTTP functionality.

Tests the integration between ToolNodeExecutor and HTTPClient for real HTTP requests.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from workflow_engine.nodes.tool_node import ToolNodeExecutor
from workflow_engine.nodes.base import NodeExecutionContext, ExecutionStatus
from workflow_engine.clients.http_client import HTTPClientError, AuthenticationError


class MockNode:
    """Mock node object for testing."""
    def __init__(self, subtype="HTTP", parameters=None):
        self.subtype = subtype
        self.parameters = parameters or {}


class TestToolNodeHTTPIntegration:
    """Test cases for Tool Node HTTP integration."""
    
    def test_execute_http_tool_get_request(self):
        """Test successful GET request through tool node."""
        # Create tool node executor
        executor = ToolNodeExecutor()
        
        # Mock context
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://httpbin.org/get",
                "method": "GET",
                "headers": {"User-Agent": "TestClient/1.0"}
            }),
            workflow_id="test-workflow",
            execution_id="test-execution", 
            input_data={"test": "data"},
            static_data={},
            credentials={},
            metadata={}
        )
        
        # Mock HTTPClient to avoid real network calls
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "data": {"args": {}, "headers": {"User-Agent": "TestClient/1.0"}},
                "url": "https://httpbin.org/get",
                "method": "GET",
                "success": True,
                "response_time": 0.5,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            # Execute
            result = executor._execute_http_tool(context, [], time.time())
            
            # Verify result
            assert result.status == ExecutionStatus.SUCCESS
            assert result.output_data["tool_type"] == "http"
            assert result.output_data["url"] == "https://httpbin.org/get"
            assert result.output_data["method"] == "GET"
            assert result.output_data["http_result"]["status_code"] == 200
            assert "executed_at" in result.output_data
            
            # Verify HTTP client was called correctly
            mock_client.request.assert_called_once_with(
                method="GET",
                url="https://httpbin.org/get",
                auth_config=None,
                headers={"User-Agent": "TestClient/1.0"},
                data={"test": "data"},
                json_data=None
            )
    
    def test_execute_http_tool_post_request_with_json(self):
        """Test POST request with JSON data through tool node."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://httpbin.org/post",
                "method": "POST",
                "json": {"name": "test", "value": 123}
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={"additional": "data"},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 201,
                "headers": {"content-type": "application/json"},
                "data": {"json": {"name": "test", "value": 123}},
                "url": "https://httpbin.org/post",
                "method": "POST",
                "success": True,
                "response_time": 0.8,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            result = executor._execute_http_tool(context, [], time.time())
            
            assert result.status == ExecutionStatus.SUCCESS
            assert result.output_data["method"] == "POST"
            assert result.output_data["json_data"] == {"name": "test", "value": 123}
            assert result.output_data["http_result"]["status_code"] == 201
            
            # Verify JSON data was passed correctly
            mock_client.request.assert_called_once_with(
                method="POST",
                url="https://httpbin.org/post",
                auth_config=None,
                headers=None,
                data={"additional": "data"},
                json_data={"name": "test", "value": 123}
            )
    
    def test_execute_http_tool_with_bearer_auth(self):
        """Test HTTP request with Bearer token authentication."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://api.example.com/secure",
                "method": "GET",
                "auth": {
                    "type": "bearer",
                    "token": "abc123xyz"
                }
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "data": {"authenticated": True},
                "url": "https://api.example.com/secure",
                "method": "GET",
                "success": True,
                "response_time": 0.3,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            result = executor._execute_http_tool(context, [], time.time())
            
            assert result.status == ExecutionStatus.SUCCESS
            assert result.output_data["auth_config"]["type"] == "bearer"
            assert result.output_data["http_result"]["data"]["authenticated"] is True
            
            # Verify auth config was passed
            mock_client.request.assert_called_once_with(
                method="GET",
                url="https://api.example.com/secure",
                auth_config={"type": "bearer", "token": "abc123xyz"},
                headers=None,
                data=None,
                json_data=None
            )
    
    def test_execute_http_tool_with_api_key_auth(self):
        """Test HTTP request with API key authentication."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://api.example.com/data",
                "method": "GET",
                "auth": {
                    "type": "api_key",
                    "key_name": "X-API-Key",
                    "key_value": "secret-123",
                    "location": "header"
                }
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "data": {"api_key_valid": True},
                "url": "https://api.example.com/data",
                "method": "GET",
                "success": True,
                "response_time": 0.4,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            result = executor._execute_http_tool(context, [], time.time())
            
            assert result.status == ExecutionStatus.SUCCESS
            assert result.output_data["auth_config"]["type"] == "api_key"
            
            # Verify API key auth was passed
            auth_config = {
                "type": "api_key",
                "key_name": "X-API-Key",
                "key_value": "secret-123",
                "location": "header"
            }
            mock_client.request.assert_called_once_with(
                method="GET",
                url="https://api.example.com/data",
                auth_config=auth_config,
                headers=None,
                data=None,
                json_data=None
            )
    
    def test_execute_http_tool_with_basic_auth(self):
        """Test HTTP request with Basic authentication."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://api.example.com/secure",
                "method": "GET",
                "auth": {
                    "type": "basic_auth",
                    "username": "testuser",
                    "password": "testpass"
                }
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "data": {"user": "testuser"},
                "url": "https://api.example.com/secure",
                "method": "GET",
                "success": True,
                "response_time": 0.6,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            result = executor._execute_http_tool(context, [], time.time())
            
            assert result.status == ExecutionStatus.SUCCESS
            assert result.output_data["auth_config"]["type"] == "basic_auth"
            
            # Verify Basic auth was passed
            auth_config = {
                "type": "basic_auth",
                "username": "testuser",
                "password": "testpass"
            }
            mock_client.request.assert_called_once_with(
                method="GET",
                url="https://api.example.com/secure",
                auth_config=auth_config,
                headers=None,
                data=None,
                json_data=None
            )
    
    def test_execute_http_tool_authentication_error(self):
        """Test HTTP request with authentication error."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://api.example.com/secure",
                "method": "GET",
                "auth": {
                    "type": "bearer",
                    "token": "invalid-token"
                }
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.side_effect = AuthenticationError("Authentication failed: 401 Unauthorized")
            mock_http_client_class.return_value = mock_client
            
            result = executor._execute_http_tool(context, [], time.time())
            
            assert result.status == ExecutionStatus.ERROR
            assert "Authentication failed" in result.error_message
            assert result.error_details["exception"] == "Authentication failed: 401 Unauthorized"
            assert result.error_details["url"] == "https://api.example.com/secure"
            assert result.error_details["method"] == "GET"
    
    def test_execute_http_tool_network_error(self):
        """Test HTTP request with network error."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://unreachable.example.com",
                "method": "GET"
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.side_effect = HTTPClientError("Network error after 3 retries: Connection failed")
            mock_http_client_class.return_value = mock_client
            
            result = executor._execute_http_tool(context, [], time.time())
            
            assert result.status == ExecutionStatus.ERROR
            assert "Network error" in result.error_message
            assert result.error_details["url"] == "https://unreachable.example.com"
    
    def test_execute_http_tool_default_method(self):
        """Test HTTP tool with default GET method."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://httpbin.org/get"
                # No method specified - should default to GET
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "data": {"method": "GET"},
                "url": "https://httpbin.org/get",
                "method": "GET",
                "success": True,
                "response_time": 0.2,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            result = executor._execute_http_tool(context, [], time.time())
            
            assert result.status == ExecutionStatus.SUCCESS
            assert result.output_data["method"] == "GET"
            
            # Verify default method was used
            mock_client.request.assert_called_once_with(
                method="GET",
                url="https://httpbin.org/get",
                auth_config=None,
                headers=None,
                data=None,
                json_data=None
            )
    
    def test_execute_http_tool_custom_headers(self):
        """Test HTTP request with custom headers."""
        executor = ToolNodeExecutor()
        
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "Accept": "application/vnd.api+json"
        }
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": custom_headers
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/vnd.api+json"},
                "data": {"message": "success"},
                "url": "https://api.example.com/data",
                "method": "GET",
                "success": True,
                "response_time": 0.3,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            result = executor._execute_http_tool(context, [], time.time())
            
            assert result.status == ExecutionStatus.SUCCESS
            assert result.output_data["headers"] == custom_headers
            
            # Verify custom headers were passed
            mock_client.request.assert_called_once_with(
                method="GET",
                url="https://api.example.com/data",
                auth_config=None,
                headers=custom_headers,
                data=None,
                json_data=None
            )
    
    def test_execute_http_tool_logs_generated(self):
        """Test that appropriate logs are generated during execution."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://httpbin.org/get",
                "method": "GET"
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "data": {"status": "ok"},
                "url": "https://httpbin.org/get",
                "method": "GET",
                "success": True,
                "response_time": 0.2,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            logs = []
            result = executor._execute_http_tool(context, logs, time.time())
            
            assert result.status == ExecutionStatus.SUCCESS
            assert len(logs) >= 2  # Should have at least start and completion logs
            assert "Executing HTTP GET request to https://httpbin.org/get" in logs[0]
            assert "HTTP request completed with status 200" in logs[1]
    
    def test_execute_http_tool_execution_time_recorded(self):
        """Test that execution time is properly recorded."""
        executor = ToolNodeExecutor()
        
        context = NodeExecutionContext(
            node=MockNode("HTTP", {
                "url": "https://httpbin.org/get",
                "method": "GET"
            }),
            workflow_id="test-workflow",
            execution_id="test-execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        with patch('workflow_engine.clients.http_client.HTTPClient') as mock_http_client_class:
            mock_client = Mock()
            mock_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "data": {"status": "ok"},
                "url": "https://httpbin.org/get",
                "method": "GET",
                "success": True,
                "response_time": 0.5,
                "timestamp": datetime.now().isoformat()
            }
            mock_http_client_class.return_value = mock_client
            
            start_time = time.time()
            result = executor._execute_http_tool(context, [], start_time)
            
            assert result.status == ExecutionStatus.SUCCESS
            assert result.execution_time is not None
            assert result.execution_time > 0
            assert result.execution_time < 1.0  # Should be quick for mocked request 