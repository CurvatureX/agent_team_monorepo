# OpenTelemetry Collector ECS Task Definition
resource "aws_ecs_task_definition" "otel_collector" {
  family                   = "${local.name_prefix}-otel-collector"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.otel_collector_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "otel-collector"
      # Use AWS distro for OpenTelemetry Collector
      image = "public.ecr.aws/aws-observability/aws-otel-collector:latest"

      portMappings = [
        {
          containerPort = 4317  # gRPC
          protocol      = "tcp"
        },
        {
          containerPort = 4318  # HTTP
          protocol      = "tcp"
        },
        {
          containerPort = 8889  # Prometheus metrics
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "AOT_CONFIG_CONTENT"
          value = <<-EOT
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
  memory_limiter:
    check_interval: 1s
    limit_mib: 256

exporters:
  awsxray:
    region: ${var.aws_region}
    no_verify_ssl: false
    local_mode: false
  
  awsemf:
    region: ${var.aws_region}
    namespace: ${local.name_prefix}
    dimension_rollup_option: "NoDimensionRollup"
    
  prometheus:
    endpoint: "0.0.0.0:8889"
    
  logging:
    loglevel: info

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [awsxray, logging]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [awsemf, prometheus, logging]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [logging]
EOT
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.otel_collector.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "otel-collector"
        }
      }

      healthCheck = {
        command     = ["CMD", "/healthcheck"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    }
  ])

  tags = local.common_tags
}

# CloudWatch Log Group for OTEL Collector
resource "aws_cloudwatch_log_group" "otel_collector" {
  name              = "/ecs/${local.name_prefix}/otel-collector"
  retention_in_days = 7

  tags = local.common_tags
}

# OTEL Collector Task Role with permissions for CloudWatch
resource "aws_iam_role" "otel_collector_task_role" {
  name = "${local.name_prefix}-otel-collector-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for OTEL Collector to write to CloudWatch
resource "aws_iam_policy" "otel_collector_cloudwatch" {
  name        = "${local.name_prefix}-otel-collector-cloudwatch"
  description = "Policy for OTEL Collector to write to CloudWatch"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = local.name_prefix
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "otel_collector_cloudwatch" {
  role       = aws_iam_role.otel_collector_task_role.name
  policy_arn = aws_iam_policy.otel_collector_cloudwatch.arn
}

# Additional IAM policy for EC2 and ECS discovery (optional for service discovery)
resource "aws_iam_policy" "otel_collector_discovery" {
  name        = "${local.name_prefix}-otel-collector-discovery"
  description = "Policy for OTEL Collector to discover ECS services"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:ListTasks",
          "ecs:ListServices",
          "ecs:DescribeServices",
          "ecs:DescribeContainerInstances",
          "ecs:DescribeTasks",
          "ecs:DescribeTaskDefinition",
          "ec2:DescribeInstances",
          "ec2:DescribeNodes"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "otel_collector_discovery" {
  role       = aws_iam_role.otel_collector_task_role.name
  policy_arn = aws_iam_policy.otel_collector_discovery.arn
}

# ECS Service for OTEL Collector
resource "aws_ecs_service" "otel_collector" {
  name            = "${local.name_prefix}-otel-collector"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.otel_collector.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.otel_collector.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.otel_collector.arn
  }

  tags = local.common_tags
}

# Service Discovery for OTEL Collector
resource "aws_service_discovery_service" "otel_collector" {
  name = "otel-collector"

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

  tags = local.common_tags
}

# Security Group for OTEL Collector
resource "aws_security_group" "otel_collector" {
  name        = "${local.name_prefix}-otel-collector"
  description = "Security group for OpenTelemetry Collector"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 4317
    to_port         = 4317
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "gRPC from ECS tasks"
  }

  ingress {
    from_port       = 4318
    to_port         = 4318
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "HTTP from ECS tasks"
  }

  ingress {
    from_port       = 8889
    to_port         = 8889
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "Prometheus metrics"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = local.common_tags
}

# Output the OTEL Collector endpoint for other services
output "otel_collector_endpoint" {
  value       = "otel-collector.${aws_service_discovery_private_dns_namespace.main.name}:4317"
  description = "OpenTelemetry Collector gRPC endpoint"
}