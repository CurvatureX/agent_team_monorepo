"""
Direct test of GitHub External Action Node (SDK-only implementation).

This test validates the GitHub External Action runner that strictly follows
the node specification from shared/node_specs/EXTERNAL_ACTION/GITHUB.py.
"""

import asyncio
import json
import os
import sys
import time

# Add backend to path
sys.path.insert(0, "/Users/jingweizhang/Workspace/agent_team_monorepo/apps/backend")

from shared.models import ExecutionStatus, TriggerInfo
from shared.models.workflow import Node
from workflow_engine_v2.core.context import NodeExecutionContext
from workflow_engine_v2.runners.external_actions.github_external_action import GitHubExternalAction

# GitHub App credentials (from https://github.com/apps/starmates)
GITHUB_APP_ID = "1741577"
GITHUB_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAnTl4Q3OvN2HR9esfa/g9+WqAdf7J7NMvxvlCP/JjUkoMhK5c
QG1xaGirfQrmKmryDWO55NsXY8YF0asSxpu6GPpcb1LAjxUVd4zIG4hlwT2lCzp/
IwR9d3KCHLpej7qnkjqDsTWfHbbkwPfIjqmeafQhFoDifQM4+xpkyHM/HrVPW5BO
eHl/VTZ8cQUXqpXRON1yVaHqz4V7YaRMw4u43CoG4S0SrxsVKv1jvXmm8zIJXdNw
4UbNnMX9RAMn0B0rMx3x6Gznm92Cvb5cRfOaRpDE2NrnrVvhBBgSNTLP5dUEtZZR
b6IxuNZfYjEAzkLHnpFfHGoH3GFbU2r5UyVTfQIDAQABAoIBAACHuhUYJcYdCVU3
9sIpcyQNLOO4+TtYNvgHzSZkDduwLjygTeVVuSUt/S4NxFruQ2SyKmVQK9MFTu23
EvgifE0rQvaJI+cXnhvqGJ6nJhixuYXBK76VfErT0wZ/xmPbsEb49Yq6cI/sFvdj
noSEo+kdjqMBykG7qgyGuUJHyTW0S3ajn+Ck/XKSkrDiW4cgeek0K7gupHWK4Nm6
F+pFVozHZMMokj8pXgnJfySfR7mKrMUeI0x/kntFxRuz039vunkONVbdBczQOzZN
D2RgPMNSb+6chJMZtDXeFtfL/DvhzgQrRc/zhhGGX/18wj6NfZd8KkU+dhY9rAuW
pnEqVs0CgYEAz1A/E+GsSDn2xuW9xXLZuUXnuWCnT0glIR4A4EAEkXhD2yJdaiYg
yMyv/0QQiYUIGmBpzneJejk2wiNV56bdQWDvP8FPJ0MUINbwQtIz3ZkBQywPUfVJ
tbM9xvFobzkqrp7RxwrGE3+1Rj5HkmXhbt7sIjzxf0Vf6LAnGRPIAS8CgYEAwiXb
ooflbzcGpMwXWcPkl72UghrJNolNXQnI6AmbDcVEh8aIh0ByiZVI1wPsxHEtDDB8
2B6YR/wsVBCJG/KLUAILfMjebkrZke/BtnxJbBo3LQ68T4AlgF+Qfl15QY1YNa9W
hFe6gKDeeXHQQgdiVnXKlsCBatE0FaqRc5MFUxMCgYAIRaRur6eHLkDpiMs8sKt9
WAu5+uBSKofIvYC9cfB8uXbDrKhbju/p8zjmj5m1UwiSvNwb7+sdZGEJ+Az6dE8J
x8tkGNuGroeEE+98SxTkt7E0M/Lci1QImwFRCdrn7TkFxLKMJaLnrkXWaq/CaKxJ
Fz4G07WzJVqBV14IAyEM4wKBgGrDNMdo4bNJ2B5xmPmk7qS+/Naa8kFKOb/K7K8k
8R4ed7QOae+ucg3UiQysPNw9vF7ynwSdtnIHaz0DJtK2iwOBTF3fe+m8wW4uISE/
sYR/2g2uB8HUH0s7whKrRk3U80f6VqJKN+YaEJ1KCBL3So1vEuvZipF536F2favH
kmr/AoGBALn6p0bg9I3pvhLyhbNKlBbLMwUTljS5Ib1f/2528gzkLYuZtWAK/Suc
C84GG01L2YRDqJs56sBJoPtdkPuGb5g3AfiSrQY++vxjwRD5anIkf3Mb13fZnRSt
j/lLLH97GxA8oL+tW5ziE1+FUBrQMXDgyMRubYBt2CDga7g3oCEh
-----END RSA PRIVATE KEY-----"""

# GitHub App installation ID
GITHUB_INSTALLATION_ID = 80684269  # CurvatureX organization installation

# Test repository
REPO_OWNER = "CurvatureX"
REPO_NAME = "agent_team_monorepo"


def validate_node_spec_output(output_data: dict, operation: str) -> bool:
    """
    Validate that output_data follows the node spec format.

    Required fields per node spec:
    - success: boolean
    - github_response: object
    - resource_id: string
    - resource_url: string
    - error_message: string
    - rate_limit_info: object
    - execution_metadata: object
    """
    required_fields = {
        "success": bool,
        "github_response": (dict, list),
        "resource_id": str,
        "resource_url": str,
        "error_message": str,
        "rate_limit_info": dict,
        "execution_metadata": dict,
    }

    print(f"\n📋 Validating node spec output format for {operation}...")
    all_valid = True

    for field, expected_type in required_fields.items():
        if field not in output_data:
            print(f"  ❌ Missing field: {field}")
            all_valid = False
        elif not isinstance(output_data[field], expected_type):
            print(
                f"  ❌ Wrong type for {field}: expected {expected_type}, got {type(output_data[field])}"
            )
            all_valid = False
        else:
            print(f"  ✅ {field}: {expected_type.__name__}")

    if all_valid:
        print("✅ All node spec output fields validated!")

    return all_valid


async def test_create_issue():
    """Test creating a GitHub issue."""
    print("=" * 70)
    print("🧪 Test 1: Create GitHub Issue (Node Spec Compliant)")
    print("=" * 70)

    # Set environment variables for GitHub App
    os.environ["GITHUB_APP_ID"] = GITHUB_APP_ID
    os.environ["GITHUB_PRIVATE_KEY"] = GITHUB_PRIVATE_KEY

    # Create node following node spec
    node = Node(
        id="github_create_issue_node",
        name="GitHub_Create_Issue",
        description="Create a GitHub issue for testing",
        type="EXTERNAL_ACTION",
        subtype="GITHUB",
        configurations={
            "action_type": "create_issue",
            "installation_id": GITHUB_INSTALLATION_ID,  # Can be provided here
            "repository_config": {
                "owner": REPO_OWNER,
                "repo": REPO_NAME,
            },
        },
        input_params={},  # Defined in node spec
        output_params={},  # Defined in node spec
    )

    # Create trigger info
    trigger = TriggerInfo(
        trigger_type="MANUAL",
        trigger_subtype="MANUAL",
        trigger_data={"test_type": "create_issue"},
        timestamp=int(time.time() * 1000),
    )

    # Create execution context with input_data (per node spec)
    context = NodeExecutionContext(
        node=node,
        input_data={
            # Input params as per node spec
            "owner": REPO_OWNER,
            "repo": REPO_NAME,
            "title": "🧪 SDK-Only Test Issue",
            "body": f"Test issue created by SDK-only GitHub External Action.\n\n**Created at**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "labels": ["automated-test", "sdk-implementation"],
        },
        trigger=trigger,
        metadata={
            "execution_id": "test-exec-gh-001",
            "user_id": "test-user-123",
        },
    )

    print("\n📝 Initializing GitHub External Action (SDK-only)...")
    action = GitHubExternalAction()

    print(f"✅ Using GitHub App ID: {GITHUB_APP_ID}")
    print(f"✅ Installation ID: {GITHUB_INSTALLATION_ID}")
    print(f"✅ Repository: {REPO_OWNER}/{REPO_NAME}")

    # Execute the action
    print("\n🚀 Executing create_issue action...")
    print(f"   Title: {context.input_data['title']}")
    print(f"   Labels: {context.input_data['labels']}")

    try:
        result = await action.execute(context)

        print(f"\n📊 Execution Result:")
        print(f"   Status: {result.status}")
        print(f"   Error Message: {result.error_message or 'None'}")

        # Validate node spec output format
        output_valid = validate_node_spec_output(result.output_data, "create_issue")

        # Display output data
        print(f"\n📄 Output Data (Node Spec Format):")
        print(f"   success: {result.output_data.get('success')}")
        print(f"   resource_id: {result.output_data.get('resource_id')}")
        print(f"   resource_url: {result.output_data.get('resource_url')}")
        print(f"   error_message: {result.output_data.get('error_message') or 'None'}")

        if result.output_data.get("success"):
            github_response = result.output_data.get("github_response", {})
            print(f"\n✅ Issue Created Successfully:")
            print(f"   Issue Number: #{github_response.get('number')}")
            print(f"   Title: {github_response.get('title')}")
            print(f"   State: {github_response.get('state')}")
            print(f"   URL: {result.output_data.get('resource_url')}")

        print("\n" + "=" * 70)
        print(
            f"✅ Test 1 {'PASSED' if output_valid and result.output_data.get('success') else 'FAILED'}"
        )
        print("=" * 70)

        return result.output_data.get("success", False) and output_valid

    except Exception as e:
        print(f"\n❌ Error during execution: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_list_issues():
    """Test listing GitHub issues."""
    print("\n\n" + "=" * 70)
    print("🧪 Test 2: List GitHub Issues (Node Spec Compliant)")
    print("=" * 70)

    os.environ["GITHUB_APP_ID"] = GITHUB_APP_ID
    os.environ["GITHUB_PRIVATE_KEY"] = GITHUB_PRIVATE_KEY

    node = Node(
        id="github_list_issues_node",
        name="GitHub_List_Issues",
        description="List GitHub issues",
        type="EXTERNAL_ACTION",
        subtype="GITHUB",
        configurations={
            "action_type": "list_issues",
            "installation_id": GITHUB_INSTALLATION_ID,
        },
        input_params={},
        output_params={},
    )

    trigger = TriggerInfo(
        trigger_type="MANUAL",
        trigger_subtype="MANUAL",
        trigger_data={"test_type": "list_issues"},
        timestamp=int(time.time() * 1000),
    )

    context = NodeExecutionContext(
        node=node,
        input_data={
            "owner": REPO_OWNER,
            "repo": REPO_NAME,
            "state": "open",
        },
        trigger=trigger,
        metadata={
            "execution_id": "test-exec-gh-002",
            "user_id": "test-user-123",
        },
    )

    print("\n📝 Initializing GitHub External Action...")
    action = GitHubExternalAction()

    print("\n🚀 Executing list_issues action...")

    try:
        result = await action.execute(context)

        print(f"\n📊 Execution Result:")
        print(f"   Status: {result.status}")

        # Validate node spec output
        output_valid = validate_node_spec_output(result.output_data, "list_issues")

        print(f"\n📄 Output Data:")
        print(f"   success: {result.output_data.get('success')}")

        if result.output_data.get("success"):
            github_response = result.output_data.get("github_response", {})
            issues = github_response.get("issues", [])
            print(f"\n✅ Issues Retrieved:")
            print(f"   Count: {github_response.get('count', 0)}")

            if issues:
                print(f"\n   📋 First {min(3, len(issues))} Issues:")
                for i, issue in enumerate(issues[:3], 1):
                    print(f"\n   {i}. #{issue.get('number')} - {issue.get('title')}")
                    print(f"      State: {issue.get('state')}")
                    print(f"      URL: {issue.get('html_url')}")
                    if issue.get("labels"):
                        print(
                            f"      Labels: {', '.join([str(l) for l in issue.get('labels', [])])}"
                        )

        print("\n" + "=" * 70)
        print(
            f"✅ Test 2 {'PASSED' if output_valid and result.output_data.get('success') else 'FAILED'}"
        )
        print("=" * 70)

        return result.output_data.get("success", False) and output_valid

    except Exception as e:
        print(f"\n❌ Error during execution: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_list_repositories():
    """Test listing accessible repositories."""
    print("\n\n" + "=" * 70)
    print("🧪 Test 3: List Repositories (Node Spec Compliant)")
    print("=" * 70)

    os.environ["GITHUB_APP_ID"] = GITHUB_APP_ID
    os.environ["GITHUB_PRIVATE_KEY"] = GITHUB_PRIVATE_KEY

    node = Node(
        id="github_list_repos_node",
        name="GitHub_List_Repos",
        description="List GitHub repositories",
        type="EXTERNAL_ACTION",
        subtype="GITHUB",
        configurations={
            "action_type": "list_repositories",
            "installation_id": GITHUB_INSTALLATION_ID,
        },
        input_params={},
        output_params={},
    )

    trigger = TriggerInfo(
        trigger_type="MANUAL",
        trigger_subtype="MANUAL",
        trigger_data={"test_type": "list_repos"},
        timestamp=int(time.time() * 1000),
    )

    context = NodeExecutionContext(
        node=node,
        input_data={},  # No input params needed for list_repositories
        trigger=trigger,
        metadata={
            "execution_id": "test-exec-gh-003",
            "user_id": "test-user-123",
        },
    )

    print("\n📝 Initializing GitHub External Action...")
    action = GitHubExternalAction()

    print("\n🚀 Executing list_repositories action...")

    try:
        result = await action.execute(context)

        print(f"\n📊 Execution Result:")
        print(f"   Status: {result.status}")

        # Validate node spec output
        output_valid = validate_node_spec_output(result.output_data, "list_repositories")

        print(f"\n📄 Output Data:")
        print(f"   success: {result.output_data.get('success')}")

        if result.output_data.get("success"):
            github_response = result.output_data.get("github_response", {})
            repos = github_response.get("repositories", [])
            print(f"\n✅ Repositories Retrieved:")
            print(f"   Count: {github_response.get('count', 0)}")

            if repos:
                print(f"\n   📋 First {min(5, len(repos))} Repositories:")
                for i, repo in enumerate(repos[:5], 1):
                    print(f"\n   {i}. {repo.get('full_name')}")
                    print(f"      Description: {repo.get('description') or 'N/A'}")
                    print(f"      Private: {repo.get('private')}")
                    print(f"      Default Branch: {repo.get('default_branch')}")

        print("\n" + "=" * 70)
        print(
            f"✅ Test 3 {'PASSED' if output_valid and result.output_data.get('success') else 'FAILED'}"
        )
        print("=" * 70)

        return result.output_data.get("success", False) and output_valid

    except Exception as e:
        print(f"\n❌ Error during execution: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_create_pull_request():
    """Test creating a pull request."""
    print("\n\n" + "=" * 70)
    print("🧪 Test 4: Create Pull Request (Node Spec Compliant)")
    print("=" * 70)

    os.environ["GITHUB_APP_ID"] = GITHUB_APP_ID
    os.environ["GITHUB_PRIVATE_KEY"] = GITHUB_PRIVATE_KEY

    node = Node(
        id="github_create_pr_node",
        name="GitHub_Create_PR",
        description="Create a GitHub pull request",
        type="EXTERNAL_ACTION",
        subtype="GITHUB",
        configurations={
            "action_type": "create_pull_request",
            "installation_id": GITHUB_INSTALLATION_ID,
        },
        input_params={},
        output_params={},
    )

    trigger = TriggerInfo(
        trigger_type="MANUAL",
        trigger_subtype="MANUAL",
        trigger_data={"test_type": "create_pr"},
        timestamp=int(time.time() * 1000),
    )

    # Note: This test requires an existing branch to create a PR from
    # For demo purposes, we'll attempt to create a PR and handle the error gracefully
    context = NodeExecutionContext(
        node=node,
        input_data={
            "owner": REPO_OWNER,
            "repo": REPO_NAME,
            "title": "🧪 SDK Test Pull Request",
            "body": f"Test PR created by SDK-only GitHub External Action.\n\n**Created at**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "head": "test-branch-sdk",  # This branch may not exist
            "base": "main",
        },
        trigger=trigger,
        metadata={
            "execution_id": "test-exec-gh-004",
            "user_id": "test-user-123",
        },
    )

    print("\n📝 Initializing GitHub External Action...")
    action = GitHubExternalAction()

    print("\n🚀 Executing create_pull_request action...")
    print(f"   Title: {context.input_data['title']}")
    print(f"   Head: {context.input_data['head']}")
    print(f"   Base: {context.input_data['base']}")
    print("   Note: This may fail if test branch doesn't exist (expected)")

    try:
        result = await action.execute(context)

        print(f"\n📊 Execution Result:")
        print(f"   Status: {result.status}")

        # Validate node spec output (should work even on error)
        output_valid = validate_node_spec_output(result.output_data, "create_pull_request")

        print(f"\n📄 Output Data:")
        print(f"   success: {result.output_data.get('success')}")
        print(f"   error_message: {result.output_data.get('error_message') or 'None'}")

        if result.output_data.get("success"):
            print(f"   resource_url: {result.output_data.get('resource_url')}")
            print(f"\n✅ PR Created Successfully!")
        else:
            print(f"\n⚠️  PR creation failed (expected if branch doesn't exist)")
            print(f"   This validates proper error handling!")

        print("\n" + "=" * 70)
        print(f"✅ Test 4 {'PASSED' if output_valid else 'FAILED'} (output validation)")
        print("=" * 70)

        return output_valid  # Pass if output format is correct, regardless of success

    except Exception as e:
        print(f"\n❌ Error during execution: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all GitHub External Action tests."""
    print("\n" + "=" * 70)
    print("🚀 GitHub External Action SDK-Only Tests")
    print("   Following Node Spec: shared/node_specs/EXTERNAL_ACTION/GITHUB.py")
    print("=" * 70)
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    print(f"GitHub App ID: {GITHUB_APP_ID}")
    print(f"Installation ID: {GITHUB_INSTALLATION_ID}")
    print("=" * 70)

    results = []

    # Test 1: Create Issue
    results.append(("Create Issue", await test_create_issue()))

    # Test 2: List Issues
    results.append(("List Issues", await test_list_issues()))

    # Test 3: List Repositories
    results.append(("List Repositories", await test_list_repositories()))

    # Test 4: Create Pull Request (may fail, but validates error handling)
    results.append(("Create Pull Request", await test_create_pull_request()))

    # Summary
    print("\n\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, success in results if success)
    total_tests = len(results)
    print(f"\n{total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 All tests passed! SDK-only implementation validated!")
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
