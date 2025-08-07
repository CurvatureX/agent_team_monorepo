#\!/bin/bash

# API配置
API_URL="http://localhost:8000"
SUPABASE_URL="https://mkrczzgjeduruwxpanbj.supabase.co"
SUPABASE_ANON_KEY="sb_publishable_GDldaQkfc6tfJ2aEOx_H3w_rq2Tc5G3"

# 测试账号
TEST_EMAIL="daming.lu@starmates.ai"
TEST_PASSWORD="test.1234\!"

echo "1. Getting auth token..."

# 使用printf来构建JSON，避免转义问题
JSON_DATA=$(printf '{"email":"%s","password":"%s"}' "$TEST_EMAIL" "$TEST_PASSWORD")

AUTH_RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/auth/v1/token?grant_type=password" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d "$JSON_DATA")

ACCESS_TOKEN=$(echo $AUTH_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Failed to get access token"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "Got access token: ${ACCESS_TOKEN:0:20}..."

echo -e "\n2. Creating session..."
SESSION_RESPONSE=$(curl -s -X POST "${API_URL}/api/app/sessions" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"source":"test"}')

SESSION_ID=$(echo $SESSION_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -z "$SESSION_ID" ]; then
    echo "Failed to create session"
    echo "Response: $SESSION_RESPONSE"
    exit 1
fi

echo "Created session: $SESSION_ID"

echo -e "\n3. Sending chat message..."
echo "Message: I want to sync unread gmail to slack"
echo -e "\nResponse stream:"

curl -X POST "${API_URL}/api/app/chat/stream" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "{
    \"session_id\": \"${SESSION_ID}\",
    \"message\": \"I want to sync unread gmail to slack\"
  }"
