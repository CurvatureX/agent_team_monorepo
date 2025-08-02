#!/usr/bin/env python3
"""
测试增强的日志格式，展示 Level, Timestamp, File:LineNo
"""

import json
import logging
from datetime import datetime

# 模拟更新后的 CloudWatchTracingFormatter
class EnhancedCloudWatchFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        # 获取 tracking_id
        tracking_id = getattr(record, 'tracking_id', 'unknown')
        
        # 构建时间戳
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # 构建文件位置信息
        file_location = f"{record.filename}:{record.lineno}"
        
        log_entry = {
            "@timestamp": timestamp,
            "@level": record.levelname,
            "@message": record.getMessage(),
            "level": record.levelname,      # 便于查询
            "timestamp": timestamp,          # 便于查询
            "file": file_location,          # 文件:行号
            "service": self.service_name,
            "tracking_id": tracking_id,
            "source": {
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "filename": record.filename,
                "pathname": record.pathname
            }
        }
        
        # 处理额外字段
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info', 
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process', 'getMessage',
                          'message', 'tracking_id']:
                if key.startswith('request_'):
                    if 'request' not in log_entry:
                        log_entry['request'] = {}
                    log_entry['request'][key.replace('request_', '')] = value
                elif key.startswith('response_'):
                    if 'response' not in log_entry:
                        log_entry['response'] = {}
                    log_entry['response'][key.replace('response_', '')] = value
                else:
                    log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))

print("🎯 展示增强的日志格式（Level, Timestamp, File:LineNo）\n")

# 设置测试 logger
logger = logging.getLogger("test-service")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(EnhancedCloudWatchFormatter("api-gateway"))
logger.addHandler(handler)

# 测试不同级别的日志
print("="*80)
print("📋 日志示例")
print("="*80)

print("\n1️⃣ INFO 级别:")
logger.info("Processing user request", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "request_method": "GET",
    "request_path": "/api/v1/users/123",
    "user_id": "user_123"
})

print("\n2️⃣ WARNING 级别:")
logger.warning("Rate limit approaching", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4737",
    "user_id": "user_456",
    "requests_remaining": 10
})

print("\n3️⃣ ERROR 级别:")
logger.error("Database connection failed", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4738",
    "error_type": "ConnectionError",
    "database": "postgresql"
})

print("\n4️⃣ DEBUG 级别:")
logger.debug("Cache hit for key", extra={
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4739",
    "cache_key": "user:123:profile",
    "ttl": 3600
})

print("\n" + "="*80)
print("📊 日志格式说明")
print("="*80)
print("""
每条日志现在包含以下关键字段：
1. level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
2. timestamp: ISO 格式时间戳
3. file: 文件名:行号 (如 test_enhanced_log_format.py:78)
4. tracking_id: OpenTelemetry trace ID
5. service: 服务名称
6. @level, @timestamp: CloudWatch 标准字段

便于查询的格式：
- 快速查看级别: 直接查 "level" 字段
- 快速定位代码: 查看 "file" 字段
- 详细源码信息: 在 "source" 对象中

CloudWatch 查询示例:
fields timestamp, level, file, @message, tracking_id
| filter level = "ERROR"
| sort timestamp desc
""")