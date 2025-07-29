"""
Enhanced gRPC Client with AWS ECS Service Discovery support
"""

import asyncio
import logging
import os
import random
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import grpc
from app.core.config import settings

# Import proto modules
try:
    from proto import workflow_agent_pb2, workflow_agent_pb2_grpc

    GRPC_AVAILABLE = True
except ImportError:
    workflow_agent_pb2 = None
    workflow_agent_pb2_grpc = None
    GRPC_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """服务端点定义"""

    host: str
    port: int
    weight: int = 1
    health_score: float = 1.0
    last_health_check: Optional[float] = None


class CircuitBreakerState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service is back


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.

    Features:
    - Configurable failure threshold and timeout
    - Exponential backoff for recovery attempts
    - Health monitoring and statistics
    """

    def __init__(
        self, failure_threshold: int = 5, recovery_timeout: float = 60.0, success_threshold: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.next_attempt_time = 0

    def can_execute(self) -> bool:
        """Check if operation can be executed based on circuit breaker state."""
        current_time = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if current_time >= self.next_attempt_time:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("🔄 Circuit breaker entering HALF_OPEN state")
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True

        return False

    def record_success(self):
        """Record successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("✅ Circuit breaker recovered, state: CLOSED")
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed operation."""
        current_time = time.time()
        self.failure_count += 1
        self.last_failure_time = current_time

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = current_time + self.recovery_timeout
            logger.warning("⚠️ Circuit breaker failed in HALF_OPEN, state: OPEN")
        elif self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.next_attempt_time = current_time + self.recovery_timeout
                logger.error(f"🔴 Circuit breaker OPEN - {self.failure_count} failures")

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "next_attempt_time": self.next_attempt_time
            if self.state == CircuitBreakerState.OPEN
            else None,
            "can_execute": self.can_execute(),
        }


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff."""
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

        if self.jitter:
            # Add jitter to prevent thundering herd
            delay *= 0.5 + random.random() * 0.5

        return delay


class HealthMonitor:
    """Health monitoring for gRPC endpoints."""

    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.endpoint_health: Dict[str, Dict[str, Any]] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False

    def start_monitoring(self, endpoints: List[ServiceEndpoint]):
        """Start health monitoring for endpoints."""
        if not self.running:
            self.running = True
            self.monitoring_task = asyncio.create_task(self._monitor_endpoints(endpoints))
            logger.info("🏥 Started health monitoring")

    def stop_monitoring(self):
        """Stop health monitoring."""
        self.running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
            logger.info("🔐 Stopped health monitoring")

    async def _monitor_endpoints(self, endpoints: List[ServiceEndpoint]):
        """Monitor endpoint health in background."""
        while self.running:
            try:
                for endpoint in endpoints:
                    await self._check_endpoint_health(endpoint)
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Health monitoring error: {e}")
                await asyncio.sleep(self.check_interval)

    async def _check_endpoint_health(self, endpoint: ServiceEndpoint):
        """Check health of a specific endpoint."""
        endpoint_key = f"{endpoint.host}:{endpoint.port}"
        start_time = time.time()

        try:
            # Simple TCP connection test
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(endpoint.host, endpoint.port), timeout=5.0
            )
            writer.close()
            await writer.wait_closed()

            response_time = time.time() - start_time
            endpoint.health_score = min(1.0, max(0.1, 1.0 - (response_time / 5.0)))
            endpoint.last_health_check = time.time()

            self.endpoint_health[endpoint_key] = {
                "healthy": True,
                "response_time": response_time,
                "last_check": time.time(),
                "health_score": endpoint.health_score,
            }

            logger.debug(f"✅ Health check passed for {endpoint_key} ({response_time:.2f}s)")

        except Exception as e:
            endpoint.health_score = max(0.0, endpoint.health_score - 0.2)
            endpoint.last_health_check = time.time()

            self.endpoint_health[endpoint_key] = {
                "healthy": False,
                "error": str(e),
                "last_check": time.time(),
                "health_score": endpoint.health_score,
            }

            logger.warning(f"⚠️ Health check failed for {endpoint_key}: {e}")

    def get_healthy_endpoints(self, endpoints: List[ServiceEndpoint]) -> List[ServiceEndpoint]:
        """Get list of healthy endpoints sorted by health score."""
        healthy = []

        for endpoint in endpoints:
            endpoint_key = f"{endpoint.host}:{endpoint.port}"
            health_info = self.endpoint_health.get(endpoint_key)

            if health_info and health_info.get("healthy", False):
                healthy.append(endpoint)

        # Sort by health score (descending)
        healthy.sort(key=lambda e: e.health_score, reverse=True)
        return healthy

    def get_health_stats(self) -> Dict[str, Any]:
        """Get health monitoring statistics."""
        return {
            "monitored_endpoints": len(self.endpoint_health),
            "healthy_endpoints": sum(
                1 for info in self.endpoint_health.values() if info.get("healthy", False)
            ),
            "monitoring_active": self.running,
            "endpoint_details": self.endpoint_health,
        }


