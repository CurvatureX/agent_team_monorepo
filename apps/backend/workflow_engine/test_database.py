#!/usr/bin/env python3
"""
Test database connection
"""

import os
import logging
from workflow_engine.core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection."""
    try:
        settings = get_settings()
        logger.info(f"Database URL: {settings.database_url}")
        
        # Try to import psycopg2
        try:
            import psycopg2
            logger.info("✅ psycopg2 imported successfully")
        except ImportError:
            logger.error("❌ psycopg2 not installed. Please install: pip install psycopg2-binary")
            return False
        
        # Try to connect
        conn = psycopg2.connect(settings.database_url)
        logger.info("✅ Database connection successful")
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(f"✅ Database version: {version[0]}")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('workflows', 'nodes', 'workflow_executions')
        """)
        
        tables = cursor.fetchall()
        logger.info(f"✅ Found tables: {[table[0] for table in tables]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_database_connection() 