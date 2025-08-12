#!/bin/bash

# Deploy OpenTelemetry Collector to AWS ECS
# This script applies the Terraform changes to add OTEL Collector service

set -e

echo "🔵 Deploying OpenTelemetry Collector to AWS ECS..."

# Navigate to infrastructure directory
cd ../infra

# Initialize Terraform if needed
echo "📦 Initializing Terraform..."
terraform init

# Plan the changes
echo "📋 Planning infrastructure changes..."
terraform plan -out=tfplan

# Show what will be created
echo "🔍 Changes to be applied:"
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions[] == "create") | {type: .type, name: .name, action: .change.actions}'

# Apply the changes
echo "🚀 Applying Terraform changes..."
terraform apply tfplan

# Get the OTEL Collector endpoint
OTEL_ENDPOINT=$(terraform output -raw otel_collector_endpoint 2>/dev/null || echo "Not available yet")
echo "✅ OpenTelemetry Collector deployed!"
echo "📊 Collector endpoint: $OTEL_ENDPOINT"

# Update ECS services to use new configuration
echo "🔄 Updating ECS services with new environment variables..."

# Force new deployment for each service
for service in api-gateway workflow-agent workflow-engine; do
    echo "  Updating $service..."
    aws ecs update-service \
        --cluster agent-team-dev-cluster \
        --service agent-team-dev-$service \
        --force-new-deployment \
        --region us-east-1
done

echo "⏳ Waiting for services to stabilize..."
aws ecs wait services-stable \
    --cluster agent-team-dev-cluster \
    --services agent-team-dev-api-gateway agent-team-dev-workflow-agent agent-team-dev-workflow-engine \
    --region us-east-1

echo "✅ All services updated successfully!"
echo ""
echo "📊 You can now view telemetry data in:"
echo "  - CloudWatch X-Ray for traces"
echo "  - CloudWatch Metrics for metrics"
echo "  - CloudWatch Logs for logs"
echo ""
echo "🔍 To check OTEL Collector logs:"
echo "  aws logs tail /ecs/agent-team-dev/otel-collector --follow"