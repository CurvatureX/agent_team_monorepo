# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs.name
      }
    }
  }

  tags = local.common_tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 7

  tags = local.common_tags
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${local.name_prefix}-ecs-task-execution-role"

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

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role
resource "aws_iam_role" "ecs_task_role" {
  name = "${local.name_prefix}-ecs-task-role"

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

# IAM Policy for Service Discovery
resource "aws_iam_policy" "service_discovery" {
  name        = "${local.name_prefix}-service-discovery"
  description = "Policy for ECS tasks to access service discovery"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "servicediscovery:DiscoverInstances",
          "servicediscovery:GetService",
          "servicediscovery:ListServices"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTasks",
          "ecs:ListTasks"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

# Attach Service Discovery policy to ECS task role
resource "aws_iam_role_policy_attachment" "ecs_task_service_discovery" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.service_discovery.arn
}

# IAM Policy for OpenTelemetry X-Ray and CloudWatch
resource "aws_iam_policy" "otel_observability" {
  name        = "${local.name_prefix}-otel-observability"
  description = "Policy for OpenTelemetry X-Ray and CloudWatch access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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
            "cloudwatch:namespace" = "AgentTeam"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

# Attach OTEL policy to ECS task role
resource "aws_iam_role_policy_attachment" "ecs_task_otel" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.otel_observability.arn
}

# API Gateway Task Definition
resource "aws_ecs_task_definition" "api_gateway" {
  family                   = "${local.name_prefix}-api-gateway"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_gateway_cpu
  memory                   = var.api_gateway_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "api-gateway"
      image = "${aws_ecr_repository.api_gateway.repository_url}:${var.image_tag}"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DEBUG"
          value = "true"
        },
        {
          name  = "LOG_FORMAT"
          value = "json"
        },
        {
          name  = "LOG_LEVEL"
          value = "DEBUG"
        },
        {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        },
        {
          name  = "WORKFLOW_SERVICE_DNS_NAME"
          value = "workflow-agent.${local.name_prefix}.local"
        },
        {
          name  = "WORKFLOW_AGENT_URL"
          value = "http://${aws_lb.internal.dns_name}:8001"
        },
        {
          name  = "WORKFLOW_ENGINE_URL"
          value = "http://${aws_lb.internal.dns_name}:8002"
        },
        {
          name  = "WORKFLOW_SCHEDULER_URL"
          value = "http://${aws_lb.internal.dns_name}:8003"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "REDIS_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "OTEL_SDK_DISABLED"
          value = "true"
        }
      ]

      secrets = [
        {
          name      = "SUPABASE_URL"
          valueFrom = aws_ssm_parameter.supabase_url.arn
        },
        {
          name      = "SUPABASE_SECRET_KEY"
          valueFrom = aws_ssm_parameter.supabase_secret_key.arn
        },
        {
          name      = "SUPABASE_PUB_KEY"
          valueFrom = aws_ssm_parameter.supabase_pub_key.arn
        },
        {
          name      = "NOTION_CLIENT_ID"
          valueFrom = aws_ssm_parameter.notion_client_id.arn
        },
        {
          name      = "NOTION_CLIENT_SECRET"
          valueFrom = aws_ssm_parameter.notion_client_secret.arn
        },
        {
          name      = "NOTION_REDIRECT_URI"
          valueFrom = aws_ssm_parameter.notion_redirect_uri.arn
        },
        {
          name      = "SLACK_SIGNING_SECRET"
          valueFrom = aws_ssm_parameter.slack_signing_secret.arn
        },
        {
          name      = "SLACK_CLIENT_ID"
          valueFrom = aws_ssm_parameter.slack_client_id.arn
        },
        {
          name      = "SLACK_CLIENT_SECRET"
          valueFrom = aws_ssm_parameter.slack_client_secret.arn
        },
        {
          name      = "SLACK_REDIRECT_URI"
          valueFrom = aws_ssm_parameter.slack_redirect_uri.arn
        },
        {
          name      = "GOOGLE_CLIENT_ID"
          valueFrom = aws_ssm_parameter.google_client_id.arn
        },
        {
          name      = "GOOGLE_CLIENT_SECRET"
          valueFrom = aws_ssm_parameter.google_client_secret.arn
        },
        {
          name      = "GOOGLE_REDIRECT_URI"
          valueFrom = aws_ssm_parameter.google_redirect_uri.arn
        },
        {
          name      = "DNS_DOMAIN_NAME"
          valueFrom = aws_ssm_parameter.dns_domain_name.arn
        }
      ]


      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api-gateway"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = local.common_tags
}

