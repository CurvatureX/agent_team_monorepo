"""
GITHUB Trigger Node Specification

GitHub webhook trigger for repository events. This trigger has no input ports
and produces execution context when GitHub events occur.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, TriggerSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec


class GitHubTriggerSpec(BaseNodeSpec):
    """GitHub trigger specification for webhook-based repository events."""

    def __init__(self):
        super().__init__(
            type=NodeType.TRIGGER,
            subtype=TriggerSubtype.GITHUB,
            name="GitHub_Trigger",
            description="GitHub webhook trigger for repository events and actions",
            # Configuration parameters
            configurations={
                "repository": {
                    "type": "string",
                    "default": "",
                    "description": "GitHub仓库名称 (owner/repo)",
                    "required": True,
                },
                "events": {
                    "type": "array",
                    "default": ["push", "pull_request"],
                    "description": "监听的GitHub事件类型",
                    "required": True,
                    "options": [
                        "push",
                        "pull_request",
                        "issues",
                        "issue_comment",
                        "pull_request_review",
                        "release",
                        "workflow_run",
                        "repository",
                        "star",
                        "watch",
                        "fork",
                    ],
                },
                "branches": {
                    "type": "array",
                    "default": [],
                    "description": "监听的分支列表（空为所有分支）",
                    "required": False,
                },
                "webhook_secret": {
                    "type": "string",
                    "default": "",
                    "description": "GitHub Webhook密钥",
                    "required": False,
                    "sensitive": True,
                },
                "filter_conditions": {
                    "type": "object",
                    "default": {},
                    "description": "事件过滤条件",
                    "required": False,
                },
                "include_payload": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否包含完整的GitHub负载数据",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={},  # Triggers have no runtime inputs
            output_params={
                "trigger_time": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 time when the webhook was received",
                    "required": False,
                },
                "event_type": {
                    "type": "string",
                    "default": "",
                    "description": "GitHub event type",
                    "required": False,
                    "options": [
                        "push",
                        "pull_request",
                        "issues",
                        "issue_comment",
                        "pull_request_review",
                        "release",
                        "workflow_run",
                        "repository",
                        "star",
                        "watch",
                        "fork",
                    ],
                },
                "repository": {
                    "type": "string",
                    "default": "",
                    "description": "owner/repo for the event",
                    "required": False,
                },
                "sender": {
                    "type": "string",
                    "default": "",
                    "description": "GitHub username of the sender",
                    "required": False,
                },
                "branch": {
                    "type": "string",
                    "default": "",
                    "description": "Branch name if applicable",
                    "required": False,
                },
                "commit_sha": {
                    "type": "string",
                    "default": "",
                    "description": "Commit SHA if applicable",
                    "required": False,
                },
                "trigger_message": {
                    "type": "string",
                    "default": "",
                    "description": "Human-friendly trigger description",
                    "required": False,
                },
                "github_payload": {
                    "type": "object",
                    "default": {},
                    "description": "Raw GitHub webhook payload",
                    "required": False,
                },
            },
            # Port definitions
            input_ports=[],  # Triggers have no input ports
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "GitHub event output with repository and event data",
                    "required": False,
                    "max_connections": -1,
                }
            ],
            # Metadata
            tags=["trigger", "github", "webhook", "repository", "version-control"],
            # Examples
            examples=[
                {
                    "name": "Push Event Trigger",
                    "description": "Trigger on code pushes to main branch",
                    "configurations": {
                        "repository": "myorg/myapp",
                        "events": ["push"],
                        "branches": ["main", "develop"],
                        "webhook_secret": "github_webhook_secret_123",
                        "include_payload": True,
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T14:30:00Z",
                        "execution_id": "github_exec_456",
                        "event_type": "push",
                        "repository": "myorg/myapp",
                        "sender": "developer_alice",
                        "branch": "main",
                        "commit_sha": "a1b2c3d4e5f6",
                        "trigger_message": "Code pushed to main branch by developer_alice",
                        "github_payload": {
                            "ref": "refs/heads/main",
                            "commits": [
                                {
                                    "id": "a1b2c3d4e5f6",
                                    "message": "Fix authentication bug",
                                    "author": {
                                        "name": "Alice Developer",
                                        "email": "alice@example.com",
                                    },
                                }
                            ],
                            "pusher": {"name": "developer_alice"},
                        },
                    },
                },
                {
                    "name": "Pull Request Trigger",
                    "description": "Trigger on pull request events for code review automation",
                    "configurations": {
                        "repository": "myorg/myapp",
                        "events": ["pull_request"],
                        "filter_conditions": {"action": ["opened", "synchronize", "closed"]},
                        "include_payload": True,
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T16:15:00Z",
                        "execution_id": "github_exec_789",
                        "event_type": "pull_request",
                        "repository": "myorg/myapp",
                        "sender": "developer_bob",
                        "branch": "feature/new-api",
                        "commit_sha": "f6e5d4c3b2a1",
                        "trigger_message": "Pull request opened: Add new API endpoints",
                        "github_payload": {
                            "action": "opened",
                            "number": 42,
                            "pull_request": {
                                "title": "Add new API endpoints",
                                "body": "This PR adds new REST API endpoints for user management",
                                "head": {"ref": "feature/new-api", "sha": "f6e5d4c3b2a1"},
                                "base": {"ref": "main"},
                                "user": {"login": "developer_bob"},
                            },
                        },
                    },
                },
                {
                    "name": "Release Trigger",
                    "description": "Trigger on new releases for deployment automation",
                    "configurations": {
                        "repository": "myorg/myapp",
                        "events": ["release"],
                        "filter_conditions": {"action": ["published"]},
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T18:00:00Z",
                        "execution_id": "github_exec_101",
                        "event_type": "release",
                        "repository": "myorg/myapp",
                        "sender": "release_manager",
                        "branch": "main",
                        "commit_sha": "1a2b3c4d5e6f",
                        "trigger_message": "Release v2.1.0 published by release_manager",
                        "github_payload": {
                            "action": "published",
                            "release": {
                                "tag_name": "v2.1.0",
                                "name": "Version 2.1.0",
                                "body": "New features and bug fixes",
                                "prerelease": False,
                                "target_commitish": "main",
                            },
                        },
                    },
                },
                {
                    "name": "Issue Comment Trigger",
                    "description": "Trigger on issue comments for automated responses",
                    "configurations": {
                        "repository": "myorg/myapp",
                        "events": ["issue_comment"],
                        "filter_conditions": {
                            "action": ["created"],
                            "comment_contains": ["/deploy", "/test"],
                        },
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T20:30:00Z",
                        "execution_id": "github_exec_202",
                        "event_type": "issue_comment",
                        "repository": "myorg/myapp",
                        "sender": "developer_charlie",
                        "branch": "",
                        "commit_sha": "",
                        "trigger_message": "Issue comment with /deploy command by developer_charlie",
                        "github_payload": {
                            "action": "created",
                            "issue": {
                                "number": 15,
                                "title": "Deploy to staging environment",
                                "state": "open",
                            },
                            "comment": {
                                "body": "/deploy staging",
                                "user": {"login": "developer_charlie"},
                            },
                        },
                    },
                },
            ],
        )


# Export the specification instance
GITHUB_TRIGGER_SPEC = GitHubTriggerSpec()
