#!/usr/bin/env bash

# Trigger a Slack message event against the workflow_scheduler (port 8003 by default)
# to invoke workflows with Slack triggers.
#
# Config via env vars (defaults shown):
#   SCHEDULER_URL=http://localhost:8003
#   TEAM_ID=T0974ULPRAN
#   USER_ID=U_TEST_AGENT
#   CHANNEL_ID=C_TEST_DOCS
#   MESSAGE="can you clean up the existing document"
#   TS=<unix seconds>         # optional, auto-generated if not set
#   EVENT_ID=<string>         # optional, auto-generated if not set
#
# Usage:
#   bash apps/backend/workflow_scheduler/tests/scripts/trigger_slack_message_event.sh

set -euo pipefail

SCHEDULER_URL=${SCHEDULER_URL:-http://localhost:8003}
TEAM_ID=${TEAM_ID:-T0974ULPRAN}
USER_ID=${USER_ID:-U_TEST_AGENT}
CHANNEL_ID=${CHANNEL_ID:-C_TEST_DOCS}
MESSAGE=${MESSAGE:-"can you clean up the existing document"}

TS=${TS:-$(date +%s)}
EVENT_ID=${EVENT_ID:-Ev-${TS}-$$-${RANDOM}}

read -r -d '' PAYLOAD <<JSON
{
  "team_id": "${TEAM_ID}",
  "event_data": {
    "type": "event_callback",
    "event": {
      "type": "message",
      "text": ${MESSAGE@Q},
      "user": "${USER_ID}",
      "channel": "${CHANNEL_ID}",
      "ts": "${TS}.000100"
    },
    "event_id": "${EVENT_ID}",
    "event_time": ${TS}
  }
}
JSON

echo "POST ${SCHEDULER_URL}/api/v1/triggers/slack/events"
echo "Payload:" >&2
echo "${PAYLOAD}" | sed 's/.*/  &/' >&2

curl -sS -X POST \
  "${SCHEDULER_URL}/api/v1/triggers/slack/events" \
  -H "Content-Type: application/json" \
  --data-raw "${PAYLOAD}"
