#!/bin/bash
set -e

echo "🚀 Starting Workflow Engine v2..."

# Start FastAPI app
exec uvicorn workflow_engine_v2.main:app --host 0.0.0.0 --port 8002
