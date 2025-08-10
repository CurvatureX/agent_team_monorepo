#!/usr/bin/env python3
"""
直接测试OAuth2集成的脚本
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# 添加路径
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from workflow_engine.nodes.factory import get_node_executor_factory, register_default_executors
from workflow_engine.nodes.base import NodeExecutionContext, ExecutionStatus

async def main():
    print("🔧 正在测试OAuth2集成...")
    
    # 注册执行器
    register_default_executors()
    factory = get_node_executor_factory()
    
    # 创建EXTERNAL_ACTION_NODE执行器
    executor = factory.create_executor('EXTERNAL_ACTION_NODE', 'GOOGLE_CALENDAR')
    print(f"✅ 执行器创建成功: {executor}")
    
    # 创建测试参数
    test_parameters = {
        'action': 'list_events',
        'calendar_id': 'primary',
        'max_results': '5'
    }
    
    # 创建模拟的节点对象
    class MockNode:
        def __init__(self, parameters):
            self.parameters = parameters
            self.id = "test-google-calendar-node"
            self.type = "EXTERNAL_ACTION_NODE"
            self.subtype = "GOOGLE_CALENDAR"
    
    # 创建执行上下文
    context = NodeExecutionContext(
        node=MockNode(test_parameters),
        workflow_id="test-workflow-123",
        execution_id="test-execution-123",
        input_data={},
        static_data={},
        credentials={},  # 没有凭据，应该触发OAuth2流程
        metadata={"user_id": "7ba36345-a2bb-4ec9-a001-bb46d79d629d"}
    )
    
    print("🚀 执行Google Calendar节点...")
    print(f"参数: {json.dumps(test_parameters, indent=2)}")
    
    try:
        # 执行节点
        result = await executor.execute(context)
        
        print("📊 执行结果:")
        print(f"状态: {result.status}")
        print(f"输出数据: {json.dumps(result.output_data, indent=2, ensure_ascii=False)}")
        
        if result.status == ExecutionStatus.ERROR:
            print(f"❌ 错误信息: {result.error_message}")
        elif result.status == ExecutionStatus.SUCCESS:
            print("✅ 执行成功!")
            
        # 检查是否需要OAuth2授权
        if result.output_data and result.output_data.get('requires_auth'):
            print("🔐 检测到需要OAuth2授权")
            print("✅ OAuth2流程检测正常工作")
        
    except Exception as e:
        print(f"❌ 执行出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())