# Workflow Engine Task Definition
resource "aws_ecs_task_definition" "workflow_engine" {
  family                   = "${local.name_prefix}-workflow-engine"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.workflow_engine_cpu
  memory                   = var.workflow_engine_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "workflow-engine"
      image = "${aws_ecr_repository.workflow_engine.repository_url}:${var.image_tag}"

      portMappings = [
        {
          containerPort = 8002
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DEBUG"
          value = "true"
        },
        {
          name  = "LOG_FORMAT"
          value = "json"
        },
        {
          name  = "LOG_LEVEL"
          value = "DEBUG"
        },
        {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        },
        {
          name  = "HOST"
          value = "0.0.0.0"
        },
        {
          name  = "PORT"
          value = "8002"
        },
        {
          name  = "API_GATEWAY_URL"
          value = "http://api-gateway.${local.name_prefix}.local:8000"
        },
        {
          name  = "REDIS_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/2"
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "OTEL_SDK_DISABLED"
          value = "true"
        }
      ]

      secrets = [
        {
          name      = "OPENAI_API_KEY"
          valueFrom = aws_ssm_parameter.openai_api_key.arn
        },
        {
          name      = "OPENAI_MODEL"
          valueFrom = aws_ssm_parameter.openai_model.arn
        },
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = aws_ssm_parameter.anthropic_api_key.arn
        },
        {
          name      = "GEMINI_API_KEY"
          valueFrom = aws_ssm_parameter.gemini_api_key.arn
        },
        {
          name      = "SUPABASE_URL"
          valueFrom = aws_ssm_parameter.supabase_url.arn
        },
        {
          name      = "SUPABASE_SECRET_KEY"
          valueFrom = aws_ssm_parameter.supabase_secret_key.arn
        },
        {
          name      = "SUPABASE_PUB_KEY"
          valueFrom = aws_ssm_parameter.supabase_pub_key.arn
        },
        {
          name      = "DATABASE_URL"
          valueFrom = aws_ssm_parameter.database_url.arn
        },
        {
          name      = "DNS_DOMAIN_NAME"
          valueFrom = aws_ssm_parameter.dns_domain_name.arn
        }
      ]


      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "workflow-engine"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8002/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 120
      }
    }
  ])

  tags = local.common_tags
}

# ECS Service for API Gateway
resource "aws_ecs_service" "api_gateway" {
  name            = "api-gateway-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api_gateway.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_gateway.arn
    container_name   = "api-gateway"
    container_port   = 8000
  }

  service_registries {
    registry_arn = aws_service_discovery_service.api_gateway.arn
  }

  depends_on = [aws_lb_listener.main]

  tags = local.common_tags
}

