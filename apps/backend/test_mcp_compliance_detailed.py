#!/usr/bin/env python3
"""
Detailed test to check MCP compliance in workflow generation.
Shows exactly what parameters are generated and their types.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mcp_compliance():
    """Test that LLM follows MCP ParameterType specifications"""
    import httpx
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get credentials
    api_url = "http://localhost:8000"
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    test_email = os.getenv("TEST_USER_EMAIL", "daming.lu@starmates.ai")
    test_password = os.getenv("TEST_USER_PASSWORD", "test.1234!")
    
    logger.info("=" * 80)
    logger.info("MCP COMPLIANCE TEST - DETAILED PARAMETER ANALYSIS")
    logger.info("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # 1. Authenticate
        logger.info("\n1. Authenticating...")
        auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
        auth_data = {
            "email": test_email,
            "password": test_password
        }
        
        resp = await client.post(auth_url, json=auth_data, headers={"apikey": supabase_anon_key})
        if resp.status_code != 200:
            logger.error(f"Auth failed: {resp.text}")
            return
        auth_result = resp.json()
        access_token = auth_result["access_token"]
        
        logger.info("   ✅ Authenticated successfully")
        
        # 2. Create session
        logger.info("\n2. Creating session...")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        resp = await client.post(f"{api_url}/api/app/sessions", headers=headers)
        if resp.status_code != 200:
            logger.error(f"Session creation failed: {resp.text}")
            return
        session_data = resp.json()
        session_id = session_data["session"]["id"]
        
        logger.info(f"   ✅ Session created: {session_id[:8]}...")
        
        # 3. Generate workflow
        logger.info("\n3. Generating workflow...")
        logger.info("   Request: Create GitHub issue comment workflow")
        
        workflow = None
        async with client.stream(
            "POST",
            f"{api_url}/api/app/chat/stream",
            headers={**headers, "Accept": "text/event-stream"},
            json={
                "session_id": session_id,
                "message": "Create a workflow that comments on GitHub issues when they are created. Use GitHub trigger and webhook action."
            }
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "workflow":
                            workflow = data.get("data", {})
                            break
                    except json.JSONDecodeError:
                        continue
            
            if not workflow:
                logger.error("   ❌ No workflow generated")
                return
            
            logger.info("   ✅ Workflow generated")
            
            # 4. Analyze parameters
            logger.info("\n4. PARAMETER ANALYSIS:")
            logger.info("   " + "=" * 70)
            
            errors = []
            for node in workflow.get("nodes", []):
                node_type = node.get("type", "")
                node_subtype = node.get("subtype", "")
                parameters = node.get("parameters", {})
                
                if parameters:
                    logger.info(f"\n   Node: {node_type}:{node_subtype}")
                    logger.info("   Parameters:")
                    
                    for param_name, param_value in parameters.items():
                        value_type = type(param_value).__name__
                        
                        # Analyze the value
                        issues = []
                        
                        # Check for "mock-" prefix
                        if isinstance(param_value, str) and "mock-" in param_value.lower():
                            issues.append("Contains 'mock-' prefix")
                        
                        # Check for template variables
                        if isinstance(param_value, str) and ("{{" in param_value or "${" in param_value):
                            issues.append("Template variable")
                        
                        # Check for reference objects
                        if isinstance(param_value, dict) and ("$ref" in param_value or "$expr" in param_value):
                            issues.append("Reference object")
                        
                        # Check expected types for known parameters
                        expected_issues = []
                        if "installation_id" in param_name and not isinstance(param_value, int):
                            expected_issues.append(f"Should be integer, got {value_type}")
                        if "number" in param_name and not isinstance(param_value, int):
                            expected_issues.append(f"Should be integer, got {value_type}")
                        if ("enabled" in param_name or "disabled" in param_name) and not isinstance(param_value, bool):
                            expected_issues.append(f"Should be boolean, got {value_type}")
                        
                        # Log the parameter
                        status = "✅"
                        if issues or expected_issues:
                            status = "❌"
                            all_issues = issues + expected_issues
                            errors.append(f"{param_name}: {', '.join(all_issues)}")
                        
                        logger.info(f"     {status} {param_name}: {param_value} (type: {value_type})")
                        if issues or expected_issues:
                            for issue in issues + expected_issues:
                                logger.info(f"        ⚠️  {issue}")
            
            # 5. Summary
            logger.info("\n5. SUMMARY:")
            logger.info("   " + "=" * 70)
            if errors:
                logger.error(f"   ❌ Found {len(errors)} parameter issues:")
                for error in errors:
                    logger.error(f"      - {error}")
            else:
                logger.info("   ✅ All parameters comply with MCP types!")
            
            # Save workflow for inspection
            with open("test_workflow_mcp_detailed.json", "w") as f:
                json.dump(workflow, f, indent=2)
            logger.info(f"\n   💾 Full workflow saved to: test_workflow_mcp_detailed.json")

if __name__ == "__main__":
    asyncio.run(test_mcp_compliance())