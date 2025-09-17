#!/usr/bin/env python3
"""
Initialize node_templates in the database if empty.
This script should be run on startup in production.
"""
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text

from workflow_engine.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_node_templates():
    """Initialize node_templates table with seed data if empty"""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Check if node_templates is empty
            result = conn.execute(text("SELECT COUNT(*) FROM node_templates"))
            count = result.scalar()

            if count == 0:
                logger.info("Node templates table is empty, initializing with seed data...")

                # Read and execute seed data
                seed_file = Path(__file__).parent.parent / "database" / "seed_data.sql"
                if seed_file.exists():
                    with open(seed_file, "r") as f:
                        seed_sql = f.read()

                    # Execute the seed data
                    conn.execute(text(seed_sql))
                    conn.commit()

                    # Verify
                    result = conn.execute(text("SELECT COUNT(*) FROM node_templates"))
                    new_count = result.scalar()
                    logger.info(f"Successfully initialized {new_count} node templates")
                else:
                    logger.error(f"Seed data file not found: {seed_file}")
            else:
                logger.info(f"Node templates already initialized with {count} templates")

    except Exception as e:
        logger.error(f"Error initializing node templates: {e}")
        raise


if __name__ == "__main__":
    init_node_templates()
