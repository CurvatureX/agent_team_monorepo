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
    api_gateway     = aws_ecr_repository.api_gateway.repository_url
    workflow_engine = aws_ecr_repository.workflow_engine.repository_url
  }
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  sensitive   = true
}
