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
        "workflow_service_pb2_grpc.py"
    ]
    
    for filename in files_to_fix:
        filepath = os.path.join(proto_dir, filename)
        if os.path.exists(filepath):
            print(f"Fixing imports in {filename}...")
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Fix various import statement patterns
            # Fix "from . from . from ." patterns (multiple levels)
            content = re.sub(
                r'from \. from \. from \. import',
                'from . import',
                content
            )
            
            # Fix "from . from ." patterns (double levels)
            content = re.sub(
                r'from \. from \. import',
                'from . import',
                content
            )
            
            # Fix direct imports to relative imports
            content = re.sub(
                r'import workflow_pb2 as workflow__pb2',
                'from . import workflow_pb2 as workflow__pb2',
                content
            )
            content = re.sub(
                r'import execution_pb2 as execution__pb2',
                'from . import execution_pb2 as execution__pb2',
                content
            )
            content = re.sub(
                r'import ai_system_pb2 as ai__system__pb2',
                'from . import ai_system_pb2 as ai__system__pb2',
                content
            )
            content = re.sub(
                r'import integration_pb2 as integration__pb2',
                'from . import integration_pb2 as integration__pb2',
                content
            )
            content = re.sub(
                r'import workflow_service_pb2 as workflow__service__pb2',
                'from . import workflow_service_pb2 as workflow__service__pb2',
                content
            )
            
            # Fix any remaining malformed imports
            content = re.sub(
                r'from \. import \. import',
                'from . import',
                content
            )
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            print(f"✅ Fixed {filename}")

if __name__ == "__main__":
    fix_proto_imports() 