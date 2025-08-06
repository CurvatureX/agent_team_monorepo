#!/bin/bash

# Run integration tests for API Gateway
# This script loads environment variables and runs the integration tests

echo "🧪 Running API Gateway Integration Tests..."

# Navigate to api-gateway directory
cd "$(dirname "$0")"

# Check if we're in CI environment
if [ "$CI" == "true" ]; then
    echo "⚠️  CI environment detected. Skipping integration tests."
    exit 0
fi

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo "❌ Error: .env file not found at ../.env"
    echo "Please create a .env file with the required environment variables."
    exit 1
fi

# Load environment variables
set -a
source ../.env
set +a

# Check required environment variables
required_vars=("TEST_USER_EMAIL" "TEST_USER_PASSWORD" "SUPABASE_URL" "SUPABASE_ANON_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ Environment variables loaded successfully"

# Install dependencies if needed
echo "📦 Installing dependencies..."
uv sync

# Run integration tests
echo "🚀 Running integration tests..."
uv run pytest tests/test_integration.py -v --tb=short

# Check test result
if [ $? -eq 0 ]; then
    echo "✅ All integration tests passed!"
else
    echo "❌ Integration tests failed!"
    exit 1
fi
