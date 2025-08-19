variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "agent-team"
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

# ECS Configuration
variable "api_gateway_cpu" {
  description = "CPU units for API Gateway service"
  type        = number
  default     = 512
}

variable "api_gateway_memory" {
  description = "Memory for API Gateway service"
  type        = number
  default     = 1024
}

variable "workflow_engine_cpu" {
  description = "CPU units for Workflow Engine service"
  type        = number
  default     = 1024
}

variable "workflow_engine_memory" {
  description = "Memory for Workflow Engine service"
  type        = number
  default     = 2048
}

variable "workflow_agent_cpu" {
  description = "CPU units for Workflow Agent service"
  type        = number
  default     = 1024
}

variable "workflow_agent_memory" {
  description = "Memory for Workflow Agent service"
  type        = number
  default     = 2048
}

variable "workflow_scheduler_cpu" {
  description = "CPU units for Workflow Scheduler service"
  type        = number
  default     = 512
}

variable "workflow_scheduler_memory" {
  description = "Memory for Workflow Scheduler service"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

# Domain Configuration
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN"
  type        = string
  default     = ""
}


# Environment Variables
variable "supabase_url" {
  description = "Supabase URL"
  type        = string
  sensitive   = true
}

variable "supabase_secret_key" {
  description = "Supabase secret key (service role key)"
  type        = string
  sensitive   = true
}

variable "supabase_anon_key" {
  description = "Supabase anonymous key for RLS operations"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
}

# Workflow Scheduler Configuration
variable "smtp_username" {
  description = "SMTP username for Migadu email service"
  type        = string
  sensitive   = true
  default     = ""
}

variable "smtp_password" {
  description = "SMTP password for Migadu email service"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_app_id" {
  description = "GitHub App ID for GitHub trigger integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_app_private_key" {
  description = "GitHub App private key for GitHub trigger integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_webhook_secret" {
  description = "GitHub webhook secret for GitHub trigger integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_client_id" {
  description = "GitHub App Client ID for GitHub trigger integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "slack_bot_token" {
  description = "Slack bot token for notifications"
  type        = string
  sensitive   = true
}

variable "slack_client_id" {
  description = "Slack OAuth client ID for app installation"
  type        = string
  sensitive   = true
  default     = ""
}

variable "slack_client_secret" {
  description = "Slack OAuth client secret for app installation"
  type        = string
  sensitive   = true
  default     = ""
}

variable "slack_signing_secret" {
  description = "Slack signing secret for webhook verification"
  type        = string
  sensitive   = true
  default     = ""
}

variable "slack_redirect_uri" {
  description = "Slack OAuth redirect URI"
  type        = string
  sensitive   = true
  default     = ""
}

variable "notion_client_id" {
  description = "Notion integration client ID for OAuth"
  type        = string
  sensitive   = true
  default     = ""
}

variable "notion_client_secret" {
  description = "Notion integration client secret for OAuth"
  type        = string
  sensitive   = true
}

variable "notion_redirect_uri" {
  description = "Notion OAuth redirect URI"
  type        = string
  sensitive   = true
  default     = ""
}

# Monitoring Configuration
variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
  default     = ""
}

# Grafana Cloud 集成配置
variable "grafana_cloud_api_key" {
  description = "Grafana Cloud API Key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "grafana_cloud_tenant_id" {
  description = "Grafana Cloud Tenant ID"
  type        = string
  default     = ""
}

variable "grafana_cloud_prometheus_url" {
  description = "Grafana Cloud Prometheus Push URL"
  type        = string
  default     = "https://prometheus-prod-01-eu-west-0.grafana.net/api/prom/push"
}

variable "grafana_cloud_loki_url" {
  description = "Grafana Cloud Loki Push URL"
  type        = string
  default     = "https://logs-prod-006.grafana.net/loki/api/v1/push"
}
