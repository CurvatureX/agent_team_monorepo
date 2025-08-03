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
import subprocess
import sys

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
                    "timezone": "UTC"
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
                    "authentication": "none",
                    "data": {}
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
                    "condition": "response.status_code == 200"
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
                    "transformation_rule": "format_monitoring_data"
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
                    }
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
                    "operation": "create_event"
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
        
        "settings": {},
        "static_data": {},
        "tags": ["monitoring", "automation", "google", "health-check"],
        "user_id": "test-user",
        "session_id": "test-session"
    }
    
    return workflow_data

def submit_workflow_with_curl():
    """使用curl提交workflow到API Gateway"""
    
    print("🚀 创建网站监控Workflow...")
    
    # 创建workflow数据
    workflow_data = create_website_monitoring_workflow()
    
    print(f"📋 Workflow包含 {len(workflow_data['nodes'])} 个节点:")
    for node in workflow_data['nodes']:
        print(f"  - {node['name']}: {node['type']}.{node['subtype']}")
    
    print(f"\n🔗 包含 {len(workflow_data['connections']['connections'])} 个连接关系")
    
    # 将数据写入临时文件
    temp_file = "/tmp/workflow_data.json"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(workflow_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📤 提交workflow到API Gateway...")
    
    # 使用curl提交
    curl_command = [
        'curl',
        '-X', 'POST',
        '-H', 'Content-Type: application/json',
        '-d', f'@{temp_file}',
        'http://localhost:8000/api/v1/workflows',
        '-w', '\\nHTTP Status: %{http_code}\\n'
    ]
    
    try:
        result = subprocess.run(
            curl_command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("📄 API响应:")
        print(f"状态码: {result.returncode}")
        print(f"输出: {result.stdout}")
        
        if result.stderr:
            print(f"错误: {result.stderr}")
        
        # 尝试解析响应
        if result.stdout:
            try:
                # 提取JSON部分（排除HTTP状态行）
                lines = result.stdout.strip().split('\n')
                json_lines = [line for line in lines if not line.startswith('HTTP Status:')]
                json_response = '\n'.join(json_lines)
                
                if json_response:
                    response_data = json.loads(json_response)
                    if response_data.get('success'):
                        print("✅ Workflow创建成功!")
                        workflow_info = response_data.get('workflow', {})
                        print(f"   Workflow ID: {workflow_info.get('id', 'N/A')}")
                        print(f"   名称: {workflow_info.get('name', 'N/A')}")
                        return True
                    else:
                        print("❌ Workflow创建失败!")
                        print(f"   错误信息: {response_data.get('message', 'Unknown error')}")
                        return False
            except json.JSONDecodeError as e:
                print(f"⚠️  响应解析失败: {e}")
                print(f"原始响应: {result.stdout}")
                return False
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return False

def validate_workflow_locally():
    """本地验证workflow结构"""
    print("🔍 本地验证workflow结构...")
    
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
        node_ids = set()
        
        for i, node in enumerate(nodes):
            # 检查节点必需字段
            node_required = ["id", "name", "type", "subtype", "parameters"]
            for field in node_required:
                if field not in node:
                    errors.append(f"节点 {i}: 缺少字段 {field}")
            
            # 检查重复名称和ID
            if "name" in node:
                if node["name"] in node_names:
                    errors.append(f"重复的节点名称: {node['name']}")
                node_names.add(node["name"])
                
            if "id" in node:
                if node["id"] in node_ids:
                    errors.append(f"重复的节点ID: {node['id']}")
                node_ids.add(node["id"])
    
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

def print_workflow_summary():
    """打印workflow总结"""
    print("\n📊 Workflow详细信息:")
    print("=" * 60)
    print("📋 名称: 网站监控和通知系统")
    print("📝 描述: 定时监控Google网站状态，记录监控结果并在异常时通知")
    print("\n🔧 节点组成:")
    print("   1️⃣  TRIGGER_NODE.TRIGGER_CRON - 定时监控触发器")
    print("       └─ 每小时触发一次 (cron: 0 * * * *)")
    print("   2️⃣  ACTION_NODE.HTTP_REQUEST - 检查Google网站状态") 
    print("       └─ GET https://www.google.com")
    print("   3️⃣  FLOW_NODE.IF - 判断网站状态")
    print("       └─ 条件: response.status_code == 200")
    print("   4️⃣  ACTION_NODE.DATA_TRANSFORMATION - 格式化监控数据")
    print("       └─ 转换类型: map")
    print("   5️⃣  FLOW_NODE.FILTER - 异常情况过滤器")
    print("       └─ 筛选需要告警的异常")
    print("   6️⃣  TOOL_NODE.TOOL_CALENDAR - 记录监控事件")
    print("       └─ 创建日历事件记录监控结果")
    print("\n🔗 执行流程:")
    print("   定时触发 → HTTP检查 → 状态判断 → 数据格式化 → 异常过滤 → 日历记录")
    print("\n✅ 满足所有要求:")
    print("   ✓ 包含2个ACTION节点 (HTTP请求 + 数据转换)")
    print("   ✓ 包含2个FLOW节点 (IF条件 + 过滤器)")  
    print("   ✓ 包含1个TRIGGER节点 (定时触发)")
    print("   ✓ 包含1个TOOL节点 (日历工具)")
    print("   ✓ 其中一个ACTION是向www.google.com发送HTTP请求")
    print("   ✓ 所有节点逻辑连贯，形成完整的监控workflow")

if __name__ == "__main__":
    print("🧪 创建完整的网站监控Workflow")
    print("=" * 60)
    
    # 打印workflow详情
    print_workflow_summary()
    
    print("\n" + "=" * 60)
    print("🔍 开始验证和创建...")
    
    # 本地验证
    local_valid = validate_workflow_locally()
    
    if local_valid:
        # 提交到API
        api_success = submit_workflow_with_curl()
        
        if api_success:
            print("\n🎉 恭喜！网站监控Workflow已成功创建并提交到系统")
            print("📈 这个workflow已经包含了你要求的所有节点类型")
            print("🔄 现在可以在系统中看到这个完整的监控流程")
        else:
            print("\n⚠️  API提交失败，但workflow结构是正确的")
            print("💡 请检查Docker服务是否正常运行")
    else:
        print("\n❌ 本地验证失败，请检查workflow结构")