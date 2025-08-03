#!/usr/bin/env python3
"""
展示更易读的日志格式
"""

import json

# 模拟的日志条目
log_examples = [
    {
        "@timestamp": "2025-01-31T10:30:45.123Z",
        "@level": "INFO",
        "@message": "POST /api/v1/sessions - 201",
        "level": "INFO",
        "timestamp": "2025-01-31T10:30:45.123Z",
        "file": "main.py:131",
        "service": "api-gateway",
        "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "request": {
            "method": "POST",
            "path": "/api/v1/sessions",
            "duration": 0.245
        },
        "response": {
            "status": 201
        }
    },
    {
        "@timestamp": "2025-01-31T10:30:45.368Z",
        "@level": "INFO",
        "@message": "Processing workflow generation request",
        "level": "INFO", 
        "timestamp": "2025-01-31T10:30:45.368Z",
        "file": "fastapi_server.py:156",
        "service": "workflow-agent",
        "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "workflow_stage": "CLARIFICATION"
    },
    {
        "@timestamp": "2025-01-31T10:30:47.892Z",
        "@level": "ERROR",
        "@message": "Failed to execute workflow node",
        "level": "ERROR",
        "timestamp": "2025-01-31T10:30:47.892Z", 
        "file": "execution_engine.py:234",
        "service": "workflow-engine",
        "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "error": {
            "type": "NodeExecutionError",
            "message": "Timeout waiting for AI response"
        }
    }
]

print("📋 增强后的日志格式示例\n")
print("每条日志都包含: Level | Timestamp | File:LineNo | TrackingID\n")
print("="*100)

for log in log_examples:
    # 构建易读的日志输出
    level = log['level'].ljust(7)
    timestamp = log['timestamp']
    file_info = log['file'].ljust(25)
    service = log['service'].ljust(15)
    message = log['@message']
    tracking_id = log['tracking_id']
    
    # 基础信息行
    print(f"[{level}] {timestamp} | {file_info} | {service} | {tracking_id}")
    print(f"         {message}")
    
    # 额外信息
    if 'request' in log:
        print(f"         Request: {log['request']['method']} {log['request']['path']} ({log['request']['duration']}s)")
    if 'response' in log:
        print(f"         Response: {log['response']['status']}")
    if 'error' in log:
        print(f"         Error: {log['error']['type']} - {log['error']['message']}")
    if 'workflow_stage' in log:
        print(f"         Stage: {log['workflow_stage']}")
    
    print("-"*100)

print("\n📊 JSON 格式（用于 CloudWatch）:")
print("="*100)
print(json.dumps(log_examples[0], indent=2, ensure_ascii=False))

print("\n🔍 CloudWatch Logs Insights 查询示例:")
print("="*100)
print("""
# 查找所有 ERROR 级别的日志
fields timestamp, level, file, service, @message
| filter level = "ERROR"
| sort timestamp desc

# 追踪特定请求的完整流程
fields timestamp, level, file, service, @message
| filter tracking_id = "4bf92f3577b34da6a3ce929d0e0e4736"
| sort timestamp asc

# 查找慢请求（超过1秒）
fields timestamp, file, request.path, request.duration
| filter request.duration > 1.0
| sort request.duration desc

# 按服务和级别统计日志
stats count() by service, level
""")