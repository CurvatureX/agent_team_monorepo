#!/bin/bash

# Simple Supabase Migration Script
# Uses Supabase CLI with existing SUPABASE_URL and SUPABASE_SECRET_KEY

set -euo pipefail

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found. Install with: npm install -g supabase"
    exit 1
fi

# Validate environment variables
if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_SECRET_KEY:-}" ]]; then
    echo "❌ SUPABASE_URL and SUPABASE_SECRET_KEY must be set"
    exit 1
fi

# Extract project ID from URL
PROJECT_ID=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|\.supabase\.co||')

cd "$(dirname "$0")/../supabase"

# Validate DB password
if [[ -z "${SUPABASE_DB_PASSWORD:-}" ]]; then
    echo "❌ SUPABASE_DB_PASSWORD must be set (your Postgres database password)"
    exit 1
fi

# Database connection string - use pooler for better connectivity
DB_URL="postgresql://postgres.mkrczzgjeduruwxpanbj:${SUPABASE_DB_PASSWORD}@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

case "${1:-check}" in
    "check")
        echo "🔍 Checking for pending migrations..."
        supabase migration list --db-url "$DB_URL"
        ;;
    "migrate")
        echo "🚀 Applying migrations..."
        supabase db push --db-url "$DB_URL"
        ;;
    "status")
        echo "📊 Migration status:"
        supabase migration list --db-url "$DB_URL"
        ;;
    *)
        echo "Usage: $0 [check|migrate|status]"
        exit 1
        ;;
esac