class ServiceDiscoveryStrategy:
    """服务发现策略基类"""

    async def discover_services(self) -> List[ServiceEndpoint]:
        """发现服务实例"""
        raise NotImplementedError


class EnvironmentVariableStrategy(ServiceDiscoveryStrategy):
    """环境变量策略（开发环境）"""

    async def discover_services(self) -> List[ServiceEndpoint]:
        host = os.getenv("WORKFLOW_SERVICE_HOST", settings.WORKFLOW_SERVICE_HOST)
        port = int(os.getenv("WORKFLOW_SERVICE_PORT", settings.WORKFLOW_SERVICE_PORT))

        if host and host != "localhost":
            return [ServiceEndpoint(host=host, port=port)]
        return []


class CloudMapDNSStrategy(ServiceDiscoveryStrategy):
    """AWS Cloud Map DNS 策略"""

    def __init__(self, service_name: str = "workflow-agent.workflow.local"):
        self.service_name = service_name

    async def discover_services(self) -> List[ServiceEndpoint]:
        """通过 DNS 解析发现服务"""
        try:
            # 使用 asyncio 包装同步的 DNS 查询
            addresses = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: socket.getaddrinfo(
                    self.service_name, 50051, socket.AF_INET, socket.SOCK_STREAM
                ),
            )

            endpoints = []
            seen_ips = set()

            for addr in addresses:
                ip = addr[4][0]
                if ip not in seen_ips:
                    endpoints.append(ServiceEndpoint(host=ip, port=50051))
                    seen_ips.add(ip)

            logger.info(f"Discovered {len(endpoints)} service instances via DNS")
            return endpoints

        except (socket.gaierror, OSError) as e:
            logger.warning(f"DNS discovery failed for {self.service_name}: {e}")
            return []


class LoadBalancerStrategy(ServiceDiscoveryStrategy):
    """负载均衡器策略"""

    def __init__(self, lb_endpoint: str):
        self.lb_endpoint = lb_endpoint

    async def discover_services(self) -> List[ServiceEndpoint]:
        """返回负载均衡器端点"""
        if self.lb_endpoint:
            # 解析主机和端口
            if ":" in self.lb_endpoint:
                host, port_str = self.lb_endpoint.rsplit(":", 1)
                port = int(port_str)
            else:
                host = self.lb_endpoint
                port = 50051

            return [ServiceEndpoint(host=host, port=port)]
        return []


class ServiceDiscoveryClient:
    """服务发现客户端"""

    def __init__(self):
        self.strategies = self._init_strategies()

    def _init_strategies(self) -> List[ServiceDiscoveryStrategy]:
        """初始化服务发现策略"""
        strategies = []

        # 1. 环境变量策略（优先级最高）
        strategies.append(EnvironmentVariableStrategy())

        # 2. 负载均衡器策略
        lb_endpoint = os.getenv("WORKFLOW_SERVICE_LB_ENDPOINT")
        if lb_endpoint:
            strategies.append(LoadBalancerStrategy(lb_endpoint))

        # 3. Cloud Map DNS 策略
        service_name = os.getenv("WORKFLOW_SERVICE_DNS_NAME", "workflow-agent.workflow.local")
        strategies.append(CloudMapDNSStrategy(service_name))

        return strategies

    async def discover_workflow_service(self) -> List[ServiceEndpoint]:
        """发现 workflow 服务实例"""
        for strategy in self.strategies:
            try:
                endpoints = await strategy.discover_services()
                if endpoints:
                    logger.info(f"Service discovery successful using {strategy.__class__.__name__}")
                    return endpoints
            except Exception as e:
                logger.warning(f"Strategy {strategy.__class__.__name__} failed: {e}")
                continue

        logger.error("All service discovery strategies failed")
        return []


