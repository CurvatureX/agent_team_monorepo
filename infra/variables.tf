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

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2
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

# Monitoring Configuration
variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
  default     = ""
}
