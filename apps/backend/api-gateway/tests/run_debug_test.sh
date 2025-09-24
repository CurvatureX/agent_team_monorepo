#!/bin/bash

# Run the sessions and chat debug test
# This script runs the integration test with detailed logging

echo "🚀 Running Sessions and Chat Debug Test"
echo "======================================"

# Change to the api-gateway directory
cd "$(dirname "$0")/.."

# Check if the API Gateway is running
if ! curl -s http://localhost:8000/api/v1/public/health > /dev/null; then
    echo "❌ Error: API Gateway is not running on http://localhost:8000"
    echo "Please start the API Gateway first with: uv run uvicorn app.main:app --reload"
    exit 1
fi

echo "✅ API Gateway is running"
echo ""

# Run the test
echo "📋 Running integration test with detailed logging..."
echo ""

python tests/test_sessions_chat_debug.py

echo ""
echo "✨ Test completed!"
