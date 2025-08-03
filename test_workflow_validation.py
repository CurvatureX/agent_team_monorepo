#!/usr/bin/env python3
"""
测试Workflow验证功能 - 创建包含所有node子类型的workflow

这个脚本用于验证我们刚刚改造的节点规范系统是否正常工作。
它将创建一个包含所有支持的node子类型的workflow，并测试验证功能。
"""

import json
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from shared.models import CreateWorkflowRequest, NodeData, ConnectionsMap
    from workflow_engine.utils.workflow_validator import WorkflowValidator
    print("✅ 成功导入所需模块")
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    sys.exit(1)

def create_comprehensive_test_workflow():
    """创建包含所有node子类型的测试workflow"""
    
    nodes = []
    node_id_counter = 1
    
    # 1. TRIGGER_NODE 子类型
    trigger_subtypes = [
        "TRIGGER_MANUAL",
        "TRIGGER_WEBHOOK", 
        "TRIGGER_CRON",
        "TRIGGER_CHAT",
        "TRIGGER_EMAIL",
        "TRIGGER_FORM",
        "TRIGGER_CALENDAR"
    ]
    
    for subtype in trigger_subtypes:
        node_id = f"trigger_{node_id_counter}"
        node_id_counter += 1
        
        if subtype == "TRIGGER_MANUAL":
            parameters = {
                "trigger_name": "Manual Test",
                "description": "Manual trigger for testing",
                "require_confirmation": True
            }
        elif subtype == "TRIGGER_WEBHOOK":
            parameters = {
                "webhook_path": "/test-webhook",
                "http_method": "POST",
                "authentication": "none"
            }
        elif subtype == "TRIGGER_CRON":
            parameters = {
                "cron_expression": "0 9 * * MON",
                "timezone": "UTC"
            }
        elif subtype == "TRIGGER_CHAT":
            parameters = {
                "chat_platform": "slack",
                "message_filter": "hello"
            }
        elif subtype == "TRIGGER_EMAIL":
            parameters = {
                "email_filter": "subject:test",
                "email_provider": "gmail"
            }
        elif subtype == "TRIGGER_FORM":
            parameters = {
                "form_id": "test-form",
                "form_fields": ["name", "email"]
            }
        elif subtype == "TRIGGER_CALENDAR":
            parameters = {
                "calendar_id": "primary",
                "event_filter": "meeting"
            }
        
        nodes.append(NodeData(
            id=node_id,
            name=f"Test {subtype}",
            type="TRIGGER_NODE",
            subtype=subtype,
            parameters=parameters,
            position={"x": 100, "y": 100 + len(nodes) * 100}
        ))
    
    # 2. AI_AGENT_NODE 子类型
    ai_subtypes = [
        "GEMINI_NODE",
        "OPENAI_NODE", 
        "CLAUDE_NODE"
    ]
    
    for subtype in ai_subtypes:
        node_id = f"ai_{node_id_counter}"
        node_id_counter += 1
        
        base_params = {
            "system_prompt": f"You are a helpful {subtype.lower()} assistant",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        if subtype == "GEMINI_NODE":
            parameters = {
                **base_params,
                "model_version": "gemini-pro",
                "safety_settings": {}
            }
        elif subtype == "OPENAI_NODE":
            parameters = {
                **base_params,
                "model_version": "gpt-4",
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            }
        elif subtype == "CLAUDE_NODE":
            parameters = {
                **base_params,
                "model_version": "claude-3-sonnet",
                "stop_sequences": []
            }
        
        nodes.append(NodeData(
            id=node_id,
            name=f"Test {subtype}",
            type="AI_AGENT_NODE",
            subtype=subtype,
            parameters=parameters,
            position={"x": 300, "y": 100 + len(nodes) * 100}
        ))
    
    # 3. ACTION_NODE 子类型
    action_subtypes = [
        "RUN_CODE",
        "HTTP_REQUEST",
        "DATA_TRANSFORMATION",
        "FILE_OPERATION"
    ]
    
    for subtype in action_subtypes:
        node_id = f"action_{node_id_counter}"
        node_id_counter += 1
        
        if subtype == "RUN_CODE":
            parameters = {
                "code": "print('Hello World')",
                "language": "python",
                "timeout": 30,
                "environment": {},
                "capture_output": True
            }
        elif subtype == "HTTP_REQUEST":
            parameters = {
                "method": "GET",
                "url": "https://api.example.com/test",
                "headers": {},
                "data": {},
                "timeout": 30,
                "authentication": "none",
                "retry_attempts": 3
            }
        elif subtype == "DATA_TRANSFORMATION":
            parameters = {
                "transformation_type": "filter",
                "transformation_rule": "filter condition"
            }
        elif subtype == "FILE_OPERATION":
            parameters = {
                "operation": "read",
                "file_path": "/tmp/test.txt"
            }
        
        nodes.append(NodeData(
            id=node_id,
            name=f"Test {subtype}",
            type="ACTION_NODE", 
            subtype=subtype,
            parameters=parameters,
            position={"x": 500, "y": 100 + len(nodes) * 100}
        ))
    
    # 4. FLOW_NODE 子类型
    flow_subtypes = [
        "IF",
        "FILTER", 
        "LOOP",
        "MERGE",
        "SWITCH",
        "WAIT"
    ]
    
    for subtype in flow_subtypes:
        node_id = f"flow_{node_id_counter}"
        node_id_counter += 1
        
        if subtype == "IF":
            parameters = {
                "condition": "input.value > 10"
            }
        elif subtype == "FILTER":
            parameters = {
                "filter_condition": {"status": "active"}
            }
        elif subtype == "LOOP":
            parameters = {
                "loop_type": "for_each",
                "max_iterations": 100
            }
        elif subtype == "MERGE":
            parameters = {
                "merge_strategy": "combine"
            }
        elif subtype == "SWITCH":
            parameters = {
                "switch_cases": [
                    {"value": "case1", "route": "branch1"},
                    {"value": "case2", "route": "branch2"}
                ]
            }
        elif subtype == "WAIT":
            parameters = {
                "wait_type": "time",
                "duration": 5
            }
        
        nodes.append(NodeData(
            id=node_id,
            name=f"Test {subtype}",
            type="FLOW_NODE",
            subtype=subtype, 
            parameters=parameters,
            position={"x": 700, "y": 100 + len(nodes) * 100}
        ))
    
    # 5. 其他节点类型...
    # 为了简化测试，我们先测试以上这些主要类型
    
    # 创建workflow请求
    workflow_request = CreateWorkflowRequest(
        name="Comprehensive Node Types Test Workflow",
        description="测试所有node子类型的验证功能",
        nodes=nodes,
        connections=None,  # 简化测试，不添加连接
        settings={},
        static_data={},
        tags=["test", "validation"],
        user_id="test-user",
        session_id="test-session"
    )
    
    return workflow_request

def test_workflow_validation():
    """测试workflow验证功能"""
    print("🧪 开始测试workflow验证功能...")
    
    # 创建测试workflow
    print("📝 创建包含所有node子类型的测试workflow...")
    workflow_request = create_comprehensive_test_workflow()
    
    print(f"✅ 创建了包含 {len(workflow_request.nodes)} 个节点的workflow")
    
    # 打印节点信息
    print("\n📋 节点列表:")
    for node in workflow_request.nodes:
        print(f"  - {node.id}: {node.type}.{node.subtype} ({node.name})")
    
    # 使用WorkflowValidator进行验证
    print("\n🔍 开始验证workflow...")
    validator = WorkflowValidator()
    
    # 转换为dict格式
    workflow_dict = {
        "name": workflow_request.name,
        "nodes": [node.dict() for node in workflow_request.nodes],
        "connections": workflow_request.connections.dict() if workflow_request.connections else {},
        "settings": workflow_request.settings
    }
    
    # 执行验证
    result = validator.validate_workflow_structure(workflow_dict, validate_node_parameters=True)
    
    # 输出验证结果
    print(f"\n📊 验证结果:")
    print(f"  ✅ 是否有效: {result['valid']}")
    
    if result['errors']:
        print(f"  ❌ 错误 ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"    - {error}")
    else:
        print("  ✅ 没有发现错误")
    
    if result['warnings']:
        print(f"  ⚠️  警告 ({len(result['warnings'])}):")
        for warning in result['warnings']:
            print(f"    - {warning}")
    else:
        print("  ✅ 没有警告")
    
    return result

def test_invalid_workflow():
    """测试无效workflow的验证"""
    print("\n\n🧪 测试无效workflow的验证...")
    
    # 创建一个有错误的node
    invalid_node = NodeData(
        id="invalid_node",
        name="Invalid Node",
        type="AI_AGENT_NODE",
        subtype="OPENAI_NODE",
        parameters={
            # 缺少必需的system_prompt参数
            "temperature": "invalid_type",  # 错误的类型
            "max_tokens": -100  # 无效值
        },
        position={"x": 100, "y": 100}
    )
    
    workflow_request = CreateWorkflowRequest(
        name="Invalid Test Workflow",
        description="测试无效节点的验证",
        nodes=[invalid_node],
        connections=None,
        settings={},
        static_data={},
        tags=["test", "invalid"],
        user_id="test-user", 
        session_id="test-session"
    )
    
    validator = WorkflowValidator()
    workflow_dict = {
        "name": workflow_request.name,
        "nodes": [node.dict() for node in workflow_request.nodes],
        "connections": {},
        "settings": workflow_request.settings
    }
    
    result = validator.validate_workflow_structure(workflow_dict, validate_node_parameters=True)
    
    print(f"📊 无效workflow验证结果:")
    print(f"  ❌ 是否有效: {result['valid']} (应该为False)")
    print(f"  ❌ 错误数量: {len(result['errors'])}")
    
    if result['errors']:
        print("  错误详情:")
        for error in result['errors']:
            print(f"    - {error}")
    
    return result

if __name__ == "__main__":
    print("🚀 开始测试Workflow节点规范系统...")
    print("=" * 60)
    
    try:
        # 测试有效workflow
        valid_result = test_workflow_validation()
        
        # 测试无效workflow
        invalid_result = test_invalid_workflow()
        
        print("\n" + "=" * 60)
        print("📈 测试总结:")
        print(f"  ✅ 有效workflow验证: {'通过' if valid_result['valid'] else '失败'}")
        print(f"  ❌ 无效workflow验证: {'通过' if not invalid_result['valid'] else '失败'}")
        
        if valid_result['valid'] and not invalid_result['valid']:
            print("🎉 所有测试通过！节点规范系统工作正常。")
        else:
            print("⚠️  部分测试未通过，需要进一步检查。")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()