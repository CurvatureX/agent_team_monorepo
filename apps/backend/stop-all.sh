#!/bin/bash

# Stop all services
echo "🛑 Stopping all Workflow Agent Backend Services..."

docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

echo "✅ All services stopped"
echo "💾 To also remove volumes (data will be lost): docker-compose down -v"