#!/bin/bash

# Simple Supabase Migration Script
# Uses Supabase CLI with existing SUPABASE_URL and SUPABASE_SECRET_KEY

set -euo pipefail

# Check if we can run Supabase CLI via npx
if ! npx supabase --version &> /dev/null; then
    echo "❌ Supabase CLI not found. Install with: npm install supabase --save-dev"
    exit 1
fi

# Check if SUPABASE_URL is already a database URL or HTTP URL
if [[ "${SUPABASE_URL:-}" =~ ^postgresql:// ]]; then
    # SUPABASE_URL is already a database connection string
    DB_URL="${SUPABASE_URL}?application_name=migration_check_$(date +%s)"
    echo "✅ Using database URL from SUPABASE_URL"
else
    # Traditional setup - validate environment variables
    if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_SECRET_KEY:-}" ]]; then
        echo "❌ SUPABASE_URL and SUPABASE_SECRET_KEY must be set"
        exit 1
    fi

    # Validate DB password for traditional setup
    if [[ -z "${SUPABASE_DB_PASSWORD:-}" ]]; then
        echo "❌ SUPABASE_DB_PASSWORD must be set (your Postgres database password)"
        exit 1
    fi

    # Database connection string - use pooler with unique application name to avoid conflicts
    DB_URL="postgresql://postgres.mkrczzgjeduruwxpanbj:${SUPABASE_DB_PASSWORD}@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?application_name=migration_check_$(date +%s)"
fi

cd "$(dirname "$0")/../supabase"

case "${1:-check}" in
    "check")
        echo "🔍 Checking for pending migrations..."
        # Retry logic to handle connection pooling issues
        MAX_RETRIES=3
        RETRY_COUNT=0
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if npx supabase migration list --db-url "$DB_URL" 2>/dev/null; then
                echo "✅ Migration check completed successfully"
                break
            else
                RETRY_COUNT=$((RETRY_COUNT + 1))
                echo "⚠️ Retry $RETRY_COUNT/$MAX_RETRIES - Connection issue, retrying in 2 seconds..."
                sleep 2
            fi
        done

        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "❌ Failed to connect after $MAX_RETRIES attempts. Using direct psql check..."
            # Fallback to direct database check - extract connection details from DB_URL
            if [[ "${SUPABASE_URL:-}" =~ ^postgresql:// ]]; then
                # Use the database URL directly with psql
                APPLIED_MIGRATIONS=$(psql "$DB_URL" -t -c "SELECT version FROM supabase_migrations.schema_migrations ORDER BY version DESC;" | xargs)
            else
                # Traditional setup with separate password
                APPLIED_MIGRATIONS=$(PGPASSWORD="$SUPABASE_DB_PASSWORD" psql -h aws-0-ap-southeast-1.pooler.supabase.com -p 6543 -U postgres.mkrczzgjeduruwxpanbj -d postgres -t -c "SELECT version FROM supabase_migrations.schema_migrations ORDER BY version DESC;" | xargs)
            fi

            # Check for pending migrations by comparing with files
            PENDING_COUNT=0
            echo "🔍 Applied migrations: $APPLIED_MIGRATIONS"

            for migration_file in migrations/*.sql; do
                if [ -f "$migration_file" ]; then
                    # Extract migration version from filename
                    MIGRATION_VERSION=$(basename "$migration_file" .sql)
                    if [[ ! " $APPLIED_MIGRATIONS " =~ " $MIGRATION_VERSION " ]]; then
                        echo "⚠️  Pending migration: $MIGRATION_VERSION"
                        PENDING_COUNT=$((PENDING_COUNT + 1))
                    fi
                fi
            done

            if [ $PENDING_COUNT -gt 0 ]; then
                echo "❌ Found $PENDING_COUNT pending migrations"
                exit 1
            else
                echo "✅ All migrations are applied"
            fi
        fi
        ;;
    "migrate")
        echo "🚀 Applying migrations..."

        # Get list of applied migrations
        if [[ "${SUPABASE_URL:-}" =~ ^postgresql:// ]]; then
            APPLIED_MIGRATIONS=$(psql "$DB_URL" -t -c "SELECT version FROM supabase_migrations.schema_migrations ORDER BY version DESC;" | xargs)
        else
            APPLIED_MIGRATIONS=$(PGPASSWORD="$SUPABASE_DB_PASSWORD" psql -h aws-0-ap-southeast-1.pooler.supabase.com -p 6543 -U postgres.mkrczzgjeduruwxpanbj -d postgres -t -c "SELECT version FROM supabase_migrations.schema_migrations ORDER BY version DESC;" | xargs)
        fi

        echo "🔍 Currently applied migrations: $APPLIED_MIGRATIONS"

        # Apply pending migrations one by one
        APPLIED_COUNT=0
        for migration_file in migrations/*.sql; do
            if [ -f "$migration_file" ]; then
                MIGRATION_VERSION=$(basename "$migration_file" .sql)
                if [[ ! " $APPLIED_MIGRATIONS " =~ " $MIGRATION_VERSION " ]]; then
                    echo "🔄 Applying migration: $MIGRATION_VERSION"

                    # Apply the migration
                    if [[ "${SUPABASE_URL:-}" =~ ^postgresql:// ]]; then
                        if psql "$DB_URL" -f "$migration_file"; then
                            # Record the migration
                            psql "$DB_URL" -c "INSERT INTO supabase_migrations.schema_migrations (version, statements, name) VALUES ('$MIGRATION_VERSION', '{}', '$MIGRATION_VERSION')" || true
                            echo "✅ Applied: $MIGRATION_VERSION"
                            APPLIED_COUNT=$((APPLIED_COUNT + 1))
                        else
                            echo "❌ Failed to apply migration: $MIGRATION_VERSION"
                            exit 1
                        fi
                    else
                        if PGPASSWORD="$SUPABASE_DB_PASSWORD" psql -h aws-0-ap-southeast-1.pooler.supabase.com -p 6543 -U postgres.mkrczzgjeduruwxpanbj -d postgres -f "$migration_file"; then
                            # Record the migration
                            PGPASSWORD="$SUPABASE_DB_PASSWORD" psql -h aws-0-ap-southeast-1.pooler.supabase.com -p 6543 -U postgres.mkrczzgjeduruwxpanbj -d postgres -c "INSERT INTO supabase_migrations.schema_migrations (version, statements, name) VALUES ('$MIGRATION_VERSION', '{}', '$MIGRATION_VERSION')" || true
                            echo "✅ Applied: $MIGRATION_VERSION"
                            APPLIED_COUNT=$((APPLIED_COUNT + 1))
                        else
                            echo "❌ Failed to apply migration: $MIGRATION_VERSION"
                            exit 1
                        fi
                    fi
                fi
            fi
        done

        if [ $APPLIED_COUNT -gt 0 ]; then
            echo "✅ Applied $APPLIED_COUNT migrations successfully"
        else
            echo "ℹ️  No pending migrations to apply"
        fi
        ;;
    "status")
        echo "📊 Migration status:"
        # Use direct psql for more reliable status check
        if [[ "${SUPABASE_URL:-}" =~ ^postgresql:// ]]; then
            # Use the database URL directly with psql
            psql "$DB_URL" -c "SELECT version, name FROM supabase_migrations.schema_migrations ORDER BY version DESC LIMIT 20;" || exit 1
        else
            # Traditional setup with separate password
            PGPASSWORD="$SUPABASE_DB_PASSWORD" psql -h aws-0-ap-southeast-1.pooler.supabase.com -p 6543 -U postgres.mkrczzgjeduruwxpanbj -d postgres -c "SELECT version, name FROM supabase_migrations.schema_migrations ORDER BY version DESC LIMIT 20;" || exit 1
        fi
        ;;
    *)
        echo "Usage: $0 [check|migrate|status]"
        exit 1
        ;;
esac
