#!/usr/bin/env python3
"""
Test script to verify state manager consistency with database schema
验证state管理器与数据库schema的一致性
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from agents.state import (
    WorkflowState,
    WorkflowStage,
    ClarificationContext,
    GapDetail,
    Conversation,
)
from services.state_manager import WorkflowAgentStateManager


def create_test_state() -> WorkflowState:
    """创建一个完整的测试状态"""
    return {
        "session_id": "test-session-123",
        "user_id": "test-user-456",
        "created_at": 1234567890000,
        "updated_at": 1234567890000,
        "stage": WorkflowStage.GAP_ANALYSIS,
        "previous_stage": WorkflowStage.CLARIFICATION,
        "intent_summary": "Create a daily Slack notification workflow",
        "conversations": [
            {
                "role": "user",
                "text": "I need a daily notification system",
                "timestamp": 1234567890000,
            },
            {
                "role": "assistant",
                "text": "I'll help you create a daily notification workflow. What time should it run?",
                "timestamp": 1234567891000,
            }
        ],
        "execution_history": ["clarification", "gap_analysis"],
        "clarification_context": {
            "purpose": "initial_intent",
            "collected_info": {"time": "9am", "channel": "#general"},
            "pending_questions": ["Which days of the week?"],
            "origin": "create"
        },
        "gap_status": "has_gap",
        "identified_gaps": [
            {
                "required_capability": "slack_api",
                "missing_component": "api_key",
                "alternatives": ["webhook", "email"]
            }
        ],
        "current_workflow": {
            "id": "workflow-001",
            "name": "Daily Slack Notification",
            "nodes": [
                {"id": "trigger", "type": "schedule", "config": {"time": "09:00"}},
                {"id": "notify", "type": "slack", "config": {"channel": "#general"}}
            ],
            "connections": [{"from": "trigger", "to": "notify"}]
        },
        "template_workflow": None,
        "workflow_context": {
            "origin": "create",
            "requirements": {
                "platform": "slack",
                "frequency": "daily",
                "time": "9am"
            }
        },
        "debug_result": {
            "success": False,
            "errors": ["Missing Slack API credentials"],
            "warnings": ["Consider adding error handling"],
            "suggestions": ["Add retry logic for failed notifications"],
            "iteration_count": 1,
            "timestamp": 1234567892000
        },
        "debug_loop_count": 1,
        "template_id": None
    }


def test_state_manager():
    """测试state管理器的各项功能"""
    print("🧪 Testing State Manager DB Consistency")
    print("=" * 60)
    
    manager = WorkflowAgentStateManager()
    test_state = create_test_state()
    session_id = test_state["session_id"]
    
    # Test 1: Create state
    print("\n1️⃣ Testing create_state...")
    state_id = manager.create_state(
        session_id=session_id,
        user_id=test_state["user_id"],
        initial_stage="clarification",
        workflow_context=test_state["workflow_context"]
    )
    
    if state_id:
        print(f"✅ State created with ID: {state_id}")
    else:
        print("⚠️ Using mock state (no Supabase connection)")
    
    # Test 2: Save full state
    print("\n2️⃣ Testing save_full_state...")
    success = manager.save_full_state(session_id, test_state)
    
    if success:
        print("✅ Full state saved successfully")
    else:
        print("❌ Failed to save full state")
    
    # Test 3: Retrieve state
    print("\n3️⃣ Testing get_state_by_session...")
    retrieved_state = manager.get_state_by_session(session_id)
    
    if retrieved_state:
        print("✅ State retrieved successfully")
        
        # Verify key fields
        print("\n📋 Verifying key fields:")
        
        fields_to_check = [
            ("session_id", session_id),
            ("user_id", test_state["user_id"]),
            ("stage", test_state["stage"].value if hasattr(test_state["stage"], 'value') else test_state["stage"]),
            ("intent_summary", test_state["intent_summary"]),
            ("gap_status", test_state["gap_status"]),
            ("debug_loop_count", test_state["debug_loop_count"]),
            ("template_id", test_state["template_id"])
        ]
        
        for field_name, expected_value in fields_to_check:
            actual_value = retrieved_state.get(field_name)
            if actual_value == expected_value:
                print(f"  ✅ {field_name}: {actual_value}")
            else:
                print(f"  ❌ {field_name}: expected {expected_value}, got {actual_value}")
        
        # Check JSONB fields
        print("\n📦 Checking JSONB fields:")
        
        jsonb_fields = [
            "conversations",
            "clarification_context",
            "identified_gaps",
            "current_workflow",
            "workflow_context",
            "debug_result"
        ]
        
        for field_name in jsonb_fields:
            if field_name in retrieved_state:
                field_value = retrieved_state[field_name]
                if field_value is not None:
                    if isinstance(field_value, (dict, list)):
                        print(f"  ✅ {field_name}: {type(field_value).__name__} with {len(field_value)} items")
                    else:
                        print(f"  ⚠️ {field_name}: {type(field_value).__name__}")
                else:
                    print(f"  ⚠️ {field_name}: None")
            else:
                print(f"  ❌ {field_name}: Missing")
    else:
        print("❌ Failed to retrieve state")
    
    # Test 4: Update state
    print("\n4️⃣ Testing update_state...")
    updates = {
        "stage": WorkflowStage.DEBUG.value,
        "debug_loop_count": 2,
        "debug_result": {
            "success": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "iteration_count": 2,
            "timestamp": 1234567893000
        }
    }
    
    success = manager.update_state(session_id, updates)
    
    if success:
        print("✅ State updated successfully")
        
        # Verify update
        updated_state = manager.get_state_by_session(session_id)
        if updated_state:
            if updated_state.get("stage") == WorkflowStage.DEBUG.value:
                print("  ✅ Stage updated to DEBUG")
            if updated_state.get("debug_loop_count") == 2:
                print("  ✅ Debug loop count updated to 2")
            if updated_state.get("debug_result", {}).get("success") == True:
                print("  ✅ Debug result updated with success=True")
    else:
        print("❌ Failed to update state")
    
    # Test 5: Clean up
    print("\n5️⃣ Testing delete_state...")
    success = manager.delete_state(session_id)
    
    if success:
        print("✅ State deleted successfully")
    else:
        print("❌ Failed to delete state")
    
    print("\n" + "=" * 60)
    print("✅ State Manager DB Consistency Test Complete!")


if __name__ == "__main__":
    test_state_manager()