#!/usr/bin/env python3
"""
Debug database content
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from workflow_engine.models.database import get_db

def debug_database():
    """Debug database content"""
    print("🔍 Debugging Database Content")
    print("=" * 40)
    
    try:
        db = next(get_db())
        
        # Check workflows table
        print("\n📋 Checking workflows table...")
        result = db.execute(text("""
            SELECT id, name, description, active, tags, created_at, updated_at 
            FROM workflows 
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        workflows = result.fetchall()
        print(f"Found {len(workflows)} workflows:")
        
        for workflow in workflows:
            print(f"  - ID: {workflow[0]}")
            print(f"    Name: {workflow[1]}")
            print(f"    Description: {workflow[2]}")
            print(f"    Active: {workflow[3]}")
            print(f"    Tags: {workflow[4]}")
            print(f"    Created: {workflow[5]}")
            print(f"    Updated: {workflow[6]}")
            print()
        
        # Check workflow_data column for problematic data
        print("\n📋 Checking workflow_data for problematic fields...")
        result = db.execute(text("""
            SELECT id, name, workflow_data 
            FROM workflows 
            WHERE workflow_data::text LIKE '%test%'
            LIMIT 3
        """))
        
        problematic_workflows = result.fetchall()
        print(f"Found {len(problematic_workflows)} workflows with 'test' in data:")
        
        for workflow in problematic_workflows:
            print(f"  - ID: {workflow[0]}")
            print(f"    Name: {workflow[1]}")
            print(f"    Data keys: {list(workflow[2].keys()) if workflow[2] else 'None'}")
            print()
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_database() 