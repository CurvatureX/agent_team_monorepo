# CloudWatch Dashboard for gRPC Service Discovery
resource "aws_cloudwatch_dashboard" "grpc_service_dashboard" {
  dashboard_name = "${local.name_prefix}-grpc-services"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.workflow_agent.name, "ClusterName", aws_ecs_cluster.main.name],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", aws_ecs_service.workflow_agent.name, "ClusterName", aws_ecs_cluster.main.name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Workflow Agent Resource Utilization"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.internal.arn_suffix],
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.internal.arn_suffix]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Internal Load Balancer Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "RunningTaskCount", "ServiceName", aws_ecs_service.workflow_agent.name, "ClusterName", aws_ecs_cluster.main.name],
            ["AWS/ECS", "DesiredCount", "ServiceName", aws_ecs_service.workflow_agent.name, "ClusterName", aws_ecs_cluster.main.name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Workflow Agent Task Count"
          period  = 300
        }
      }
    ]
  })
}

# CloudWatch Alarms for gRPC Service Health
resource "aws_cloudwatch_metric_alarm" "workflow_agent_cpu_high" {
  alarm_name          = "${local.name_prefix}-workflow-agent-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors workflow agent CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = aws_ecs_service.workflow_agent.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "workflow_agent_memory_high" {
  alarm_name          = "${local.name_prefix}-workflow-agent-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors workflow agent memory utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = aws_ecs_service.workflow_agent.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "internal_alb_unhealthy_targets" {
  alarm_name          = "${local.name_prefix}-internal-alb-unhealthy-targets"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors internal ALB unhealthy targets"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TargetGroup  = aws_lb_target_group.workflow_agent_http.arn_suffix
    LoadBalancer = aws_lb.internal.arn_suffix
  }

  tags = local.common_tags
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"

  tags = local.common_tags
}

# SNS Topic Subscription (email)
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Log Insights Queries
resource "aws_cloudwatch_query_definition" "grpc_errors" {
  name = "${local.name_prefix}-grpc-errors"

  log_group_names = [
    aws_cloudwatch_log_group.ecs.name
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /ERROR/
| filter @message like /grpc/
| sort @timestamp desc
| limit 100
EOF
}

resource "aws_cloudwatch_query_definition" "service_discovery_logs" {
  name = "${local.name_prefix}-service-discovery"

  log_group_names = [
    aws_cloudwatch_log_group.ecs.name
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /discovery/ or @message like /DNS/ or @message like /endpoint/
| sort @timestamp desc
| limit 100
EOF
}

# ============================================================================
# Grafana Cloud 集成配置
# ============================================================================

# Grafana Cloud API Key 存储在 AWS SSM Parameter Store
resource "aws_ssm_parameter" "grafana_cloud_api_key" {
  count = length(var.grafana_cloud_api_key) > 0 ? 1 : 0

  name  = "/ai-teams/${var.environment}/monitoring/grafana-cloud-api-key"
  type  = "SecureString"
  value = var.grafana_cloud_api_key

  tags = local.common_tags
}

# Grafana Cloud 配置信息
resource "aws_ssm_parameter" "grafana_cloud_config" {
  count = length(var.grafana_cloud_tenant_id) > 0 ? 1 : 0

  name = "/ai-teams/${var.environment}/monitoring/grafana-cloud-config"
  type = "String"
  value = jsonencode({
    tenant_id     = var.grafana_cloud_tenant_id
    prometheus_url = var.grafana_cloud_prometheus_url
    loki_url      = var.grafana_cloud_loki_url
  })

  tags = local.common_tags
}

# OpenTelemetry Collector 配置存储
resource "aws_ssm_parameter" "otel_collector_config" {
  name = "/ai-teams/${var.environment}/monitoring/otel-collector-config"
  type = "String"
  value = jsonencode({
    environment = var.environment
    project    = "starmates-ai-team"
    otlp_endpoint = "http://localhost:4317"
  })

  tags = local.common_tags
}

# CloudWatch Logs Insights 查询 - 追踪 ID 关联
resource "aws_cloudwatch_query_definition" "tracking_id_correlation" {
  name = "${local.name_prefix}-tracking-id-correlation"

  log_group_names = [
    aws_cloudwatch_log_group.ecs.name
  ]

  query_string = <<EOF
fields @timestamp, @message, tracking_id, service, @level
| filter ispresent(tracking_id)
| sort @timestamp desc
| limit 100
EOF
}

# CloudWatch Logs Insights 查询 - 错误追踪
resource "aws_cloudwatch_query_definition" "error_tracking" {
  name = "${local.name_prefix}-error-tracking"

  log_group_names = [
    aws_cloudwatch_log_group.ecs.name
  ]

  query_string = <<EOF
fields @timestamp, @message, tracking_id, service, error.type, error.message
| filter @level = "ERROR"
| filter ispresent(tracking_id)
| sort @timestamp desc
| limit 50
EOF
}

# CloudWatch Logs Insights 查询 - 请求性能分析
resource "aws_cloudwatch_query_definition" "request_performance" {
  name = "${local.name_prefix}-request-performance"

  log_group_names = [
    aws_cloudwatch_log_group.ecs.name
  ]

  query_string = <<EOF
fields @timestamp, tracking_id, request.method, request.path, request.duration, response.status
| filter ispresent(request.duration)
| filter request.duration > 1.0
| sort request.duration desc
| limit 50
EOF
}
