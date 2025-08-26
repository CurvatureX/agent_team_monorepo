#!/usr/bin/env python3
"""
Add execution_metadata column to workflow_executions table
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from workflow_engine.models.database import get_db


def add_execution_metadata_column():
    """Add execution_metadata column to workflow_executions table"""
    print("🔧 Adding execution_metadata column to workflow_executions table")
    print("=" * 60)

    try:
        db = next(get_db())

        # Check if column already exists
        print("\n📋 Checking if execution_metadata column exists...")
        result = db.execute(
            text(
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'workflow_executions'
            AND column_name = 'execution_metadata'
        """
            )
        )

        column_exists = result.fetchone() is not None

        if column_exists:
            print("✅ execution_metadata column already exists")
        else:
            print("📋 Adding execution_metadata column...")

            # Add the column
            db.execute(
                text(
                    """
                ALTER TABLE workflow_executions
                ADD COLUMN execution_metadata JSONB DEFAULT '{}'::jsonb
            """
                )
            )

            db.commit()
            print("✅ execution_metadata column added successfully")

        # Verify the column was added
        print("\n📋 Verifying table structure...")
        result = db.execute(
            text(
                """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'workflow_executions'
            ORDER BY ordinal_position
        """
            )
        )

        columns = result.fetchall()
        print(f"Found {len(columns)} columns:")

        for column in columns:
            print(f"  - {column[0]}: {column[1]} (nullable: {column[2]}, default: {column[3]})")

        db.close()
        print("\n✅ Database migration completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    add_execution_metadata_column()
