#!/usr/bin/env python3
"""
Debug execution service step by step
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_engine.models.database import get_db
from workflow_engine.models.execution import WorkflowExecution as ExecutionModel
from proto import execution_pb2

def debug_execution_service_step_by_step():
    """Debug execution service step by step"""
    print("🔍 Debugging Execution Service Step by Step")
    print("=" * 50)
    
    execution_id = "b98426f6-9dc4-4f16-9b29-e67759f6e110"
    
    try:
        db = next(get_db())
        
        print(f"📋 Step 1: Query database for execution {execution_id}")
        
        # Step 1: Query database
        db_execution = db.query(ExecutionModel).filter(
            ExecutionModel.execution_id == execution_id
        ).first()
        
        if not db_execution:
            print("❌ Execution not found in database")
            return
        
        print(f"✅ Execution found: {db_execution.execution_id}")
        print(f"  - workflow_id: {db_execution.workflow_id}")
        print(f"  - status: {db_execution.status} (type: {type(db_execution.status)})")
        print(f"  - mode: {db_execution.mode} (type: {type(db_execution.mode)})")
        print(f"  - triggered_by: {db_execution.triggered_by} (type: {type(db_execution.triggered_by)})")
        print(f"  - start_time: {db_execution.start_time} (type: {type(db_execution.start_time)})")
        print(f"  - end_time: {db_execution.end_time} (type: {type(db_execution.end_time)})")
        print(f"  - execution_metadata: {db_execution.execution_metadata} (type: {type(db_execution.execution_metadata)})")
        
        print(f"\n📋 Step 2: Create protobuf execution object")
        
        # Step 2: Create protobuf execution object
        execution = execution_pb2.ExecutionData()
        print(f"✅ ExecutionData object created")
        
        print(f"\n📋 Step 3: Set basic fields")
        
        # Step 3: Set basic fields
        execution.execution_id = db_execution.execution_id
        print(f"✅ Set execution_id: {execution.execution_id}")
        
        execution.workflow_id = db_execution.workflow_id
        print(f"✅ Set workflow_id: {execution.workflow_id}")
        
        print(f"\n📋 Step 4: Convert status enum")
        
        # Step 4: Convert status enum
        try:
            print(f"  Trying execution_pb2.ExecutionStatus.Value('{db_execution.status}')...")
            status_enum = execution_pb2.ExecutionStatus.Value(db_execution.status)
            execution.status = status_enum
            print(f"  ✅ Status conversion successful: {status_enum}")
        except Exception as e:
            print(f"  ❌ Status conversion failed: {e}")
            raise
        
        print(f"\n📋 Step 5: Convert mode enum")
        
        # Step 5: Convert mode enum
        try:
            print(f"  Trying execution_pb2.ExecutionMode.Value('{db_execution.mode}')...")
            mode_enum = execution_pb2.ExecutionMode.Value(db_execution.mode)
            execution.mode = mode_enum
            print(f"  ✅ Mode conversion successful: {mode_enum}")
        except Exception as e:
            print(f"  ❌ Mode conversion failed: {e}")
            raise
        
        print(f"\n📋 Step 6: Set other fields")
        
        # Step 6: Set other fields
        execution.triggered_by = db_execution.triggered_by or ""
        print(f"✅ Set triggered_by: {execution.triggered_by}")
        
        execution.start_time = db_execution.start_time or 0
        print(f"✅ Set start_time: {execution.start_time}")
        
        execution.end_time = db_execution.end_time or 0
        print(f"✅ Set end_time: {execution.end_time}")
        
        print(f"\n📋 Step 7: Update metadata")
        
        # Step 7: Update metadata
        try:
            print(f"  Database execution_metadata: {db_execution.execution_metadata}")
            print(f"  Type: {type(db_execution.execution_metadata)}")
            
            if db_execution.execution_metadata is None:
                metadata_to_update = {}
            else:
                metadata_to_update = db_execution.execution_metadata
            
            print(f"  Updating with: {metadata_to_update}")
            execution.metadata.update(metadata_to_update)
            print(f"  ✅ Metadata update successful: {dict(execution.metadata)}")
        except Exception as e:
            print(f"  ❌ Metadata update failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        print(f"\n✅ All steps completed successfully!")
        print(f"📋 Final execution object:")
        print(f"  - execution_id: {execution.execution_id}")
        print(f"  - workflow_id: {execution.workflow_id}")
        print(f"  - status: {execution.status}")
        print(f"  - mode: {execution.mode}")
        print(f"  - triggered_by: {execution.triggered_by}")
        print(f"  - start_time: {execution.start_time}")
        print(f"  - end_time: {execution.end_time}")
        print(f"  - metadata: {dict(execution.metadata)}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_execution_service_step_by_step() 