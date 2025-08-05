#!/bin/bash

# Workflow Scheduler Startup Script
# This script starts the workflow_scheduler service with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Workflow Scheduler Service${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cat > .env << EOF
# Core Service Configuration
PORT=8003
HOST=0.0.0.0
DEBUG=true
SERVICE_NAME=workflow_scheduler

# External Service URLs
WORKFLOW_ENGINE_URL=http://localhost:8002
API_GATEWAY_URL=http://localhost:8000

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/workflow_scheduler
REDIS_URL=redis://localhost:6379/1

# Email Configuration (Optional - for EmailTrigger)
IMAP_SERVER=imap.gmail.com
EMAIL_USER=
EMAIL_PASSWORD=
EMAIL_CHECK_INTERVAL=60

# SMTP Configuration (for sending notifications)
SMTP_HOST=smtp.migadu.com
SMTP_PORT=465
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=false
SMTP_USE_SSL=true
SMTP_SENDER_EMAIL=
SMTP_SENDER_NAME=Workflow Scheduler
SMTP_TIMEOUT=30

# GitHub App Configuration (Optional)
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# APScheduler Configuration
SCHEDULER_TIMEZONE=UTC
SCHEDULER_MAX_WORKERS=10

# Distributed Lock Configuration
LOCK_TIMEOUT=300
LOCK_RETRY_DELAY=0.1

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    echo -e "${YELLOW}📝 Please configure .env file with your settings${NC}"
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

echo -e "${GREEN}🔧 Configuration loaded${NC}"
echo -e "   Port: ${PORT}"
echo -e "   Debug: ${DEBUG}"
echo -e "   Log Level: ${LOG_LEVEL}"

# Check dependencies
echo -e "${GREEN}📦 Checking dependencies...${NC}"

if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found. Please install Python 3.11+${NC}"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}📥 Installing dependencies...${NC}"
    if command -v uv &> /dev/null; then
        uv sync
    else
        pip install -e .
    fi
fi

# Health checks for external dependencies (optional)
echo -e "${GREEN}🔍 Checking external services...${NC}"

# Check Redis connection (optional, won't fail startup)
if command -v redis-cli &> /dev/null; then
    if redis-cli -u ${REDIS_URL} ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis connection OK${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis not available - distributed locking will be disabled${NC}"
    fi
fi

# Check database connection (optional)
if [[ $DATABASE_URL == postgresql* ]]; then
    echo -e "${YELLOW}💾 Database configured: PostgreSQL${NC}"
else
    echo -e "${YELLOW}⚠️  Database not configured - using in-memory storage${NC}"
fi

echo -e "${GREEN}🎯 Starting Workflow Scheduler on http://${HOST}:${PORT}${NC}"
echo -e "${GREEN}📊 Health check: http://${HOST}:${PORT}/health${NC}"
echo -e "${GREEN}📖 API docs: http://${HOST}:${PORT}/docs${NC}"
echo ""

# Start the service
if [ "$DEBUG" = "true" ]; then
    echo -e "${YELLOW}🐛 Running in DEBUG mode with auto-reload${NC}"
    if command -v uv &> /dev/null; then
        exec uv run uvicorn workflow_scheduler.app.main:app \
            --host $HOST \
            --port $PORT \
            --reload \
            --log-level debug
    else
        exec python -m uvicorn workflow_scheduler.app.main:app \
            --host $HOST \
            --port $PORT \
            --reload \
            --log-level debug
    fi
else
    echo -e "${GREEN}🚀 Running in PRODUCTION mode${NC}"
    if command -v uv &> /dev/null; then
        exec uv run uvicorn workflow_scheduler.app.main:app \
            --host $HOST \
            --port $PORT \
            --workers 1
    else
        exec python -m uvicorn workflow_scheduler.app.main:app \
            --host $HOST \
            --port $PORT \
            --workers 1
    fi
fi
