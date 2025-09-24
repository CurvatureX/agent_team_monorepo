#!/bin/bash
# start.sh - Entrypoint script for the API Gateway service

set -e

# Ensure the logs directory exists
mkdir -p /app/logs

# Function to check if a service is available
wait_for_service() {
    local service_name=$1
    local port=$2
    echo "Waiting for $service_name to be available on port $port..."
    while ! nc -z localhost $port; do
        echo "$service_name is not available yet. Waiting..."
        sleep 1
    done
    echo "$service_name is now available."
}

echo "🚀 Starting API Gateway MVP..."

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "✅ Activating virtual environment"
    source .venv/bin/activate
else
    echo "🚨 .venv not found, running without virtual environment"
fi

# Wait for dependent services (optional, for robust startup)
# wait_for_service redis 6379
# wait_for_service workflow-engine 50050

echo "▶️ Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
