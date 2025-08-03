#!/usr/bin/env python3
"""
External APIs Integration Demo
外部API集成演示脚本
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

async def demo_oauth2_flow():
    """演示OAuth2授权流程"""
    print("🔐 OAuth2 Authorization Flow Demo")
    print("=" * 50)
    
    # 1. 用户选择API提供商
    provider = "google_calendar"
    scopes = ["https://www.googleapis.com/auth/calendar"]
    
    print(f"1. User wants to connect {provider}")
    print(f"   Requested scopes: {scopes}")
    
    # 2. 生成授权URL
    auth_request = {
        "provider": provider,
        "scopes": scopes,
        "redirect_url": "https://app.example.com/oauth/callback"
    }
    
    print(f"\n2. Generate authorization URL")
    print(f"   Request: {json.dumps(auth_request, indent=2)}")
    
    # 模拟API响应
    auth_response = {
        "auth_url": f"https://accounts.google.com/oauth/authorize?client_id=mock&scope={','.join(scopes)}&state=mock_state",
        "state": "mock_state_12345",
        "expires_at": "2025-08-02T10:10:00Z",
        "provider": provider
    }
    
    print(f"   Response: {json.dumps(auth_response, indent=2)}")
    
    # 3. 用户授权后的回调
    print(f"\n3. User authorizes and returns with callback")
    callback_params = {
        "code": "auth_code_12345",
        "state": "mock_state_12345",
        "provider": provider
    }
    
    print(f"   Callback params: {json.dumps(callback_params, indent=2)}")
    
    # 4. 交换访问令牌
    token_response = {
        "access_token": "ya29.mock_access_token",
        "refresh_token": "1//04mock_refresh_token",
        "expires_at": "2025-08-02T11:00:00Z",
        "scope": scopes,
        "provider": provider,
        "token_type": "Bearer"
    }
    
    print(f"   Token response: {json.dumps(token_response, indent=2)}")
    print("✅ OAuth2 flow completed successfully!\n")

async def demo_credential_management():
    """演示凭证管理"""
    print("📋 Credential Management Demo")
    print("=" * 50)
    
    # 1. 获取用户凭证列表
    print("1. List user credentials")
    credentials = [
        {
            "provider": "google_calendar",
            "is_valid": True,
            "scope": ["https://www.googleapis.com/auth/calendar"],
            "last_used_at": "2025-08-02T08:00:00Z",
            "expires_at": "2025-09-01T10:00:00Z",
            "created_at": "2025-07-28T10:00:00Z"
        },
        {
            "provider": "github",
            "is_valid": True,
            "scope": ["repo", "user:email"],
            "last_used_at": "2025-08-01T15:00:00Z",
            "expires_at": None,
            "created_at": "2025-07-25T10:00:00Z"
        },
        {
            "provider": "slack",
            "is_valid": False,
            "scope": ["chat:write", "channels:read"],
            "last_used_at": "2025-07-26T12:00:00Z",
            "expires_at": "2025-08-01T10:00:00Z",
            "created_at": "2025-07-20T10:00:00Z"
        }
    ]
    
    print(f"   Found {len(credentials)} credentials:")
    for cred in credentials:
        status = "✅ Valid" if cred["is_valid"] else "❌ Invalid"
        print(f"   - {cred['provider']}: {status}")
    
    # 2. 撤销凭证
    print(f"\n2. Revoke slack credential")
    revoke_response = {
        "success": True,
        "message": "Credential for slack has been revoked successfully",
        "details": {
            "provider": "slack",
            "user_id": "user123",
            "revoked_at": datetime.now().isoformat()
        }
    }
    
    print(f"   Revoke response: {json.dumps(revoke_response, indent=2)}")
    print("✅ Credential management completed!\n")

async def demo_api_testing():
    """演示API测试功能"""
    print("🧪 API Testing Demo")
    print("=" * 50)
    
    # 1. Google Calendar API测试
    print("1. Test Google Calendar API")
    calendar_request = {
        "provider": "google_calendar",
        "operation": "list_events",
        "parameters": {
            "calendar_id": "primary",
            "time_min": "2025-08-01T00:00:00Z",
            "time_max": "2025-08-31T23:59:59Z",
            "max_results": 10
        },
        "timeout_seconds": 30
    }
    
    print(f"   Request: {json.dumps(calendar_request, indent=2)}")
    
    calendar_response = {
        "success": True,
        "provider": "google_calendar",
        "operation": "list_events",
        "execution_time_ms": 245.6,
        "result": {
            "events": [
                {
                    "id": "event123",
                    "summary": "Team Meeting",
                    "start": "2025-08-02T10:00:00Z",
                    "end": "2025-08-02T11:00:00Z"
                },
                {
                    "id": "event124",
                    "summary": "Client Call",
                    "start": "2025-08-02T14:00:00Z",
                    "end": "2025-08-02T15:00:00Z"
                }
            ],
            "total_count": 2
        }
    }
    
    print(f"   Response: {json.dumps(calendar_response, indent=2)}")
    
    # 2. GitHub API测试
    print(f"\n2. Test GitHub API")
    github_request = {
        "provider": "github",
        "operation": "create_issue",
        "parameters": {
            "owner": "myorg",
            "repo": "myrepo",
            "issue": {
                "title": "Bug Report from Workflow",
                "body": "Automatically created issue from workflow execution",
                "labels": ["bug", "workflow"]
            }
        }
    }
    
    print(f"   Request: {json.dumps(github_request, indent=2)}")
    
    github_response = {
        "success": True,
        "provider": "github",
        "operation": "create_issue",
        "execution_time_ms": 189.3,
        "result": {
            "id": 123456,
            "number": 42,
            "title": "Bug Report from Workflow",
            "html_url": "https://github.com/myorg/myrepo/issues/42",
            "state": "open",
            "created_at": "2025-08-02T10:00:00Z"
        }
    }
    
    print(f"   Response: {json.dumps(github_response, indent=2)}")
    
    # 3. Slack API测试
    print(f"\n3. Test Slack API")
    slack_request = {
        "provider": "slack",
        "operation": "send_message",
        "parameters": {
            "channel": "#general",
            "text": "Hello from the workflow engine!",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Workflow completed successfully!* 🎉"
                    }
                }
            ]
        }
    }
    
    print(f"   Request: {json.dumps(slack_request, indent=2)}")
    
    slack_response = {
        "success": True,
        "provider": "slack",
        "operation": "send_message",
        "execution_time_ms": 156.7,
        "result": {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1625097600.000100",
            "message": {
                "text": "Hello from the workflow engine!",
                "user": "U1234567890"
            }
        }
    }
    
    print(f"   Response: {json.dumps(slack_response, indent=2)}")
    print("✅ API testing completed!\n")

async def demo_status_monitoring():
    """演示状态监控"""
    print("📊 Status Monitoring Demo")
    print("=" * 50)
    
    # 1. API状态检查
    print("1. Check API status")
    status_response = {
        "providers": [
            {
                "provider": "google_calendar",
                "available": True,
                "operations": ["list_events", "create_event", "update_event", "delete_event"],
                "last_check": "2025-08-02T10:00:00Z",
                "response_time_ms": 150.5
            },
            {
                "provider": "github",
                "available": True,
                "operations": ["list_repos", "create_issue", "update_issue", "list_prs"],
                "last_check": "2025-08-02T10:00:00Z",
                "response_time_ms": 89.2
            },
            {
                "provider": "slack",
                "available": False,
                "operations": ["send_message", "list_channels", "upload_file"],
                "last_check": "2025-08-02T10:00:00Z",
                "error_message": "Rate limit exceeded"
            }
        ],
        "total_available": 2,
        "last_updated": "2025-08-02T10:00:00Z"
    }
    
    print(f"   Status summary: {status_response['total_available']}/{len(status_response['providers'])} providers available")
    for provider in status_response['providers']:
        status = "🟢 Available" if provider['available'] else "🔴 Unavailable"
        print(f"   - {provider['provider']}: {status}")
        if not provider['available'] and 'error_message' in provider:
            print(f"     Error: {provider['error_message']}")
    
    # 2. 使用指标
    print(f"\n2. Usage metrics (24h)")
    metrics_response = {
        "metrics": [
            {
                "provider": "google_calendar",
                "total_calls": 156,
                "successful_calls": 148,
                "failed_calls": 8,
                "average_response_time_ms": 245.6,
                "last_24h_calls": 23,
                "success_rate": 94.9
            },
            {
                "provider": "github",
                "total_calls": 89,
                "successful_calls": 87,
                "failed_calls": 2,
                "average_response_time_ms": 156.3,
                "last_24h_calls": 12,
                "success_rate": 97.8
            },
            {
                "provider": "slack",
                "total_calls": 234,
                "successful_calls": 198,
                "failed_calls": 36,
                "average_response_time_ms": 189.4,
                "last_24h_calls": 8,
                "success_rate": 84.6
            }
        ],
        "time_range": "24h",
        "generated_at": "2025-08-02T10:00:00Z"
    }
    
    for metric in metrics_response['metrics']:
        print(f"   - {metric['provider']}:")
        print(f"     📞 Calls: {metric['total_calls']} (24h: {metric['last_24h_calls']})")
        print(f"     ✅ Success rate: {metric['success_rate']:.1f}%")
        print(f"     ⏱️  Avg response: {metric['average_response_time_ms']:.1f}ms")
    
    print("✅ Status monitoring completed!\n")

async def demo_workflow_integration():
    """演示工作流集成"""
    print("🔄 Workflow Integration Demo")
    print("=" * 50)
    
    # 演示工作流节点配置
    workflow_nodes = [
        {
            "node_type": "EXTERNAL_ACTION",
            "name": "Create Calendar Event",
            "parameters": {
                "api_service": "google_calendar",
                "operation": "create_event",
                "parameters": {
                    "calendar_id": "primary",
                    "event": {
                        "summary": "{{workflow.input.meeting_title}}",
                        "description": "{{workflow.input.meeting_description}}",
                        "start": {"dateTime": "{{workflow.input.start_time}}"},
                        "end": {"dateTime": "{{workflow.input.end_time}}"},
                        "attendees": [{"email": "{{workflow.input.attendee_email}}"}]
                    }
                }
            }
        },
        {
            "node_type": "EXTERNAL_ACTION",
            "name": "Create GitHub Issue",
            "parameters": {
                "api_service": "github",
                "operation": "create_issue",
                "parameters": {
                    "owner": "{{workflow.config.github_owner}}",
                    "repo": "{{workflow.config.github_repo}}",
                    "issue": {
                        "title": "Meeting Follow-up: {{workflow.input.meeting_title}}",
                        "body": "Created from calendar event: {{nodes.create_calendar_event.output.html_link}}",
                        "labels": ["meeting", "follow-up"]
                    }
                }
            }
        },
        {
            "node_type": "EXTERNAL_ACTION",
            "name": "Send Slack Notification",
            "parameters": {
                "api_service": "slack",
                "operation": "send_message",
                "parameters": {
                    "channel": "#team-updates",
                    "text": "Meeting scheduled and GitHub issue created",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Meeting Scheduled* 📅\n\n*Title:* {{workflow.input.meeting_title}}\n*Time:* {{workflow.input.start_time}}\n*Issue:* {{nodes.create_github_issue.output.html_url}}"
                            }
                        }
                    ]
                }
            }
        }
    ]
    
    print("Workflow with 3 external API integrations:")
    for i, node in enumerate(workflow_nodes, 1):
        print(f"\n{i}. {node['name']} ({node['parameters']['api_service']})")
        print(f"   Operation: {node['parameters']['operation']}")
        print(f"   Configuration: {json.dumps(node['parameters']['parameters'], indent=2)}")
    
    print("\n✅ Workflow integration example completed!\n")

async def main():
    """主演示函数"""
    print("🚀 External APIs Integration Demo")
    print("=" * 80)
    print("This demo showcases the external API integration capabilities")
    print("of the Agent Team Monorepo workflow engine.\n")
    
    # 运行所有演示
    await demo_oauth2_flow()
    await demo_credential_management()
    await demo_api_testing()
    await demo_status_monitoring()
    await demo_workflow_integration()
    
    print("🎉 Demo completed! The external API integration system provides:")
    print("   ✅ OAuth2 authorization flow management")
    print("   ✅ Secure credential storage and management")
    print("   ✅ API testing and validation")
    print("   ✅ Real-time status monitoring")
    print("   ✅ Comprehensive usage metrics")
    print("   ✅ Seamless workflow integration")
    print("\nReady for production use! 🚀")

if __name__ == "__main__":
    asyncio.run(main())