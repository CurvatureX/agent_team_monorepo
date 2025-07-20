#!/usr/bin/env python3
"""
Debug database execution_metadata field
"""

import sys
import json
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from workflow_engine.models.database import get_db

def debug_db_metadata():
    """Debug database execution_metadata field"""
    print("🔍 Debugging database execution_metadata field")
    print("=" * 50)
    
    try:
        db = next(get_db())
        
        # Check execution_metadata values
        print("\n📋 Execution metadata values:")
        result = db.execute(text("""
            SELECT execution_id, execution_metadata, metadata
            FROM workflow_executions 
            ORDER BY start_time DESC 
            LIMIT 3
        """))
        
        executions = result.fetchall()
        print(f"Found {len(executions)} executions:")
        
        for execution in executions:
            execution_id = execution[0]
            execution_metadata = execution[1]
            metadata = execution[2]
            
            print(f"\n  - Execution ID: {execution_id}")
            print(f"    execution_metadata: {execution_metadata} (type: {type(execution_metadata)})")
            print(f"    metadata: {metadata} (type: {type(metadata)})")
            
            # Test conversion
            try:
                if execution_metadata is not None:
                    if isinstance(execution_metadata, str):
                        parsed_metadata = json.loads(execution_metadata)
                    else:
                        parsed_metadata = execution_metadata
                    
                    print(f"    ✅ Parsed metadata: {parsed_metadata} (type: {type(parsed_metadata)})")
                    
                    # Test protobuf update
                    from workflow_engine.proto import execution_pb2
                    test_execution = execution_pb2.ExecutionData()
                    test_execution.metadata.update(parsed_metadata)
                    print(f"    ✅ Protobuf update successful: {dict(test_execution.metadata)}")
                else:
                    print(f"    ⚠️  execution_metadata is None")
                    
            except Exception as e:
                print(f"    ❌ Error processing metadata: {e}")
                import traceback
                traceback.print_exc()
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_db_metadata() 