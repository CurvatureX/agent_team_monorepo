#!/usr/bin/env python3
"""直接检查数据库中的 connections 数据"""

import os
import psycopg2
import json

# 从环境变量获取数据库连接
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/workflow_engine")

# 连接数据库
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# 查询最新的 workflow
cur.execute("""
    SELECT id, name, workflow_data->>'connections' as connections
    FROM workflows
    ORDER BY created_at DESC
    LIMIT 5
""")

print("🔍 数据库中最新的 5 个 Workflow 的 connections 数据：")
print("=" * 80)

for row in cur.fetchall():
    workflow_id, name, connections_json = row
    print(f"\n📋 Workflow: {name}")
    print(f"🆔 ID: {workflow_id}")
    
    if connections_json:
        try:
            connections = json.loads(connections_json)
            print(f"🔗 Connections: {json.dumps(connections, indent=2, ensure_ascii=False)}")
        except:
            print(f"🔗 Connections (raw): {connections_json}")
    else:
        print("🔗 Connections: NULL")
    
    print("-" * 40)

cur.close()
conn.close()