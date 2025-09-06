#!/usr/bin/env python3
"""
Fix protobuf import paths
"""

import os
import re


def fix_proto_imports():
    """Fix import paths in generated protobuf files."""

    proto_dir = os.path.join(os.path.dirname(__file__), "workflow_engine", "proto")

    # Files to fix
    files_to_fix = [
        "workflow_service_pb2.py",
        "execution_pb2.py",
        "ai_system_pb2.py",
        "integration_pb2.py",
        "workflow_service_pb2_grpc.py",
    ]

    for filename in files_to_fix:
        filepath = os.path.join(proto_dir, filename)
        if os.path.exists(filepath):
            print(f"Fixing imports in {filename}...")

            with open(filepath, "r") as f:
                content = f.read()

            # 1. 强力修复所有多余的 from . 前缀
            content = re.sub(
                r"(from\s+(?:\.\s*)+)+import", "from . import", content, flags=re.MULTILINE
            )
            # 2. 再修复 from(\s+from\s+\.)+import
            content = re.sub(
                r"from(\s+from\s+\.)+import", "from . import", content, flags=re.MULTILINE
            )
            # 3. 修复 direct import
            content = re.sub(r"import (\w+_pb2) as (\w+__pb2)", r"from . import \1 as \2", content)

            # 终极修复方案
            content = re.sub(r"from(\s+from\s+\.)+import", "from . import", content)

            with open(filepath, "w") as f:
                f.write(content)

            print(f"✅ Fixed {filename}")


if __name__ == "__main__":
    fix_proto_imports()
