# SSM Parameters for sensitive data
resource "aws_ssm_parameter" "supabase_url" {
  name  = "/${local.name_prefix}/supabase/url"
  type  = "SecureString"
  value = var.supabase_url != "" ? var.supabase_url : "placeholder"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-supabase-url"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "supabase_anon_key" {
  name  = "/${local.name_prefix}/supabase/anon-key"
  type  = "SecureString"
  value = var.supabase_anon_key != "" ? var.supabase_anon_key : "placeholder"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-supabase-anon-key"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "supabase_service_role_key" {
  name  = "/${local.name_prefix}/supabase/service-role-key"
  type  = "SecureString"
  value = var.supabase_service_role_key != "" ? var.supabase_service_role_key : "placeholder"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-supabase-service-role-key"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${local.name_prefix}/openai/api-key"
  type  = "SecureString"
  value = var.openai_api_key != "" ? var.openai_api_key : "placeholder"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-openai-api-key"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "anthropic_api_key" {
  name  = "/${local.name_prefix}/anthropic/api-key"
  type  = "SecureString"
  value = var.anthropic_api_key != "" ? var.anthropic_api_key : "placeholder"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-anthropic-api-key"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/${local.name_prefix}/database/password"
  type  = "SecureString"
  value = random_password.db_password.result

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-password"
  })
}

# IAM policy for ECS tasks to access SSM parameters
resource "aws_iam_policy" "ecs_ssm_policy" {
  name        = "${local.name_prefix}-ecs-ssm-policy"
  description = "Policy for ECS tasks to access SSM parameters"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${local.name_prefix}/*"
        ]
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_ssm" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_ssm_policy.arn
}
