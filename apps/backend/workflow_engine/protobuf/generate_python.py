#!/usr/bin/env python3
"""
Generate Python code from protobuf definitions.

This script generates Python classes from the protobuf files in this directory.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)


def check_protoc():
    """Check if protoc is installed."""
    try:
        result = subprocess.run(
            ["protoc", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(f"Found protoc: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: protoc not found. Please install Protocol Buffers compiler.")
        print("Installation instructions:")
        print("  macOS: brew install protobuf")
        print("  Ubuntu: sudo apt-get install protobuf-compiler")
        print("  Windows: Download from https://github.com/protocolbuffers/protobuf/releases")
        return False


def fix_import_statements(output_dir):
    """Fix import statements in generated protobuf files."""
    print("\nFixing import statements...")
    
    # Files to fix
    files_to_fix = [
        "workflow_service_pb2.py",
        "execution_pb2.py", 
        "ai_system_pb2.py",
        "integration_pb2.py",
        "workflow_service_pb2_grpc.py"
    ]
    
    for filename in files_to_fix:
        filepath = output_dir / filename
        if filepath.exists():
            print(f"  Fixing imports in {filename}...")
            
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
            
            print(f"  ✅ Fixed {filename}")


def generate_python_code():
    """Generate Python code from protobuf files."""
    # Get the current directory (protobuf directory)
    proto_dir = Path(__file__).parent
    
    # Find .proto files in shared/proto/engine directory
    shared_proto_dir = Path("/Users/bytedance/personal/agent_team_monorepo/apps/backend/shared/proto/engine")
    
    if not shared_proto_dir.exists():
        print(f"Error: Shared proto directory not found: {shared_proto_dir}")
        return
    
    # Output directory for generated Python files
    output_dir = proto_dir.parent / "workflow_engine" / "proto"
    output_dir.mkdir(exist_ok=True)
    
    # Create __init__.py in the output directory
    init_file = output_dir / "__init__.py"
    init_file.write_text('"""Generated protobuf modules."""\n')
    
    # Find all .proto files in shared/proto/engine
    proto_files = list(shared_proto_dir.glob("*.proto"))
    
    if not proto_files:
        print("No .proto files found in the shared/proto/engine directory.")
        return
    
    print(f"Found {len(proto_files)} proto files:")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")
    
    # Generate Python code for each proto file
    for proto_file in proto_files:
        print(f"\nGenerating Python code for {proto_file.name}...")
        
        cmd = [
            "protoc",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
            f"--proto_path={shared_proto_dir}",
            str(proto_file)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"✓ Generated Python code for {proto_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to generate Python code for {proto_file.name}")
            print(f"Error: {e}")
    
    print(f"\nPython code generated in: {output_dir}")
    
    # Fix import statements after generation
    fix_import_statements(output_dir)
    
    # List generated files
    generated_files = list(output_dir.glob("*_pb2.py")) + list(output_dir.glob("*_pb2_grpc.py"))
    if generated_files:
        print("\nGenerated files:")
        for file in generated_files:
            print(f"  - {file.name}")


def main():
    """Main function."""
    print("Protocol Buffers Python Code Generator")
    print("=" * 40)
    
    # Check if protoc is installed
    if not check_protoc():
        sys.exit(1)
    
    # Generate Python code
    generate_python_code()
    
    print("\nDone! You can now import the generated modules in your Python code.")
    print("Example:")
    print("  from workflow_engine.proto import workflow_pb2")
    print("  from workflow_engine.proto import workflow_service_pb2_grpc")


if __name__ == "__main__":
    main() 