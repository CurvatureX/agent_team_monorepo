#!/usr/bin/env python3
"""
Test SQLAlchemy ARRAY type directly
"""

import sys
import os
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import Column, String, Boolean, Integer, Text, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY

# Import database configuration
from workflow_engine.core.config import get_settings

settings = get_settings()

# Create a simple test model
Base = declarative_base()

class TestWorkflow(Base):
    __tablename__ = "test_workflows"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    tags = Column(ARRAY(Text), default=list)  # PostgreSQL text array

def test_sqlalchemy_array():
    """Test SQLAlchemy ARRAY type directly"""
    print("🧪 Testing SQLAlchemy ARRAY type directly...")
    
    try:
        # Create engine
        engine = create_engine(settings.database_url)
        
        # Create session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Create table
        Base.metadata.create_all(bind=engine)
        
        # Test 1: Create workflow with array
        print("\n📋 Test 1: Create workflow with array using ORM")
        test_workflow = TestWorkflow(
            id='00000000-0000-0000-0000-000000000001',
            name='Test Workflow ORM',
            tags=['orm', 'test', 'array']
        )
        
        db.add(test_workflow)
        db.commit()
        
        # Test 2: Query back
        print("\n📋 Test 2: Query workflow back")
        retrieved = db.query(TestWorkflow).filter_by(id='00000000-0000-0000-0000-000000000001').first()
        if retrieved:
            print(f"✅ Retrieved: {retrieved.id}, {retrieved.name}, {retrieved.tags}")
        else:
            print("❌ No workflow found")
        
        # Test 3: Check raw SQL
        print("\n📋 Test 3: Check raw SQL")
        result = db.execute(text("""
            SELECT id, name, tags FROM test_workflows WHERE id = :id
        """), {'id': '00000000-0000-0000-0000-000000000001'})
        
        row = result.fetchone()
        if row:
            print(f"✅ Raw SQL result: {row}")
        else:
            print("❌ No row found")
        
        db.close()
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    test_sqlalchemy_array() 