#!/usr/bin/env python3
"""
Debug workflow_id type issue
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_engine.models.database import get_db
from workflow_engine.models.execution import WorkflowExecution as ExecutionModel

def debug_workflow_id_type():
    """Debug workflow_id type issue"""
    print("🔍 Debugging workflow_id type issue")
    print("=" * 40)
    
    execution_id = "b98426f6-9dc4-4f16-9b29-e67759f6e110"
    
    try:
        db = next(get_db())
        
        db_execution = db.query(ExecutionModel).filter(
            ExecutionModel.execution_id == execution_id
        ).first()
        
        if not db_execution:
            print("❌ Execution not found")
            return
        
        print(f"📋 Database execution object:")
        print(f"  - execution_id: {db_execution.execution_id} (type: {type(db_execution.execution_id)})")
        print(f"  - workflow_id: {db_execution.workflow_id} (type: {type(db_execution.workflow_id)})")
        
        # Test conversion
        print(f"\n📋 Testing conversions:")
        
        # Convert to string
        workflow_id_str = str(db_execution.workflow_id)
        print(f"  - str(workflow_id): {workflow_id_str} (type: {type(workflow_id_str)})")
        
        # Test protobuf assignment
        from proto import execution_pb2
        execution = execution_pb2.ExecutionData()
        
        try:
            execution.execution_id = db_execution.execution_id
            print(f"  ✅ execution_id assignment successful")
        except Exception as e:
            print(f"  ❌ execution_id assignment failed: {e}")
        
        try:
            execution.workflow_id = workflow_id_str
            print(f"  ✅ workflow_id assignment successful with string")
        except Exception as e:
            print(f"  ❌ workflow_id assignment failed with string: {e}")
        
        try:
            execution.workflow_id = db_execution.workflow_id
            print(f"  ✅ workflow_id assignment successful with original type")
        except Exception as e:
            print(f"  ❌ workflow_id assignment failed with original type: {e}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_workflow_id_type() 