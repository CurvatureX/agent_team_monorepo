#!/usr/bin/env python3
"""
Script to check and populate node_templates in the database
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text

from workflow_engine.core.config import get_settings


def check_node_templates():
    """Check if node_templates table has data"""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        # Check count
        result = conn.execute(text("SELECT COUNT(*) FROM node_templates"))
        count = result.scalar()
        print(f"Current node_templates count: {count}")

        if count == 0:
            print("No node templates found. The database needs to be seeded.")
            print("\nTo fix this, run:")
            print("psql $DATABASE_URL < database/seed_data.sql")
        else:
            # Show some examples
            result = conn.execute(
                text(
                    "SELECT template_id, name, node_type, node_subtype FROM node_templates LIMIT 5"
                )
            )
            print("\nExample templates:")
            for row in result:
                print(f"  - {row.template_id}: {row.name} ({row.node_type}.{row.node_subtype})")


if __name__ == "__main__":
    check_node_templates()
