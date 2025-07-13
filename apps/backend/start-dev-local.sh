#!/bin/bash

# Local development startup script using uv for Workflow Agent Team backend services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Workflow Agent Team Backend Services (Local Development)${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${RED}❗ Please edit .env file and add your API keys before starting services${NC}"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}📦 Installing uv package manager...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo -e "${GREEN}✅ uv installed successfully${NC}"
fi

# Create virtual environment and install dependencies
echo -e "${YELLOW}🔧 Setting up development environment...${NC}"
uv sync --dev

# Generate gRPC files
echo -e "${YELLOW}📝 Generating gRPC proto files...${NC}"
cd shared && uv run python scripts/generate_grpc.py && cd ..

# Start Redis and PostgreSQL with Docker
echo -e "${YELLOW}🐳 Starting supporting services (Redis & PostgreSQL)...${NC}"
docker-compose up -d redis postgres

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for supporting services to be ready...${NC}"
sleep 5

# Check if services are ready
echo -e "${YELLOW}🔍 Checking supporting services...${NC}"
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is ready${NC}"
else
    echo -e "${RED}❌ Redis is not responding${NC}"
fi

if docker-compose exec postgres pg_isready -U workflow_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL is not responding${NC}"
fi

echo -e "${GREEN}🎉 Development environment ready!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo -e "  • Start Workflow Agent: ${GREEN}cd workflow_agent && uv run python -m main${NC}"
echo -e "  • Start API Gateway: ${GREEN}cd api-gateway && uv run uvicorn main:app --reload --port 8000${NC}"
echo ""
echo -e "${YELLOW}📝 Useful commands:${NC}"
echo -e "  • Install dependencies: ${GREEN}uv sync${NC}"
echo -e "  • Add new dependency: ${GREEN}uv add <package>${NC}"
echo -e "  • Run tests: ${GREEN}uv run pytest${NC}"
echo -e "  • Format code: ${GREEN}uv run black .${NC}"
echo -e "  • Type check: ${GREEN}uv run mypy .${NC}"
echo -e "  • Stop supporting services: ${GREEN}docker-compose stop redis postgres${NC}"
