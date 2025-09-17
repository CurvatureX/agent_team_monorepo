#!/bin/bash

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
PROJECT_NAME=${PROJECT_NAME:-"agent-team"}

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."

    for cmd in terraform aws docker; do
        if ! command -v $cmd &> /dev/null; then
            print_error "$cmd is not installed or not in PATH"
            exit 1
        fi
    done

    print_success "All dependencies are available"
}

# Check AWS credentials
check_aws_credentials() {
    print_status "Checking AWS credentials..."

    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid"
        exit 1
    fi

    print_success "AWS credentials are valid"
}

# Initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."

    terraform init

    print_success "Terraform initialized"
}

# Plan Terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."

    terraform plan -out=tfplan

    print_success "Terraform plan created"
}

# Apply Terraform deployment
apply_terraform() {
    print_status "Applying Terraform deployment..."

    terraform apply tfplan

    print_success "Infrastructure deployed successfully"
}

# Build and push Docker images
build_and_push_images() {
    print_status "Building and pushing Docker images..."

    # Get ECR repository URLs from Terraform output
    API_GATEWAY_REPO=$(terraform output -raw ecr_repository_urls | jq -r '.api_gateway')
    WORKFLOW_AGENT_REPO=$(terraform output -raw ecr_repository_urls | jq -r '.workflow_agent')
    WORKFLOW_ENGINE_REPO=$(terraform output -raw ecr_repository_urls | jq -r '.workflow_engine')
    WORKFLOW_SCHEDULER_REPO=$(terraform output -raw ecr_repository_urls | jq -r '.workflow_scheduler')

    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $API_GATEWAY_REPO

    # Build and push API Gateway
    print_status "Building API Gateway image..."
    cd ../apps/backend/api-gateway
    docker build -t $API_GATEWAY_REPO:latest .
    docker push $API_GATEWAY_REPO:latest

    # Build and push Workflow Agent
    print_status "Building Workflow Agent image..."
    cd ../workflow_agent
    docker build -f ../../../infra/Dockerfile.workflow-agent -t $WORKFLOW_AGENT_REPO:latest .
    docker push $WORKFLOW_AGENT_REPO:latest

    # Build and push Workflow Engine
    print_status "Building Workflow Engine image..."
    cd ../
    docker build -f workflow_engine/Dockerfile -t $WORKFLOW_ENGINE_REPO:latest .
    docker push $WORKFLOW_ENGINE_REPO:latest

    # Build and push Workflow Scheduler
    print_status "Building Workflow Scheduler image..."
    cd ../
    docker build -f workflow_scheduler/Dockerfile -t $WORKFLOW_SCHEDULER_REPO:latest .
    docker push $WORKFLOW_SCHEDULER_REPO:latest

    cd ../../../infra

    print_success "All images built and pushed successfully"
}

# Update ECS services to use new images
update_services() {
    print_status "Updating ECS services..."

    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)

    # Force new deployment for all services
    aws ecs update-service --cluster $CLUSTER_NAME --service api-gateway-service --force-new-deployment --region $AWS_REGION
    aws ecs update-service --cluster $CLUSTER_NAME --service workflow-agent-service --force-new-deployment --region $AWS_REGION
    aws ecs update-service --cluster $CLUSTER_NAME --service workflow-engine-service --force-new-deployment --region $AWS_REGION
    aws ecs update-service --cluster $CLUSTER_NAME --service workflow-scheduler-service --force-new-deployment --region $AWS_REGION

    print_success "ECS services updated"
}

# Wait for services to be stable
wait_for_services() {
    print_status "Waiting for services to stabilize..."

    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)

    aws ecs wait services-stable --cluster $CLUSTER_NAME --services api-gateway-service --region $AWS_REGION
    aws ecs wait services-stable --cluster $CLUSTER_NAME --services workflow-agent-service --region $AWS_REGION
    aws ecs wait services-stable --cluster $CLUSTER_NAME --services workflow-engine-service --region $AWS_REGION
    aws ecs wait services-stable --cluster $CLUSTER_NAME --services workflow-scheduler-service --region $AWS_REGION

    print_success "All services are stable"
}

# Display deployment information
show_deployment_info() {
    print_status "Deployment Information:"

    echo ""
    echo "API Gateway URL: $(terraform output -raw api_gateway_url)"
    echo "gRPC Load Balancer: $(terraform output -raw grpc_load_balancer_endpoint)"
    echo "Service Discovery Namespace: $(terraform output -raw service_discovery_namespace_name)"
    echo "Workflow Agent DNS: $(terraform output -raw workflow_agent_service_discovery_dns)"
    echo ""

    print_success "Deployment completed successfully!"
}

# Main deployment flow
main() {
    print_status "Starting deployment of gRPC service discovery architecture..."

    check_dependencies
    check_aws_credentials
    init_terraform
    plan_terraform

    # Ask for confirmation before applying
    echo ""
    read -p "Do you want to apply the Terraform plan? (y/N): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apply_terraform
        build_and_push_images
        update_services
        wait_for_services
        show_deployment_info
    else
        print_warning "Deployment cancelled"
        exit 0
    fi
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "plan")
        check_dependencies
        check_aws_credentials
        init_terraform
        plan_terraform
        ;;
    "destroy")
        print_warning "This will destroy all infrastructure. Are you sure?"
        read -p "Type 'yes' to confirm: " -r
        if [[ $REPLY == "yes" ]]; then
            terraform destroy
            print_success "Infrastructure destroyed"
        else
            print_warning "Destroy cancelled"
        fi
        ;;
    *)
        echo "Usage: $0 {deploy|plan|destroy}"
        exit 1
        ;;
esac
