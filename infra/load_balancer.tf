# Application Load Balancer for HTTP/HTTPS traffic
resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb"
  })
}

# Internal Application Load Balancer for backend services (HTTP)
resource "aws_lb" "internal" {
  name               = "${local.name_prefix}-int-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_internal.id]
  subnets            = aws_subnet.private[*].id

  enable_deletion_protection = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-internal-alb"
  })
}

# Target Group for API Gateway (HTTP)
resource "aws_lb_target_group" "api_gateway" {
  name        = "${local.name_prefix}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-gateway-tg"
  })
}

# Target Group for Workflow Agent (HTTP)
resource "aws_lb_target_group" "workflow_agent_http" {
  name        = "${local.name_prefix}-agent-tg"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-agent-tg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Target Group for Workflow Engine (HTTP)
resource "aws_lb_target_group" "workflow_engine_http" {
  name        = "${local.name_prefix}-engine-tg"
  port        = 8002
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-engine-tg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Target Group for Workflow Scheduler (HTTP)
resource "aws_lb_target_group" "workflow_scheduler" {
  name        = "${local.name_prefix}-scheduler-tg"
  port        = 8003
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workflow-scheduler-tg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ALB Listener for HTTP/HTTPS
resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = var.certificate_arn != "" ? "443" : "80"
  protocol          = var.certificate_arn != "" ? "HTTPS" : "HTTP"
  ssl_policy        = var.certificate_arn != "" ? "ELBSecurityPolicy-TLS-1-2-2017-01" : null
  certificate_arn   = var.certificate_arn != "" ? var.certificate_arn : null

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_gateway.arn
  }

  tags = local.common_tags
}

# Internal ALB Listener for backend services
resource "aws_lb_listener" "internal" {
  load_balancer_arn = aws_lb.internal.arn
  port              = "80"
  protocol          = "HTTP"

  # Default action - forward to Workflow Agent
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_agent_http.arn
  }

  tags = local.common_tags
}

# Internal ALB Listener Rules for path-based routing
resource "aws_lb_listener_rule" "workflow_agent" {
  listener_arn = aws_lb_listener.internal.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_agent_http.arn
  }

  condition {
    path_pattern {
      values = ["/process-conversation*", "/v1/workflows/generate*", "/v1/workflows/*/refine*", "/v1/workflows/validate*"]
    }
  }

  tags = local.common_tags
}

resource "aws_lb_listener_rule" "workflow_engine" {
  listener_arn = aws_lb_listener.internal.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_engine_http.arn
  }

  condition {
    path_pattern {
      values = ["/v1/workflows*", "/v1/triggers*", "/v1/executions*"]
    }
  }

  tags = local.common_tags
}

resource "aws_lb_listener_rule" "workflow_scheduler" {
  listener_arn = aws_lb_listener.internal.arn
  priority     = 300

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.workflow_scheduler.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/deployment*", "/api/v1/triggers*"]
    }
  }

  tags = local.common_tags
}

# HTTP to HTTPS redirect (if certificate is provided)
resource "aws_lb_listener" "redirect" {
  count = var.certificate_arn != "" ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = local.common_tags
}