# Workflow Agent Task Definition (gRPC service)
resource "aws_ecs_task_definition" "workflow_agent" {
  family                   = "${local.name_prefix}-workflow-agent"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.workflow_agent_cpu
  memory                   = var.workflow_agent_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "workflow-agent"
      image = "${aws_ecr_repository.workflow_agent.repository_url}:${var.image_tag}"

      portMappings = [
        {
          containerPort = 8001
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DEBUG"
          value = "true"
        },
        {
          name  = "LOG_FORMAT"
          value = "json"
        },
        {
          name  = "LOG_LEVEL"
          value = "DEBUG"
        },
        {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        },
        {
          name  = "HOST"
          value = "0.0.0.0"
        },
        {
          name  = "PORT"
          value = "8001"
        },
        {
          name  = "FASTAPI_PORT"
          value = "8001"
        },
        {
          name  = "WORKFLOW_ENGINE_URL"
          value = "http://workflow-engine.${local.name_prefix}.local:8002"
        },
        {
          name  = "API_GATEWAY_URL"
          value = "http://api-gateway.${local.name_prefix}.local:8000"
        },
        {
          name  = "REDIS_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "DEFAULT_MODEL_PROVIDER"
          value = "openai"
        },
        {
          name  = "DEFAULT_MODEL_NAME"
          value = "gpt-5-mini-2025-08-07"  # Updated to GPT-5 mini model
        },
        {
          name  = "LLM_PROVIDER"
          value = "openai"
        },
        {
          name  = "LLM_TIMEOUT"
          value = "1200"  # 20 minutes timeout
        },
        {
          name  = "LLM_MAX_TOKENS"
          value = "0"  # 0 means no limit
        },
        {
          name  = "LLM_TEMPERATURE"
          value = "0"
        },
        {
          name  = "OTEL_SDK_DISABLED"
          value = "true"
        }
      ]

      secrets = [
        {
          name      = "OPENAI_API_KEY"
          valueFrom = aws_ssm_parameter.openai_api_key.arn
        },
        {
          name      = "OPENAI_MODEL"
          valueFrom = aws_ssm_parameter.openai_model.arn
        },
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = aws_ssm_parameter.anthropic_api_key.arn
        },
        {
          name      = "GEMINI_API_KEY"
          valueFrom = aws_ssm_parameter.gemini_api_key.arn
        },
        {
          name      = "SUPABASE_URL"
          valueFrom = aws_ssm_parameter.supabase_url.arn
        },
        {
          name      = "SUPABASE_SECRET_KEY"
          valueFrom = aws_ssm_parameter.supabase_secret_key.arn
        },
        {
          name      = "DNS_DOMAIN_NAME"
          valueFrom = aws_ssm_parameter.dns_domain_name.arn
        }
      ]


      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "workflow-agent"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 120
      }
    }
  ])

  tags = local.common_tags
}

# ECS Service for Workflow Engine
resource "aws_ecs_service" "workflow_engine" {
  name            = "workflow-engine-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.workflow_engine.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.workflow_engine_http.arn
    container_name   = "workflow-engine"
    container_port   = 8002
  }

  service_registries {
    registry_arn = aws_service_discovery_service.workflow_engine.arn
  }

  depends_on = [aws_lb_listener.internal]

  tags = local.common_tags
}

# ECS Service for Workflow Agent (gRPC)
resource "aws_ecs_service" "workflow_agent" {
  name            = "workflow-agent-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.workflow_agent.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.workflow_agent_http.arn
    container_name   = "workflow-agent"
    container_port   = 8001
  }

  service_registries {
    registry_arn = aws_service_discovery_service.workflow_agent.arn
  }

  depends_on = [aws_lb_listener.internal]

  tags = local.common_tags
}

