#!/usr/bin/env python3
"""
Script to generate gRPC Python files from protobuf definitions for the Workflow Engine.
"""
import subprocess
import sys
from pathlib import Path
import os
import argparse


def generate_grpc_files(proto_path, output_dir):
    """Generate gRPC Python files from proto definitions"""
    
    proto_dir = Path(proto_path)
    output_path = Path(output_dir)

    # Create output directory
    output_path.mkdir(exist_ok=True, parents=True)

    # Create __init__.py file
    (output_path / "__init__.py").touch()
    
    # Recursively find all .proto files to be robust
    proto_files = list(proto_dir.glob('**/*.proto'))

    if not proto_files:
        print(f"No .proto files found in {proto_dir}", file=sys.stderr)
        sys.exit(1)
        
    print(f"Found {len(proto_files)} .proto files in {proto_dir}")

    print(f"Generating gRPC files from {proto_dir} into {output_path}...")
    
    # CRITICAL FIX: Pass the full relative path from the CWD to protoc for each file.
    # The --proto_path is used for resolving imports between them.
    proto_filenames = [str(p) for p in proto_files]
    
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_path}",
        f"--python_out={output_path}",
        f"--grpc_python_out={output_path}",
    ] + proto_filenames

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        print(f"Error generating gRPC files:", file=sys.stderr)
        print(result.stdout, file=sys.stdout)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    print("gRPC files generated successfully!")
    print(f"Generated files are in: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate gRPC Python files for Workflow Engine.")
    parser.add_argument(
        "--proto_path",
        type=str,
        required=True,
        help="Directory containing the .proto files.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directory where the generated Python files will be placed.",
    )
    args = parser.parse_args()
    generate_grpc_files(args.proto_path, args.output_dir) 