#!/usr/bin/env python3
"""
Test database connection to Supabase
"""

import psycopg2
import time
from urllib.parse import urlparse

def test_supabase_connection():
    """Test connection to Supabase database."""
    
    # Database connection string from .env
    database_url = "postgresql://postgres:Starmates2025%40@db.mkrczzgjeduruwxpanbj.supabase.co:5432/postgres?sslmode=require"
    
    print(f"Testing connection to: {database_url}")
    
    try:
        # Parse the URL
        parsed = urlparse(database_url)
        print(f"Host: {parsed.hostname}")
        print(f"Port: {parsed.port}")
        print(f"Database: {parsed.path[1:]}")
        print(f"User: {parsed.username}")
        print(f"SSL Mode: {parsed.query}")
        
        # Test connection with timeout
        print("\nAttempting connection...")
        start_time = time.time()
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            sslmode='require',
            connect_timeout=10
        )
        
        end_time = time.time()
        print(f"✅ Connection successful! Time: {end_time - start_time:.2f}s")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_supabase_connection() 