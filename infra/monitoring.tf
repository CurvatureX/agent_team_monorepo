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
            ["AWS/NetworkELB", "TargetResponseTime", "LoadBalancer", aws_lb.grpc_internal.arn_suffix],
            ["AWS/NetworkELB", "ActiveFlowCount", "LoadBalancer", aws_lb.grpc_internal.arn_suffix]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "gRPC Load Balancer Metrics"
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

  tags = local.common_tags
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

resource "aws_cloudwatch_metric_alarm" "grpc_nlb_unhealthy_targets" {
  alarm_name          = "${local.name_prefix}-grpc-nlb-unhealthy-targets"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/NetworkELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors gRPC NLB unhealthy targets"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TargetGroup  = aws_lb_target_group.workflow_agent_grpc.arn_suffix
    LoadBalancer = aws_lb.grpc_internal.arn_suffix
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