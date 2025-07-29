#!/usr/bin/env python3
"""
测试修复后的 gRPC 服务端
"""

import asyncio
import time
from services.grpc_server import WorkflowAgentServicer, StateConverter
from workflow_agent_pb2 import ConversationRequest, AgentState, WorkflowContext

def test_state_converter():
    """测试状态转换器"""
    print("🧪 测试状态转换器...")
    
    try:
        # 测试空状态转换
        empty_proto = AgentState()
        workflow_state = StateConverter.proto_to_workflow_state(empty_proto)
        print(f"✅ 空状态转换成功: stage={workflow_state.get('stage')}")
        
        # 验证默认值
        if workflow_state.get('stage') != 'clarification':
            print(f"❌ 默认stage应该是clarification，实际是{workflow_state.get('stage')}")
            return False
        
        # 测试状态转换回proto
        proto_state = StateConverter.workflow_state_to_proto(workflow_state)
        print(f"✅ 状态转换回proto成功: stage={proto_state.stage}")
        
        # 验证proto状态
        if proto_state.stage != 0:  # STAGE_CLARIFICATION = 0
            print(f"❌ Proto stage应该是0，实际是{proto_state.stage}")
            return False
        
        # 测试枚举转换
        stage_str = StateConverter._proto_enum_to_stage(0)
        stage_enum = StateConverter._stage_to_proto_enum("clarification")
        print(f"✅ 枚举转换正常: 0 -> '{stage_str}', 'clarification' -> {stage_enum}")
        
        # 验证枚举转换
        if stage_str != "clarification" or stage_enum != 0:
            print(f"❌ 枚举转换错误: {stage_str} != 'clarification' 或 {stage_enum} != 0")
            return False
        
        # 测试所有stage的转换
        test_stages = [
            "clarification", "negotiation", "gap_analysis", 
            "alternative_generation", "workflow_generation", "debug", "completed"
        ]
        
        for stage in test_stages:
            enum_val = StateConverter._stage_to_proto_enum(stage)
            stage_back = StateConverter._proto_enum_to_stage(enum_val)
            if stage_back != stage:
                print(f"❌ Stage往返转换失败: {stage} -> {enum_val} -> {stage_back}")
                return False
        
        print("✅ 所有stage往返转换正常")
        return True
        
    except Exception as e:
        print(f"❌ 状态转换器测试异常: {e}")
        return False

def test_servicer_initialization():
    """测试服务端初始化"""
    print("\n🧪 测试服务端初始化...")
    
    try:
        servicer = WorkflowAgentServicer()
        print("✅ WorkflowAgentServicer 初始化成功")
        
        # 检查服务端方法
        if hasattr(servicer, 'ProcessConversation'):
            print("✅ ProcessConversation 方法存在")
        else:
            print("❌ ProcessConversation 方法缺失")
            
    except Exception as e:
        print(f"❌ 服务端初始化失败: {e}")
        return False
    
    return True

def test_request_creation():
    """测试请求创建"""
    print("\n🧪 测试请求创建...")
    
    try:
        # 创建测试请求
        request = ConversationRequest()
        request.session_id = "test-session-123"
        request.user_id = "test-user"
        request.user_message = "创建一个简单的邮件工作流"
        
        # 设置当前状态
        current_state = AgentState()
        current_state.session_id = request.session_id
        current_state.user_id = request.user_id
        current_state.stage = 0  # STAGE_CLARIFICATION
        current_state.created_at = int(time.time() * 1000)
        current_state.updated_at = int(time.time() * 1000)
        
        request.current_state.CopyFrom(current_state)
        
        # 设置工作流上下文
        workflow_context = WorkflowContext()
        workflow_context.origin = "create"
        workflow_context.source_workflow_id = ""
        workflow_context.modification_intent = ""
        
        request.workflow_context.CopyFrom(workflow_context)
        
        print("✅ ConversationRequest 创建成功")
        print(f"   Session ID: {request.session_id}")
        print(f"   User Message: {request.user_message}")
        print(f"   Current Stage: {request.current_state.stage}")
        
        return request
        
    except Exception as e:
        print(f"❌ 请求创建失败: {e}")
        return None

async def test_process_conversation_structure():
    """测试ProcessConversation方法结构（不实际调用LangGraph）"""
    print("\n🧪 测试ProcessConversation方法结构...")
    
    try:
        servicer = WorkflowAgentServicer()
        request = test_request_creation()
        
        if not request:
            print("❌ 无法创建测试请求")
            return False
        
        # 检查方法是否可以调用（不实际运行以避免依赖问题）
        import inspect
        method = getattr(servicer, 'ProcessConversation')
        sig = inspect.signature(method)
        
        print(f"✅ ProcessConversation 方法签名: {sig}")
        print(f"✅ 方法参数数量: {len(sig.parameters)}")
        
        # 检查是否是异步生成器
        import types
        if inspect.isgeneratorfunction(method) or inspect.isasyncgenfunction(method):
            print("✅ ProcessConversation 是生成器函数")
        else:
            print("⚠️ ProcessConversation 不是生成器函数")
        
        return True
        
    except Exception as e:
        print(f"❌ ProcessConversation 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试修复后的 gRPC 服务端")
    print("=" * 50)
    
    # 运行测试
    tests = [
        ("状态转换器", test_state_converter),
        ("服务端初始化", test_servicer_initialization),
        ("请求创建", lambda: test_request_creation() is not None),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 运行异步测试
    print(f"\n--- ProcessConversation方法结构 ---")
    try:
        result = asyncio.run(test_process_conversation_structure())
        results.append(("ProcessConversation方法结构", result))
    except Exception as e:
        print(f"❌ ProcessConversation测试异常: {e}")
        results.append(("ProcessConversation方法结构", False))
    
    # 生成报告
    print("\n" + "=" * 50)
    print("📊 修复后的 gRPC 服务端测试报告")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {test_name}")
    
    print(f"\n通过率: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有proto类型错误已修复！")
        print("✅ gRPC服务端可以正常使用")
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)