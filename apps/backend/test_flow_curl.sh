#!/bin/bash

# Test the new workflow agent flow using curl

echo "🚀 Testing Workflow Agent New Flow"
echo "=================================="

# Test 1: Initial vague request
echo -e "\n📋 Test 1: Initial vague request"
echo "Sending: 'I want to automate something'"

SESSION_ID="test-session-$(date +%s)"

curl -X POST http://localhost:8001/process-conversation \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "session_id": "'$SESSION_ID'",
    "user_id": "test-user",
    "user_message": "I want to automate something",
    "access_token": ""
  }' \
  -N 2>/dev/null | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      # Extract JSON after "data: "
      json="${line#data: }"
      
      # Parse response type
      response_type=$(echo "$json" | jq -r '.response_type // empty' 2>/dev/null)
      
      case "$response_type" in
        "RESPONSE_TYPE_STATUS_CHANGE")
          current_stage=$(echo "$json" | jq -r '.status_change.current_stage // empty' 2>/dev/null)
          if [ -n "$current_stage" ]; then
            echo "🔄 Stage: $current_stage"
          fi
          ;;
        "RESPONSE_TYPE_MESSAGE")
          message=$(echo "$json" | jq -r '.message // empty' 2>/dev/null)
          if [ -n "$message" ]; then
            echo -e "\n🤖 Assistant: $message"
          fi
          ;;
        "RESPONSE_TYPE_ERROR")
          error=$(echo "$json" | jq -r '.error.message // empty' 2>/dev/null)
          if [ -n "$error" ]; then
            echo "❌ Error: $error"
          fi
          ;;
      esac
    fi
done

echo -e "\n\n✅ Test 1 Complete"

# Test 2: Continue with specific request
echo -e "\n\n📋 Test 2: Continue with specific request"
echo "Waiting 2 seconds..."
sleep 2

echo "Sending: 'I want to send daily email reports at 9 AM'"

curl -X POST http://localhost:8001/process-conversation \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "session_id": "'$SESSION_ID'",
    "user_id": "test-user", 
    "user_message": "I want to send daily email reports at 9 AM with sales data from our database",
    "access_token": ""
  }' \
  -N 2>/dev/null | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      json="${line#data: }"
      response_type=$(echo "$json" | jq -r '.response_type // empty' 2>/dev/null)
      
      case "$response_type" in
        "RESPONSE_TYPE_STATUS_CHANGE")
          current_stage=$(echo "$json" | jq -r '.status_change.current_stage // empty' 2>/dev/null)
          if [ -n "$current_stage" ]; then
            echo "🔄 Stage: $current_stage"
          fi
          ;;
        "RESPONSE_TYPE_MESSAGE")
          message=$(echo "$json" | jq -r '.message // empty' 2>/dev/null)
          if [ -n "$message" ]; then
            echo -e "\n🤖 Assistant: $message"
          fi
          ;;
        "RESPONSE_TYPE_WORKFLOW")
          echo -e "\n✨ Workflow generated!"
          workflow=$(echo "$json" | jq '.workflow' 2>/dev/null)
          if [ -n "$workflow" ]; then
            echo "$workflow" | jq '.' 2>/dev/null || echo "$workflow"
          fi
          ;;
      esac
    fi
done

echo -e "\n\n✅ All tests complete!"