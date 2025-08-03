#!/usr/bin/env python3
"""
创建测试Workflow - 网站监控和通知系统

这个workflow的逻辑流程：
1. [TRIGGER] 定时触发器 - 每小时检查一次
2. [ACTION] HTTP请求 - 检查Google网站状态
3. [FLOW] IF条件 - 判断网站是否可访问
4. [ACTION] 数据转换 - 格式化监控数据
5. [FLOW] 过滤器 - 筛选需要通知的异常情况
6. [TOOL] 日历工具 - 记录监控事件到日历

这是一个完整的、逻辑连贯的监控workflow。
"""

import json
import requests

def create_website_monitoring_workflow():
    """创建网站监控workflow"""
    
    workflow_data = {
        "name": "网站监控和通知系统",
        "description": "定时监控Google网站状态，记录监控结果并在异常时通知",
        "nodes": [
            # 1. TRIGGER节点 - 定时触发器
            {
                "id": "cron_trigger_1",
                "name": "定时监控触发器",
                "type": "TRIGGER_NODE",
                "subtype": "TRIGGER_CRON",
                "parameters": {
                    "cron_expression": "0 * * * *",  # 每小时触发一次
                    "timezone": "UTC",
                    "description": "每小时检查网站状态"
                },
                "position": {"x": 100, "y": 100}
            },
            
            # 2. ACTION节点 - HTTP请求检查Google
            {
                "id": "http_check_1", 
                "name": "检查Google网站状态",
                "type": "ACTION_NODE",
                "subtype": "HTTP_REQUEST",
                "parameters": {
                    "method": "GET",
                    "url": "https://www.google.com",
                    "headers": {
                        "User-Agent": "Website-Monitor-Bot/1.0"
                    },
                    "timeout": 10,
                    "retry_attempts": 3,
                    "authentication": "none"
                },
                "position": {"x": 300, "y": 100}
            },
            
            # 3. FLOW节点 - IF条件判断
            {
                "id": "status_check_1",
                "name": "判断网站状态",
                "type": "FLOW_NODE", 
                "subtype": "IF",
                "parameters": {
                    "condition": "response.status_code == 200",
                    "description": "检查HTTP响应状态码是否为200"
                },
                "position": {"x": 500, "y": 100}
            },
            
            # 4. ACTION节点 - 数据转换
            {
                "id": "data_transform_1",
                "name": "格式化监控数据",
                "type": "ACTION_NODE",
                "subtype": "DATA_TRANSFORMATION", 
                "parameters": {
                    "transformation_type": "map",
                    "transformation_rule": "format_monitoring_data",
                    "transformation_config": {
                        "output_format": "json",
                        "include_timestamp": True,
                        "include_response_time": True
                    }
                },
                "position": {"x": 700, "y": 100}
            },
            
            # 5. FLOW节点 - 过滤器
            {
                "id": "alert_filter_1",
                "name": "异常情况过滤器",
                "type": "FLOW_NODE",
                "subtype": "FILTER",
                "parameters": {
                    "filter_condition": {
                        "status": "error",
                        "response_time": ">5000"
                    },
                    "description": "筛选需要发送告警的异常情况"
                },
                "position": {"x": 900, "y": 100}
            },
            
            # 6. TOOL节点 - 日历记录
            {
                "id": "calendar_log_1",
                "name": "记录监控事件",
                "type": "TOOL_NODE",
                "subtype": "TOOL_CALENDAR",
                "parameters": {
                    "calendar_id": "monitoring@company.com",
                    "operation": "create_event",
                    "event_data": {
                        "title": "网站监控报告",
                        "description": "定时网站状态检查结果",
                        "duration": 30
                    }
                },
                "position": {"x": 1100, "y": 100}
            }
        ],
        
        # 连接关系
        "connections": {
            "connections": {
                "定时监控触发器": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "检查Google网站状态",
                                    "index": 0,
                                    "type": "MAIN"
                                }
                            ]
                        }
                    }
                },
                "检查Google网站状态": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "判断网站状态", 
                                    "index": 0,
                                    "type": "MAIN"
                                }
                            ]
                        }
                    }
                },
                "判断网站状态": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "格式化监控数据",
                                    "index": 0, 
                                    "type": "MAIN"
                                }
                            ]
                        }
                    }
                },
                "格式化监控数据": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "异常情况过滤器",
                                    "index": 0,
                                    "type": "MAIN"
                                }
                            ]
                        }
                    }
                },
                "异常情况过滤器": {
                    "connection_types": {
                        "main": {
                            "connections": [
                                {
                                    "node": "记录监控事件",
                                    "index": 0,
                                    "type": "MAIN"
                                }
                            ]
                        }
                    }
                }
            }
        },
        
        "settings": {
            "retry_policy": {
                "max_retries": 3,
                "retry_delay": 5
            },
            "timeout": 300,
            "parallel_execution": False
        },
        
        "static_data": {
            "monitoring_config": {
                "check_interval": "1h",
                "alert_threshold": 5000,
                "notification_channels": ["email", "calendar"]
            }
        },
        
        "tags": ["monitoring", "automation", "google", "health-check"],
        "user_id": "test-user",
        "session_id": "test-session"
    }
    
    return workflow_data

