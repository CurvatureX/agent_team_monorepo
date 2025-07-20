#!/usr/bin/env python3
"""
Debug metadata.update() issue
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_engine.proto import execution_pb2

def debug_metadata_update():
    """Debug metadata.update() issue"""
    print("🔍 Debugging metadata.update() issue")
    print("=" * 50)
    
    try:
        # Create execution data
        execution = execution_pb2.ExecutionData()
        
        print(f"📋 Execution object created: {type(execution)}")
        print(f"📋 Execution.metadata type: {type(execution.metadata)}")
        
        # Test different metadata values
        test_cases = [
            None,
            {},
            {"test": "value"},
            {"key1": "value1", "key2": "value2"}
        ]
        
        for i, test_metadata in enumerate(test_cases):
            print(f"\n📋 Test case {i+1}: {test_metadata}")
            
            try:
                if test_metadata is None:
                    execution.metadata.update({})
                else:
                    execution.metadata.update(test_metadata)
                print(f"  ✅ Update successful")
                print(f"  📋 Current metadata: {dict(execution.metadata)}")
            except Exception as e:
                print(f"  ❌ Update failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Test with database-like data
        print(f"\n📋 Testing with database-like data:")
        
        # Simulate database execution metadata
        db_metadata = {"test": "true", "environment": "development"}
        print(f"  Database metadata: {db_metadata}")
        
        try:
            execution.metadata.update(db_metadata)
            print(f"  ✅ Database metadata update successful")
            print(f"  📋 Final metadata: {dict(execution.metadata)}")
        except Exception as e:
            print(f"  ❌ Database metadata update failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_metadata_update() 