class EnhancedWorkflowGRPCClient:
    """
    Enhanced gRPC client with advanced fault tolerance features.

    Features:
    - Service discovery with multiple strategies
    - Circuit breaker pattern for fault tolerance
    - Retry logic with exponential backoff
    - Health monitoring and automatic failover
    - Connection pooling and load balancing
    """

    def __init__(self):
        self.discovery_client = ServiceDiscoveryClient()
        self.channel = None
        self.stub = None
        self.connected = False
        self.current_endpoints: List[ServiceEndpoint] = []
        self.current_endpoint_index = 0
        self.connection_timeout = 10.0

        # Enhanced features
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=60.0, success_threshold=3
        )
        self.retry_config = RetryConfig(
            max_retries=3, base_delay=1.0, max_delay=30.0, exponential_base=2.0, jitter=True
        )
        self.health_monitor = HealthMonitor(check_interval=30.0)

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "circuit_breaker_trips": 0,
            "endpoint_switches": 0,
            "last_request_time": None,
        }

    async def connect(self) -> bool:
        """连接到 workflow 服务"""
        if not GRPC_AVAILABLE:
            logger.error("gRPC modules not available")
            return False

        # 发现服务端点
        endpoints = await self.discovery_client.discover_workflow_service()
        if not endpoints:
            logger.error("No service endpoints discovered")
            return False

        self.current_endpoints = endpoints

        # Start health monitoring for discovered endpoints
        self.health_monitor.start_monitoring(endpoints)

        # Get healthy endpoints from health monitor (if available)
        healthy_endpoints = self.health_monitor.get_healthy_endpoints(endpoints)
        connection_candidates = healthy_endpoints if healthy_endpoints else endpoints

        # 尝试连接到可用的端点
        for i, endpoint in enumerate(connection_candidates):
            original_index = endpoints.index(endpoint) if endpoint in endpoints else i
            if await self._try_connect_to_endpoint(endpoint):
                self.current_endpoint_index = original_index
                logger.info(
                    f"🎯 Connected to endpoint {endpoint.host}:{endpoint.port} (health score: {endpoint.health_score:.2f})"
                )
                return True

        logger.error("Failed to connect to any discovered endpoints")
        return False

    async def _try_connect_to_endpoint(self, endpoint: ServiceEndpoint) -> bool:
        """尝试连接到特定端点"""
        try:
            logger.info(f"Attempting to connect to {endpoint.host}:{endpoint.port}")

            # 创建 gRPC 通道
            channel_options = [
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
                ("grpc.keepalive_permit_without_calls", True),
                ("grpc.http2.max_pings_without_data", 0),
                ("grpc.http2.min_time_between_pings_ms", 10000),
                ("grpc.http2.min_ping_interval_without_data_ms", 300000),
            ]

            self.channel = grpc.aio.insecure_channel(
                f"{endpoint.host}:{endpoint.port}", options=channel_options
            )

            # 测试连接
            await asyncio.wait_for(self.channel.channel_ready(), timeout=self.connection_timeout)

            # 创建 stub
            self.stub = workflow_agent_pb2_grpc.WorkflowAgentStub(self.channel)

            self.connected = True
            logger.info(f"Successfully connected to {endpoint.host}:{endpoint.port}")
            return True

        except Exception as e:
            logger.warning(f"Failed to connect to {endpoint.host}:{endpoint.port}: {e}")
            if self.channel:
                await self.channel.close()
                self.channel = None
            return False

    async def disconnect(self):
        """断开连接"""
        # Stop health monitoring
        self.health_monitor.stop_monitoring()

        if self.channel:
            await self.channel.close()
            self.channel = None
            self.stub = None
            self.connected = False
            logger.info("🔐 Disconnected from gRPC service")

    async def _reconnect_to_next_endpoint(self) -> bool:
        """重连到下一个可用端点（优先选择健康的端点）"""
        if not self.current_endpoints:
            return await self.connect()

        self.stats["endpoint_switches"] += 1

        # Get healthy endpoints first
        healthy_endpoints = self.health_monitor.get_healthy_endpoints(self.current_endpoints)

        if healthy_endpoints:
            # Try healthy endpoints first
            for endpoint in healthy_endpoints:
                original_index = self.current_endpoints.index(endpoint)
                if original_index != self.current_endpoint_index:  # Skip current failed endpoint
                    if await self._try_connect_to_endpoint(endpoint):
                        self.current_endpoint_index = original_index
                        logger.info(
                            f"🔄 Switched to healthy endpoint {endpoint.host}:{endpoint.port}"
                        )
                        return True

        # Fallback: try all other endpoints sequentially
        for i in range(len(self.current_endpoints)):
            next_index = (self.current_endpoint_index + i + 1) % len(self.current_endpoints)
            endpoint = self.current_endpoints[next_index]

            if await self._try_connect_to_endpoint(endpoint):
                self.current_endpoint_index = next_index
                logger.info(f"🔄 Switched to endpoint {endpoint.host}:{endpoint.port}")
                return True

        # 如果所有端点都失败，重新发现服务
        logger.warning("⚠️ All current endpoints failed, rediscovering services")
        return await self.connect()

    async def ensure_connected(self) -> bool:
        """确保连接可用"""
        if not self.connected:
            return await self.connect()

        # 检查连接状态
        try:
            if self.channel:
                state = self.channel.get_state()
                if state in [
                    grpc.ChannelConnectivity.SHUTDOWN,
                    grpc.ChannelConnectivity.TRANSIENT_FAILURE,
                ]:
                    self.connected = False
                    return await self._reconnect_to_next_endpoint()
        except Exception:
            self.connected = False
            return await self._reconnect_to_next_endpoint()

        return True

    async def process_conversation(self, request: Any, timeout: float = 60.0) -> Optional[Any]:
        """
        Process conversation request with advanced fault tolerance.

        Features:
        - Circuit breaker protection
        - Exponential backoff retry
        - Automatic failover to healthy endpoints
        - Request/response statistics tracking
        """
        self.stats["total_requests"] += 1
        self.stats["last_request_time"] = time.time()

        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            self.stats["circuit_breaker_trips"] += 1
            raise Exception(f"Circuit breaker is {self.circuit_breaker.state.value}")

        if not await self.ensure_connected():
            self.circuit_breaker.record_failure()
            self.stats["failed_requests"] += 1
            raise Exception("Unable to establish connection to workflow service")

        for attempt in range(self.retry_config.max_retries):
            try:
                # Execute gRPC call with timeout
                response_count = 0
                async for response in self.stub.ProcessConversation(request, timeout=timeout):
                    response_count += 1
                    yield response

                # Success - update statistics and circuit breaker
                if response_count > 0:
                    self.circuit_breaker.record_success()
                    self.stats["successful_requests"] += 1
                    logger.debug(f"✅ gRPC request successful ({response_count} responses)")
                return

            except grpc.RpcError as e:
                error_code = e.code()
                is_retryable = error_code in [
                    grpc.StatusCode.UNAVAILABLE,
                    grpc.StatusCode.DEADLINE_EXCEEDED,
                    grpc.StatusCode.CANCELLED,
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                ]

                logger.warning(
                    f"gRPC call failed (attempt {attempt + 1}/{self.retry_config.max_retries}): "
                    f"{error_code.name} - {e.details()}"
                )

                if is_retryable and attempt < self.retry_config.max_retries - 1:
                    # Record failure and calculate retry delay
                    self.circuit_breaker.record_failure()
                    delay = self.retry_config.get_delay(attempt)

                    logger.info(f"⏳ Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)

                    # Try to reconnect to next healthy endpoint
                    self.connected = False
                    if await self._reconnect_to_next_endpoint():
                        continue

                # Not retryable or out of retries
                self.circuit_breaker.record_failure()
                self.stats["failed_requests"] += 1
                raise

            except Exception as e:
                logger.error(f"Unexpected error during gRPC call: {e}")
                self.circuit_breaker.record_failure()
                self.stats["failed_requests"] += 1

                if attempt < self.retry_config.max_retries - 1:
                    delay = self.retry_config.get_delay(attempt)
                    await asyncio.sleep(delay)

                    self.connected = False
                    if await self._reconnect_to_next_endpoint():
                        continue

                raise

        self.stats["failed_requests"] += 1
        raise Exception(
            f"Failed to complete request after {self.retry_config.max_retries} attempts"
        )

    async def start_health_monitoring(self):
        """Start health monitoring for discovered endpoints."""
        if self.current_endpoints:
            self.health_monitor.start_monitoring(self.current_endpoints)

    async def stop_health_monitoring(self):
        """Stop health monitoring."""
        self.health_monitor.stop_monitoring()

    def get_client_stats(self) -> Dict[str, Any]:
        """Get comprehensive client statistics."""
        success_rate = 0.0
        if self.stats["total_requests"] > 0:
            success_rate = (self.stats["successful_requests"] / self.stats["total_requests"]) * 100

        return {
            "client_stats": self.stats,
            "success_rate_percent": round(success_rate, 2),
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "health_monitor": self.health_monitor.get_health_stats(),
            "current_endpoint": f"{self.current_endpoints[self.current_endpoint_index].host}:{self.current_endpoints[self.current_endpoint_index].port}"
            if self.current_endpoints
            else None,
            "total_endpoints": len(self.current_endpoints),
            "connected": self.connected,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            health_status = {
                "healthy": False,
                "connection_status": self.connected,
                "circuit_breaker_state": self.circuit_breaker.state.value,
                "can_execute": self.circuit_breaker.can_execute(),
            }

            # Test basic connectivity
            if await self.ensure_connected():
                health_status["healthy"] = True
                health_status["endpoint"] = (
                    f"{self.current_endpoints[self.current_endpoint_index].host}:{self.current_endpoints[self.current_endpoint_index].port}"
                    if self.current_endpoints
                    else None
                )

            # Add monitoring stats
            health_status.update(self.health_monitor.get_health_stats())

            return health_status

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "connection_status": self.connected,
                "circuit_breaker_state": self.circuit_breaker.state.value,
            }


class WorkflowGRPCClientManager:
    """gRPC 客户端管理器，提供单例和连接池"""

    _instance = None
    _client = None

    @classmethod
    async def get_client(cls) -> EnhancedWorkflowGRPCClient:
        """获取客户端实例"""
        if cls._instance is None:
            cls._instance = cls()
            cls._client = EnhancedWorkflowGRPCClient()
            await cls._client.connect()

        return cls._client

    @classmethod
    async def close(cls):
        """关闭客户端连接"""
        if cls._client:
            await cls._client.disconnect()
            cls._client = None
            cls._instance = None


# 便捷函数
async def get_workflow_client() -> EnhancedWorkflowGRPCClient:
    """获取 workflow gRPC 客户端"""
    return await WorkflowGRPCClientManager.get_client()


async def close_workflow_client():
    """关闭 workflow gRPC 客户端"""
    await WorkflowGRPCClientManager.close()


# 使用示例
async def example_usage():
    """使用示例"""
    try:
        # 获取客户端
        client = await get_workflow_client()

        # 创建请求
        request = workflow_agent_pb2.ConversationRequest(
            session_id="test-session", 
            user_id="test-user",
            user_message="Hello, workflow agent!"
        )

        # 处理请求
        async for response in client.process_conversation(request):
            print(f"Received response: {response}")

    except Exception as e:
        logger.error(f"Error in example usage: {e}")
    finally:
        await close_workflow_client()


if __name__ == "__main__":
    asyncio.run(example_usage())
