#!/usr/bin/env python3
"""
Demonstration script showing the configuration validation and startup checks functionality
"""

import asyncio
import os
import sys
from unittest.mock import patch

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_validator import ConfigValidator, get_missing_env_vars_message
from core.startup_checks import StartupHealthChecker


def demo_config_validation():
    """Demonstrate configuration validation"""
    print("🔧 Configuration Validation Demo")
    print("=" * 50)

    # Demo 1: Valid configuration
    print("\n1. Valid Configuration:")
    with patch("core.config_validator.settings") as mock_settings:
        mock_settings.APP_NAME = "Demo API Gateway"
        mock_settings.MCP_ENABLED = True
        mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = "https://demo.supabase.co"
        mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = "demo-key"
        mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 0.7
        mock_settings.MCP_MAX_RESULTS_PER_TOOL = 50
        mock_settings.WORKFLOW_AGENT_HOST = "localhost"
        mock_settings.WORKFLOW_AGENT_PORT = 50051
        mock_settings.SECRET_KEY = "a-very-secure-secret-key-for-demo-purposes"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
        mock_settings.ELASTICSEARCH_HOST = "elasticsearch.example.com"
        mock_settings.ELASTICSEARCH_PORT = 9200

        validator = ConfigValidator()
        result = validator.validate_all()

        print(f"   ✅ Validation Result: {'PASSED' if result['valid'] else 'FAILED'}")
        print(f"   📊 MCP Enabled: {result['mcp_enabled']}")
        if result["warnings"]:
            print(f"   ⚠️  Warnings: {len(result['warnings'])}")
            for warning in result["warnings"]:
                print(f"      - {warning}")

    # Demo 2: Missing credentials
    print("\n2. Missing Credentials Configuration:")
    try:
        with patch("core.config_validator.settings") as mock_settings:
            mock_settings.APP_NAME = "Demo API Gateway"
            mock_settings.MCP_ENABLED = True
            mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = ""  # Missing
            mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = ""  # Missing
            mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 0.5
            mock_settings.MCP_MAX_RESULTS_PER_TOOL = 100
            mock_settings.WORKFLOW_AGENT_HOST = "localhost"
            mock_settings.WORKFLOW_AGENT_PORT = 50051
            mock_settings.SECRET_KEY = "demo-key"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
            mock_settings.ELASTICSEARCH_HOST = "localhost"
            mock_settings.ELASTICSEARCH_PORT = 9200

            validator = ConfigValidator()
            validator.validate_all()
    except Exception as e:
        print(f"   ❌ Validation Failed: {str(e)[:100]}...")

        # Show helpful error message
        missing_vars = ["NODE_KNOWLEDGE_SUPABASE_URL", "NODE_KNOWLEDGE_SUPABASE_KEY"]
        help_message = get_missing_env_vars_message(missing_vars)
        print(f"\n   💡 Helpful Error Message:")
        print("   " + "\n   ".join(help_message.split("\n")[:8]))  # Show first 8 lines

    # Demo 3: Configuration summary
    print("\n3. Configuration Summary:")
    with patch("core.config_validator.settings") as mock_settings:
        mock_settings.APP_NAME = "Demo API Gateway"
        mock_settings.DEBUG = False
        mock_settings.MCP_ENABLED = True
        mock_settings.MCP_MAX_RESULTS_PER_TOOL = 100
        mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 0.5
        mock_settings.WORKFLOW_AGENT_HOST = "localhost"
        mock_settings.WORKFLOW_AGENT_PORT = 50051
        mock_settings.ELASTICSEARCH_HOST = "elasticsearch.demo.com"
        mock_settings.ELASTICSEARCH_PORT = 9200
        mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
        mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = "https://demo.supabase.co"
        mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = "demo-key"

        validator = ConfigValidator()
        summary = validator.get_configuration_summary()

        print(f"   📋 App Name: {summary['app_name']}")
        print(f"   🔧 Debug Mode: {summary['debug']}")
        print(f"   🤖 MCP Enabled: {summary['mcp_enabled']}")
        print(f"   🌐 CORS Origins: {summary['cors_origins_count']}")
        print(f"   🗄️  Supabase Configured: {summary['supabase_url_configured']}")
        print(f"   🔍 Search Host: {summary['elasticsearch_host']}")


async def demo_startup_checks():
    """Demonstrate startup health checks"""
    print("\n\n🚀 Startup Health Checks Demo")
    print("=" * 50)

    checker = StartupHealthChecker()

    # Demo 1: Successful startup checks
    print("\n1. Successful Startup Checks:")
    with (
        patch.object(checker, "_check_configuration") as mock_config,
        patch.object(checker, "_check_supabase_connection") as mock_supabase,
        patch.object(checker, "_check_node_knowledge_service") as mock_node_knowledge,
        patch("core.startup_checks.settings") as mock_settings,
    ):
        mock_settings.MCP_ENABLED = True

        mock_config.return_value = {
            "healthy": True,
            "status": "passed",
            "message": "Configuration validation successful",
            "warnings": ["Minor warning about CORS"],
        }
        mock_supabase.return_value = {
            "healthy": True,
            "status": "connected",
            "message": "Supabase connection successful",
            "details": {"test_query_results": 5},
        }
        mock_node_knowledge.return_value = {
            "healthy": True,
            "status": "healthy",
            "message": "Node Knowledge service is operational",
            "details": {"total_records": 150},
        }

        result = await checker.run_all_checks()

        print(f"   ✅ Overall Health: {'HEALTHY' if result['healthy'] else 'UNHEALTHY'}")
        print(f"   📊 Total Checks: {len(result['checks'])}")

        for check_name, check_result in result["checks"].items():
            status_emoji = "✅" if check_result.get("healthy") else "❌"
            print(
                f"   {status_emoji} {check_name.replace('_', ' ').title()}: {check_result.get('status', 'unknown')}"
            )
            if check_result.get("details"):
                for key, value in check_result["details"].items():
                    print(f"      - {key}: {value}")

    # Demo 2: MCP disabled scenario
    print("\n2. MCP Disabled Scenario:")
    with (
        patch.object(checker, "_check_configuration") as mock_config,
        patch("core.startup_checks.settings") as mock_settings,
    ):
        mock_settings.MCP_ENABLED = False

        mock_config.return_value = {
            "healthy": True,
            "status": "passed",
            "message": "Configuration validation successful",
        }

        result = await checker.run_all_checks()

        print(f"   ✅ Overall Health: {'HEALTHY' if result['healthy'] else 'UNHEALTHY'}")
        print(f"   📊 MCP Status: DISABLED")

        for check_name, check_result in result["checks"].items():
            if check_result.get("status") == "skipped":
                print(f"   ⏭️  {check_name.replace('_', ' ').title()}: SKIPPED (MCP disabled)")
            else:
                status_emoji = "✅" if check_result.get("healthy") else "❌"
                print(
                    f"   {status_emoji} {check_name.replace('_', ' ').title()}: {check_result.get('status', 'unknown')}"
                )


async def main():
    """Run the demonstration"""
    print("🎯 MCP Service Configuration & Startup Checks Demo")
    print("=" * 60)
    print("This demo shows the configuration validation and startup")
    print("health checks implemented for the MCP service integration.")

    demo_config_validation()
    await demo_startup_checks()

    print("\n" + "=" * 60)
    print("✨ Demo completed! The implementation provides:")
    print("   • Comprehensive configuration validation")
    print("   • Helpful error messages for missing settings")
    print("   • Startup health checks for all services")
    print("   • Graceful handling of disabled features")
    print("   • Detailed logging and monitoring")


if __name__ == "__main__":
    asyncio.run(main())
