#!/bin/bash

# Quick deploy fix for OpenTelemetry Collector
# Fixes the deprecated logging exporter issue

set -e

echo "🚀 Deploying OpenTelemetry Collector fix..."

# Navigate to infrastructure directory
cd ../infra

# Apply only the OTEL collector changes
echo "📦 Applying Terraform changes for OTEL Collector..."
terraform apply -auto-approve \
  -target=aws_ecs_task_definition.otel_collector \
  -target=aws_ecs_service.otel_collector

# Force a new deployment
echo "🔄 Forcing new deployment..."
aws ecs update-service \
  --cluster agent-team-prod-cluster \
  --service agent-team-prod-otel-collector \
  --force-new-deployment \
  --region us-east-1 2>/dev/null || \
aws ecs update-service \
  --cluster agent-team-dev-cluster \
  --service agent-team-dev-otel-collector \
  --force-new-deployment \
  --region us-east-1

# Wait a moment for the deployment to start
sleep 5

# Check the status
echo "📊 Checking deployment status..."
aws ecs describe-services \
  --cluster agent-team-prod-cluster \
  --services agent-team-prod-otel-collector \
  --region us-east-1 \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,LastEvent:events[0].message}' \
  --output table 2>/dev/null || \
aws ecs describe-services \
  --cluster agent-team-dev-cluster \
  --services agent-team-dev-otel-collector \
  --region us-east-1 \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,LastEvent:events[0].message}' \
  --output table

echo "✅ Deployment initiated!"
echo ""
echo "🔍 Monitor logs with:"
echo "  aws logs tail /ecs/agent-team-prod/otel-collector --follow"
echo "  or"
echo "  aws logs tail /ecs/agent-team-dev/otel-collector --follow"