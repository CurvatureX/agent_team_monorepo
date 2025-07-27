# Configuration file for Terraform variables
# SECURITY NOTE: All sensitive values should be set via environment variables
# See terraform.tfvars.example for required variables

# Non-sensitive configuration
supabase_url = "https://mkrczzgjeduruwxpanbj.supabase.co"

# Sensitive values - these should be set via environment variables:
# export TF_VAR_supabase_secret_key="your_supabase_secret_key"
# export TF_VAR_openai_api_key="your_openai_api_key"
# export TF_VAR_anthropic_api_key="your_anthropic_api_key"

# Placeholder values (will be overridden by environment variables)
supabase_secret_key = ""
openai_api_key = ""
anthropic_api_key = ""
