# Agent Team Infrastructure

This directory contains Terraform configurations for deploying the Agent Team application on AWS. The infrastructure follows a modern, scalable microservices architecture using containerized services on AWS ECS Fargate.

## 🏗️ Architecture Overview

```
Internet → API Gateway → Load Balancer → ECS Services → Database/Cache
                                      │
                                      ├─ API Gateway (FastAPI)
                                      └─ Workflow Engine (gRPC)
```

## 📁 File Structure

| File | Purpose | Resources |
|------|---------|-----------|
| `main.tf` | Provider configuration, data sources, and common locals | AWS provider, S3 backend, availability zones |
| `vpc.tf` | Virtual Private Cloud and networking infrastructure | VPC, subnets, NAT gateways, route tables |
| `security_groups.tf` | Network security rules for all services | Security groups for ALB, ECS, RDS, ElastiCache |
| `ecs.tf` | Container orchestration and task definitions | ECS cluster, services, task definitions |
| `load_balancer.tf` | Application Load Balancer for traffic distribution | ALB, target groups, listeners |
| `api_gateway.tf` | AWS API Gateway for external API access | API Gateway v2, VPC link, routes |
| `ecr.tf` | Container registries for Docker images | ECR repositories for both services |
| `cache.tf` | Redis caching layer | ElastiCache Redis cluster |
| `secrets.tf` | Secure parameter storage | SSM parameters, RDS database |
| `service_discovery.tf` | Internal service communication | AWS Cloud Map for service discovery |
| `variables.tf` | Input variable definitions | All configurable parameters |
| `outputs.tf` | Output values after deployment | URLs, endpoints, resource ARNs |

## 🔧 Core Components

### Networking (`vpc.tf`)
- **VPC**: Isolated network environment with DNS resolution enabled
- **Public Subnets**: Host NAT gateways and load balancer (2 AZs for HA)
- **Private Subnets**: Host ECS tasks, database, and cache (2 AZs for HA)
- **NAT Gateways**: Enable outbound internet access for private resources
- **Route Tables**: Direct traffic appropriately between subnets

### Container Platform (`ecs.tf`)
- **ECS Fargate Cluster**: Serverless container orchestration
- **API Gateway Service**: FastAPI application handling HTTP requests
- **Workflow Engine Service**: gRPC service for workflow processing
- **Task Definitions**: Container specifications with health checks
- **IAM Roles**: Task execution and application permissions
- **CloudWatch Logging**: Centralized log collection

### Load Balancing (`load_balancer.tf`)
- **Application Load Balancer**: Distributes traffic across ECS tasks
- **Target Groups**: Health check endpoints for services
- **SSL/HTTPS Support**: Optional certificate-based encryption
- **HTTP to HTTPS Redirect**: Automatic security enforcement

### API Gateway (`api_gateway.tf`)
- **HTTP API Gateway**: Public endpoint for the application
- **VPC Link**: Secure connection to private load balancer
- **CORS Configuration**: Cross-origin request support
- **Access Logging**: Request/response logging to CloudWatch
- **Throttling**: Rate limiting and burst protection
- **Custom Domain**: Optional custom domain mapping

### Data Layer (`secrets.tf`)
- **RDS PostgreSQL**: Managed relational database with encryption
- **Database Subnets**: Isolated subnet group for database
- **Automated Backups**: Point-in-time recovery enabled
- **Multi-AZ Deployment**: High availability across zones

### Caching (`cache.tf`)
- **ElastiCache Redis**: In-memory data store for session/cache data
- **Subnet Groups**: Private subnet placement
- **Security Groups**: Network access control

### Security (`security_groups.tf`)
- **ALB Security Group**: HTTP/HTTPS ingress from internet
- **ECS Security Group**: Port 8000 from ALB + internal communication
- **RDS Security Group**: PostgreSQL access from ECS only
- **ElastiCache Security Group**: Redis access from ECS only

