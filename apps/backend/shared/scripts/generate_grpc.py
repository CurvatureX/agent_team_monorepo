#!/usr/bin/env python3
"""
Script to generate gRPC Python files from protobuf definitions
"""
import subprocess
import sys
from pathlib import Path


def generate_grpc_files():
    """Generate gRPC Python files from proto definitions"""

    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent.parent
    proto_dir = project_root / "apps" / "backend" / "shared" / "proto"

    # Output directories
    api_gateway_proto_dir = project_root / "apps" / "backend" / "api-gateway" / "proto"
    workflow_agent_proto_dir = project_root / "apps" / "backend" / "workflow_agent" / "proto"
    workflow_engine_proto_dir = project_root / "apps" / "backend" / "workflow_engine" / "workflow_engine" / "proto"

    # Create output directories
    api_gateway_proto_dir.mkdir(exist_ok=True, parents=True)
    workflow_agent_proto_dir.mkdir(exist_ok=True, parents=True)
    workflow_engine_proto_dir.mkdir(exist_ok=True, parents=True)

    # Create __init__.py files
    (api_gateway_proto_dir / "__init__.py").touch()
    (workflow_agent_proto_dir / "__init__.py").touch()
    (workflow_engine_proto_dir / "__init__.py").touch()

    # Generate for API Gateway
    print("Generating gRPC files for API Gateway...")
    cmd_api_gateway = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_dir}",
        f"--python_out={api_gateway_proto_dir}",
        f"--grpc_python_out={api_gateway_proto_dir}",
        str(proto_dir / "workflow_agent.proto"),
    ]

    result = subprocess.run(cmd_api_gateway, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error generating API Gateway gRPC files: {result.stderr}")
        sys.exit(1)

    # Generate for Workflow Agent
    print("Generating gRPC files for Workflow Agent...")
    cmd_workflow_agent = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_dir}",
        f"--python_out={workflow_agent_proto_dir}",
        f"--grpc_python_out={workflow_agent_proto_dir}",
        str(proto_dir / "workflow_agent.proto"),
    ]

    result = subprocess.run(cmd_workflow_agent, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error generating Workflow Agent gRPC files: {result.stderr}")
        sys.exit(1)

    # Generate for Workflow Engine (new credential management service)
    print("Generating gRPC files for Workflow Engine...")
    cmd_workflow_engine = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_dir}",
        f"--proto_path={proto_dir / 'engine'}",
        f"--python_out={workflow_engine_proto_dir}",
        f"--grpc_python_out={workflow_engine_proto_dir}",
        str(proto_dir / "engine" / "workflow_service.proto"),
    ]

    result = subprocess.run(cmd_workflow_engine, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error generating Workflow Engine gRPC files: {result.stderr}")
        sys.exit(1)

    print("gRPC files generated successfully!")
    print(f"API Gateway files: {api_gateway_proto_dir}")
    print(f"Workflow Agent files: {workflow_agent_proto_dir}")
    print(f"Workflow Engine files: {workflow_engine_proto_dir}")


if __name__ == "__main__":
    generate_grpc_files()
