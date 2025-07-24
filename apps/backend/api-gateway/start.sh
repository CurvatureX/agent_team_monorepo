#!/bin/bash
# MVP API Gateway startup script with uv

set -e

echo "🚀 Starting API Gateway MVP with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
source .env

# Check required environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "❌ Missing required environment variables:"
    echo "   SUPABASE_URL and SUPABASE_SERVICE_KEY are required"
    exit 1
fi

# Install dependencies with uv
echo "📦 Installing dependencies with uv..."
uv sync

# Start the server
echo "🌟 Starting FastAPI server with uv..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload