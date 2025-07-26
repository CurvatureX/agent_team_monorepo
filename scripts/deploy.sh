#!/bin/bash

# Deployment script for Agent Team services
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-production}
PROJECT_NAME=${PROJECT_NAME:-agent-team}

echo -e "${GREEN}🚀 Starting deployment for ${PROJECT_NAME} (${ENVIRONMENT})${NC}"

# Check required tools
check_requirements() {
    echo -e "${YELLOW}📋 Checking requirements...${NC}"

    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI is required but not installed${NC}"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is required but not installed${NC}"
        exit 1
    fi

    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}❌ Terraform is required but not installed${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ All requirements satisfied${NC}"
}

# Build and push Docker images
build_and_push() {
    echo -e "${YELLOW}🔨 Building and pushing Docker images...${NC}"

    # Get ECR login token
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

    cd apps/backend
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Build and push API Gateway
    echo -e "${YELLOW}Building API Gateway...${NC}"
    docker build --target production -f api-gateway/Dockerfile -t $PROJECT_NAME/api-gateway:latest .
    docker tag $PROJECT_NAME/api-gateway:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/api-gateway:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/api-gateway:latest

    # Build and push Workflow Agent
    echo -e "${YELLOW}Building Workflow Agent...${NC}"
    docker build -f workflow_agent/Dockerfile -t $PROJECT_NAME/workflow-agent:latest .
    docker tag $PROJECT_NAME/workflow-agent:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/workflow-agent:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/workflow-agent:latest

    # Build and push Workflow Engine
    echo -e "${YELLOW}Building Workflow Engine...${NC}"
    docker build --target production -f workflow_engine/Dockerfile -t $PROJECT_NAME/workflow-engine:latest .
    docker tag $PROJECT_NAME/workflow-engine:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/workflow-engine:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/workflow-engine:latest
    
    cd ../..

    echo -e "${GREEN}✅ Images built and pushed successfully${NC}"
}

# Deploy infrastructure
deploy_infrastructure() {
    echo -e "${YELLOW}🏗️  Deploying infrastructure...${NC}"

    cd infra

    # Initialize Terraform
    terraform init

    # Plan deployment
    terraform plan -out=tfplan

    # Apply deployment
    terraform apply -auto-approve tfplan

    cd ..

    echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
}

# Update ECS services
update_services() {
    echo -e "${YELLOW}🔄 Updating ECS services...${NC}"

    # Update API Gateway service
    aws ecs update-service \
        --cluster $PROJECT_NAME-$ENVIRONMENT-cluster \
        --service api-gateway-service \
        --force-new-deployment \
        --region $AWS_REGION

    # Update Workflow Agent service
    aws ecs update-service \
        --cluster $PROJECT_NAME-$ENVIRONMENT-cluster \
        --service workflow-agent-service \
        --force-new-deployment \
        --region $AWS_REGION

    # Update Workflow Engine service
    aws ecs update-service \
        --cluster $PROJECT_NAME-$ENVIRONMENT-cluster \
        --service workflow-engine-service \
        --force-new-deployment \
        --region $AWS_REGION

    # Wait for services to stabilize
    echo -e "${YELLOW}⏳ Waiting for services to stabilize...${NC}"
    aws ecs wait services-stable \
        --cluster $PROJECT_NAME-$ENVIRONMENT-cluster \
        --services api-gateway-service workflow-agent-service workflow-engine-service \
        --region $AWS_REGION

    echo -e "${GREEN}✅ Services updated successfully${NC}"
}

# Get deployment status
get_status() {
    echo -e "${YELLOW}📊 Getting deployment status...${NC}"

    # Get load balancer URL
    LB_URL=$(aws elbv2 describe-load-balancers \
        --names $PROJECT_NAME-$ENVIRONMENT-alb \
        --query 'LoadBalancers[0].DNSName' \
        --output text \
        --region $AWS_REGION 2>/dev/null || echo "Not found")

    echo -e "${GREEN}🌐 Load Balancer URL: http://$LB_URL${NC}"

    # Get service status
    aws ecs describe-services \
        --cluster $PROJECT_NAME-$ENVIRONMENT-cluster \
        --services api-gateway-service workflow-agent-service workflow-engine-service \
        --query 'services[*].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}' \
        --output table \
        --region $AWS_REGION
}

# Main deployment flow
main() {
    case "${1:-all}" in
        "check")
            check_requirements
            ;;
        "build")
            check_requirements
            build_and_push
            ;;
        "infra")
            check_requirements
            deploy_infrastructure
            ;;
        "services")
            check_requirements
            update_services
            ;;
        "status")
            get_status
            ;;
        "all")
            check_requirements
            build_and_push
            deploy_infrastructure
            update_services
            get_status
            ;;
        *)
            echo "Usage: $0 {check|build|infra|services|status|all}"
            echo "  check    - Check requirements"
            echo "  build    - Build and push Docker images"
            echo "  infra    - Deploy infrastructure"
            echo "  services - Update ECS services"
            echo "  status   - Get deployment status"
            echo "  all      - Run complete deployment (default)"
            exit 1
            ;;
    esac
}

main "$@"

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
