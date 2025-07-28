# Sensitive values are set via environment variables in CI/CD (TF_VAR_*)
# Do not set supabase_url, supabase_secret_key, openai_api_key, anthropic_api_key here
# as they would override the GitHub Actions environment variables
