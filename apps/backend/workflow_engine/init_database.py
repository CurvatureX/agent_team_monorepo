#!/usr/bin/env python3
"""
Initialize database schema
"""

import logging
import psycopg2
from workflow_engine.core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database schema."""
    try:
        settings = get_settings()
        logger.info("Connecting to database...")
        
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        
        # Read schema file
        with open('database/schema.sql', 'r') as f:
            schema_sql = f.read()
        
        logger.info("Creating database schema...")
        cursor.execute(schema_sql)
        conn.commit()
        
        logger.info("✅ Database schema created successfully")
        
        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('workflows', 'nodes', 'workflow_executions')
        """)
        
        tables = cursor.fetchall()
        logger.info(f"✅ Tables created: {[table[0] for table in tables]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    init_database() 