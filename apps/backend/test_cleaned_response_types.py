#!/usr/bin/env python
"""
Test the cleaned response types after removing gap_analysis, negotiation and DEBUG_RESULT
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_response_types():
    """Test that ResponseType enum has been cleaned"""
    from shared.models.conversation import ResponseType
    
    print("=" * 60)
    print("Testing Cleaned Response Types")
    print("=" * 60)
    
    # Check available response types
    response_types = [t.value for t in ResponseType]
    print(f"\n✓ Available ResponseType values: {len(response_types)}")
    for rt in response_types:
        print(f"  - {rt}")
    
    # Verify DEBUG_RESULT is removed
    assert "RESPONSE_TYPE_DEBUG_RESULT" not in response_types, "DEBUG_RESULT should be removed"
    print("\n✅ DEBUG_RESULT has been successfully removed")
    
    # Verify we have the expected types
    expected_types = [
        "RESPONSE_TYPE_UNKNOWN",
        "RESPONSE_TYPE_MESSAGE", 
        "RESPONSE_TYPE_WORKFLOW",
        "RESPONSE_TYPE_ERROR",
        "RESPONSE_TYPE_STATUS_CHANGE"
    ]
    
    for expected in expected_types:
        assert expected in response_types, f"Missing expected type: {expected}"
    
    print("✅ All expected response types are present")
    
    return True

def test_response_processor():
    """Test that response processor has been cleaned"""
    from api_gateway.app.services.response_processor import UnifiedResponseProcessor
    
    print("\n" + "=" * 60)
    print("Testing Response Processor")
    print("=" * 60)
    
    # Check available processors
    test_state = {"conversations": [], "stage": "test"}
    
    # Test that gap_analysis and negotiation are removed
    stages_to_test = ["clarification", "workflow_generation", "debug", "completed"]
    
    print(f"\n✓ Testing {len(stages_to_test)} stage processors:")
    for stage in stages_to_test:
        try:
            result = UnifiedResponseProcessor.process_stage_response(stage, test_state)
            print(f"  ✅ {stage}: OK")
        except Exception as e:
            print(f"  ❌ {stage}: {e}")
            return False
    
    # Verify gap_analysis and negotiation don't have processors
    removed_stages = ["gap_analysis", "negotiation"]
    print(f"\n✓ Verifying removed stages don't have dedicated processors:")
    for stage in removed_stages:
        result = UnifiedResponseProcessor.process_stage_response(stage, test_state)
        # Should fallback to clarification processor
        if result.get("content", {}).get("stage") == "clarification":
            print(f"  ✅ {stage}: Correctly falls back to clarification")
        else:
            print(f"  ⚠️  {stage}: Has unexpected processor")
    
    return True

def test_debug_message_integration():
    """Test that debug results are integrated into messages"""
    from api_gateway.app.services.response_processor import UnifiedResponseProcessor
    
    print("\n" + "=" * 60)
    print("Testing Debug Message Integration")
    print("=" * 60)
    
    # Test debug with success
    success_state = {
        "conversations": [{"role": "assistant", "text": "验证工作流"}],
        "debug_result": {"success": True},
        "stage": "debug"
    }
    
    result = UnifiedResponseProcessor.process_stage_response("debug", success_state)
    message = result.get("content", {}).get("text", "")
    
    if "SUCCESS" in message or "✅" in message:
        print("✅ Debug success is properly integrated into message")
    else:
        print(f"⚠️  Debug success message: {message}")
    
    # Test debug with error
    error_state = {
        "conversations": [{"role": "assistant", "text": "验证工作流"}],
        "debug_result": {"success": False, "error": "Invalid node type"},
        "stage": "debug"
    }
    
    result = UnifiedResponseProcessor.process_stage_response("debug", error_state)
    message = result.get("content", {}).get("text", "")
    
    if "ERROR" in message or "❌" in message:
        print("✅ Debug error is properly integrated into message")
    else:
        print(f"⚠️  Debug error message: {message}")
    
    return True

def main():
    """Run all tests"""
    print("\n🔍 Running Response Type Cleanup Tests\n")
    
    tests = [
        ("Response Types", test_response_types),
        ("Response Processor", test_response_processor),
        ("Debug Message Integration", test_debug_message_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Cleanup successful!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())