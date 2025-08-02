#!/bin/bash

# Test script using curl for SSE streaming
# This avoids potential Postman timeout/disconnection issues

# Configuration
API_URL="http://localhost:8000/api/v1/app/chat/stream"
AUTH_URL="https://mkrczzgjeduruwxpanbj.supabase.co/auth/v1/token?grant_type=password"
SESSION_URL="http://localhost:8000/api/v1/app/sessions"

# Credentials from .env
EMAIL="daming.lu@starmates.ai"
PASSWORD="test.1234!"
ANON_KEY="sb_publishable_GDldaQkfc6tfJ2aEOx_H3w_rq2Tc5G3"

echo "🔐 Getting access token..."

# Get access token
AUTH_RESPONSE=$(curl -s -X POST "$AUTH_URL" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"gotrue_meta_security\": {}
  }")

ACCESS_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ]; then
  echo "❌ Authentication failed"
  echo $AUTH_RESPONSE
  exit 1
fi

echo "✅ Got access token"

# Create session
echo -e "\n📝 Creating session..."

SESSION_RESPONSE=$(curl -s -X POST "$SESSION_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "create", "workflow_id": null}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session.id')

if [ "$SESSION_ID" == "null" ]; then
  echo "❌ Failed to create session"
  echo $SESSION_RESPONSE
  exit 1
fi

echo "✅ Session created: $SESSION_ID"

# First request
echo -e "\n📨 First request: Create a workflow to sync Gmail emails to Slack"
echo "================================================================"

curl -N -X POST "$API_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"user_message\": \"Create a workflow to sync Gmail emails to Slack\"
  }" 2>/dev/null | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      echo "$line" | cut -d' ' -f2- | jq -r '.type // .response_type // "unknown"' 2>/dev/null | xargs -I {} echo "  Event: {}"
    fi
done

echo -e "\n⏳ Waiting 5 seconds before second request..."
sleep 5

# Second request
echo -e "\n📨 Second request: Everyday"
echo "================================================================"

curl -N -X POST "$API_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"user_message\": \"Everyday\"
  }" 2>/dev/null | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      # Extract event type and other info
      EVENT_DATA=$(echo "$line" | cut -d' ' -f2-)
      EVENT_TYPE=$(echo "$EVENT_DATA" | jq -r '.type // .response_type // "unknown"' 2>/dev/null)
      
      echo "  Event: $EVENT_TYPE"
      
      # Show details for specific event types
      if [ "$EVENT_TYPE" == "status_change" ] || [ "$EVENT_TYPE" == "RESPONSE_TYPE_STATUS_CHANGE" ]; then
        STAGE=$(echo "$EVENT_DATA" | jq -r '.data.current_stage // .status_change.current_stage // "unknown"' 2>/dev/null)
        echo "    Stage: $STAGE"
      fi
      
      if [ "$EVENT_TYPE" == "error" ] || [ "$EVENT_TYPE" == "RESPONSE_TYPE_ERROR" ]; then
        ERROR=$(echo "$EVENT_DATA" | jq -r '.data.message // .error.message // "unknown error"' 2>/dev/null)
        echo "    ❌ Error: $ERROR"
      fi
    fi
done

echo -e "\n✅ Test completed!"