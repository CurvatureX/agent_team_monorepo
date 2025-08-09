output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "api_gateway_service_name" {
  description = "Name of the API Gateway ECS service"
  value       = aws_ecs_service.api_gateway.name
}

output "workflow_engine_service_name" {
  description = "Name of the Workflow Engine ECS service"
  value       = aws_ecs_service.workflow_engine.name
}

output "workflow_agent_service_name" {
  description = "Name of the Workflow Agent ECS service"
  value       = aws_ecs_service.workflow_agent.name
}

output "workflow_scheduler_service_name" {
  description = "Name of the Workflow Scheduler ECS service"
  value       = aws_ecs_service.workflow_scheduler.name
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

output "ecr_repository_urls" {
  description = "URLs of the ECR repositories"
  value = {
    api_gateway        = aws_ecr_repository.api_gateway.repository_url
    workflow_engine    = aws_ecr_repository.workflow_engine.repository_url
    workflow_agent     = aws_ecr_repository.workflow_agent.repository_url
    workflow_scheduler = aws_ecr_repository.workflow_scheduler.repository_url
  }
}


output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  sensitive   = true
}

# Service Discovery Outputs
output "service_discovery_namespace_id" {
  description = "ID of the service discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.main.id
}

output "service_discovery_namespace_name" {
  description = "Name of the service discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.main.name
}


output "workflow_agent_service_discovery_dns" {
  description = "Service discovery DNS name for workflow agent"
  value       = "workflow-agent.${local.name_prefix}.local"
}
