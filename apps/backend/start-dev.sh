#!/bin/bash

# Development startup script for Workflow Agent Team backend services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Workflow Agent Team Backend Services${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${RED}❗ Please edit .env file and add your API keys before starting services${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}📦 Installing uv package manager...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Generate gRPC files if needed
echo -e "${YELLOW}📝 Generating gRPC proto files...${NC}"
cd shared && uv run python scripts/generate_grpc.py && cd ..

# Build and start services
echo -e "${YELLOW}🔨 Building Docker images...${NC}"
docker-compose build

echo -e "${YELLOW}🏃 Starting services...${NC}"
docker-compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Check service health
echo -e "${YELLOW}🔍 Checking service health...${NC}"

# Check API Gateway
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API Gateway is healthy${NC}"
else
    echo -e "${RED}❌ API Gateway is not responding${NC}"
fi

# Check if workflow agent gRPC is responding (basic check)
if nc -z localhost 50051 2>/dev/null; then
    echo -e "${GREEN}✅ Workflow Agent gRPC is listening${NC}"
else
    echo -e "${RED}❌ Workflow Agent gRPC is not responding${NC}"
fi

echo -e "${GREEN}🎉 Services started successfully!${NC}"
echo -e "${YELLOW}📋 Service URLs:${NC}"
echo -e "  • API Gateway: http://localhost:8000"
echo -e "  • API Docs: http://localhost:8000/docs"
echo -e "  • Workflow Agent gRPC: localhost:50051"
echo ""
echo -e "${YELLOW}📝 Useful commands:${NC}"
echo -e "  • View logs: docker-compose logs -f"
echo -e "  • Stop services: docker-compose down"
echo -e "  • Restart services: docker-compose restart"
