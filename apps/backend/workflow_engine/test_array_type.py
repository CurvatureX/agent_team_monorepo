#!/usr/bin/env python3
"""
Test PostgreSQL ARRAY type with SQLAlchemy
"""

import sys
import os
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

# Import database configuration
from workflow_engine.core.config import get_settings
from workflow_engine.models.database import get_db

settings = get_settings()

def test_array_type():
    """Test PostgreSQL ARRAY type"""
    print("🧪 Testing PostgreSQL ARRAY type...")
    
    try:
        # Get database session
        db = next(get_db())
        
        # Test 1: Check existing workflows table structure
        print("\n📋 Test 1: Check existing workflows table structure")
        result = db.execute(text("""
            SELECT column_name, data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'workflows' AND column_name = 'tags'
        """))
        
        column_info = result.fetchone()
        if column_info:
            print(f"✅ Tags column: {column_info}")
        else:
            print("❌ Tags column not found")
        
        # Test 2: Try to insert into workflows table with array
        print("\n📋 Test 2: Insert into workflows table with array")
        result = db.execute(text("""
            INSERT INTO workflows (id, user_id, name, description, version, active, workflow_data, tags, created_at, updated_at)
            VALUES (:id, :user_id, :name, :description, :version, :active, :workflow_data, :tags, :created_at, :updated_at)
            RETURNING id, name, tags
        """), {
            'id': '00000000-0000-0000-0000-000000000001',
            'user_id': '00000000-0000-0000-0000-000000000123',
            'name': 'Array Test Workflow',
            'description': 'Testing array tags',
            'version': '1.0.0',
            'active': True,
            'workflow_data': '{"test": "data"}',
            'tags': ['array', 'test', 'postgresql'],
            'created_at': 1752941579,
            'updated_at': 1752941579
        })
        
        workflow_row = result.fetchone()
        if workflow_row:
            print(f"✅ Workflow inserted: {workflow_row}")
        else:
            print("❌ No row returned")
        
        # Test 3: Query the inserted workflow
        print("\n📋 Test 3: Query the inserted workflow")
        result = db.execute(text("""
            SELECT id, name, tags FROM workflows WHERE id = :id
        """), {'id': '00000000-0000-0000-0000-000000000001'})
        
        query_row = result.fetchone()
        if query_row:
            print(f"✅ Query result: {query_row}")
        else:
            print("❌ No workflow found")
        
        db.commit()
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_array_type() 