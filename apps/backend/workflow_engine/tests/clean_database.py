#!/usr/bin/env python3
"""
Clean problematic database data
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from workflow_engine.models.database import get_db


def clean_database():
    """Clean problematic database data"""
    print("🧹 Cleaning Database")
    print("=" * 30)

    try:
        db = next(get_db())

        # Delete the problematic workflow
        print("\n📋 Deleting problematic workflow...")
        result = db.execute(
            text(
                """
            DELETE FROM workflows
            WHERE id = '00000000-0000-0000-0000-000000000001'
        """
            )
        )

        deleted_count = result.rowcount
        print(f"Deleted {deleted_count} problematic workflows")

        # Commit the changes
        db.commit()

        # Verify deletion
        print("\n📋 Verifying deletion...")
        result = db.execute(
            text(
                """
            SELECT COUNT(*) FROM workflows
            WHERE id = '00000000-0000-0000-0000-000000000001'
        """
            )
        )

        remaining_count = result.fetchone()[0]
        if remaining_count == 0:
            print("✅ Problematic workflow successfully deleted")
        else:
            print(f"❌ Still {remaining_count} problematic workflows remaining")

        # Show remaining workflows
        print("\n📋 Remaining workflows:")
        result = db.execute(
            text(
                """
            SELECT id, name, description, active
            FROM workflows
            ORDER BY created_at DESC
            LIMIT 5
        """
            )
        )

        workflows = result.fetchall()
        print(f"Found {len(workflows)} workflows:")

        for workflow in workflows:
            print(f"  - {workflow[0]}: {workflow[1]} (Active: {workflow[3]})")

        db.close()
        print("\n✅ Database cleaning completed!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    clean_database()
