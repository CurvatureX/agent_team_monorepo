#!/usr/bin/env python3
"""Batch update script to replace hardcoded default values with placeholders in MCP specs."""

import os
import re
import sys
from pathlib import Path


def update_mcp_spec_file(file_path: Path):
    """Update a single MCP spec file to use placeholders for sensitive/required fields."""
    print(f"🔧 Processing: {file_path}")

    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # Patterns to replace with {{$placeholder}}
        sensitive_patterns = [
            # API keys and tokens
            (r'"default":\s*"[^"]*token[^"]*"', '"default": "{{$placeholder}}"'),
            (r'"default":\s*"[^"]*key[^"]*"', '"default": "{{$placeholder}}"'),
            (r'"default":\s*"[^"]*secret[^"]*"', '"default": "{{$placeholder}}"'),

            # Specific service patterns
            (r'"default":\s*"https://[^"]*"', '"default": "{{$placeholder}}"'),  # URLs
            (r'"default":\s*"sk-[^"]*"', '"default": "{{$placeholder}}"'),  # OpenAI keys
            (r'"default":\s*"xoxb-[^"]*"', '"default": "{{$placeholder}}"'),  # Slack bot tokens
            (r'"default":\s*"ghp_[^"]*"', '"default": "{{$placeholder}}"'),  # GitHub tokens

            # Common sensitive field names
            (r'"bot_token":\s*{\s*"[^}]*"default":\s*"[^"]*"',
             lambda m: m.group(0).replace('"default": "', '"default": "{{$placeholder}}"').replace('""', '"')),
            (r'"api_key":\s*{\s*"[^}]*"default":\s*"[^"]*"',
             lambda m: m.group(0).replace('"default": "', '"default": "{{$placeholder}}"').replace('""', '"')),
            (r'"access_token":\s*{\s*"[^}]*"default":\s*"[^"]*"',
             lambda m: m.group(0).replace('"default": "', '"default": "{{$placeholder}}"').replace('""', '"')),
        ]

        changes_made = []

        # Apply each pattern
        for pattern, replacement in sensitive_patterns:
            if callable(replacement):
                # For complex replacements using lambda
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, replacement, content)
                    changes_made.extend([f"Updated {len(matches)} complex field(s)"])
            else:
                # For simple string replacements
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, replacement, content)
                    changes_made.extend([f"Replaced: {match}" for match in matches])

        # Special handling for commonly hardcoded values
        hardcoded_replacements = [
            # Common hardcoded values that should be placeholders
            ('"default": ""', '"default": "{{$placeholder}}"',
             lambda line: any(field in line for field in ['token', 'key', 'secret', 'password', 'credential']) and 'required": True' in line),
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines):
            for old_pattern, new_pattern, condition_func in hardcoded_replacements:
                if old_pattern in line and condition_func(line):
                    lines[i] = line.replace(old_pattern, new_pattern)
                    changes_made.append(f"Line {i+1}: {old_pattern} → {new_pattern}")

        content = '\n'.join(lines)

        # Write back if changes were made
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"   ✅ Updated with {len(changes_made)} change(s)")
            for change in changes_made[:3]:  # Show first 3 changes
                print(f"      - {change}")
            if len(changes_made) > 3:
                print(f"      - ... and {len(changes_made) - 3} more")
            return True
        else:
            print(f"   ℹ️  No changes needed")
            return False

    except Exception as e:
        print(f"   ❌ Error processing {file_path}: {str(e)}")
        return False


def main():
    """Main function to process all MCP spec files."""
    print("🚀 Updating MCP specs to use placeholders for sensitive fields...")

    # Find all Python files in node_specs directory
    backend_dir = Path(__file__).parent
    node_specs_dir = backend_dir / "shared" / "node_specs"

    if not node_specs_dir.exists():
        print(f"❌ Node specs directory not found: {node_specs_dir}")
        return False

    python_files = list(node_specs_dir.rglob("*.py"))

    # Filter out __init__.py and base.py files
    spec_files = [f for f in python_files if f.name not in ['__init__.py', 'base.py', 'registry.py']]

    print(f"📁 Found {len(spec_files)} MCP spec files to process")

    updated_count = 0
    for spec_file in spec_files:
        if update_mcp_spec_file(spec_file):
            updated_count += 1

    print(f"\n📊 Summary:")
    print(f"   - Total files processed: {len(spec_files)}")
    print(f"   - Files updated: {updated_count}")
    print(f"   - Files unchanged: {len(spec_files) - updated_count}")

    if updated_count > 0:
        print(f"\n✨ Successfully updated {updated_count} MCP specification files!")
        print(f"💡 All sensitive fields now use {{{{$placeholder}}}} as default values")
    else:
        print(f"\nℹ️  All files were already up to date")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)