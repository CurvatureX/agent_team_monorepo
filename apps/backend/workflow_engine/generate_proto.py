#!/usr/bin/env python3
"""
Generate protobuf files for workflow_engine
"""

import os
import re
import subprocess
import sys

def fix_import_statements(output_dir):
    """Fix import statements in generated protobuf files."""
    print("Fixing import statements...")
    
    # Files to fix
    files_to_fix = [
        "workflow_service_pb2.py",
        "execution_pb2.py", 
        "ai_system_pb2.py",
        "integration_pb2.py",
        "workflow_service_pb2_grpc.py"
    ]
    
    for filename in files_to_fix:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            print(f"  Fixing imports in {filename}...")
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            # 1. 强力修复所有多余的 from . 前缀
            content = re.sub(
                r'(from\s+(?:\.\s*)+)+import',
                'from . import',
                content,
                flags=re.MULTILINE
            )
            # 2. 再修复 from(\s+from\s+\.)+import
            content = re.sub(
                r'from(\s+from\s+\.)+import',
                'from . import',
                content,
                flags=re.MULTILINE
            )
            # 3. 修复 direct import
            content = re.sub(
                r'import (\w+_pb2) as (\w+__pb2)',
                r'from . import \1 as \2',
                content
            )
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            print(f"  ✅ Fixed {filename}")

def generate_proto_files():
    """Generate protobuf files from .proto files."""
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to shared proto files (allow override via environment variable)
    shared_proto_dir = os.environ.get(
        "SHARED_PROTO_DIR",
        os.path.join(current_dir, "..", "shared", "proto", "engine")
    )
    
    # Path to output directory
    output_dir = os.path.join(current_dir, "proto")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # List of proto files to generate
    proto_files = [
        "workflow.proto",
        "execution.proto", 
        "workflow_service.proto",
        "ai_system.proto",
        "integration.proto"
    ]
    
    print(f"Generating protobuf files for workflow_engine...")
    print(f"Shared proto directory: {shared_proto_dir}")
    print(f"Output directory: {output_dir}")
    
    for proto_file in proto_files:
        proto_path = os.path.join(shared_proto_dir, proto_file)
        if os.path.exists(proto_path):
            print(f"Generating {proto_file}...")
            
            # Generate Python files
            cmd = [
                "python", "-m", "grpc_tools.protoc",
                f"--python_out={output_dir}",
                f"--grpc_python_out={output_dir}",
                f"--proto_path={shared_proto_dir}",
                proto_path
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print(f"✅ Generated {proto_file}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to generate {proto_file}: {e}")
                print(f"Error output: {e.stderr}")
                return False
        else:
            print(f"⚠️ Proto file not found: {proto_path}")
    
    # Create __init__.py if it doesn't exist
    init_file = os.path.join(output_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Generated protobuf files\n")
    
    # Fix import statements after generation
    fix_import_statements(output_dir)
    
    print("✅ Protobuf files generated successfully!")
    return True

if __name__ == "__main__":
    success = generate_proto_files()
    sys.exit(0 if success else 1) 