### Container Registry (`ecr.tf`)
- **ECR Repositories**: Private Docker image storage
- **Lifecycle Policies**: Automatic image cleanup
- **Image Scanning**: Security vulnerability detection

### Service Discovery (`service_discovery.tf`)
- **Cloud Map Namespace**: Internal DNS for services
- **Service Registration**: Automatic service discovery
- **Health Checks**: Service health monitoring

### Secrets Management (`secrets.tf`)
- **SSM Parameters**: Encrypted storage for API keys and secrets
- **Database Credentials**: Secure random password generation
- **Environment Variables**: Secure injection into containers

## 🚀 Deployment

### Prerequisites
1. AWS CLI configured with appropriate permissions
2. Terraform >= 1.0 installed
3. S3 bucket for Terraform state storage
4. Docker images pushed to ECR repositories

### Configuration
1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Update variables with your specific values:
   ```hcl
   aws_region = "us-east-1"
   environment = "production"
   domain_name = "api.yourdomain.com"  # optional
   certificate_arn = "arn:aws:acm:..."  # optional
   ```

### Deploy Infrastructure
```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply changes
terraform apply
```

## 🔐 Security Features

- **Network Isolation**: Private subnets for all application components
- **Security Groups**: Principle of least privilege access
- **Encryption**: RDS encryption at rest and in transit
- **Secrets Management**: No hardcoded secrets in configuration
- **HTTPS Support**: SSL/TLS termination at load balancer
- **VPC Endpoints**: Secure AWS service communication (if needed)

## 📊 Monitoring & Logging

- **CloudWatch Logs**: Centralized application and infrastructure logs
- **Health Checks**: Container and load balancer health monitoring
- **Metrics**: ECS, ALB, and RDS performance metrics
- **API Gateway Analytics**: Request/response analytics and throttling

## 💰 Cost Optimization

- **Fargate Spot**: Optional spot pricing for non-critical workloads
- **RDS Instance Sizing**: Right-sized database instances
- **ElastiCache Micro**: Small cache instance for development
- **Log Retention**: 7-day log retention to manage costs
- **Image Lifecycle**: Automatic cleanup of old container images

## 🔄 High Availability

- **Multi-AZ Deployment**: Resources spread across availability zones
- **Auto Scaling**: ECS services can scale based on demand
- **Database Failover**: RDS Multi-AZ for automatic failover
- **Load Balancer Health Checks**: Automatic traffic routing to healthy instances

## 🛠️ Maintenance

### Updates
- **Container Images**: Update via ECR and ECS service updates
- **Infrastructure Changes**: Use Terraform for all modifications
- **Database Migrations**: Handle via application deployment

### Monitoring
- Check CloudWatch dashboards for performance metrics
- Monitor ECS service health and scaling
- Review API Gateway throttling and error rates

## 📝 Environment Variables

The infrastructure automatically configures the following environment variables for services:

### API Gateway Service
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: ElastiCache Redis connection
- `WORKFLOW_SERVICE_HOST`: Internal workflow engine hostname
- `SUPABASE_*`: Supabase configuration (from SSM)

### Workflow Engine Service
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: ElastiCache Redis connection
- `GRPC_HOST`/`GRPC_PORT`: gRPC server configuration
- `OPENAI_API_KEY`: OpenAI API key (from SSM)
- `ANTHROPIC_API_KEY`: Anthropic API key (from SSM)

## 🚨 Troubleshooting

### Common Issues
1. **ECS Tasks Not Starting**: Check CloudWatch logs for container errors
2. **Load Balancer Health Check Failures**: Verify `/health` endpoint
3. **Database Connection Issues**: Check security group rules
4. **API Gateway 5xx Errors**: Verify VPC link and ALB configuration

### Useful Commands
```bash
# Check ECS service status
aws ecs describe-services --cluster <cluster-name> --services <service-name>

# View container logs
aws logs describe-log-streams --log-group-name /ecs/<prefix>

# Test load balancer health
curl -f http://<alb-dns-name>/health
```

## 📚 Additional Resources

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
