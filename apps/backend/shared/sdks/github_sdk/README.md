# GitHub SDK

A comprehensive Python SDK for GitHub App integration, providing easy access to GitHub API operations including repository management, pull requests, issues, and code manipulation.

## Installation

```bash
cd apps/backend/shared/sdks/github_sdk
pip install -r requirements.txt
```

## Quick Start

```python
from shared.sdks.github_sdk import GitHubSDK

# Initialize the SDK
github = GitHubSDK(
    app_id="your_app_id",
    private_key="path/to/private_key.pem"  # or key content as string
)

# Use the SDK
async with github as client:
    # List repositories
    repos = await client.list_repositories(installation_id)

    # Get a pull request
    pr = await client.get_pull_request(installation_id, "owner/repo", 42)

    # Create a comment
    comment = await client.create_pull_request_comment(
        installation_id, "owner/repo", 42, "Great work! 🎉"
    )
```

## Features

### Repository Operations
- List accessible repositories
- Get repository details
- Read file content
- Create/update files
- Create/delete branches
- Get commit information

### Pull Request Operations
- List, get, create, update pull requests
- Merge pull requests
- Get PR diffs and changed files
- Manage PR comments
- Request reviewers
- Handle draft PRs

### Issue Operations
- List, get, create, update, close issues
- Manage issue comments
- Add/remove labels
- Assign/unassign users
- Handle milestones

### Authentication
- GitHub App JWT token generation
- Installation token management with caching
- Automatic token refresh
- Webhook signature verification

## Usage Examples

### Repository Management

```python
async with GitHubSDK(app_id, private_key) as github:
    # Get file content
    file_content = await github.get_file_content(
        installation_id, "owner/repo", "src/main.py"
    )

    # Create a new branch
    branch = await github.create_branch(
        installation_id, "owner/repo", "feature/new-feature"
    )

    # Update a file
    await github.create_or_update_file(
        installation_id,
        "owner/repo",
        "src/main.py",
        "print('Hello, World!')",
        "Add hello world",
        branch="feature/new-feature"
    )
```

### Pull Request Workflow

```python
async with GitHubSDK(app_id, private_key) as github:
    # Create a pull request
    pr = await github.create_pull_request(
        installation_id,
        "owner/repo",
        title="Add new feature",
        head_branch="feature/new-feature",
        base_branch="main",
        body="This PR adds a new feature..."
    )

    # Add a comment
    await github.create_pull_request_comment(
        installation_id, "owner/repo", pr.number,
        "Please review this implementation."
    )

    # Request reviewers
    await github.request_pull_request_reviewers(
        installation_id, "owner/repo", pr.number,
        reviewers=["reviewer1", "reviewer2"]
    )

    # Get PR diff
    diff = await github.get_pull_request_diff(
        installation_id, "owner/repo", pr.number
    )

    # Merge the PR
    await github.merge_pull_request(
        installation_id, "owner/repo", pr.number,
        merge_method="squash"
    )
```

### Issue Management

```python
async with GitHubSDK(app_id, private_key) as github:
    # Create an issue
    issue = await github.create_issue(
        installation_id, "owner/repo",
        title="Bug report",
        body="Found a bug in the application...",
        labels=["bug", "high-priority"]
    )

    # Add a comment
    await github.create_issue_comment(
        installation_id, "owner/repo", issue.number,
        "I'm investigating this issue."
    )

    # Assign users
    await github.assign_issue(
        installation_id, "owner/repo", issue.number,
        assignees=["developer1"]
    )

    # Close the issue
    await github.close_issue(
        installation_id, "owner/repo", issue.number
    )
```

### Advanced Code Operations

```python
async with GitHubSDK(app_id, private_key) as github:
    # Create a feature branch
    await github.create_branch(
        installation_id, "owner/repo",
        "feature/automated-fix", "main"
    )

    # Read existing file
    file_content = await github.get_file_content(
        installation_id, "owner/repo", "bug_file.py", "main"
    )

    # Apply fix to content
    fixed_content = file_content.content.replace("old_bug", "fixed_code")

    # Update file on feature branch
    await github.create_or_update_file(
        installation_id, "owner/repo",
        "bug_file.py", fixed_content,
        "🤖 Automated bug fix",
        branch="feature/automated-fix",
        sha=file_content.sha
    )

    # Create PR for the fix
    pr = await github.create_pull_request(
        installation_id, "owner/repo",
        title="🤖 Automated Bug Fix",
        head_branch="feature/automated-fix",
        body="This is an automated fix for the reported bug."
    )

    # Add comment with details
    await github.create_pull_request_comment(
        installation_id, "owner/repo", pr.number,
        "This fix was automatically generated by AI workflow analysis."
    )
```

### Webhook Verification

```python
from shared.sdks.github_sdk.auth import GitHubAuth

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    return GitHubAuth.verify_webhook_signature(payload, signature, secret)

# In your webhook handler
@app.post("/webhooks/github")
async def github_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_webhook_signature(payload, signature, webhook_secret):
        raise HTTPException(401, "Invalid signature")

    # Process webhook...
```

## Configuration

### Environment Variables

```bash
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
# OR
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_WEBHOOK_SECRET=your_webhook_secret
```

### Error Handling

The SDK provides specific exception types for different error conditions:

```python
from shared.sdks.github_sdk import (
    GitHubError, GitHubAuthError, GitHubRateLimitError,
    GitHubNotFoundError, GitHubPermissionError
)

try:
    pr = await github.get_pull_request(installation_id, "owner/repo", 999)
except GitHubNotFoundError:
    print("PR not found")
except GitHubRateLimitError as e:
    print(f"Rate limited until: {e.reset_time}")
except GitHubAuthError:
    print("Authentication failed")
except GitHubError as e:
    print(f"GitHub API error: {e.message}")
```

## Node Integration

Use the SDK in workflow nodes:

```python
from shared.sdks.github_sdk import GitHubSDK

class GitHubCreatePRNode:
    async def execute(self, input_data: dict) -> dict:
        github = GitHubSDK(
            app_id=os.getenv("GITHUB_APP_ID"),
            private_key=os.getenv("GITHUB_APP_PRIVATE_KEY")
        )

        async with github:
            pr = await github.create_pull_request(
                installation_id=input_data["installation_id"],
                repo_name=input_data["repository"],
                title=input_data["title"],
                head_branch=input_data["head_branch"],
                base_branch=input_data.get("base_branch", "main"),
                body=input_data.get("body")
            )

            return {
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "success": True
            }
```

## Testing

```python
# Test with development GitHub App
github = GitHubSDK(
    app_id="dev_app_id",
    private_key="dev_private_key"
)

async def test_sdk():
    async with github:
        # Test on your personal repositories
        repos = await github.list_repositories(dev_installation_id)
        print(f"Found {len(repos)} repositories")

        # Test creating a PR
        pr = await github.create_pull_request(
            dev_installation_id,
            "your-username/test-repo",
            title="Test PR from SDK",
            head_branch="test-branch"
        )
        print(f"Created PR: {pr.html_url}")
```

## API Reference

See the individual module documentation:
- `client.py` - Main SDK client and repository operations
- `pulls.py` - Pull request operations
- `issues.py` - Issue operations
- `auth.py` - Authentication and JWT management
- `models.py` - Data models
- `exceptions.py` - Exception classes

## Best Practices

1. **Use async context manager** for automatic client cleanup
2. **Handle rate limits** gracefully with exponential backoff
3. **Cache installation tokens** to avoid unnecessary API calls
4. **Verify webhook signatures** for security
5. **Use specific exception types** for proper error handling
6. **Log API operations** for debugging and monitoring
