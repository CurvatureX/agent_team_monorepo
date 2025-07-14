#!/usr/bin/env python3
"""
Generate Python code from protobuf definitions.

This script generates Python protobuf code from the shared proto files
and places them in the workflow_engine package.
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Define paths
    proto_dir = project_root / "shared" / "proto" / "engine"
    output_dir = script_dir.parent / "workflow_engine" / "proto"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py in proto directory
    init_file = output_dir / "__init__.py"
    init_file.write_text('"""Generated protobuf modules."""\n')
    
    # Find all .proto files
    proto_files = list(proto_dir.glob("*.proto"))
    
    if not proto_files:
        print(f"No .proto files found in {proto_dir}")
        sys.exit(1)
    
    print(f"Found {len(proto_files)} proto files:")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")
    
    # Generate Python code
    cmd = [
        "python", "-m", "grpc_tools.protoc",
        f"--proto_path={proto_dir}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
    ]
    
    # Add all proto files to the command
    for proto_file in proto_files:
        cmd.append(str(proto_file))
    
    print(f"\nRunning command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Protobuf code generation successful!")
        
        # List generated files
        generated_files = list(output_dir.glob("*.py"))
        print(f"\nGenerated {len(generated_files)} Python files:")
        for file in generated_files:
            print(f"  - {file.name}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating protobuf code:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: grpc_tools.protoc not found.")
        print("Please install grpcio-tools: pip install grpcio-tools")
        sys.exit(1)

if __name__ == "__main__":
    main() 