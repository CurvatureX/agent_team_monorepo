"""
Performance benchmark tests for tool integration system.

This module tests performance characteristics of the complete tool integration system
including response times, throughput, memory usage, and scalability.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from workflow_engine.clients.google_calendar_client import GoogleCalendarClient
from workflow_engine.clients.github_client import GitHubClient
from workflow_engine.clients.slack_client import SlackClient
from workflow_engine.clients.http_client import HTTPClient
from workflow_engine.services.oauth2_handler import OAuth2Handler
from workflow_engine.services.credential_service import CredentialService
from workflow_engine.nodes.tool_node import ToolNodeExecutor
from workflow_engine.models.credential import OAuth2Credential


@pytest.fixture
def mock_credentials():
    """Create mock credentials for performance testing."""
    credentials = OAuth2Credential()
    credentials.provider = "test_provider"
    credentials.access_token = "test_access_token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now() + timedelta(hours=1)).timestamp())
    return credentials


class PerformanceBenchmarks:
    """Base class for performance benchmarks."""
    
    @staticmethod
    def measure_execution_time(func):
        """Decorator to measure execution time."""
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            return result, execution_time
        return wrapper
    
    @staticmethod
    def calculate_statistics(times: List[float]) -> Dict[str, float]:
        """Calculate statistical metrics for execution times."""
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0.0,
            "p95": sorted(times)[int(0.95 * len(times))] if len(times) > 1 else times[0],
            "p99": sorted(times)[int(0.99 * len(times))] if len(times) > 1 else times[0]
        }


class TestGoogleCalendarPerformance(PerformanceBenchmarks):
    """Performance tests for Google Calendar client."""
    
    @pytest.mark.asyncio
    async def test_calendar_client_response_time(self, mock_credentials):
        """Test Google Calendar client response time performance."""
        
        # Mock API response
        mock_response = {
            "id": "test_event_123",
            "summary": "Performance Test Event",
            "start": {"dateTime": "2025-01-20T10:00:00Z"},
            "end": {"dateTime": "2025-01-20T11:00:00Z"}
        }
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            mock_request.return_value = mock_response
            
            client = GoogleCalendarClient(mock_credentials)
            
            # Measure response time for single operation
            @self.measure_execution_time
            async def create_event():
                return await client.create_event("primary", {
                    "summary": "Performance Test Event",
                    "start": {"dateTime": "2025-01-20T10:00:00Z"},
                    "end": {"dateTime": "2025-01-20T11:00:00Z"}
                })
            
            result, execution_time = await create_event()
            
            # Performance requirement: < 5 seconds (excluding network latency)
            assert execution_time < 5.0
            assert result["id"] == "test_event_123"
            
            print(f"Google Calendar create_event execution time: {execution_time:.4f}s")
    
    @pytest.mark.asyncio
    async def test_calendar_throughput_benchmark(self, mock_credentials):
        """Test Google Calendar throughput with concurrent operations."""
        
        mock_response = {"id": f"event_{i}", "summary": f"Event {i}"} 
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            mock_request.return_value = mock_response
            
            client = GoogleCalendarClient(mock_credentials)
            
            # Test concurrent operations
            concurrent_requests = 10
            execution_times = []
            
            async def timed_create_event(event_id: int):
                start_time = time.perf_counter()
                await client.create_event("primary", {
                    "summary": f"Concurrent Event {event_id}",
                    "start": {"dateTime": "2025-01-20T10:00:00Z"},
                    "end": {"dateTime": "2025-01-20T11:00:00Z"}
                })
                end_time = time.perf_counter()
                return end_time - start_time
            
            # Execute concurrent requests
            start_time = time.perf_counter()
            tasks = [timed_create_event(i) for i in range(concurrent_requests)]
            individual_times = await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_time
            
            # Calculate metrics
            stats = self.calculate_statistics(individual_times)
            throughput = concurrent_requests / total_time
            
            # Performance requirements
            assert stats["mean"] < 5.0  # Average response time < 5s
            assert stats["p95"] < 10.0  # 95th percentile < 10s
            assert throughput >= 1.0    # At least 1 request per second
            
            print(f"Google Calendar throughput: {throughput:.2f} req/s")
            print(f"Mean response time: {stats['mean']:.4f}s")
            print(f"P95 response time: {stats['p95']:.4f}s")
    
    @pytest.mark.asyncio
    async def test_calendar_memory_usage(self, mock_credentials):
        """Test memory usage during calendar operations."""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            mock_request.return_value = {"id": "test_event"}
            
            client = GoogleCalendarClient(mock_credentials)
            
            # Perform many operations to test memory usage
            for i in range(100):
                await client.create_event("primary", {
                    "summary": f"Memory Test Event {i}",
                    "start": {"dateTime": "2025-01-20T10:00:00Z"},
                    "end": {"dateTime": "2025-01-20T11:00:00Z"}
                })
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (< 50MB for 100 operations)
            assert memory_increase < 50.0
            
            print(f"Memory usage increase: {memory_increase:.2f} MB for 100 operations")


class TestGitHubPerformance(PerformanceBenchmarks):
    """Performance tests for GitHub client."""
    
    @pytest.mark.asyncio
    async def test_github_client_response_time(self, mock_credentials):
        """Test GitHub client response time performance."""
        
        mock_response = {
            "id": 123456789,
            "number": 42,
            "title": "Performance Test Issue",
            "state": "open"
        }
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.return_value = mock_response
            
            client = GitHubClient(mock_credentials)
            
            @self.measure_execution_time
            async def create_issue():
                return await client.create_issue(
                    repo="test/repo",
                    title="Performance Test Issue",
                    body="Testing GitHub client performance"
                )
            
            result, execution_time = await create_issue()
            
            # Performance requirement: < 5 seconds
            assert execution_time < 5.0
            assert result["number"] == 42
            
            print(f"GitHub create_issue execution time: {execution_time:.4f}s")
    
    @pytest.mark.asyncio
    async def test_github_file_operations_performance(self, mock_credentials):
        """Test GitHub file operations performance."""
        
        file_operations = [
            ("create_file", {
                "repo": "test/repo",
                "path": "test.txt",
                "content": "Performance test content",
                "message": "Performance test commit"
            }),
            ("get_file_content", {
                "repo": "test/repo", 
                "path": "test.txt"
            }),
            ("update_file", {
                "repo": "test/repo",
                "path": "test.txt", 
                "content": "Updated content",
                "message": "Update commit",
                "sha": "abc123"
            })
        ]
        
        with patch.object(GitHubClient, '_make_request') as mock_request:
            mock_request.return_value = {"sha": "abc123", "content": "test content"}
            
            client = GitHubClient(mock_credentials)
            execution_times = []
            
            for operation, kwargs in file_operations:
                start_time = time.perf_counter()
                method = getattr(client, operation)
                await method(**kwargs)
                execution_time = time.perf_counter() - start_time
                execution_times.append(execution_time)
            
            stats = self.calculate_statistics(execution_times)
            
            # All file operations should complete quickly
            assert stats["mean"] < 5.0
            assert stats["max"] < 10.0
            
            print(f"GitHub file operations - Mean: {stats['mean']:.4f}s, Max: {stats['max']:.4f}s")


class TestSlackPerformance(PerformanceBenchmarks):
    """Performance tests for Slack client."""
    
    @pytest.mark.asyncio
    async def test_slack_message_sending_performance(self, mock_credentials):
        """Test Slack message sending performance."""
        
        mock_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456"
        }
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.return_value = mock_response
            
            client = SlackClient(mock_credentials)
            
            @self.measure_execution_time
            async def send_message():
                return await client.send_message(
                    channel="#general",
                    text="Performance test message with *markdown* formatting"
                )
            
            result, execution_time = await send_message()
            
            # Performance requirement: < 5 seconds
            assert execution_time < 5.0
            assert result["ok"] == True
            
            print(f"Slack send_message execution time: {execution_time:.4f}s")
    
    @pytest.mark.asyncio
    async def test_slack_markdown_processing_performance(self, mock_credentials):
        """Test Slack markdown processing performance."""
        
        with patch.object(SlackClient, '_make_request') as mock_request:
            mock_request.return_value = {"ok": True}
            
            client = SlackClient(mock_credentials)
            
            # Test with complex markdown content
            complex_markdown = """
            Hello @user1, @user2, and @user3!
            
            Please check the #engineering and #design channels.
            
            Important links:
            - [Documentation](https://docs.example.com)
            - [GitHub](https://github.com/example/repo)
            - [Slack](https://example.slack.com)
            
            Code examples:
            `console.log("Hello World")`
            
            **Bold text** and _italic text_ and ~strikethrough~.
            """
            
            start_time = time.perf_counter()
            formatted_text = client.format_markdown(complex_markdown)
            formatting_time = time.perf_counter() - start_time
            
            # Markdown formatting should be very fast
            assert formatting_time < 0.1  # 100ms
            assert "<@user1>" in formatted_text
            assert "<#engineering>" in formatted_text
            assert "<https://docs.example.com|Documentation>" in formatted_text
            
            print(f"Slack markdown formatting time: {formatting_time:.6f}s")


class TestHTTPClientPerformance(PerformanceBenchmarks):
    """Performance tests for HTTP client."""
    
    @pytest.mark.asyncio
    async def test_http_request_performance(self):
        """Test HTTP client request performance."""
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": "test"}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_response
            
            client = HTTPClient({
                "type": "bearer",
                "token": "test_token"
            })
            
            @self.measure_execution_time
            async def make_request():
                return await client.request(
                    "GET",
                    "https://api.example.com/performance-test"
                )
            
            result, execution_time = await make_request()
            
            # Performance requirement: < 5 seconds
            assert execution_time < 5.0
            assert result["success"] == True
            
            print(f"HTTP request execution time: {execution_time:.4f}s")
    
    @pytest.mark.asyncio
    async def test_http_authentication_overhead(self):
        """Test HTTP authentication processing overhead."""
        
        auth_configs = [
            {"type": "bearer", "token": "test_token"},
            {"type": "api_key", "key_name": "X-API-Key", "key_value": "test_key", "location": "header"},
            {"type": "basic_auth", "username": "user", "password": "pass"}
        ]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = mock_response
            
            auth_times = []
            
            for auth_config in auth_configs:
                client = HTTPClient(auth_config)
                
                start_time = time.perf_counter()
                await client.request("GET", "https://api.example.com/test")
                execution_time = time.perf_counter() - start_time
                
                auth_times.append(execution_time)
            
            stats = self.calculate_statistics(auth_times)
            
            # Authentication overhead should be minimal
            assert stats["mean"] < 5.0
            assert stats["max"] < 10.0
            
            print(f"HTTP auth overhead - Mean: {stats['mean']:.4f}s, Max: {stats['max']:.4f}s")


class TestToolNodePerformance(PerformanceBenchmarks):
    """Performance tests for tool node execution."""
    
    @pytest.mark.asyncio
    async def test_tool_node_execution_performance(self, mock_credentials):
        """Test tool node execution performance."""
        
        # Mock credential service
        mock_credential_service = AsyncMock(spec=CredentialService)
        mock_credential_service.get_credential.return_value = mock_credentials
        
        # Mock API responses
        with patch('workflow_engine.services.credential_service.CredentialService', return_value=mock_credential_service):
            with patch.object(GoogleCalendarClient, '_make_request') as mock_calendar:
                mock_calendar.return_value = {"id": "test_event"}
                
                # Create mock execution context
                context = MagicMock()
                context.get_parameter.side_effect = lambda key, default=None: {
                    "provider": "google_calendar",
                    "action": "create_event",
                    "user_id": "test_user"
                }.get(key, default)
                
                context.input_data = {
                    "summary": "Test Event",
                    "start": {"dateTime": "2025-01-20T10:00:00Z"},
                    "end": {"dateTime": "2025-01-20T11:00:00Z"}
                }
                
                executor = ToolNodeExecutor()
                
                @self.measure_execution_time
                async def execute_tool():
                    return executor._execute_calendar_tool(context, [], 0.0)
                
                result, execution_time = await execute_tool()
                
                # Tool node execution should be fast
                assert execution_time < 5.0
                assert result.status.value == "SUCCESS"
                
                print(f"Tool node execution time: {execution_time:.4f}s")
    
    @pytest.mark.asyncio
    async def test_tool_node_concurrent_execution(self, mock_credentials):
        """Test concurrent tool node execution performance."""
        
        mock_credential_service = AsyncMock(spec=CredentialService)
        mock_credential_service.get_credential.return_value = mock_credentials
        
        with patch('workflow_engine.services.credential_service.CredentialService', return_value=mock_credential_service):
            with patch.object(GoogleCalendarClient, '_make_request') as mock_calendar:
                mock_calendar.return_value = {"id": "test_event"}
                
                executor = ToolNodeExecutor()
                execution_times = []
                
                async def execute_single_tool(tool_id: int):
                    context = MagicMock()
                    context.get_parameter.side_effect = lambda key, default=None: {
                        "provider": "google_calendar",
                        "action": "create_event", 
                        "user_id": f"user_{tool_id}"
                    }.get(key, default)
                    
                    context.input_data = {
                        "summary": f"Concurrent Event {tool_id}",
                        "start": {"dateTime": "2025-01-20T10:00:00Z"},
                        "end": {"dateTime": "2025-01-20T11:00:00Z"}
                    }
                    
                    start_time = time.perf_counter()
                    result = executor._execute_calendar_tool(context, [], 0.0)
                    execution_time = time.perf_counter() - start_time
                    
                    return result, execution_time
                
                # Execute 10 concurrent tool executions
                start_time = time.perf_counter()
                tasks = [execute_single_tool(i) for i in range(10)]
                results = await asyncio.gather(*tasks)
                total_time = time.perf_counter() - start_time
                
                # Extract execution times
                individual_times = [result[1] for result in results]
                stats = self.calculate_statistics(individual_times)
                throughput = 10 / total_time
                
                # Performance requirements for concurrent execution
                assert stats["mean"] < 5.0   # Average execution time
                assert stats["p95"] < 10.0   # 95th percentile
                assert throughput >= 1.0     # At least 1 tool execution per second
                
                print(f"Tool node concurrent throughput: {throughput:.2f} executions/s")
                print(f"Mean execution time: {stats['mean']:.4f}s")
                print(f"P95 execution time: {stats['p95']:.4f}s")


class TestOAuth2PerformanceCache:
    """Performance tests for OAuth2 operations."""
    
    @pytest.mark.asyncio
    async def test_oauth2_url_generation_performance(self):
        """Test OAuth2 authorization URL generation performance."""
        
        mock_settings = MagicMock()
        mock_settings.get_oauth2_config.return_value = {
            "google_calendar": {
                "client_id": "test_client_id",
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "scopes": ["calendar"]
            }
        }
        
        mock_redis = AsyncMock()
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis):
                
                handler = OAuth2Handler()
                
                # Measure URL generation performance
                start_time = time.perf_counter()
                
                for i in range(100):
                    auth_url = await handler.generate_auth_url(
                        provider="google_calendar",
                        user_id=f"user_{i}",
                        scopes=["calendar"]
                    )
                    assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
                
                total_time = time.perf_counter() - start_time
                avg_time = total_time / 100
                
                # URL generation should be very fast
                assert avg_time < 0.1  # 100ms per URL
                assert total_time < 5.0  # 5s for 100 URLs
                
                print(f"OAuth2 URL generation: {avg_time:.6f}s per URL")
                print(f"OAuth2 URL generation throughput: {100/total_time:.2f} URLs/s")


class TestSystemIntegrationPerformance(PerformanceBenchmarks):
    """Performance tests for complete system integration."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_performance(self, mock_credentials):
        """Test end-to-end workflow performance from OAuth to API execution."""
        
        # Mock all components
        mock_credential_service = AsyncMock(spec=CredentialService)
        mock_credential_service.get_credential.return_value = mock_credentials
        
        mock_settings = MagicMock()
        mock_redis = AsyncMock()
        
        with patch('workflow_engine.services.credential_service.CredentialService', return_value=mock_credential_service):
            with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
                with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis):
                    with patch.object(GoogleCalendarClient, '_make_request') as mock_api:
                        mock_api.return_value = {"id": "test_event", "status": "confirmed"}
                        
                        # Simulate complete workflow
                        start_time = time.perf_counter()
                        
                        # 1. Tool node execution
                        context = MagicMock()
                        context.get_parameter.side_effect = lambda key, default=None: {
                            "provider": "google_calendar",
                            "action": "create_event",
                            "user_id": "workflow_user"
                        }.get(key, default)
                        
                        context.input_data = {
                            "summary": "Workflow Test Event",
                            "start": {"dateTime": "2025-01-20T10:00:00Z"},
                            "end": {"dateTime": "2025-01-20T11:00:00Z"}
                        }
                        
                        executor = ToolNodeExecutor()
                        result = executor._execute_calendar_tool(context, [], 0.0)
                        
                        total_time = time.perf_counter() - start_time
                        
                        # End-to-end workflow should complete quickly
                        assert total_time < 10.0  # 10 seconds for complete workflow
                        assert result.status.value == "SUCCESS"
                        
                        print(f"End-to-end workflow execution time: {total_time:.4f}s")
    
    @pytest.mark.asyncio
    async def test_system_scalability(self, mock_credentials):
        """Test system scalability with increasing load."""
        
        mock_credential_service = AsyncMock(spec=CredentialService)
        mock_credential_service.get_credential.return_value = mock_credentials
        
        load_levels = [1, 5, 10, 20, 50]  # Number of concurrent operations
        scalability_results = {}
        
        with patch('workflow_engine.services.credential_service.CredentialService', return_value=mock_credential_service):
            with patch.object(GoogleCalendarClient, '_make_request') as mock_api:
                mock_api.return_value = {"id": "test_event"}
                
                for load_level in load_levels:
                    async def single_operation(op_id: int):
                        context = MagicMock()
                        context.get_parameter.side_effect = lambda key, default=None: {
                            "provider": "google_calendar",
                            "action": "create_event",
                            "user_id": f"load_user_{op_id}"
                        }.get(key, default)
                        
                        context.input_data = {
                            "summary": f"Load Test Event {op_id}",
                            "start": {"dateTime": "2025-01-20T10:00:00Z"},
                            "end": {"dateTime": "2025-01-20T11:00:00Z"}
                        }
                        
                        executor = ToolNodeExecutor()
                        start_time = time.perf_counter()
                        result = executor._execute_calendar_tool(context, [], 0.0)
                        execution_time = time.perf_counter() - start_time
                        
                        return result, execution_time
                    
                    # Execute concurrent operations
                    start_time = time.perf_counter()
                    tasks = [single_operation(i) for i in range(load_level)]
                    results = await asyncio.gather(*tasks)
                    total_time = time.perf_counter() - start_time
                    
                    # Calculate metrics
                    execution_times = [result[1] for result in results]
                    stats = self.calculate_statistics(execution_times)
                    throughput = load_level / total_time
                    
                    scalability_results[load_level] = {
                        "throughput": throughput,
                        "mean_time": stats["mean"],
                        "p95_time": stats["p95"]
                    }
                    
                    # System should maintain reasonable performance under load
                    assert stats["mean"] < 10.0  # Mean response time under load
                    assert throughput >= 0.5     # Minimum throughput
                    
                    print(f"Load level {load_level}: {throughput:.2f} ops/s, "
                          f"mean: {stats['mean']:.4f}s, p95: {stats['p95']:.4f}s")
                
                # Verify scalability characteristics
                # Throughput should generally increase with load (up to a point)
                throughputs = [scalability_results[level]["throughput"] for level in load_levels]
                
                # At minimum, system should handle increased load without catastrophic degradation
                assert max(throughputs) >= 2 * min(throughputs)  # Some scalability improvement
                
                print("Scalability test completed successfully") 