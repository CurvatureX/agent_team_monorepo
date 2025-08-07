# SSM Parameters for sensitive data
resource "aws_ssm_parameter" "supabase_url" {
  name  = "/${local.name_prefix}/supabase/url"
  type  = "SecureString"
  value = var.supabase_url

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-supabase-url"
  })
}

resource "aws_ssm_parameter" "supabase_secret_key" {
  name  = "/${local.name_prefix}/supabase/secret-key"
  type  = "SecureString"
  value = var.supabase_secret_key

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-supabase-secret-key"
  })
}


resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${local.name_prefix}/openai/api-key"
  type  = "SecureString"
  value = var.openai_api_key

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-openai-api-key"
  })
}

resource "aws_ssm_parameter" "anthropic_api_key" {
  name  = "/${local.name_prefix}/anthropic/api-key"
  type  = "SecureString"
  value = var.anthropic_api_key

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-anthropic-api-key"
  })
}

resource "aws_ssm_parameter" "database_url" {
  name  = "/${local.name_prefix}/database/url"
  type  = "SecureString"
  value = var.database_url

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-database-url"
  })
}

# Workflow Scheduler SSM Parameters
resource "aws_ssm_parameter" "smtp_username" {
  name  = "/${local.name_prefix}/smtp/username"
  type  = "SecureString"
  value = var.smtp_username

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-smtp-username"
  })
}

resource "aws_ssm_parameter" "smtp_password" {
  name  = "/${local.name_prefix}/smtp/password"
  type  = "SecureString"
  value = var.smtp_password

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-smtp-password"
  })
}

resource "aws_ssm_parameter" "github_app_id" {
  name  = "/${local.name_prefix}/github/app-id"
  type  = "SecureString"
  value = var.github_app_id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-github-app-id"
  })
}

resource "aws_ssm_parameter" "github_app_private_key" {
  name  = "/${local.name_prefix}/github/app-private-key"
  type  = "SecureString"
  value = var.github_app_private_key

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-github-app-private-key"
  })
}

resource "aws_ssm_parameter" "github_webhook_secret" {
  name  = "/${local.name_prefix}/github/webhook-secret"
  type  = "SecureString"
  value = var.github_webhook_secret

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-github-webhook-secret"
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
