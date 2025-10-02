#!/usr/bin/env python3
"""
Migration utility for the workflow scheduler service
This can be run from within the workflow scheduler container
"""
import asyncio
import logging
import os
import sys

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.direct_db_service import DirectDBService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_schema_migrations():
    """Run database schema migrations using the workflow scheduler's database connection"""

    db_service = DirectDBService()

    try:
        # Initialize the connection pool
        await db_service._initialize_pool()

        async with db_service.pool.acquire() as conn:
            logger.info("✅ Connected to database via workflow scheduler connection")

            # Migration 1: Add deployment columns to workflows table
            logger.info("🔧 Adding deployment columns to workflows table...")

            deployment_columns = [
                ("deployment_status", "VARCHAR(50) NOT NULL DEFAULT 'DRAFT'"),
                ("deployed_at", "TIMESTAMP WITH TIME ZONE"),
                ("deployed_by", "UUID"),
                ("undeployed_at", "TIMESTAMP WITH TIME ZONE"),
                ("deployment_version", "INTEGER NOT NULL DEFAULT 1"),
                ("deployment_config", "JSON NOT NULL DEFAULT '{}'"),
            ]

            for column_name, column_def in deployment_columns:
                try:
                    sql = (
                        f"ALTER TABLE workflows ADD COLUMN IF NOT EXISTS {column_name} {column_def}"
                    )
                    await conn.execute(sql)
                    logger.info(f"✅ Added column: {column_name}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"✅ Column {column_name} already exists")
                    else:
                        logger.error(f"❌ Error adding column {column_name}: {e}")

            # Add indexes
            logger.info("🔧 Adding indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_workflows_deployment_status ON workflows(deployment_status)",
                "CREATE INDEX IF NOT EXISTS idx_workflows_deployed_at ON workflows(deployed_at)",
                "CREATE INDEX IF NOT EXISTS idx_workflows_deployment_version ON workflows(deployment_version)",
            ]

            for sql in indexes:
                try:
                    await conn.execute(sql)
                    logger.info("✅ Added index")
                except Exception as e:
                    logger.debug(f"Index: {e}")

            # Migration 2: Create trigger_index table
            logger.info("🔧 Creating trigger_index table...")

            trigger_index_sql = """
            CREATE TABLE IF NOT EXISTS trigger_index (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                workflow_id UUID NOT NULL,
                trigger_type VARCHAR(50) NOT NULL,
                trigger_subtype VARCHAR(100) NOT NULL,
                trigger_config JSON NOT NULL DEFAULT '{}',
                deployment_status VARCHAR(50) NOT NULL DEFAULT 'active',
                index_key VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workflow_id, index_key)
            )
            """

            await conn.execute(trigger_index_sql)
            logger.info("✅ Created trigger_index table")

            # Migration 3: Create workflow_deployment_history table
            logger.info("🔧 Creating workflow_deployment_history table...")

            deployment_history_sql = """
            CREATE TABLE IF NOT EXISTS workflow_deployment_history (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                workflow_id UUID NOT NULL,
                deployment_action VARCHAR(50) NOT NULL,
                from_status VARCHAR(50) NOT NULL,
                to_status VARCHAR(50) NOT NULL,
                deployment_version INTEGER NOT NULL,
                deployment_config JSON NOT NULL DEFAULT '{}',
                triggered_by UUID,
                started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP WITH TIME ZONE,
                error_message TEXT,
                deployment_logs JSON DEFAULT '{}'
            )
            """

            await conn.execute(deployment_history_sql)
            logger.info("✅ Created workflow_deployment_history table")

            # Add table indexes
            logger.info("🔧 Adding table indexes...")
            table_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_trigger_index_workflow_id ON trigger_index(workflow_id)",
                "CREATE INDEX IF NOT EXISTS idx_trigger_index_type ON trigger_index(trigger_type, trigger_subtype)",
                "CREATE INDEX IF NOT EXISTS idx_trigger_index_status ON trigger_index(deployment_status)",
                "CREATE INDEX IF NOT EXISTS idx_deployment_history_workflow_id ON workflow_deployment_history(workflow_id)",
                "CREATE INDEX IF NOT EXISTS idx_deployment_history_action ON workflow_deployment_history(deployment_action)",
            ]

            for sql in table_indexes:
                try:
                    await conn.execute(sql)
                except Exception as e:
                    logger.debug(f"Index: {e}")

            # Verify migration
            logger.info("🔍 Verifying migrations...")

            # Check workflows columns
            columns = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'workflows'
                AND column_name IN ('deployment_status', 'deployed_at', 'deployed_by', 'undeployed_at', 'deployment_version', 'deployment_config')
                ORDER BY column_name
            """
            )

            logger.info("📋 Workflows table deployment columns:")
            for col in columns:
                nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col["column_default"] else ""
                logger.info(f"  ✅ {col['column_name']}: {col['data_type']} {nullable}{default}")

            # Check new tables
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('trigger_index', 'workflow_deployment_history')
                AND table_schema = 'public'
            """
            )

            logger.info("📋 New workflow scheduler tables:")
            for table in tables:
                logger.info(f"  ✅ {table['table_name']}")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    print("🔧 Running database schema migrations...")
    success = asyncio.run(run_schema_migrations())

    if success:
        print("\n🎉 Database migrations successfully applied!")
        print("The workflow scheduler should now run without any column errors.")
    else:
        print("\n❌ Migration failed")
