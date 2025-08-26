#!/usr/bin/env python3
"""
手动插入缺失的外部API节点到node_templates表
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# 加载环境变量
env_path = (
    "/Users/bytedance/personal/curvaturex/agent_team_monorepo/apps/backend/workflow_engine/.env"
)
if os.path.exists(env_path):
    load_dotenv(env_path)

# 添加路径
sys.path.append(".")
sys.path.append("/Users/bytedance/personal/curvaturex/agent_team_monorepo/apps/backend")


def insert_google_calendar_node():
    """插入Google Calendar节点"""
    return {
        "template_id": "external_google_calendar",
        "name": "Google Calendar",
        "description": "Interact with Google Calendar API - create, list, update, delete events",
        "category": "integrations",
        "node_type": "EXTERNAL_ACTION_NODE",
        "node_subtype": "GOOGLE_CALENDAR",
        "default_parameters": {
            "action": "list_events",
            "calendar_id": "primary",
            "max_results": "10",
        },
        "required_parameters": ["action"],
        "parameter_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "list_events",
                        "create_event",
                        "update_event",
                        "delete_event",
                        "get_event",
                    ],
                    "description": "Google Calendar action type",
                },
                "calendar_id": {
                    "type": "string",
                    "default": "primary",
                    "description": "Calendar ID",
                },
                "summary": {"type": "string", "description": "Event title/summary"},
                "description": {"type": "string", "description": "Event description"},
                "location": {"type": "string", "description": "Event location"},
                "start_datetime": {
                    "type": "string",
                    "description": "Event start datetime (ISO format)",
                },
                "end_datetime": {
                    "type": "string",
                    "description": "Event end datetime (ISO format)",
                },
                "event_id": {
                    "type": "string",
                    "description": "Event ID for update/delete operations",
                },
                "max_results": {
                    "type": "string",
                    "default": "10",
                    "description": "Maximum number of events to return",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        },
        "is_system_template": True,
    }


def insert_email_node():
    """插入Email节点"""
    return {
        "template_id": "external_email_smtp",
        "name": "Email SMTP",
        "description": "Send emails via SMTP server",
        "category": "integrations",
        "node_type": "EXTERNAL_ACTION_NODE",
        "node_subtype": "EMAIL",
        "default_parameters": {
            "smtp_server": "smtp.gmail.com",
            "port": 587,
            "use_tls": True,
            "content_type": "text/html",
        },
        "required_parameters": ["to", "subject", "body", "smtp_server", "username", "password"],
        "parameter_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Recipient email addresses",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CC email addresses",
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "BCC email addresses",
                },
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body content"},
                "smtp_server": {"type": "string", "description": "SMTP server hostname"},
                "port": {"type": "number", "default": 587, "description": "SMTP server port"},
                "username": {"type": "string", "description": "SMTP username"},
                "password": {
                    "type": "string",
                    "description": "SMTP password (sensitive)",
                    "format": "password",
                },
                "use_tls": {
                    "type": "boolean",
                    "default": True,
                    "description": "Use TLS encryption",
                },
                "content_type": {
                    "type": "string",
                    "enum": ["text/plain", "text/html"],
                    "default": "text/html",
                    "description": "Email content type",
                },
            },
            "required": ["to", "subject", "body", "smtp_server", "username", "password"],
            "additionalProperties": False,
        },
        "is_system_template": True,
    }


def insert_api_call_node():
    """插入API_CALL节点"""
    return {
        "template_id": "external_api_call_generic",
        "name": "Generic API Call",
        "description": "Make generic HTTP API calls to any endpoint",
        "category": "integrations",
        "node_type": "EXTERNAL_ACTION_NODE",
        "node_subtype": "API_CALL",
        "default_parameters": {
            "method": "GET",
            "headers": {},
            "query_params": {},
            "timeout": 30,
            "authentication": "none",
        },
        "required_parameters": ["method", "url"],
        "parameter_schema": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                    "default": "GET",
                    "description": "HTTP method",
                },
                "url": {"type": "string", "format": "uri", "description": "API endpoint URL"},
                "headers": {"type": "object", "default": {}, "description": "HTTP headers"},
                "query_params": {
                    "type": "object",
                    "default": {},
                    "description": "Query parameters",
                },
                "body": {"type": "object", "description": "Request body data"},
                "timeout": {"type": "number", "default": 30, "description": "Timeout in seconds"},
                "authentication": {
                    "type": "string",
                    "enum": ["none", "bearer", "basic", "api_key"],
                    "default": "none",
                    "description": "Authentication method",
                },
                "auth_token": {
                    "type": "string",
                    "description": "Authentication token (when needed)",
                    "format": "password",
                },
                "api_key_header": {
                    "type": "string",
                    "description": "API key header name (for api_key auth)",
                },
            },
            "required": ["method", "url"],
            "additionalProperties": False,
        },
        "is_system_template": True,
    }


def insert_node_to_db(node_data):
    """插入节点到数据库"""
    import uuid

    from sqlalchemy import text

    from workflow_engine.models.database import get_db_session

    with get_db_session() as db:
        # 检查是否已存在
        check_sql = text(
            """
            SELECT COUNT(*) FROM public.node_templates
            WHERE template_id = :template_id
        """
        )

        result = db.execute(check_sql, {"template_id": node_data["template_id"]}).fetchone()

        if result[0] > 0:
            print(f"⚠️ 节点 {node_data['template_id']} 已存在，跳过")
            return False

        # 插入新节点
        insert_sql = text(
            """
            INSERT INTO public.node_templates (
                id, template_id, name, description, category, node_type, node_subtype,
                default_parameters, required_parameters, parameter_schema,
                is_system_template, created_at, updated_at, version, usage_count
            ) VALUES (
                :id, :template_id, :name, :description, :category, :node_type, :node_subtype,
                :default_parameters, :required_parameters, :parameter_schema,
                :is_system_template, :created_at, :updated_at, :version, :usage_count
            )
        """
        )

        params = {
            "id": str(uuid.uuid4()),
            "template_id": node_data["template_id"],
            "name": node_data["name"],
            "description": node_data["description"],
            "category": node_data["category"],
            "node_type": node_data["node_type"],
            "node_subtype": node_data["node_subtype"],
            "default_parameters": json.dumps(node_data["default_parameters"]),
            "required_parameters": node_data["required_parameters"],
            "parameter_schema": json.dumps(node_data["parameter_schema"]),
            "is_system_template": node_data["is_system_template"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "version": "1.0.0",
            "usage_count": 0,
        }

        db.execute(insert_sql, params)
        db.commit()
        print(f"✅ 成功插入节点: {node_data['name']} ({node_data['template_id']})")
        return True


def main():
    """主函数"""
    print("🔧 开始插入缺失的外部API节点...\n")

    nodes_to_insert = [insert_google_calendar_node(), insert_email_node(), insert_api_call_node()]

    success_count = 0

    for node_data in nodes_to_insert:
        try:
            if insert_node_to_db(node_data):
                success_count += 1
        except Exception as e:
            print(f"❌ 插入节点 {node_data['template_id']} 失败: {e}")

    print(f"\n📊 插入结果:")
    print(f"   成功插入: {success_count} 个节点")
    print(f"   总计尝试: {len(nodes_to_insert)} 个节点")

    if success_count == len(nodes_to_insert):
        print(f"\n🎉 所有缺失节点插入成功!")
    else:
        print(f"\n⚠️ 部分节点插入失败，请检查错误信息")

    return success_count > 0


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 插入过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
