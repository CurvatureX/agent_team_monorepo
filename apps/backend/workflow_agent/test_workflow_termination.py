#!/usr/bin/env python
"""
测试 workflow 终止逻辑的脚本
用于验证不同场景下的中断行为
"""

import asyncio
import json
import aiohttp
from typing import AsyncGenerator

# 配置
API_URL = "http://localhost:8001/process-conversation"
TEST_SESSION_ID = "test-termination-12345"
TEST_ACCESS_TOKEN = "test-token"


async def stream_workflow_response(user_message: str) -> AsyncGenerator[dict, None]:
    """发送请求并流式读取响应"""
    headers = {
        "Content-Type": "application/json",
    }
    
    payload = {
        "session_id": TEST_SESSION_ID,
        "user_message": user_message,
        "access_token": TEST_ACCESS_TOKEN,
        "org_id": "test-org",
        "user_id": "test-user"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=headers, json=payload) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data:
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse JSON: {e}")
                            print(f"Raw data: {data}")


async def test_workflow_termination():
    """测试不同的终止场景"""
    
    print("=" * 60)
    print("测试 Workflow 终止逻辑")
    print("=" * 60)
    
    # 测试场景 1: 简单的工作流，应该在 NEGOTIATION 阶段终止
    print("\n测试场景 1: NEGOTIATION 阶段终止")
    print("-" * 40)
    
    responses = []
    async for response in stream_workflow_response("帮我创建一个每天早上8点发送天气预报的工作流"):
        print(f"收到响应: {response.get('response_type')} - Stage: {response.get('status_change', {}).get('current_stage', 'N/A')}")
        responses.append(response)
        
        # 检查是否在 NEGOTIATION 阶段停止
        if response.get('status_change', {}).get('current_stage') == 'NEGOTIATION':
            print("✓ 检测到 NEGOTIATION 阶段")
    
    print(f"\n总共收到 {len(responses)} 个响应")
    
    # 验证最后的阶段
    last_stage = None
    for resp in reversed(responses):
        if resp.get('status_change', {}).get('current_stage'):
            last_stage = resp['status_change']['current_stage']
            break
    
    print(f"最终阶段: {last_stage}")
    
    # 测试场景 2: 检查状态是否正确保存
    print("\n\n测试场景 2: 检查状态持久化")
    print("-" * 40)
    
    # 发送另一个消息到同一个会话，验证状态是否保留
    async for response in stream_workflow_response("继续上一个对话"):
        if response.get('status_change'):
            stage_state = response['status_change'].get('stage_state', {})
            print(f"当前阶段: {stage_state.get('stage')}")
            print(f"会话ID: {stage_state.get('session_id')}")
            print(f"意图摘要: {stage_state.get('intent_summary', 'N/A')}")
            break
    
    print("\n测试完成!")


async def test_debug_loop_limit():
    """测试 debug 循环限制"""
    print("\n\n测试场景 3: Debug 循环限制")
    print("-" * 40)
    
    # 这个测试需要特殊构造的输入来触发多次 debug 循环
    # 在实际使用中，这种情况比较少见
    print("注意: Debug 循环限制测试需要特殊的输入条件")
    print("当 debug_loop_count > 5 时会触发终止")


if __name__ == "__main__":
    asyncio.run(test_workflow_termination())
    # 可选：测试 debug 循环限制
    # asyncio.run(test_debug_loop_limit())