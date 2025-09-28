"""
GITHUB External Action Node Specification

GitHub action node for performing GitHub operations including repository management,
issue tracking, pull requests, releases, and workflow automation through GitHub API.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class GitHubActionSpec(BaseNodeSpec):
    """GitHub action specification for GitHub API operations."""

    def __init__(self):
        super().__init__(
            type=NodeType.EXTERNAL_ACTION,
            subtype=ExternalActionSubtype.GITHUB,
            name="GitHub_Action",
            description="Perform GitHub operations including repository management, issues, PRs, and workflow automation",
            # Configuration parameters
            configurations={
                "github_token": {
                    "type": "string",
                    "default": "",
                    "description": "GitHub个人访问令牌",
                    "required": True,
                    "sensitive": True,
                },
                "action_type": {
                    "type": "string",
                    "default": "create_issue",
                    "description": "GitHub操作类型",
                    "required": True,
                    "options": [
                        # Repository Operations
                        "create_repository",  # Create new repository
                        "update_repository",  # Update repository settings
                        "delete_repository",  # Delete repository
                        "fork_repository",  # Fork repository
                        "list_repositories",  # List user/org repositories
                        # Issue Operations
                        "create_issue",  # Create new issue
                        "update_issue",  # Update existing issue
                        "close_issue",  # Close issue
                        "reopen_issue",  # Reopen issue
                        "list_issues",  # List repository issues
                        "add_issue_comment",  # Comment on issue
                        "assign_issue",  # Assign issue to user
                        "add_issue_labels",  # Add labels to issue
                        # Pull Request Operations
                        "create_pull_request",  # Create PR
                        "update_pull_request",  # Update PR
                        "merge_pull_request",  # Merge PR
                        "close_pull_request",  # Close PR
                        "list_pull_requests",  # List PRs
                        "request_pr_review",  # Request PR review
                        "approve_pr_review",  # Approve PR
                        "add_pr_comment",  # Comment on PR
                        # File Operations
                        "create_file",  # Create file in repo
                        "update_file",  # Update file content
                        "delete_file",  # Delete file
                        "get_file_content",  # Read file content
                        "upload_release_asset",  # Upload release asset
                        # Release Operations
                        "create_release",  # Create new release
                        "update_release",  # Update release
                        "delete_release",  # Delete release
                        "list_releases",  # List releases
                        # Branch Operations
                        "create_branch",  # Create branch
                        "delete_branch",  # Delete branch
                        "list_branches",  # List branches
                        "protect_branch",  # Add branch protection
                        # Workflow Operations
                        "trigger_workflow",  # Trigger GitHub Action
                        "list_workflow_runs",  # List workflow runs
                        "cancel_workflow_run",  # Cancel workflow run
                        # Organization Operations
                        "invite_user",  # Invite user to org
                        "add_team_member",  # Add team member
                        "create_team",  # Create team
                        # Webhook Operations
                        "create_webhook",  # Create webhook
                        "update_webhook",  # Update webhook
                        "delete_webhook",  # Delete webhook
                    ],
                },
                "repository_config": {
                    "type": "object",
                    "default": {"owner": "", "repo": "", "full_name": ""},
                    "description": "仓库配置",
                    "required": True,
                },
                "issue_config": {
                    "type": "object",
                    "default": {
                        "title": "",
                        "body": "",
                        "labels": [],
                        "assignees": [],
                        "milestone": None,
                        "issue_number": None,
                    },
                    "description": "Issue配置",
                    "required": False,
                },
                "pull_request_config": {
                    "type": "object",
                    "default": {
                        "title": "",
                        "body": "",
                        "head": "",
                        "base": "main",
                        "draft": False,
                        "reviewers": [],
                        "team_reviewers": [],
                        "pr_number": None,
                    },
                    "description": "Pull Request配置",
                    "required": False,
                },
                "file_config": {
                    "type": "object",
                    "default": {
                        "path": "",
                        "content": "",
                        "message": "",
                        "branch": "main",
                        "sha": "",
                        "encoding": "base64",
                    },
                    "description": "文件操作配置",
                    "required": False,
                },
                "release_config": {
                    "type": "object",
                    "default": {
                        "tag_name": "",
                        "target_commitish": "main",
                        "name": "",
                        "body": "",
                        "draft": False,
                        "prerelease": False,
                        "generate_release_notes": False,
                    },
                    "description": "Release配置",
                    "required": False,
                },
                "branch_config": {
                    "type": "object",
                    "default": {"branch_name": "", "from_branch": "main", "protection_rules": {}},
                    "description": "分支配置",
                    "required": False,
                },
                "workflow_config": {
                    "type": "object",
                    "default": {"workflow_id": "", "ref": "main", "inputs": {}},
                    "description": "工作流配置",
                    "required": False,
                },
                "webhook_config": {
                    "type": "object",
                    "default": {
                        "name": "web",
                        "active": True,
                        "events": ["push"],
                        "config": {"url": "", "content_type": "json", "insecure_ssl": "0"},
                    },
                    "description": "Webhook配置",
                    "required": False,
                },
                "organization_config": {
                    "type": "object",
                    "default": {"org": "", "username": "", "team_slug": "", "role": "member"},
                    "description": "组织配置",
                    "required": False,
                },
                "pagination_config": {
                    "type": "object",
                    "default": {"per_page": 30, "page": 1, "max_pages": 10},
                    "description": "分页配置",
                    "required": False,
                },
                "retry_config": {
                    "type": "object",
                    "default": {"max_retries": 3, "retry_delay": 1, "exponential_backoff": True},
                    "description": "重试配置",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": {}, "context": {}, "variables": {}},
            default_output_params={
                "success": False,
                "github_response": {},
                "resource_id": "",
                "resource_url": "",
                "error_message": "",
                "rate_limit_info": {},
                "execution_metadata": {},
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for GitHub action",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="success",
                    name="success",
                    data_type="dict",
                    description="Output when GitHub action succeeds",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="error",
                    name="error",
                    data_type="dict",
                    description="Output when GitHub action fails",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=[
                "external-action",
                "github",
                "version-control",
                "repository",
                "development",
                "ci-cd",
            ],
            # Examples
            examples=[
                {
                    "name": "Create Bug Report Issue",
                    "description": "Automatically create GitHub issue for bug reports with labels and assignment",
                    "configurations": {
                        "github_token": "ghp_your_token_here",
                        "action_type": "create_issue",
                        "repository_config": {"owner": "{{repo_owner}}", "repo": "{{repo_name}}"},
                        "issue_config": {
                            "title": "🐛 {{bug_title}}",
                            "body": "## Bug Description\\n{{bug_description}}\\n\\n## Steps to Reproduce\\n{{reproduction_steps}}\\n\\n## Expected Behavior\\n{{expected_behavior}}\\n\\n## Actual Behavior\\n{{actual_behavior}}\\n\\n## Environment\\n- OS: {{os}}\\n- Browser: {{browser}}\\n- Version: {{version}}\\n\\n## Additional Context\\n{{additional_context}}\\n\\n---\\n*This issue was automatically generated by the bug reporting system.*",
                            "labels": ["bug", "{{severity}}", "needs-triage"],
                            "assignees": ["{{assigned_developer}}"],
                        },
                    },
                    "input_example": {
                        "data": {
                            "repo_owner": "myorg",
                            "repo_name": "web-app",
                            "bug_title": "Login button not responding on mobile devices",
                            "bug_description": "Users report that the login button is unresponsive when accessed from mobile devices",
                            "reproduction_steps": "1. Open the app on mobile device\\n2. Navigate to login page\\n3. Tap login button\\n4. Nothing happens",
                            "expected_behavior": "Login form should appear",
                            "actual_behavior": "Button appears inactive, no response to touch",
                            "os": "iOS 17.2, Android 14",
                            "browser": "Safari, Chrome Mobile",
                            "version": "v2.1.0",
                            "severity": "high",
                            "assigned_developer": "mobile-team-lead",
                            "additional_context": "Issue affects approximately 40% of mobile users",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "github_response": {
                                "id": 1234567890,
                                "number": 142,
                                "title": "🐛 Login button not responding on mobile devices",
                                "state": "open",
                                "html_url": "https://github.com/myorg/web-app/issues/142",
                                "labels": [
                                    {"name": "bug", "color": "d73a4a"},
                                    {"name": "high", "color": "ff6b6b"},
                                    {"name": "needs-triage", "color": "fbca04"},
                                ],
                                "assignees": [{"login": "mobile-team-lead"}],
                            },
                            "resource_id": "142",
                            "resource_url": "https://github.com/myorg/web-app/issues/142",
                            "execution_metadata": {
                                "action_type": "create_issue",
                                "repository": "myorg/web-app",
                                "labels_applied": 3,
                                "assignees_added": 1,
                                "execution_time_ms": 650,
                            },
                        }
                    },
                },
                {
                    "name": "Create Pull Request for Feature",
                    "description": "Create pull request with reviewers and detailed description",
                    "configurations": {
                        "github_token": "ghp_your_token_here",
                        "action_type": "create_pull_request",
                        "repository_config": {"owner": "{{repo_owner}}", "repo": "{{repo_name}}"},
                        "pull_request_config": {
                            "title": "{{pr_title}}",
                            "body": "## Overview\\n{{pr_description}}\\n\\n## Changes Made\\n{{changes_summary}}\\n\\n## Testing\\n{{testing_notes}}\\n\\n## Screenshots\\n{{screenshots}}\\n\\n## Checklist\\n- [x] Code follows style guidelines\\n- [x] Self-review completed\\n- [x] Tests added/updated\\n- [x] Documentation updated\\n\\n## Related Issues\\nCloses #{{issue_number}}",
                            "head": "{{feature_branch}}",
                            "base": "{{target_branch}}",
                            "draft": "{{is_draft}}",
                            "reviewers": "{{reviewer_list}}",
                            "team_reviewers": "{{team_reviewer_list}}",
                        },
                    },
                    "input_example": {
                        "data": {
                            "repo_owner": "mycompany",
                            "repo_name": "api-service",
                            "pr_title": "feat: Add user authentication middleware",
                            "pr_description": "Implements JWT-based authentication middleware for API endpoints",
                            "changes_summary": "- Added JWT middleware class\\n- Updated route handlers\\n- Added authentication tests\\n- Updated API documentation",
                            "testing_notes": "All existing tests pass. Added 15 new test cases for authentication flows.",
                            "screenshots": "N/A - Backend changes only",
                            "issue_number": "89",
                            "feature_branch": "feature/auth-middleware",
                            "target_branch": "develop",
                            "is_draft": False,
                            "reviewer_list": ["senior-dev-1", "security-lead"],
                            "team_reviewer_list": ["backend-team"],
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "github_response": {
                                "id": 987654321,
                                "number": 78,
                                "title": "feat: Add user authentication middleware",
                                "state": "open",
                                "html_url": "https://github.com/mycompany/api-service/pull/78",
                                "head": {"ref": "feature/auth-middleware"},
                                "base": {"ref": "develop"},
                                "draft": False,
                                "requested_reviewers": [
                                    {"login": "senior-dev-1"},
                                    {"login": "security-lead"},
                                ],
                                "requested_teams": [{"slug": "backend-team"}],
                            },
                            "resource_id": "78",
                            "resource_url": "https://github.com/mycompany/api-service/pull/78",
                            "execution_metadata": {
                                "action_type": "create_pull_request",
                                "repository": "mycompany/api-service",
                                "reviewers_requested": 2,
                                "team_reviewers_requested": 1,
                                "execution_time_ms": 890,
                            },
                        }
                    },
                },
                {
                    "name": "Create Release with Assets",
                    "description": "Create GitHub release with automated release notes and assets",
                    "configurations": {
                        "github_token": "ghp_your_token_here",
                        "action_type": "create_release",
                        "repository_config": {"owner": "{{repo_owner}}", "repo": "{{repo_name}}"},
                        "release_config": {
                            "tag_name": "{{version_tag}}",
                            "target_commitish": "{{release_branch}}",
                            "name": "{{release_name}}",
                            "body": "## What's New in {{version_tag}}\\n\\n{{release_highlights}}\\n\\n## Features\\n{{new_features}}\\n\\n## Bug Fixes\\n{{bug_fixes}}\\n\\n## Breaking Changes\\n{{breaking_changes}}\\n\\n## Installation\\n```bash\\nnpm install {{package_name}}@{{version_tag}}\\n```\\n\\n## Full Changelog\\n{{changelog_url}}",
                            "draft": "{{is_draft}}",
                            "prerelease": "{{is_prerelease}}",
                            "generate_release_notes": True,
                        },
                    },
                    "input_example": {
                        "data": {
                            "repo_owner": "opensource-org",
                            "repo_name": "awesome-library",
                            "version_tag": "v2.5.0",
                            "release_branch": "main",
                            "release_name": "Awesome Library v2.5.0 - Performance Boost",
                            "release_highlights": "Major performance improvements and new caching system",
                            "new_features": "- Advanced caching mechanism\\n- New API endpoints\\n- Improved TypeScript support",
                            "bug_fixes": "- Fixed memory leak in worker threads\\n- Resolved race condition in event handling\\n- Fixed CLI argument parsing",
                            "breaking_changes": "- Minimum Node.js version is now 18\\n- Deprecated `legacyMode` option removed",
                            "package_name": "@awesome/library",
                            "changelog_url": "https://github.com/opensource-org/awesome-library/compare/v2.4.0...v2.5.0",
                            "is_draft": False,
                            "is_prerelease": False,
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "github_response": {
                                "id": 555666777,
                                "tag_name": "v2.5.0",
                                "name": "Awesome Library v2.5.0 - Performance Boost",
                                "html_url": "https://github.com/opensource-org/awesome-library/releases/tag/v2.5.0",
                                "tarball_url": "https://api.github.com/repos/opensource-org/awesome-library/tarball/v2.5.0",
                                "zipball_url": "https://api.github.com/repos/opensource-org/awesome-library/zipball/v2.5.0",
                                "draft": False,
                                "prerelease": False,
                                "published_at": "2025-01-20T15:30:00Z",
                            },
                            "resource_id": "v2.5.0",
                            "resource_url": "https://github.com/opensource-org/awesome-library/releases/tag/v2.5.0",
                            "execution_metadata": {
                                "action_type": "create_release",
                                "repository": "opensource-org/awesome-library",
                                "tag_name": "v2.5.0",
                                "auto_generated_notes": True,
                                "execution_time_ms": 1200,
                            },
                        }
                    },
                },
                {
                    "name": "Trigger Deployment Workflow",
                    "description": "Trigger GitHub Actions workflow for deployment with environment variables",
                    "configurations": {
                        "github_token": "ghp_your_token_here",
                        "action_type": "trigger_workflow",
                        "repository_config": {"owner": "{{repo_owner}}", "repo": "{{repo_name}}"},
                        "workflow_config": {
                            "workflow_id": "{{workflow_file}}",
                            "ref": "{{deployment_ref}}",
                            "inputs": {
                                "environment": "{{target_environment}}",
                                "version": "{{deploy_version}}",
                                "force_deploy": "{{force_flag}}",
                                "notify_slack": "{{slack_notification}}",
                            },
                        },
                    },
                    "input_example": {
                        "data": {
                            "repo_owner": "devops-team",
                            "repo_name": "production-app",
                            "workflow_file": "deploy.yml",
                            "deployment_ref": "main",
                            "target_environment": "production",
                            "deploy_version": "v3.2.1",
                            "force_flag": "false",
                            "slack_notification": "true",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "github_response": {
                                "message": "Workflow dispatch event created",
                                "workflow_dispatch": {
                                    "inputs": {
                                        "environment": "production",
                                        "version": "v3.2.1",
                                        "force_deploy": "false",
                                        "notify_slack": "true",
                                    },
                                    "ref": "main",
                                },
                            },
                            "resource_id": "deploy.yml",
                            "resource_url": "https://github.com/devops-team/production-app/actions/workflows/deploy.yml",
                            "execution_metadata": {
                                "action_type": "trigger_workflow",
                                "repository": "devops-team/production-app",
                                "workflow_id": "deploy.yml",
                                "inputs_provided": 4,
                                "ref": "main",
                                "execution_time_ms": 420,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
GITHUB_EXTERNAL_ACTION_SPEC = GitHubActionSpec()
