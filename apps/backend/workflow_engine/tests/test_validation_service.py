#!/usr/bin/env python3
"""
测试 ValidationService 的各种场景

这个脚本创建各种有问题的workflow，并使用ValidationService来验证，
确保验证逻辑符合预期。
"""

import json
import sys
import os
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workflow_engine.services.validation_service import ValidationService
from proto import ai_system_pb2


def create_test_workflows() -> Dict[str, Dict[str, Any]]:
    """创建各种测试用的workflow"""
    
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
                "subtype": "manual",
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
            },
            {
                "id": "action_1",
                "name": "HTTP Request",
                "type": "ACTION_NODE",
                "subtype": "http_request",
                "parameters": {
                    "url": "https://api.example.com/data",
                    "method": "GET"
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
                },
                "AI Agent": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "HTTP Request",
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
    
    # 2. 缺少节点的工作流
    workflows["empty_workflow"] = {
        "name": "Empty Workflow",
        "description": "A workflow with no nodes",
        "nodes": [],
        "connections": {
            "connections": {}
        }
    }
    
    # 3. 重复节点ID的工作流
    workflows["duplicate_node_id"] = {
        "name": "Duplicate Node ID",
        "description": "A workflow with duplicate node IDs",
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
                "id": "node_1",  # 重复的ID
                "name": "Node 2",
                "type": "AI_AGENT_NODE",
                "subtype": "router_agent",
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
    
    # 4. 重复节点名称的工作流
    workflows["duplicate_node_name"] = {
        "name": "Duplicate Node Name",
        "description": "A workflow with duplicate node names",
        "nodes": [
            {
                "id": "node_1",
                "name": "Same Name",
                "type": "TRIGGER_NODE",
                "subtype": "manual",
                "parameters": {},
                "credentials": {},
                "disabled": False,
                "on_error": "STOP_WORKFLOW_ON_ERROR"
            },
            {
                "id": "node_2",
                "name": "Same Name",  # 重复的名称
                "type": "AI_AGENT_NODE",
                "subtype": "router_agent",
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
    
    # 5. 缺少节点ID的工作流
    workflows["missing_node_id"] = {
        "name": "Missing Node ID",
        "description": "A workflow with nodes missing IDs",
        "nodes": [
            {
                "id": "",  # 空的ID
                "name": "Node 1",
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
    
    # 6. 缺少节点名称的工作流
    workflows["missing_node_name"] = {
        "name": "Missing Node Name",
        "description": "A workflow with nodes missing names",
        "nodes": [
            {
                "id": "node_1",
                "name": "",  # 空的名称
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
    
    # 7. 缺少节点类型的工作流
    workflows["missing_node_type"] = {
        "name": "Missing Node Type",
        "description": "A workflow with nodes missing types",
        "nodes": [
            {
                "id": "node_1",
                "name": "Node 1",
                "type": "",  # 空的类型
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
    
    # 8. 无效节点类型的工作流
    workflows["invalid_node_type"] = {
        "name": "Invalid Node Type",
        "description": "A workflow with invalid node types",
        "nodes": [
            {
                "id": "node_1",
                "name": "Node 1",
                "type": "INVALID_NODE_TYPE",  # 无效的类型
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
    
    # 9. 连接指向不存在节点的工作流
    workflows["invalid_connection"] = {
        "name": "Invalid Connection",
        "description": "A workflow with connections to non-existent nodes",
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
            }
        ],
        "connections": {
            "connections": {
                "Node 1": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "NonExistentNode",  # 不存在的节点
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
    
    # 10. 循环依赖的工作流
    workflows["circular_dependency"] = {
        "name": "Circular Dependency",
        "description": "A workflow with circular dependencies",
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
                                    "node": "Node 1",  # 循环依赖
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
    
    # 11. 无效连接类型的工作流
    workflows["invalid_connection_type"] = {
        "name": "Invalid Connection Type",
        "description": "A workflow with invalid connection types",
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
            }
        ],
        "connections": {
            "connections": {
                "Node 1": {
                    "connection_types": {
                        "invalid_type": {  # 无效的连接类型
                            "connections": [
                                {
                                    "node": "Node 2",
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
    
    # 12. 负索引的连接
    workflows["negative_index"] = {
        "name": "Negative Index",
        "description": "A workflow with negative connection index",
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
                                    "index": -1  # 负索引
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    
    return workflows


def test_workflow_validation():
    """测试工作流验证"""
    print("=" * 60)
    print("测试 ValidationService 工作流验证")
    print("=" * 60)
    
    validation_service = ValidationService()
    workflows = create_test_workflows()
    
    for workflow_name, workflow_data in workflows.items():
        print(f"\n测试工作流: {workflow_name}")
        print("-" * 40)
        
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
            
            print(f"验证结果: {'通过' if response.is_valid else '失败'}")
            
            if response.errors:
                print("错误信息:")
                for error in response.errors:
                    print(f"  - {error.message}")
            
            if response.warnings:
                print("警告信息:")
                for warning in response.warnings:
                    print(f"  - {warning}")
                    
        except Exception as e:
            print(f"验证异常: {str(e)}")


def test_node_validation():
    """测试节点验证"""
    print("\n" + "=" * 60)
    print("测试 ValidationService 节点验证")
    print("=" * 60)
    
    validation_service = ValidationService()
    
    # 测试节点列表
    test_nodes = [
        {
            "name": "Valid Node",
            "type": "TRIGGER_NODE",
            "subtype": "manual",
            "parameters": {},
            "credentials": {}
        },
        {
            "name": "Missing Type",
            "type": "",
            "subtype": "manual",
            "parameters": {},
            "credentials": {}
        },
        {
            "name": "Invalid Type",
            "type": "INVALID_NODE_TYPE",
            "subtype": "manual",
            "parameters": {},
            "credentials": {}
        },
        {
            "name": "",
            "type": "TRIGGER_NODE",
            "subtype": "manual",
            "parameters": {},
            "credentials": {}
        }
    ]
    
    for i, node_data in enumerate(test_nodes, 1):
        print(f"\n测试节点 {i}: {node_data.get('name', 'Unnamed')}")
        print("-" * 40)
        
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
            
            print(f"测试结果: {'成功' if response.success else '失败'}")
            
            if response.error_message:
                print(f"错误信息: {response.error_message}")
            
            if response.logs:
                print("日志信息:")
                for log in response.logs:
                    print(f"  - {log}")
                    
        except Exception as e:
            print(f"测试异常: {str(e)}")


def main():
    """主函数"""
    print("开始测试 ValidationService...")
    
    # 测试工作流验证
    test_workflow_validation()
    
    # 测试节点验证
    test_node_validation()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main() 