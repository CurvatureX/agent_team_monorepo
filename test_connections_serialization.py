#!/usr/bin/env python3
"""测试 connections 序列化问题"""

import json
from shared.models.workflow import (
    WorkflowData, NodeData, NodeConnectionsData, 
    ConnectionArrayData, ConnectionData
)

# 测试数据 - 来自请求的 connections
connections_dict = {
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
    }
}

print("🔍 测试 connections 序列化问题")
print("=" * 60)

# 测试1: 直接创建 WorkflowData，传入原始字典
print("\n1️⃣ 测试直接传入字典到 WorkflowData:")
try:
    workflow = WorkflowData(
        name="测试工作流",
        nodes=[
            NodeData(
                id="node1",
                name="节点1",
                type="TRIGGER_NODE",
                position={"x": 100, "y": 100}
            )
        ],
        connections=connections_dict,  # 直接传入字典
        settings={"timeout": 300}
    )
    
    # 序列化为字典
    workflow_dict = workflow.dict()
    print(f"✅ 创建成功!")
    print(f"connections 内容: {json.dumps(workflow_dict['connections'], indent=2, ensure_ascii=False)}")
    
except Exception as e:
    print(f"❌ 错误: {e}")

# 测试2: 先构建 NodeConnectionsData 对象
print("\n2️⃣ 测试构建 NodeConnectionsData 对象:")
try:
    # 手动构建 connections 对象
    connections_obj = {}
    for node_name, conn_data in connections_dict.items():
        node_conn = NodeConnectionsData()
        for conn_type, conn_array_data in conn_data["connection_types"].items():
            conn_array = ConnectionArrayData()
            for conn in conn_array_data["connections"]:
                conn_obj = ConnectionData(
                    node=conn["node"],
                    index=conn["index"],
                    type=conn["type"]
                )
                conn_array.connections.append(conn_obj)
            node_conn.connection_types[conn_type] = conn_array
        connections_obj[node_name] = node_conn
    
    workflow2 = WorkflowData(
        name="测试工作流2",
        nodes=[
            NodeData(
                id="node1",
                name="节点1", 
                type="TRIGGER_NODE",
                position={"x": 100, "y": 100}
            )
        ],
        connections=connections_obj,  # 传入对象
        settings={"timeout": 300}
    )
    
    workflow_dict2 = workflow2.dict()
    print(f"✅ 创建成功!")
    print(f"connections 内容: {json.dumps(workflow_dict2['connections'], indent=2, ensure_ascii=False)}")
    
except Exception as e:
    print(f"❌ 错误: {e}")

# 测试3: 从 JSON 反序列化
print("\n3️⃣ 测试从 JSON 反序列化:")
workflow_json = {
    "name": "测试工作流3",
    "nodes": [{"id": "node1", "name": "节点1", "type": "TRIGGER_NODE", "position": {"x": 100, "y": 100}}],
    "connections": connections_dict,
    "settings": {"timeout": 300}
}

try:
    workflow3 = WorkflowData(**workflow_json)
    workflow_dict3 = workflow3.dict()
    print(f"✅ 反序列化成功!")
    print(f"connections 内容: {json.dumps(workflow_dict3['connections'], indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 60)
print("测试完成!")