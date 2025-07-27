#!/usr/bin/env python3
"""
Check workflow_executions table structure
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from workflow_engine.models.database import get_db

def check_execution_table():
    """Check workflow_executions table structure"""
    print("🔍 Checking workflow_executions table structure")
    print("=" * 50)
    
    try:
        db = next(get_db())
        
        # Check table structure
        print("\n📋 Table structure:")
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'workflow_executions'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        print(f"Found {len(columns)} columns:")
        
        for column in columns:
            print(f"  - {column[0]}: {column[1]} (nullable: {column[2]}, default: {column[3]})")
        
        # Check if table exists
        print("\n📋 Table existence:")
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'workflow_executions'
            )
        """))
        
        table_exists = result.fetchone()[0]
        print(f"Table exists: {table_exists}")
        
        # Check table data
        if table_exists:
            print("\n📋 Table data:")
            result = db.execute(text("""
                SELECT COUNT(*) FROM workflow_executions
            """))
            
            count = result.fetchone()[0]
            print(f"Total executions: {count}")
            
            if count > 0:
                result = db.execute(text("""
                    SELECT execution_id, workflow_id, status, mode 
                    FROM workflow_executions 
                    ORDER BY start_time DESC 
                    LIMIT 3
                """))
                
                executions = result.fetchall()
                print("Recent executions:")
                for execution in executions:
                    print(f"  - {execution[0]}: {execution[1]} ({execution[2]}, {execution[3]})")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_execution_table() 