# Sensitive values are set via environment variables in CI/CD (TF_VAR_*)
# Do not set supabase_url, supabase_secret_key, openai_api_key, anthropic_api_key here
# as they would override the GitHub Actions environment variables

# SSL Certificate Configuration
certificate_arn = "arn:aws:acm:us-east-1:982081090398:certificate/65f8b420-da5e-445b-9fed-3c0040b93453"
domain_name = "api.starmates.ai"
