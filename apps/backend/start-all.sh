#!/bin/bash

# Start all services with docker-compose
# Usage: ./start-all.sh [dev|prod]

MODE=${1:-dev}

echo "🚀 Starting Workflow Agent Backend Services in $MODE mode..."

if [ "$MODE" = "dev" ]; then
    echo "📝 Starting in development mode with hot reload..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
elif [ "$MODE" = "prod" ]; then
    echo "🏭 Starting in production mode..."
    docker-compose up --build -d
    echo "✅ Services started in background"
    echo "🔗 API Gateway: http://localhost:8000"
    echo "🔗 API Docs: http://localhost:8000/docs"
    echo "🔗 Database Admin: http://localhost:8080"
    echo "🔗 Redis Commander: http://localhost:8081"
else
    echo "❌ Invalid mode: $MODE"
    echo "Usage: $0 [dev|prod]"
    exit 1
fi