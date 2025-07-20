#!/usr/bin/env python3
"""
Test simple workflow creation using SQLAlchemy ORM
"""

import sys
import time
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_engine.models.database import get_db
from workflow_engine.models.workflow import Workflow

def test_simple_workflow():
    """Test simple workflow creation using ORM"""
    print("🧪 Testing Simple Workflow Creation")
    print("=" * 40)
    
    try:
        db = next(get_db())
        
        # Create a simple workflow
        print("\n📋 Creating simple workflow...")
        workflow = Workflow(
            id="00000000-0000-0000-0000-000000000001",
            user_id="00000000-0000-0000-0000-000000000123",
            name="Simple Test Workflow",
            description="A simple test workflow",
            version="1.0.0",
            active=True,
            workflow_data={"test": "data"},
            tags=["simple", "test", "orm"],
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        print(f"Workflow object created:")
        print(f"  ID: {workflow.id}")
        print(f"  Name: {workflow.name}")
        print(f"  Tags: {workflow.tags}")
        print(f"  Tags type: {type(workflow.tags)}")
        
        # Add to database
        db.add(workflow)
        db.commit()
        
        print("✅ Workflow added to database successfully")
        
        # Query back
        print("\n📋 Querying workflow back...")
        retrieved = db.query(Workflow).filter_by(id="00000000-0000-0000-0000-000000000001").first()
        
        if retrieved:
            print(f"✅ Retrieved workflow:")
            print(f"  ID: {retrieved.id}")
            print(f"  Name: {retrieved.name}")
            print(f"  Tags: {retrieved.tags}")
            print(f"  Tags type: {type(retrieved.tags)}")
        else:
            print("❌ Workflow not found")
        
        # Clean up
        print("\n📋 Cleaning up...")
        db.delete(workflow)
        db.commit()
        print("✅ Workflow deleted")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_workflow() 