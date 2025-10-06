"""
GITHUB External Action Node Specification

GitHub action node for performing GitHub operations including repository management,
issue tracking, pull requests, releases, and workflow automation through GitHub API.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


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
                    "default": "{{$placeholder}}",
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
                # 详细的Issue/PR/文件/发布等配置已简化，改由输入参数提供
                **COMMON_CONFIGS,
            },
            # Parameter schemas (simplified)
            input_params={
                "action_type": {
                    "type": "string",
                    "default": "",
                    "description": "Dynamic action type (overrides configuration action_type)",
                    "required": False,
                    "options": [
                        "create_repository",
                        "update_repository",
                        "delete_repository",
                        "fork_repository",
                        "list_repositories",
                        "create_issue",
                        "update_issue",
                        "close_issue",
                        "reopen_issue",
                        "list_issues",
                        "add_issue_comment",
                        "assign_issue",
                        "add_issue_labels",
                        "create_pull_request",
                        "update_pull_request",
                        "merge_pull_request",
                        "close_pull_request",
                        "list_pull_requests",
                        "request_pr_review",
                        "approve_pr_review",
                        "add_pr_comment",
                        "create_file",
                        "update_file",
                        "delete_file",
                        "get_file_content",
                        "upload_release_asset",
                        "create_release",
                        "update_release",
                        "delete_release",
                        "list_releases",
                        "create_branch",
                        "delete_branch",
                        "list_branches",
                        "protect_branch",
                        "trigger_workflow",
                        "list_workflow_runs",
                        "cancel_workflow_run",
                        "invite_user",
                        "add_team_member",
                        "create_team",
                        "create_webhook",
                        "update_webhook",
                        "delete_webhook",
                    ],
                },
                "owner": {
                    "type": "string",
                    "default": "",
                    "description": "仓库所有者",
                    "required": False,
                },
                "repo": {"type": "string", "default": "", "description": "仓库名", "required": False},
                "title": {
                    "type": "string",
                    "default": "",
                    "description": "标题（Issue/PR/Release）",
                    "required": False,
                },
                "body": {
                    "type": "string",
                    "default": "",
                    "description": "正文（Issue/PR/Release）",
                    "required": False,
                    "multiline": True,
                },
                "labels": {
                    "type": "array",
                    "default": [],
                    "description": "标签（Issue）",
                    "required": False,
                },
                "assignees": {
                    "type": "array",
                    "default": [],
                    "description": "指派用户（Issue）",
                    "required": False,
                },
                "issue_number": {
                    "type": "integer",
                    "default": 0,
                    "description": "Issue编号（评论/更新）",
                    "required": False,
                },
                "pr_number": {
                    "type": "integer",
                    "default": 0,
                    "description": "PR编号（合并/评论）",
                    "required": False,
                },
                "head": {
                    "type": "string",
                    "default": "",
                    "description": "PR来源分支",
                    "required": False,
                },
                "base": {
                    "type": "string",
                    "default": "",
                    "description": "PR目标分支",
                    "required": False,
                },
                "path": {
                    "type": "string",
                    "default": "",
                    "description": "文件路径（文件操作）",
                    "required": False,
                },
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "文件内容（Base64或文本）",
                    "required": False,
                    "multiline": True,
                },
                "branch": {
                    "type": "string",
                    "default": "main",
                    "description": "文件操作的分支",
                    "required": False,
                },
                "commit_message": {
                    "type": "string",
                    "default": "",
                    "description": "提交信息（文件操作）",
                    "required": False,
                },
                "tag_name": {
                    "type": "string",
                    "default": "",
                    "description": "发布标签名",
                    "required": False,
                },
                "workflow_file": {
                    "type": "string",
                    "default": "",
                    "description": "工作流文件路径",
                    "required": False,
                },
                "ref": {
                    "type": "string",
                    "default": "main",
                    "description": "工作流触发分支/标签",
                    "required": False,
                },
                "comment": {
                    "type": "string",
                    "default": "",
                    "description": "评论内容（Issue/PR）",
                    "required": False,
                    "multiline": True,
                },
            },
            output_params={
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether GitHub API operation succeeded",
                    "required": False,
                },
                "github_response": {
                    "type": "object",
                    "default": {},
                    "description": "Parsed GitHub API response",
                    "required": False,
                },
                "resource_id": {
                    "type": "string",
                    "default": "",
                    "description": "Created/affected resource identifier",
                    "required": False,
                },
                "resource_url": {
                    "type": "string",
                    "default": "",
                    "description": "URL to the resource",
                    "required": False,
                },
                "error_message": {
                    "type": "string",
                    "default": "",
                    "description": "Error message if operation failed",
                    "required": False,
                },
                "rate_limit_info": {
                    "type": "object",
                    "default": {},
                    "description": "GitHub rate limit information",
                    "required": False,
                },
                "execution_metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Execution metadata (timings, retries)",
                    "required": False,
                },
            },  # Metadata
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
                    "description": "Create a GitHub issue with labels and assignee",
                    "configurations": {
                        "github_token": "ghp_your_token_here",
                        "action_type": "create_issue",
                    },
                    "input_example": {
                        "owner": "myorg",
                        "repo": "web-app",
                        "title": "🐛 Login button not responding on mobile devices",
                        "body": "## Bug Description\nUsers report that the login button is unresponsive on mobile.\n\n## Steps\n1. Open app on mobile\n2. Go to login\n3. Tap login\n\n## Expected\nLogin form should appear",
                        "labels": ["bug", "high", "needs-triage"],
                        "assignees": ["mobile-team-lead"],
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "resource_url": "https://github.com/myorg/web-app/issues/142",
                        }
                    },
                },
                {
                    "name": "Create Pull Request",
                    "description": "Create a PR from feature branch to main",
                    "configurations": {
                        "github_token": "ghp_your_token_here",
                        "action_type": "create_pull_request",
                    },
                    "input_example": {
                        "owner": "mycompany",
                        "repo": "api-service",
                        "title": "feat: Add user authentication middleware",
                        "body": "Implements JWT-based authentication middleware for API endpoints",
                        "head": "feature/auth-middleware",
                        "base": "develop",
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "resource_url": "https://github.com/mycompany/api-service/pull/78",
                        }
                    },
                },
                {
                    "name": "Create Release",
                    "description": "Create a GitHub release with tag and notes",
                    "configurations": {
                        "github_token": "ghp_your_token_here",
                        "action_type": "create_release",
                    },
                    "input_example": {
                        "owner": "opensource-org",
                        "repo": "awesome-library",
                        "tag_name": "v2.5.0",
                        "title": "Awesome Library v2.5.0 - Performance Boost",
                        "body": "Major performance improvements and new caching system",
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "resource_url": "https://github.com/opensource-org/awesome-library/releases/tag/v2.5.0",
                        }
                    },
                },
                {
                    "name": "Trigger Workflow",
                    "description": "Dispatch a workflow file on main",
                    "configurations": {
                        "github_token": "ghp_your_token_here",
                        "action_type": "trigger_workflow",
                    },
                    "input_example": {
                        "owner": "devops-team",
                        "repo": "production-app",
                        "workflow_file": "deploy.yml",
                        "ref": "main",
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "resource_url": "https://github.com/devops-team/production-app/actions/workflows/deploy.yml",
                        }
                    },
                },
            ],
            # System prompt appendix for AI guidance
            system_prompt_appendix="""Output `action_type` to dynamically control GitHub operations. **If you don't know owner/repo, leave blank - workflow may provide them.**