def submit_workflow_to_api():
    """提交workflow到API Gateway"""
    
    print("🚀 创建网站监控Workflow...")
    
    # 创建workflow数据
    workflow_data = create_website_monitoring_workflow()
    
    print(f"📋 Workflow包含 {len(workflow_data['nodes'])} 个节点:")
    for node in workflow_data['nodes']:
        print(f"  - {node['name']}: {node['type']}.{node['subtype']}")
    
    print(f"\n🔗 包含 {len(workflow_data['connections']['connections'])} 个连接关系")
    
    # 提交到API
    api_url = "http://localhost:8000/api/v1/workflows"
    
    try:
        print(f"\n📤 提交workflow到: {api_url}")
        
        response = requests.post(
            api_url,
            json=workflow_data,
            headers={
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Workflow创建成功!")
            print(f"   Workflow ID: {result.get('workflow', {}).get('id', 'N/A')}")
            print(f"   名称: {result.get('workflow', {}).get('name', 'N/A')}")
            return True
            
        else:
            print(f"❌ Workflow创建失败!")
            print(f"   状态码: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 意外错误: {str(e)}")
        return False

def validate_workflow_locally():
    """本地验证workflow结构"""
    print("\n🔍 本地验证workflow结构...")
    
    workflow_data = create_website_monitoring_workflow()
    
    # 基本验证
    errors = []
    
    # 检查必需字段
    required_fields = ["name", "nodes", "connections"]
    for field in required_fields:
        if field not in workflow_data:
            errors.append(f"缺少必需字段: {field}")
    
    # 检查节点
    if "nodes" in workflow_data:
        nodes = workflow_data["nodes"]
        node_names = set()
        
        for i, node in enumerate(nodes):
            # 检查节点必需字段
            node_required = ["id", "name", "type", "subtype", "parameters"]
            for field in node_required:
                if field not in node:
                    errors.append(f"节点 {i}: 缺少字段 {field}")
            
            # 检查重复名称
            if "name" in node:
                if node["name"] in node_names:
                    errors.append(f"重复的节点名称: {node['name']}")
                node_names.add(node["name"])
    
    # 检查连接
    if "connections" in workflow_data and "nodes" in workflow_data:
        connections = workflow_data["connections"]["connections"]
        node_names = {node["name"] for node in workflow_data["nodes"]}
        
        for source, connection_data in connections.items():
            if source not in node_names:
                errors.append(f"连接源节点不存在: {source}")
                
            for conn_type, conn_array in connection_data["connection_types"].items():
                for conn in conn_array["connections"]:
                    if conn["node"] not in node_names:
                        errors.append(f"连接目标节点不存在: {conn['node']}")
    
    if errors:
        print("❌ 验证发现错误:")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("✅ 本地验证通过!")
        return True

if __name__ == "__main__":
    print("🧪 测试Workflow创建 - 网站监控系统")
    print("=" * 60)
    
    # 本地验证
    local_valid = validate_workflow_locally()
    
    if local_valid:
        # 提交到API
        api_success = submit_workflow_to_api()
        
        if api_success:
            print("\n🎉 测试完成! 网站监控Workflow已成功创建")
            print("\n📈 这个workflow包含:")
            print("   ✅ 1个TRIGGER节点 (定时触发)")
            print("   ✅ 2个ACTION节点 (HTTP请求 + 数据转换)")  
            print("   ✅ 2个FLOW节点 (IF条件 + 过滤器)")
            print("   ✅ 1个TOOL节点 (日历记录)")
            print("   ✅ 完整的逻辑连接和数据流")
            print("\n🔄 工作流程:")
            print("   1. 定时触发 → 2. 检查Google → 3. 判断状态")
            print("   4. 格式化数据 → 5. 过滤异常 → 6. 记录到日历")
        else:
            print("\n⚠️  API提交失败，但workflow结构是正确的")
    else:
        print("\n❌ 本地验证失败，请检查workflow结构")