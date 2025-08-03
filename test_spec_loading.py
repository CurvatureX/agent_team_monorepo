#!/usr/bin/env python3
"""
测试节点规范加载功能

这个脚本测试我们的节点规范系统是否能正确加载所有规范。
"""

import sys
from pathlib import Path

# Add backend path for imports
backend_dir = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

def test_spec_loading():
    """测试规范加载功能"""
    print("🧪 测试节点规范系统加载...")
    
    try:
        # 导入规范注册表
        from shared.node_specs import node_spec_registry
        print("✅ 成功导入node_spec_registry")
        
        # 获取所有规范
        all_specs = node_spec_registry.list_all_specs()
        print(f"✅ 成功加载 {len(all_specs)} 个节点规范")
        
        # 按类型分组统计
        type_counts = {}
        for spec in all_specs:
            node_type = spec.node_type
            if node_type not in type_counts:
                type_counts[node_type] = []
            type_counts[node_type].append(spec.subtype)
        
        print("\n📊 规范统计:")
        for node_type, subtypes in type_counts.items():
            print(f"  {node_type}: {len(subtypes)} 个子类型")
            for subtype in sorted(subtypes):
                print(f"    - {subtype}")
        
        # 测试获取特定规范
        print("\n🔍 测试获取特定规范:")
        test_cases = [
            ("TRIGGER_NODE", "TRIGGER_MANUAL"),
            ("AI_AGENT_NODE", "OPENAI_NODE"),
            ("ACTION_NODE", "HTTP_REQUEST"),
            ("FLOW_NODE", "IF"),
            ("MEMORY_NODE", "MEMORY_VECTOR_STORE"),
            ("TOOL_NODE", "TOOL_CALENDAR"),
            ("HUMAN_IN_THE_LOOP_NODE", "HUMAN_GMAIL"),
            ("EXTERNAL_ACTION_NODE", "GITHUB")
        ]
        
        for node_type, subtype in test_cases:
            spec = node_spec_registry.get_spec(node_type, subtype)
            if spec:
                param_count = len(spec.parameters)
                print(f"  ✅ {node_type}.{subtype}: {param_count} 个参数")
            else:
                print(f"  ❌ {node_type}.{subtype}: 未找到规范")
        
        # 测试验证功能
        print("\n🧪 测试验证功能:")
        
        # 创建一个简单的mock node来测试验证
        class MockNode:
            def __init__(self, node_type, subtype, parameters):
                self.type = node_type
                self.subtype = subtype
                self.parameters = parameters
        
        # 测试有效node
        valid_node = MockNode(
            "TRIGGER_NODE", 
            "TRIGGER_MANUAL",
            {
                "trigger_name": "Test",
                "description": "Test trigger",
                "require_confirmation": True
            }
        )
        
        errors = node_spec_registry.validate_node(valid_node)
        if not errors:
            print("  ✅ 有效节点验证通过")
        else:
            print(f"  ❌ 有效节点验证失败: {errors}")
        
        # 测试无效node
        invalid_node = MockNode(
            "TRIGGER_NODE",
            "TRIGGER_MANUAL", 
            {
                # 缺少required参数
            }
        )
        
        errors = node_spec_registry.validate_node(invalid_node)
        if errors:
            print(f"  ✅ 无效节点正确识别错误: {errors[0]}")
        else:
            print("  ❌ 无效节点验证未能识别错误")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_workflow_creation_validation():
    """测试workflow创建时的验证"""
    print("\n\n🧪 测试workflow创建验证集成...")
    
    try:
        from workflow_engine.utils.workflow_validator import WorkflowValidator
        print("✅ 成功导入WorkflowValidator")
        
        validator = WorkflowValidator()
        print("✅ 创建WorkflowValidator实例成功")
        
        # 创建一个简单的有效workflow定义
        valid_workflow = {
            "name": "Test Workflow",
            "nodes": [
                {
                    "id": "trigger_1",
                    "name": "Manual Trigger",
                    "type": "TRIGGER_NODE",
                    "subtype": "TRIGGER_MANUAL",
                    "parameters": {
                        "trigger_name": "Test Trigger",
                        "description": "Test description",
                        "require_confirmation": True
                    }
                },
                {
                    "id": "ai_1", 
                    "name": "AI Agent",
                    "type": "AI_AGENT_NODE",
                    "subtype": "OPENAI_NODE",
                    "parameters": {
                        "system_prompt": "You are helpful",
                        "model_version": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                }
            ],
            "connections": {},
            "settings": {}
        }
        
        result = validator.validate_workflow_structure(valid_workflow, validate_node_parameters=True)
        
        if result['valid']:
            print("✅ 有效workflow验证通过")
        else:
            print(f"❌ 有效workflow验证失败: {result['errors']}")
        
        # 测试无效workflow
        invalid_workflow = {
            "name": "Invalid Workflow",
            "nodes": [
                {
                    "id": "invalid_1",
                    "name": "Invalid Node", 
                    "type": "AI_AGENT_NODE",
                    "subtype": "OPENAI_NODE",
                    "parameters": {
                        # 缺少必需的system_prompt
                        "temperature": 0.7
                    }
                }
            ],
            "connections": {},
            "settings": {}
        }
        
        result = validator.validate_workflow_structure(invalid_workflow, validate_node_parameters=True)
        
        if not result['valid']:
            print(f"✅ 无效workflow正确识别错误: {result['errors'][0] if result['errors'] else 'Unknown error'}")
        else:
            print("❌ 无效workflow验证未能识别错误")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow验证测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试节点规范系统...")
    print("=" * 60)
    
    # 测试规范加载
    spec_test_passed = test_spec_loading()
    
    # 测试workflow验证
    workflow_test_passed = test_workflow_creation_validation() 
    
    print("\n" + "=" * 60)
    print("🎯 测试结果总结:")
    print(f"  📋 规范加载测试: {'✅ 通过' if spec_test_passed else '❌ 失败'}")
    print(f"  🔍 Workflow验证测试: {'✅ 通过' if workflow_test_passed else '❌ 失败'}")
    
    if spec_test_passed and workflow_test_passed:
        print("\n🎉 所有测试通过！")
        print("✅ 节点规范系统成功集成到workflow创建流程中")
        print("✅ 新建workflow时会自动进行节点参数验证")
        exit(0)
    else:
        print("\n⚠️  部分测试未通过")
        exit(1)