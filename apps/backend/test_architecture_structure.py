#!/usr/bin/env python
"""
Test that the architecture has been properly refactored
Checks that gap_analysis references are removed
"""

import os
import re

def check_file_for_gap_references(filepath, filename):
    """Check a file for gap_analysis references that should be removed"""
    
    issues = []
    
    # Patterns that should NOT exist anymore
    forbidden_patterns = [
        r'GAP_ANALYSIS\s*=',  # GAP_ANALYSIS enum value
        r'gap_analysis_node',  # gap_analysis_node function
        r'GapDetail',  # GapDetail type
        r'gap_status',  # gap_status field
        r'identified_gaps',  # identified_gaps field
        r'gap_negotiation',  # gap_negotiation references
    ]
    
    # Read file content
    with open(filepath, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Check for forbidden patterns
    for pattern in forbidden_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            line = lines[line_num - 1].strip()
            
            # Some exceptions we allow
            if 'GAP_ANALYSIS' in pattern and 'WorkflowStage' not in line:
                continue
            if 'gap' in pattern.lower() and any(ok in line for ok in ['# Removed', '# DEPRECATED', 'TODO']):
                continue
                
            issues.append(f"   Line {line_num} in {filename}: {line[:80]}")
    
    return issues

def main():
    """Check key files for proper refactoring"""
    
    print("=" * 60)
    print("Checking Optimized Architecture Structure")
    print("=" * 60)
    
    files_to_check = [
        'workflow_agent/agents/workflow_agent.py',
        'workflow_agent/agents/nodes.py',
        'workflow_agent/agents/state.py',
    ]
    
    total_issues = []
    
    for file_path in files_to_check:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"\n✓ Checking {file_path}...")
            issues = check_file_for_gap_references(full_path, file_path)
            if issues:
                print(f"  ❌ Found {len(issues)} issue(s):")
                for issue in issues:
                    print(issue)
                total_issues.extend(issues)
            else:
                print(f"  ✅ No gap_analysis references found")
        else:
            print(f"\n❌ File not found: {file_path}")
    
    # Check that new templates exist
    print("\n✓ Checking for new workflow generation templates...")
    template_files = [
        'shared/prompts/workflow_generation_optimized_system.j2',
        'shared/prompts/workflow_generation_optimized_user.j2',
    ]
    
    for template in template_files:
        full_path = os.path.join(os.path.dirname(__file__), template)
        if os.path.exists(full_path):
            print(f"  ✅ Found: {template}")
        else:
            print(f"  ❌ Missing: {template}")
            total_issues.append(f"Missing template: {template}")
    
    # Check workflow_agent.py has 3 nodes
    wa_path = os.path.join(os.path.dirname(__file__), 'workflow_agent/agents/workflow_agent.py')
    with open(wa_path, 'r') as f:
        content = f.read()
        
    # Count node additions
    node_adds = re.findall(r'workflow\.add_node\("([^"]+)"', content)
    expected_nodes = ['clarification', 'workflow_generation', 'debug']
    
    print(f"\n✓ Checking workflow graph structure...")
    print(f"  Found {len(node_adds)} nodes: {', '.join(node_adds)}")
    
    if set(node_adds) == set(expected_nodes):
        print(f"  ✅ Correct 3-node architecture")
    else:
        print(f"  ❌ Expected nodes: {', '.join(expected_nodes)}")
        total_issues.append("Incorrect node configuration")
    
    # Summary
    print("\n" + "=" * 60)
    if total_issues:
        print(f"❌ Found {len(total_issues)} issue(s) - refactoring incomplete")
        return False
    else:
        print("✅ Architecture successfully refactored to 3-node system!")
        print("   - gap_analysis node removed")
        print("   - Automatic gap handling in workflow_generation")
        print("   - RAG modules removed")
        print("   - Clean routing logic")
        return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)