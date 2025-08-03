#!/usr/bin/env python3
"""
独立测试日志格式，展示 trace_id 功能
"""

import json
import logging
from datetime import datetime

# 模拟 CloudWatchTracingFormatter 的核心功能
class SimplifiedCloudWatchFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        # 获取 tracking_id
        tracking_id = getattr(record, 'tracking_id', 'unknown')
        
        # 构建基础日志条目
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        log_entry = {
            "@timestamp": timestamp,
            "@level": record.levelname,
            "@message": record.getMessage(),
            "service": self.service_name,
            "tracking_id": tracking_id,  # 这就是 trace_id
            "source": {
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
        }
        
        # 处理额外字段
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info', 
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process', 'getMessage',
                          'message', 'tracking_id']:
                # 分组相关字段
                if key.startswith('request_'):
                    if 'request' not in log_entry:
                        log_entry['request'] = {}
                    log_entry['request'][key.replace('request_', '')] = value
                elif key.startswith('response_'):
                    if 'response' not in log_entry:
                        log_entry['response'] = {}
                    log_entry['response'][key.replace('response_', '')] = value
                elif key.startswith('user_'):
                    if 'user' not in log_entry:
                        log_entry['user'] = {}
                    log_entry['user'][key.replace('user_', '')] = value
                else:
                    log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))

# 测试三个服务的日志输出
print("🎯 展示各服务的日志格式（包含 trace_id）\n")

# 1. API Gateway
print("="*60)
print("1️⃣ API Gateway 日志示例")
print("="*60)

logger_api = logging.getLogger("api-gateway")
logger_api.setLevel(logging.INFO)
handler_api = logging.StreamHandler()
handler_api.setFormatter(SimplifiedCloudWatchFormatter("api-gateway"))
logger_api.addHandler(handler_api)

# 模拟一个 API 请求
logger_api.info("POST /api/v1/sessions - 201", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",  # 这是完整的 OpenTelemetry trace_id
    "request_method": "POST",
    "request_path": "/api/v1/sessions",
    "request_duration": 0.245,
    "request_size": 1024,
    "response_status": 201,
    "response_size": 2048,
    "user_id": "user_12345",
    "session_id": "session_67890"
})

# 2. Workflow Agent
print("\n" + "="*60)
print("2️⃣ Workflow Agent 日志示例")
print("="*60)

logger_wf = logging.getLogger("workflow-agent")
logger_wf.setLevel(logging.INFO)
handler_wf = logging.StreamHandler()
handler_wf.setFormatter(SimplifiedCloudWatchFormatter("workflow-agent"))
logger_wf.addHandler(handler_wf)

logger_wf.info("Processing workflow generation request", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",  # 同一个 trace_id
    "session_id": "session_67890",
    "workflow_stage": "CLARIFICATION",
    "ai_model": "gpt-4",
    "tokens_used": 1500
})

# 3. Workflow Engine
print("\n" + "="*60)
print("3️⃣ Workflow Engine 日志示例")
print("="*60)

logger_we = logging.getLogger("workflow-engine")
logger_we.setLevel(logging.INFO)
handler_we = logging.StreamHandler()
handler_we.setFormatter(SimplifiedCloudWatchFormatter("workflow-engine"))
logger_we.addHandler(handler_we)

logger_we.info("Executing workflow node", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",  # 同一个 trace_id
    "workflow_id": "workflow_abc123",
    "node_id": "node_trigger_001",
    "node_type": "TRIGGER",
    "execution_status": "SUCCESS"
})

# 错误日志示例
print("\n" + "="*60)
print("4️⃣ ERROR 级别日志示例")
print("="*60)

logger_api.error("Failed to process request", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4737",
    "error_type": "ValidationError",
    "error_code": "E001",
    "error_message": "Invalid input parameters",
    "request_path": "/api/v1/workflows"
})

print("\n" + "="*60)
print("📊 关键点说明")
print("="*60)
print("""
1. tracking_id 字段就是 OpenTelemetry 的 trace_id (32位十六进制)
2. 所有服务使用相同的 tracking_id 来关联整个请求链
3. 日志格式符合 CloudWatch Logs Insights 查询优化
4. 相关字段自动分组 (request.*, response.*, user.* 等)
5. ERROR 级别日志会自动在 OpenTelemetry Span 中创建事件

查询示例:
- 查找特定 tracking_id: filter tracking_id = "4bf92f3577b34da6a3ce929d0e0e4736"
- 查找用户的所有请求: filter user.id = "user_12345"
- 查找慢请求: filter request.duration > 1.0
""")