#!/bin/bash

echo "Testing timer workflow generation with correct subtypes..."

# Test creating a workflow with timer trigger
curl -X POST http://localhost:8001/api/v1/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a workflow that sends an HTTP GET request to https://google.com every 5 minutes",
    "session_id": "test-timer-fix",
    "user_id": "test_user"
  }' \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -o response.json

echo "Response saved to response.json"
echo "Checking for correct TRIGGER_CRON subtype..."
grep -o '"subtype":[^,]*' response.json | head -5