# Workflow Scheduler Task Definition
resource "aws_ecs_task_definition" "workflow_scheduler" {
  family                   = "${local.name_prefix}-workflow-scheduler"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.workflow_scheduler_cpu
  memory                   = var.workflow_scheduler_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "workflow-scheduler"
      image = "${aws_ecr_repository.workflow_scheduler.repository_url}:${var.image_tag}"

      portMappings = [
        {
          containerPort = 8003
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DEBUG"
          value = "true"
        },
        {
          name  = "LOG_FORMAT"
          value = "json"
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        },
        {
          name  = "HOST"
          value = "0.0.0.0"
        },
        {
          name  = "PORT"
          value = "8003"
        },
        {
          name  = "WORKFLOW_ENGINE_URL"
          value = "http://${aws_lb.internal.dns_name}:8002"
        },
        {
          name  = "API_GATEWAY_URL"
          value = "http://${aws_lb.internal.dns_name}:8000"
        },
        {
          name  = "REDIS_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/1"
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "OTEL_SDK_DISABLED"
          value = "true"
        }
      ]

      secrets = [
        {
          name      = "SUPABASE_URL"
          valueFrom = aws_ssm_parameter.supabase_url.arn
        },
        {
          name      = "SUPABASE_SECRET_KEY"
          valueFrom = aws_ssm_parameter.supabase_secret_key.arn
        },
        {
          name      = "SUPABASE_PUB_KEY"
          valueFrom = aws_ssm_parameter.supabase_pub_key.arn
        },
        {
          name      = "DATABASE_URL"
          valueFrom = aws_ssm_parameter.database_url.arn
        },
        {
          name      = "SMTP_USERNAME"
          valueFrom = aws_ssm_parameter.smtp_username.arn
        },
        {
          name      = "SMTP_PASSWORD"
          valueFrom = aws_ssm_parameter.smtp_password.arn
        },
        {
          name      = "GITHUB_APP_ID"
          valueFrom = aws_ssm_parameter.github_app_id.arn
        },
        {
          name      = "GITHUB_APP_PRIVATE_KEY"
          valueFrom = aws_ssm_parameter.github_app_private_key.arn
        },
        {
          name      = "GITHUB_WEBHOOK_SECRET"
          valueFrom = aws_ssm_parameter.github_webhook_secret.arn
        },
        {
          name      = "GITHUB_CLIENT_ID"
          valueFrom = aws_ssm_parameter.github_client_id.arn
        },
        {
          name      = "DEFAULT_SLACK_BOT_TOKEN"
          valueFrom = aws_ssm_parameter.slack_bot_token.arn
        },
        {
          name      = "SLACK_CLIENT_ID"
          valueFrom = aws_ssm_parameter.slack_client_id.arn
        },
        {
          name      = "SLACK_CLIENT_SECRET"
          valueFrom = aws_ssm_parameter.slack_client_secret.arn
        },
        {
          name      = "SLACK_REDIRECT_URI"
          valueFrom = aws_ssm_parameter.slack_redirect_uri.arn
        },
        {
          name      = "SLACK_SIGNING_SECRET"
          valueFrom = aws_ssm_parameter.slack_signing_secret.arn
        },
        {
          name      = "GOOGLE_CLIENT_ID"
          valueFrom = aws_ssm_parameter.google_client_id.arn
        },
        {
          name      = "GOOGLE_CLIENT_SECRET"
          valueFrom = aws_ssm_parameter.google_client_secret.arn
        },
        {
          name      = "GOOGLE_REDIRECT_URI"
          valueFrom = aws_ssm_parameter.google_redirect_uri.arn
        },
        {
          name      = "NOTION_CLIENT_ID"
          valueFrom = aws_ssm_parameter.notion_client_id.arn
        },
        {
          name      = "NOTION_CLIENT_SECRET"
          valueFrom = aws_ssm_parameter.notion_client_secret.arn
        },
        {
          name      = "NOTION_REDIRECT_URI"
          valueFrom = aws_ssm_parameter.notion_redirect_uri.arn
        },
        {
          name      = "DNS_DOMAIN_NAME"
          valueFrom = aws_ssm_parameter.dns_domain_name.arn
        }
      ]


      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "workflow-scheduler"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8003/health || exit 1"]
        interval    = 30
        timeout     = 20
        retries     = 5
        startPeriod = 300  # Increased to 5 minutes for complex initialization
      }
    }
  ])

  tags = local.common_tags
}

# ECS Service for Workflow Scheduler
resource "aws_ecs_service" "workflow_scheduler" {
  name            = "workflow-scheduler-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.workflow_scheduler.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.workflow_scheduler.arn
    container_name   = "workflow-scheduler"
    container_port   = 8003
  }

  service_registries {
    registry_arn = aws_service_discovery_service.workflow_scheduler.arn
  }

  depends_on = [aws_lb_listener.internal]

  tags = local.common_tags
}
