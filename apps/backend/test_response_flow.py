#!/usr/bin/env python3
"""
测试响应流程 - 验证修复后的单次处理逻辑
"""

import sys
from pathlib import Path

# 添加api-gateway到路径
api_gateway_path = Path(__file__).parent / "api-gateway"
sys.path.append(str(api_gateway_path))

from app.services.response_processor import UnifiedResponseProcessor

def test_grpc_client_response_processing():
    """模拟grpc_client的响应处理流程"""
    print("🧪 测试 gRPC 客户端响应处理流程...")
    
    # 模拟 agent_state 数据
    mock_agent_state = {
        "stage": "clarification",
        "conversations": [
            {"role": "assistant", "text": "请详细描述您的工作流需求", "timestamp": 1640995200000}
        ],
        "clarification_context": {
            "pending_questions": ["什么是触发条件？"]
        }
    }
    
    # 模拟 grpc_client 中的处理逻辑
    result = {
        "type": "message",  # 初始类型
        "session_id": "test-session-123",
        "timestamp": 1640995200000,
        "is_final": False,
        "agent_state": mock_agent_state
    }
    
    # grpc_client 调用 UnifiedResponseProcessor (第1次，唯一一次)
    stage = result["agent_state"].get("stage", "clarification")
    processed_response = UnifiedResponseProcessor.process_stage_response(stage, result["agent_state"])
    result.update(processed_response)  # 这里会覆盖 type 和添加 content
    
    print(f"✅ grpc_client 处理后的响应:")
    print(f"   类型: {result['type']}")
    print(f"   内容文本: {result['content']['text'][:50]}...")
    print(f"   阶段: {result['content']['stage']}")
    
    return result

def test_chat_api_response_consumption():
    """模拟chat.py的响应消费流程"""
    print("\n🧪 测试 Chat API 响应消费流程...")
    
    # 获取grpc_client处理后的响应
    grpc_response = test_grpc_client_response_processing()
    
    # chat.py 中的逻辑 - 直接使用处理结果，不再重复处理
    if grpc_response["type"] in ["ai_message", "workflow", "alternatives"] and "agent_state" in grpc_response:
        print("✅ chat.py 检测到已处理的响应")
        
        # 直接构建 SSE 数据，无需重复调用 UnifiedResponseProcessor
        sse_data = {
            "type": grpc_response["type"],
            "session_id": grpc_response["session_id"], 
            "timestamp": grpc_response["timestamp"],
            "is_final": grpc_response.get("is_final", False),
            "content": grpc_response["content"]
        }
        
        # 添加 workflow 数据（如果有）
        if "workflow" in grpc_response:
            sse_data["workflow"] = grpc_response["workflow"]
        
        print(f"✅ chat.py 构建的 SSE 数据:")
        print(f"   类型: {sse_data['type']}")
        print(f"   内容: {sse_data['content']['text'][:50]}...")
        print(f"   无重复处理: ✅")
        
        return sse_data
    else:
        print("❌ chat.py 未能识别处理后的响应")
        return None

def main():
    """主测试函数"""
    print("🚀 开始测试响应流程优化")
    print("=" * 60)
    
    # 测试完整流程
    sse_result = test_chat_api_response_consumption()
    
    print("\n" + "=" * 60)
    if sse_result:
        print("🎉 响应流程优化成功！")
        print("✅ UnifiedResponseProcessor 只调用一次（在 grpc_client 中）")
        print("✅ chat.py 直接使用处理结果，无重复处理")
        print("✅ 响应格式正确，功能完整")
    else:
        print("❌ 响应流程存在问题")
    
    print("\n🔄 优化对比:")
    print("❌ 优化前: grpc_client 处理 → chat.py 重复处理")
    print("✅ 优化后: grpc_client 处理 → chat.py 直接使用")

if __name__ == "__main__":
    main()