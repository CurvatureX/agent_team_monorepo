"""
Enhanced gRPC Client with AWS ECS Service Discovery support
"""

import os
import asyncio
import grpc
import socket
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from app.config import settings

# Import proto modules
try:
    from proto import workflow_agent_pb2
    from proto import workflow_agent_pb2_grpc
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
                    self.service_name, 
                    50051, 
                    socket.AF_INET,
                    socket.SOCK_STREAM
                )
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
        service_name = os.getenv(
            "WORKFLOW_SERVICE_DNS_NAME", 
            "workflow-agent.workflow.local"
        )
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
    """增强的 gRPC 客户端，支持服务发现和故障转移"""
    
    def __init__(self):
        self.discovery_client = ServiceDiscoveryClient()
        self.channel = None
        self.stub = None
        self.connected = False
        self.current_endpoints: List[ServiceEndpoint] = []
        self.current_endpoint_index = 0
        self.connection_timeout = 10.0
        self.max_retries = 3
    
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
        
        # 尝试连接到可用的端点
        for i, endpoint in enumerate(endpoints):
            if await self._try_connect_to_endpoint(endpoint):
                self.current_endpoint_index = i
                return True
        
        logger.error("Failed to connect to any discovered endpoints")
        return False
    
    async def _try_connect_to_endpoint(self, endpoint: ServiceEndpoint) -> bool:
        """尝试连接到特定端点"""
        try:
            logger.info(f"Attempting to connect to {endpoint.host}:{endpoint.port}")
            
            # 创建 gRPC 通道
            channel_options = [
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 10000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 300000),
            ]
            
            self.channel = grpc.aio.insecure_channel(
                f"{endpoint.host}:{endpoint.port}",
                options=channel_options
            )
            
            # 测试连接
            await asyncio.wait_for(
                self.channel.channel_ready(), 
                timeout=self.connection_timeout
            )
            
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
        if self.channel:
            await self.channel.close()
            self.channel = None
            self.stub = None
            self.connected = False
            logger.info("Disconnected from gRPC service")
    
    async def _reconnect_to_next_endpoint(self) -> bool:
        """重连到下一个可用端点"""
        if not self.current_endpoints:
            return await self.connect()
        
        # 尝试连接到下一个端点
        for i in range(len(self.current_endpoints)):
            next_index = (self.current_endpoint_index + i + 1) % len(self.current_endpoints)
            endpoint = self.current_endpoints[next_index]
            
            if await self._try_connect_to_endpoint(endpoint):
                self.current_endpoint_index = next_index
                return True
        
        # 如果所有端点都失败，重新发现服务
        logger.warning("All current endpoints failed, rediscovering services")
        return await self.connect()
    
    async def ensure_connected(self) -> bool:
        """确保连接可用"""
        if not self.connected:
            return await self.connect()
        
        # 检查连接状态
        try:
            if self.channel:
                state = self.channel.get_state()
                if state in [grpc.ChannelConnectivity.SHUTDOWN, grpc.ChannelConnectivity.TRANSIENT_FAILURE]:
                    self.connected = False
                    return await self._reconnect_to_next_endpoint()
        except Exception:
            self.connected = False
            return await self._reconnect_to_next_endpoint()
        
        return True
    
    async def process_conversation(
        self, 
        request: Any,
        timeout: float = 60.0
    ) -> Optional[Any]:
        """处理对话请求，包含自动重连和故障转移"""
        if not await self.ensure_connected():
            raise Exception("Unable to establish connection to workflow service")
        
        for attempt in range(self.max_retries):
            try:
                # 执行 gRPC 调用
                async for response in self.stub.ProcessConversation(
                    request, 
                    timeout=timeout
                ):
                    yield response
                return  # 成功完成
                
            except grpc.RpcError as e:
                logger.warning(f"gRPC call failed (attempt {attempt + 1}): {e}")
                
                if e.code() in [
                    grpc.StatusCode.UNAVAILABLE,
                    grpc.StatusCode.DEADLINE_EXCEEDED,
                    grpc.StatusCode.CANCELLED
                ]:
                    # 可重试的错误
                    self.connected = False
                    if attempt < self.max_retries - 1:
                        if await self._reconnect_to_next_endpoint():
                            continue
                    
                # 不可重试的错误或重试次数用完
                raise
            
            except Exception as e:
                logger.error(f"Unexpected error during gRPC call: {e}")
                self.connected = False
                if attempt < self.max_retries - 1:
                    if await self._reconnect_to_next_endpoint():
                        continue
                raise
        
        raise Exception(f"Failed to complete request after {self.max_retries} attempts")

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