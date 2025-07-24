#!/usr/bin/env python3
"""
改进的 ValidationService 测试脚本

修复了节点验证中的ID要求问题，并增加了更多边界条件测试。
"""

import json
import sys
import os
import time
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workflow_engine.services.validation_service import ValidationService
from proto import ai_system_pb2


def create_improved_test_workflows() -> Dict[str, Dict[str, Any]]:
    """创建改进的测试workflow，包括边界条件测试"""
    
    workflows = {}
    
    # 1. 正常的工作流
    workflows["valid_workflow"] = {
        "name": "Valid Workflow",
        "description": "A valid workflow for testing",
        "nodes": [
            {
                "id": "trigger_1",
                "name": "Manual Trigger",
                "type": "TRIGGER_NODE",
                "subtype": "MANUAL",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            },
            {
                "id": "ai_agent_1",
                "name": "AI Agent",
                "type": "AI_AGENT_NODE",
                "subtype": "router_agent",
                "parameters": {
                    "prompt": "Analyze the input and provide a response"
                },
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            }
        ],
        "connections": {
            "connections": {
                "Manual Trigger": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "AI Agent",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    
    # 2. 边界条件：极长节点名称
    workflows["long_node_name"] = {
        "name": "Long Node Name",
        "description": "A workflow with extremely long node names",
        "nodes": [
            {
                "id": "node_1",
                "name": "A" * 1000,  # 1000个字符的节点名称
                "type": "TRIGGER_NODE",
                "subtype": "manual",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            }
        ],
        "connections": {
            "connections": {}
        }
    }
    
    # 3. 边界条件：特殊字符节点名称
    workflows["special_char_name"] = {
        "name": "Special Char Name",
        "description": "A workflow with special characters in node names",
        "nodes": [
            {
                "id": "node_1",
                "name": "Node@#$%^&*()_+-=[]{}|;':\",./<>?",
                "type": "TRIGGER_NODE",
                "subtype": "manual",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            }
        ],
        "connections": {
            "connections": {}
        }
    }
    
    # 4. 边界条件：空字符串节点名称
    workflows["empty_node_name"] = {
        "name": "Empty Node Name",
        "description": "A workflow with empty node names",
        "nodes": [
            {
                "id": "node_1",
                "name": "",  # 空字符串
                "type": "TRIGGER_NODE",
                "subtype": "manual",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            }
        ],
        "connections": {
            "connections": {}
        }
    }
    
    # 5. 边界条件：大量节点
    workflows["many_nodes"] = {
        "name": "Many Nodes",
        "description": "A workflow with many nodes",
        "nodes": [
            {
                "id": f"node_{i}",
                "name": f"Node {i}",
                "type": "TRIGGER_NODE" if i == 0 else "AI_AGENT_NODE",
                "subtype": "manual" if i == 0 else "router_agent",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            }
            for i in range(50)  # 50个节点
        ],
        "connections": {
            "connections": {}
        }
    }
    
    # 6. 复杂循环依赖
    workflows["complex_circular"] = {
        "name": "Complex Circular",
        "description": "A workflow with complex circular dependencies",
        "nodes": [
            {
                "id": "node_1",
                "name": "Node 1",
                "type": "TRIGGER_NODE",
                "subtype": "manual",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            },
            {
                "id": "node_2",
                "name": "Node 2",
                "type": "AI_AGENT_NODE",
                "subtype": "router_agent",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            },
            {
                "id": "node_3",
                "name": "Node 3",
                "type": "ACTION_NODE",
                "subtype": "http_request",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            }
        ],
        "connections": {
            "connections": {
                "Node 1": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Node 2",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                },
                "Node 2": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Node 3",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                },
                "Node 3": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "Node 1",  # 形成循环
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    
    return workflows


def create_improved_test_nodes() -> Dict[str, Dict[str, Any]]:
    """创建改进的测试节点，修复ID要求问题"""
    
    nodes = {}
    
    # 1. 完全有效的节点
    nodes["valid_node"] = {
        "id": "test_node_1",
        "name": "Valid Test Node",
        "type": "TRIGGER_NODE",
        "subtype": "MANUAL",
        "parameters": {
            "test_param": "test_value"
        },
        "credentials": {},
        "disabled": False,
        "on_error": "STOP_WORKFLOW_ON_ERROR"
    }
    
    # 2. 缺少ID的节点（用于创建时验证）
    nodes["missing_id"] = {
        "name": "Node Without ID",
        "type": "TRIGGER_NODE",
        "subtype": "MANUAL",
        "parameters": {},
        "credentials": {},
        "disabled": False,
        "on_error": "STOP_WORKFLOW_ON_ERROR"
    }
    
    # 3. 缺少名称的节点
    nodes["missing_name"] = {
        "id": "test_node_3",
        "type": "TRIGGER_NODE",
        "subtype": "MANUAL",
        "parameters": {},
        "credentials": {},
        "disabled": False,
        "on_error": "STOP_WORKFLOW_ON_ERROR"
    }
    
    # 4. 缺少类型的节点
    nodes["missing_type"] = {
        "id": "test_node_4",
        "name": "Node Without Type",
        "subtype": "MANUAL",
        "parameters": {},
        "credentials": {},
        "disabled": False,
        "on_error": "STOP_WORKFLOW_ON_ERROR"
    }
    
    # 5. 无效类型的节点
    nodes["invalid_type"] = {
        "id": "test_node_5",
        "name": "Invalid Type Node",
        "type": "INVALID_NODE_TYPE",
        "subtype": "MANUAL",
        "parameters": {},
        "credentials": {},
        "disabled": False,
        "on_error": "STOP_WORKFLOW_ON_ERROR"
    }
    
    # 6. 边界条件：极长参数
    nodes["long_parameters"] = {
        "id": "test_node_6",
        "name": "Long Parameters Node",
        "type": "TRIGGER_NODE",
        "subtype": "MANUAL",
        "parameters": {
            "long_param": "A" * 10000  # 10000个字符的参数
        },
        "credentials": {},
        "disabled": False,
        "on_error": "STOP_WORKFLOW_ON_ERROR"
    }
    
    return nodes


def test_workflow_validation_improved():
    """改进的工作流验证测试"""
    print("=" * 60)
    print("改进的 ValidationService 工作流验证测试")
    print("=" * 60)
    
    validation_service = ValidationService()
    workflows = create_improved_test_workflows()
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": len(workflows)
    }
    
    for workflow_name, workflow_data in workflows.items():
        print(f"\n测试工作流: {workflow_name}")
        print("-" * 40)
        
        start_time = time.time()
        
        # 创建验证请求
        request = ai_system_pb2.ValidateWorkflowRequest(
            workflow_json=json.dumps(workflow_data),
            validation_type="logic"
        )
        
        # 模拟 gRPC 上下文
        class MockContext:
            def set_code(self, code):
                pass
            def set_details(self, details):
                pass
        
        context = MockContext()
        
        # 执行验证
        try:
            response = validation_service.validate_workflow(request, context)
            
            validation_time = time.time() - start_time
            
            print(f"验证结果: {'通过' if response.is_valid else '失败'}")
            print(f"验证时间: {validation_time:.3f}秒")
            
            if response.is_valid:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            if response.errors:
                print("错误信息:")
                for error in response.errors:
                    print(f"  - {error.message}")
            
            if response.warnings:
                print("警告信息:")
                for warning in response.warnings:
                    print(f"  - {warning}")
                    
        except Exception as e:
            results["failed"] += 1
            print(f"验证异常: {str(e)}")
    
    print(f"\n{'='*60}")
    print("工作流验证测试总结")
    print(f"{'='*60}")
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")


def test_node_validation_improved():
    """改进的节点验证测试"""
    print("\n" + "=" * 60)
    print("改进的 ValidationService 节点验证测试")
    print("=" * 60)
    
    validation_service = ValidationService()
    nodes = create_improved_test_nodes()
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": len(nodes)
    }
    
    for node_name, node_data in nodes.items():
        print(f"\n测试节点: {node_name}")
        print("-" * 40)
        
        start_time = time.time()
        
        # 创建测试请求
        request = ai_system_pb2.TestNodeRequest(
            node_json=json.dumps(node_data),
            input_data={"test": "data"}
        )
        
        # 模拟 gRPC 上下文
        class MockContext:
            def set_code(self, code):
                pass
            def set_details(self, details):
                pass
        
        context = MockContext()
        
        # 执行测试
        try:
            response = validation_service.test_node(request, context)
            
            test_time = time.time() - start_time
            
            print(f"测试结果: {'成功' if response.success else '失败'}")
            print(f"测试时间: {test_time:.3f}秒")
            
            if response.success:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            if response.error_message:
                print(f"错误信息: {response.error_message}")
            
            if response.logs:
                print("日志信息:")
                for log in response.logs:
                    print(f"  - {log}")
                    
        except Exception as e:
            results["failed"] += 1
            print(f"测试异常: {str(e)}")
    
    print(f"\n{'='*60}")
    print("节点验证测试总结")
    print(f"{'='*60}")
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")


def performance_test():
    """性能测试"""
    print("\n" + "=" * 60)
    print("ValidationService 性能测试")
    print("=" * 60)
    
    validation_service = ValidationService()
    
    # 创建大型工作流进行性能测试
    large_workflow = {
        "name": "Large Performance Test Workflow",
        "description": "A large workflow for performance testing",
        "nodes": [
            {
                "id": f"node_{i}",
                "name": f"Node {i}",
                "type": "TRIGGER_NODE" if i == 0 else "AI_AGENT_NODE",
                "subtype": "manual" if i == 0 else "router_agent",
                "parameters": {
                    "param1": f"value_{i}",
                    "param2": "A" * 100  # 100个字符的参数
                },
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            }
            for i in range(100)  # 100个节点
        ],
        "connections": {
            "connections": {
                f"Node {i}": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": f"Node {i+1}",
                                    "type": "MAIN",
                                    "index": 0
                                }
                            ]
                        }
                    }
                }
                for i in range(99)  # 99个连接
            }
        }
    }
    
    print("测试大型工作流验证性能...")
    print(f"节点数量: {len(large_workflow['nodes'])}")
    print(f"连接数量: {len(large_workflow['connections']['connections'])}")
    
    # 创建验证请求
    request = ai_system_pb2.ValidateWorkflowRequest(
        workflow_json=json.dumps(large_workflow),
        validation_type="logic"
    )
    
    # 模拟 gRPC 上下文
    class MockContext:
        def set_code(self, code):
            pass
        def set_details(self, details):
            pass
    
    context = MockContext()
    
    # 执行性能测试
    start_time = time.time()
    
    try:
        response = validation_service.validate_workflow(request, context)
        
        end_time = time.time()
        validation_time = end_time - start_time
        
        print(f"验证结果: {'通过' if response.is_valid else '失败'}")
        print(f"验证时间: {validation_time:.3f}秒")
        print(f"平均每节点验证时间: {validation_time/len(large_workflow['nodes'])*1000:.2f}毫秒")
        
        if response.errors:
            print(f"错误数量: {len(response.errors)}")
        
    except Exception as e:
        print(f"性能测试异常: {str(e)}")


def main():
    """主函数"""
    print("开始改进的 ValidationService 测试...")
    
    # 改进的工作流验证测试
    test_workflow_validation_improved()
    
    # 改进的节点验证测试
    test_node_validation_improved()
    
    # 性能测试
    performance_test()
    
    print("\n" + "=" * 60)
    print("改进的测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main() 