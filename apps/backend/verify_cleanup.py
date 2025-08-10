#!/usr/bin/env python
"""
Simple verification script for the cleanup without dependencies
"""

import os
import re

def check_file_for_removed_items(filepath, patterns, file_desc):
    """Check if file contains removed patterns"""
    if not os.path.exists(filepath):
        print(f"  ⚠️  {file_desc} not found")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    issues = []
    for pattern, desc in patterns:
        if re.search(pattern, content):
            issues.append(desc)
    
    if issues:
        print(f"  ❌ {file_desc} still contains: {', '.join(issues)}")
        return False
    else:
        print(f"  ✅ {file_desc} is clean")
        return True

def main():
    print("=" * 60)
    print("Verifying Response Type Cleanup")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Files to check
    checks = [
        {
            "file": os.path.join(base_dir, "shared/models/conversation.py"),
            "desc": "ResponseType enum",
            "patterns": [
                (r"DEBUG_RESULT", "DEBUG_RESULT type"),
                (r"debug_result.*Field", "debug_result field")
            ]
        },
        {
            "file": os.path.join(base_dir, "api-gateway/app/services/response_processor.py"),
            "desc": "Response Processor",
            "patterns": [
                (r"def _process_gap_analysis", "gap_analysis processor"),
                (r"def _process_negotiation", "negotiation processor"),
                (r'"gap_analysis".*:.*_process', "gap_analysis in processors dict"),
                (r'"negotiation".*:.*_process', "negotiation in processors dict")
            ]
        },
        {
            "file": os.path.join(base_dir, "workflow_agent/services/fastapi_server.py"),
            "desc": "FastAPI Server",
            "patterns": [
                (r"ResponseType\.DEBUG_RESULT", "DEBUG_RESULT usage"),
            ]
        }
    ]
    
    print("\n✓ Checking cleaned files:\n")
    
    all_passed = True
    for check in checks:
        result = check_file_for_removed_items(
            check["file"], 
            check["patterns"],
            check["desc"]
        )
        all_passed = all_passed and result
    
    # Check what ResponseType values exist
    print("\n✓ Current ResponseType values:")
    conv_file = os.path.join(base_dir, "shared/models/conversation.py")
    if os.path.exists(conv_file):
        with open(conv_file, 'r') as f:
            content = f.read()
            # Find all RESPONSE_TYPE_* values
            types = re.findall(r'RESPONSE_TYPE_\w+', content)
            unique_types = sorted(set(types))
            for rt in unique_types:
                print(f"    - {rt}")
    
    # Check debug message handling
    print("\n✓ Debug message handling:")
    processor_file = os.path.join(base_dir, "api-gateway/app/services/response_processor.py")
    if os.path.exists(processor_file):
        with open(processor_file, 'r') as f:
            content = f.read()
            if "✅ SUCCESS" in content and "❌ ERROR" in content:
                print("    ✅ Debug results integrated into messages")
            else:
                print("    ⚠️  Debug message integration not found")
    
    server_file = os.path.join(base_dir, "workflow_agent/services/fastapi_server.py")
    if os.path.exists(server_file):
        with open(server_file, 'r') as f:
            content = f.read()
            if "✅ SUCCESS: 工作流验证通过" in content:
                print("    ✅ Server sends debug as MESSAGE type")
            else:
                print("    ⚠️  Server debug message integration not found")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All cleanup checks passed!")
        print("\nSummary of changes:")
        print("  • Removed gap_analysis and negotiation processors")
        print("  • Removed DEBUG_RESULT response type")
        print("  • Debug results now sent as MESSAGE type")
        print("  • Success/Error status included in message text")
    else:
        print("⚠️  Some cleanup items still remain")
    print("=" * 60)

if __name__ == "__main__":
    main()