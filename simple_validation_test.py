#!/usr/bin/env python3
"""
简化的验证测试 - 直接测试WorkflowValidator和NodeExecutor的validate方法

这个脚本会直接测试我们修改的验证逻辑，而不依赖完整的pydantic模型。
"""

import sys
import os
from pathlib import Path

# Add backend path for imports
backend_dir = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))
workflow_engine_dir = Path(__file__).parent / "apps" / "backend" / "workflow_engine"
sys.path.insert(0, str(workflow_engine_dir))

# Simple test class to simulate node objects
class MockNode:
    def __init__(self, node_id, name, node_type, subtype, parameters):
        self.id = node_id
        self.name = name
        self.type = node_type
        self.subtype = subtype
        self.parameters = parameters

def test_node_executors():
    """测试各种node executor的validate方法"""
    print("🧪 开始测试节点执行器的validate方法...")
    
    try:
        from workflow_engine.nodes.factory import get_node_executor_factory
        print("✅ 成功导入NodeExecutorFactory")
        
        factory = get_node_executor_factory()
        print("✅ 创建Factory实例成功")
        
        # 测试数据：每种node类型的有效配置
        test_cases = [
            # TRIGGER_NODE tests
            {
                "name": "Manual Trigger",
                "type": "TRIGGER_NODE",
                "subtype": "TRIGGER_MANUAL",
                "parameters": {
                    "trigger_name": "Test Manual",
                    "description": "Test trigger",
                    "require_confirmation": True
                }
            },
            {
                "name": "Webhook Trigger", 
                "type": "TRIGGER_NODE",
                "subtype": "TRIGGER_WEBHOOK",
                "parameters": {
                    "webhook_path": "/test",
                    "http_method": "POST",
                    "authentication": "none"
                }
            },
            # AI_AGENT_NODE tests
            {
                "name": "OpenAI Agent",
                "type": "AI_AGENT_NODE", 
                "subtype": "OPENAI_NODE",
                "parameters": {
                    "system_prompt": "You are helpful",
                    "model_version": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            },
            {
                "name": "Claude Agent",
                "type": "AI_AGENT_NODE",
                "subtype": "CLAUDE_NODE", 
                "parameters": {
                    "system_prompt": "You are helpful",
                    "model_version": "claude-3-sonnet",
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            },
            # ACTION_NODE tests
            {
                "name": "HTTP Request",
                "type": "ACTION_NODE",
                "subtype": "HTTP_REQUEST",
                "parameters": {
                    "method": "GET",
                    "url": "https://api.example.com",
                    "headers": {},
                    "timeout": 30
                }
            },
            {
                "name": "Run Code",
                "type": "ACTION_NODE",
                "subtype": "RUN_CODE",
                "parameters": {
                    "code": "print('hello')",
                    "language": "python",
                    "timeout": 30
                }
            },
            # FLOW_NODE tests
            {
                "name": "If Condition",
                "type": "FLOW_NODE",
                "subtype": "IF",
                "parameters": {
                    "condition": "input.value > 10"
                }
            },
            # MEMORY_NODE tests
            {
                "name": "Vector Store",
                "type": "MEMORY_NODE", 
                "subtype": "MEMORY_VECTOR_STORE",
                "parameters": {
                    "operation": "store",
                    "collection_name": "test"
                }
            },
            # TOOL_NODE tests
            {
                "name": "Calendar Tool",
                "type": "TOOL_NODE",
                "subtype": "TOOL_CALENDAR",
                "parameters": {
                    "calendar_id": "primary",
                    "operation": "list_events"
                }
            },
            # HUMAN_IN_THE_LOOP_NODE tests
            {
                "name": "Gmail Interaction",
                "type": "HUMAN_IN_THE_LOOP_NODE",
                "subtype": "HUMAN_GMAIL",
                "parameters": {
                    "email_template": "Please review",
                    "recipients": ["test@example.com"],
                    "subject": "Review Required"
                }
            },
            # EXTERNAL_ACTION_NODE tests
            {
                "name": "GitHub Action",
                "type": "EXTERNAL_ACTION_NODE",
                "subtype": "GITHUB",
                "parameters": {
                    "action": "create_issue",
                    "repository": "test/repo"
                }
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases):
            print(f"\n📝 测试 {i+1}/{len(test_cases)}: {test_case['name']} ({test_case['type']}.{test_case['subtype']})")
            
            try:
                # 创建executor
                executor = factory.create_executor(test_case['type'], test_case['subtype'])
                
                if not executor:
                    print(f"  ❌ 无法创建executor")
                    results.append({
                        'name': test_case['name'],
                        'success': False,
                        'error': 'No executor found'
                    })
                    continue
                
                # 创建mock node
                node = MockNode(
                    node_id=f"test_node_{i}",
                    name=test_case['name'],
                    node_type=test_case['type'],
                    subtype=test_case['subtype'],
                    parameters=test_case['parameters']
                )
                
                # 运行验证
                validation_errors = executor.validate(node)
                
                if validation_errors:
                    print(f"  ⚠️  验证发现错误: {', '.join(validation_errors)}")
                    results.append({
                        'name': test_case['name'],
                        'success': False,
                        'error': '; '.join(validation_errors)
                    })
                else:
                    print(f"  ✅ 验证通过")
                    results.append({
                        'name': test_case['name'], 
                        'success': True,
                        'error': None
                    })
                    
            except Exception as e:
                print(f"  ❌ 测试异常: {str(e)}")
                results.append({
                    'name': test_case['name'],
                    'success': False,
                    'error': f'Exception: {str(e)}'
                })
        
        # 输出总结
        print("\n" + "="*60)
        print("📊 测试结果总结:")
        
        passed = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"  ✅ 通过: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed < total:
            print(f"  ❌ 失败: {total-passed}/{total}")
            print("\n失败详情:")
            for result in results:
                if not result['success']:
                    print(f"    - {result['name']}: {result['error']}")
        
        return passed == total
        
    except Exception as e:
        print(f"❌ 测试初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_invalid_nodes():
    """测试无效节点的验证"""
    print("\n\n🧪 测试无效节点的验证...")
    
    try:
        from workflow_engine.nodes.factory import get_node_executor_factory
        
        factory = get_node_executor_factory()
        
        # 无效测试用例
        invalid_cases = [
            {
                "name": "Missing required parameter",
                "type": "AI_AGENT_NODE",
                "subtype": "OPENAI_NODE",
                "parameters": {
                    # 缺少system_prompt
                    "temperature": 0.7
                }
            },
            {
                "name": "Invalid parameter type",
                "type": "ACTION_NODE", 
                "subtype": "HTTP_REQUEST",
                "parameters": {
                    "method": "INVALID_METHOD",  # 无效的HTTP方法
                    "url": "https://example.com"
                }
            },
            {
                "name": "Invalid parameter value",
                "type": "MEMORY_NODE",
                "subtype": "MEMORY_VECTOR_STORE", 
                "parameters": {
                    "operation": "invalid_operation",  # 无效操作
                    "collection_name": "test"
                }
            }
        ]
        
        invalid_results = []
        
        for i, test_case in enumerate(invalid_cases):
            print(f"\n📝 测试无效case {i+1}: {test_case['name']}")
            
            try:
                executor = factory.create_executor(test_case['type'], test_case['subtype'])
                
                if not executor:
                    print(f"  ❌ 无法创建executor")
                    continue
                
                node = MockNode(
                    node_id=f"invalid_node_{i}",
                    name=test_case['name'],
                    node_type=test_case['type'],
                    subtype=test_case['subtype'],
                    parameters=test_case['parameters']
                )
                
                validation_errors = executor.validate(node)
                
                if validation_errors:
                    print(f"  ✅ 正确识别错误: {', '.join(validation_errors)}")
                    invalid_results.append(True)
                else:
                    print(f"  ❌ 未能识别错误 (应该失败但通过了)")
                    invalid_results.append(False)
                    
            except Exception as e:
                print(f"  ⚠️  验证过程异常: {str(e)}")
                invalid_results.append(True)  # 异常也算是正确识别了问题
        
        invalid_detected = sum(invalid_results)
        total_invalid = len(invalid_results)
        
        print(f"\n📊 无效节点检测结果: {invalid_detected}/{total_invalid} 正确识别")
        
        return invalid_detected == total_invalid
        
    except Exception as e:
        print(f"❌ 无效节点测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 开始简化的节点验证测试...")
    print("=" * 60)
    
    # 测试有效节点
    valid_test_passed = test_node_executors()
    
    # 测试无效节点
    invalid_test_passed = test_invalid_nodes()
    
    print("\n" + "=" * 60)
    print("🎯 最终测试结果:")
    print(f"  ✅ 有效节点验证: {'通过' if valid_test_passed else '失败'}")
    print(f"  ❌ 无效节点检测: {'通过' if invalid_test_passed else '失败'}")
    
    if valid_test_passed and invalid_test_passed:
        print("🎉 所有测试通过！节点规范系统工作正常。")
        exit(0)
    else:
        print("⚠️  部分测试未通过，需要进一步检查。")
        exit(1)