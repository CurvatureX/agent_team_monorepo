#!/usr/bin/env python3
"""
Debug execution status query issue
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from workflow_engine.models.database import get_db

def debug_execution_status():
    """Debug execution status query issue"""
    print("🔍 Debugging execution status query issue")
    print("=" * 50)
    
    try:
        db = next(get_db())
        
        # Check recent executions
        print("\n📋 Recent executions:")
        result = db.execute(text("""
            SELECT execution_id, workflow_id, status, mode, triggered_by, start_time
            FROM workflow_executions 
            ORDER BY start_time DESC 
            LIMIT 3
        """))
        
        executions = result.fetchall()
        print(f"Found {len(executions)} executions:")
        
        for execution in executions:
            print(f"  - {execution[0]}: {execution[1]} (status: {execution[2]}, mode: {execution[3]})")
            print(f"    triggered_by: {execution[4]}, start_time: {execution[5]}")
        
        # Test protobuf enum conversion
        print("\n📋 Testing protobuf enum conversion:")
        
        # Import protobuf modules
        from workflow_engine.proto import execution_pb2
        
        # Test with actual database values
        if executions:
            test_status = executions[0][2]  # status from database
            test_mode = executions[0][3]    # mode from database
            
            print(f"  Database status: '{test_status}' (type: {type(test_status)})")
            print(f"  Database mode: '{test_mode}' (type: {type(test_mode)})")
            
            try:
                # Try to convert status
                print(f"  Trying execution_pb2.ExecutionStatus.Value('{test_status}')...")
                status_enum = execution_pb2.ExecutionStatus.Value(test_status)
                print(f"  ✅ Status conversion successful: {status_enum}")
            except Exception as e:
                print(f"  ❌ Status conversion failed: {e}")
            
            try:
                # Try to convert mode
                print(f"  Trying execution_pb2.ExecutionMode.Value('{test_mode}')...")
                mode_enum = execution_pb2.ExecutionMode.Value(test_mode)
                print(f"  ✅ Mode conversion successful: {mode_enum}")
            except Exception as e:
                print(f"  ❌ Mode conversion failed: {e}")
            
            # Check available enum values
            print(f"\n📋 Available ExecutionStatus values:")
            for name, value in execution_pb2.ExecutionStatus.items():
                print(f"  - {name}: {value}")
            
            print(f"\n📋 Available ExecutionMode values:")
            for name, value in execution_pb2.ExecutionMode.items():
                print(f"  - {name}: {value}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_execution_status() 