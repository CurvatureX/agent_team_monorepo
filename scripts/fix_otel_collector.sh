#!/bin/bash

# Fix and deploy OpenTelemetry Collector to AWS ECS
# This script updates the OTEL Collector to use AWS distro

set -e

echo "🔧 Fixing OpenTelemetry Collector configuration..."

# Navigate to infrastructure directory
cd ../infra

# Initialize Terraform if needed
echo "📦 Initializing Terraform..."
terraform init

# Taint the existing OTEL resources to force recreation
echo "🔄 Marking OTEL resources for recreation..."
terraform taint aws_ecs_task_definition.otel_collector || true
terraform taint aws_ecs_service.otel_collector || true

# Plan the changes
echo "📋 Planning infrastructure changes..."
terraform plan -target=aws_ecs_task_definition.otel_collector \
               -target=aws_ecs_service.otel_collector \
               -target=aws_cloudwatch_log_group.otel_collector \
               -target=aws_iam_role.otel_collector_task_role \
               -target=aws_iam_policy.otel_collector_cloudwatch \
               -target=aws_iam_policy.otel_collector_discovery \
               -target=aws_security_group.otel_collector \
               -target=aws_service_discovery_service.otel_collector \
               -out=tfplan

# Apply the changes
echo "🚀 Applying Terraform changes..."
terraform apply tfplan

# Wait for the service to stabilize
echo "⏳ Waiting for OTEL Collector to start..."
aws ecs wait services-stable \
    --cluster agent-team-dev-cluster \
    --services agent-team-dev-otel-collector \
    --region us-east-1 || {
    echo "⚠️ Service may still be starting. Checking status..."
    aws ecs describe-services \
        --cluster agent-team-dev-cluster \
        --services agent-team-dev-otel-collector \
        --region us-east-1 \
        --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Events:events[0:3]}' \
        --output json
}

# Check the logs
echo "📊 Checking OTEL Collector logs..."
aws logs tail /ecs/agent-team-dev/otel-collector --since 1m --region us-east-1 || true

echo "✅ OpenTelemetry Collector deployment complete!"
echo ""
echo "📊 Key changes:"
echo "  - Using AWS distro: public.ecr.aws/aws-observability/aws-otel-collector"
echo "  - Configuration via AOT_CONFIG_CONTENT environment variable"
echo "  - No shell dependency - pure container execution"
echo ""
echo "🔍 To monitor:"
echo "  aws logs tail /ecs/agent-team-dev/otel-collector --follow"