**All Action Types:**

**Repositories:**
- `create_repository`: New repo - needs name, optional description, private flag
- `update_repository`: Change settings - needs owner, repo, settings dict
- `delete_repository`: Delete repo - needs owner, repo
- `fork_repository`: Fork to your account - needs owner, repo
- `list_repositories`: List repos - optional user filter

**Issues:**
- `create_issue`: New issue - needs owner, repo, title, body, optional labels/assignees
- `update_issue`: Edit issue - needs owner, repo, issue_number, optional title/body
- `close_issue`: Close issue - needs owner, repo, issue_number
- `reopen_issue`: Reopen closed issue - needs owner, repo, issue_number
- `list_issues`: Get issues - needs owner, repo, optional state filter (open/closed/all)
- `add_issue_comment`: Comment on issue - needs owner, repo, issue_number, body
- `assign_issue`: Assign users - needs owner, repo, issue_number, assignees array
- `add_issue_labels`: Tag issue - needs owner, repo, issue_number, labels array

**Pull Requests:**
- `create_pull_request`: New PR - needs owner, repo, title, head (source branch), base (target branch), optional body
- `update_pull_request`: Edit PR - needs owner, repo, pr_number, optional title/body
- `merge_pull_request`: Merge PR - needs owner, repo, pr_number, optional commit_message
- `close_pull_request`: Close without merging - needs owner, repo, pr_number
- `list_pull_requests`: Get PRs - needs owner, repo, optional state
- `request_pr_review`: Request reviews - needs owner, repo, pr_number, reviewers array
- `approve_pr_review`: Approve PR - needs owner, repo, pr_number
- `add_pr_comment`: Comment on PR - needs owner, repo, pr_number, body

**Files:**
- `create_file`: Add file - needs owner, repo, path, content, commit message, optional branch
- `update_file`: Modify file - needs owner, repo, path, content, message, sha (file hash)
- `delete_file`: Remove file - needs owner, repo, path, message, sha
- `get_file_content`: Read file - needs owner, repo, path, optional ref (branch/commit)
- `upload_release_asset`: Attach file to release - needs owner, repo, release_id, file

**Releases:**
- `create_release`: New release - needs owner, repo, tag_name, optional name/body/draft/prerelease flags
- `update_release`: Edit release - needs owner, repo, release_id, optional name/body
- `delete_release`: Remove release - needs owner, repo, release_id
- `list_releases`: Get releases - needs owner, repo

**Branches:**
- `create_branch`: New branch - needs owner, repo, branch name, sha (commit to branch from)
- `delete_branch`: Remove branch - needs owner, repo, branch name
- `list_branches`: Get branches - needs owner, repo
- `protect_branch`: Add protection rules - needs owner, repo, branch, settings

**Workflows:**
- `trigger_workflow`: Run action - needs owner, repo, workflow_id, ref (branch), optional inputs
- `list_workflow_runs`: Get runs - needs owner, repo, optional workflow_id filter
- `cancel_workflow_run`: Stop run - needs owner, repo, run_id

**Organization:**
- `invite_user`: Invite to org - needs org, username
- `add_team_member`: Add to team - needs org, team, username
- `create_team`: New team - needs org, name, optional description

**Webhooks:**
- `create_webhook`: New webhook - needs owner, repo, url, events array
- `update_webhook`: Modify webhook - needs owner, repo, webhook_id, optional url/events
- `delete_webhook`: Remove webhook - needs owner, repo, webhook_id

**Example:**
```json
{"action_type": "create_issue", "owner": "", "repo": "", "title": "Bug: Login fails", "body": "User cannot login with valid credentials", "labels": ["bug", "priority-high"]}
```
""",
        )


# Export the specification instance
GITHUB_EXTERNAL_ACTION_SPEC = GitHubActionSpec()
