#!/usr/bin/env python3
"""
简单测试脚本，展示实际的日志输出格式
"""

import sys
import os
import json
import logging
from datetime import datetime

# 添加 shared 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/backend'))

try:
    from shared.telemetry.formatter import CloudWatchTracingFormatter
    print("✅ 成功导入 CloudWatchTracingFormatter")
except ImportError as e:
    print(f"❌ 无法导入 CloudWatchTracingFormatter: {e}")
    sys.exit(1)

# 创建 logger
logger = logging.getLogger("test_service")
logger.setLevel(logging.DEBUG)

# 创建 handler 使用 CloudWatchTracingFormatter
handler = logging.StreamHandler(sys.stdout)
formatter = CloudWatchTracingFormatter(service_name="test-service")
handler.setFormatter(formatter)
logger.addHandler(handler)

print("\n" + "="*60)
print("📋 测试日志输出格式")
print("="*60 + "\n")

# 测试不同级别的日志
print("1️⃣ INFO 级别日志:")
logger.info("这是一条测试信息", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "user_id": "user_12345",
    "session_id": "session_67890"
})

print("\n2️⃣ 带请求信息的日志:")
logger.info("处理 HTTP 请求", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4737",
    "request_method": "POST",
    "request_path": "/api/v1/sessions",
    "request_duration": 0.245,
    "response_status": 201,
    "response_size": 2048
})

print("\n3️⃣ ERROR 级别日志:")
try:
    1 / 0
except Exception as e:
    logger.error("发生错误", extra={
        "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4738",
        "error_type": "ZeroDivisionError",
        "error_message": str(e)
    }, exc_info=True)

print("\n4️⃣ 业务操作日志:")
logger.info("工作流执行完成", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4739",
    "workflow_id": "workflow_abc123",
    "workflow_type": "ai-assisted",
    "workflow_status": "completed",
    "operation_name": "execute_workflow",
    "operation_result": "success",
    "operation_duration": 1.325
})

print("\n" + "="*60)
print("📊 日志格式说明")
print("="*60)
print("""
每条日志都是 JSON 格式，包含以下字段：
- @timestamp: ISO 格式时间戳
- @level: 日志级别
- @message: 日志消息
- service: 服务名称
- tracking_id: 追踪 ID (OpenTelemetry trace_id)
- source: 源代码位置信息
- 其他业务字段按类型分组 (request, response, user, session, workflow 等)
""")