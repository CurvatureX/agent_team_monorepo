# Service Discovery Namespace
resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "${local.name_prefix}.local"
  description = "Service discovery namespace for ${local.name_prefix}"
  vpc         = aws_vpc.main.id

  tags = local.common_tags
}

# Service Discovery Service for API Gateway
resource "aws_service_discovery_service" "api_gateway" {
  name = "api-gateway"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }



  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-gateway-discovery"
  })
}

# Service Discovery Service for Workflow Engine
resource "aws_service_discovery_service" "workflow_engine" {
  name = "workflow-engine"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-engine-discovery"
  })
}

# Service Discovery Service for Workflow Agent (gRPC)
resource "aws_service_discovery_service" "workflow_agent" {
  name = "workflow-agent"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-agent-discovery"
  })
}

# Service Discovery Service for Workflow Scheduler
resource "aws_service_discovery_service" "workflow_scheduler" {
  name = "workflow-scheduler"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-scheduler-discovery"
  })
}
