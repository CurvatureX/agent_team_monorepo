from setuptools import setup, find_packages

setup(
    name="workflow-agent-proto",
    version="0.1.0",
    description="gRPC protocol definitions for workflow agent",
    packages=find_packages(),
    install_requires=[
        "grpcio>=1.60.0",
        "grpcio-tools>=1.60.0",
        "protobuf>=4.25.0",
    ],
    python_requires=">=3.8",
)