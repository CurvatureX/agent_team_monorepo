#!/usr/bin/env python3
"""
Database service for workflow engine
"""

import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from workflow_engine.core.config import get_settings

logger = logging.getLogger(__name__)

class DatabaseService:
    """Database service for workflow operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.connection = None
    
    def get_connection(self):
        """Get database connection."""
        if self.connection is None or self.connection.closed:
            try:
                self.connection = psycopg2.connect(
                    self.settings.database_url,
                    cursor_factory=RealDictCursor
                )
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self.connection
    
    def close_connection(self):
        """Close database connection."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Database connection closed")
    
    def create_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Create a new workflow in database."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Generate workflow ID
            workflow_id = str(uuid.uuid4())
            current_time = int(datetime.now().timestamp())
            
            # Insert workflow
            cursor.execute("""
                INSERT INTO workflows (
                    id, user_id, name, description, active, workflow_data, 
                    static_data, version, tags, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                workflow_id,
                workflow_data.get('user_id'),
                workflow_data.get('name'),
                workflow_data.get('description'),
                workflow_data.get('active', True),
                json.dumps(workflow_data.get('workflow_data', {})),
                json.dumps(workflow_data.get('static_data', {})),
                workflow_data.get('version', '1.0.0'),
                workflow_data.get('tags', []),
                current_time,
                current_time
            ))
            
            workflow_id = cursor.fetchone()['id']
            
            # Insert nodes
            nodes = workflow_data.get('nodes', [])
            for node in nodes:
                cursor.execute("""
                    INSERT INTO nodes (
                        id, node_id, workflow_id, node_type, node_subtype,
                        name, description, disabled, position_x, position_y,
                        parameters, credentials, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    node.get('id'),
                    workflow_id,
                    node.get('type'),
                    node.get('subtype'),
                    node.get('name'),
                    node.get('description', ''),
                    node.get('disabled', False),
                    node.get('position', {}).get('x', 0),
                    node.get('position', {}).get('y', 0),
                    json.dumps(node.get('parameters', {})),
                    json.dumps(node.get('credentials', {})),
                    datetime.now(),
                    datetime.now()
                ))
            
            conn.commit()
            logger.info(f"Workflow created in database: {workflow_id}")
            return workflow_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create workflow: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow by ID."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get workflow
            cursor.execute("""
                SELECT * FROM workflows WHERE id = %s
            """, (workflow_id,))
            
            workflow_row = cursor.fetchone()
            if not workflow_row:
                return None
            
            # Get nodes
            cursor.execute("""
                SELECT * FROM nodes WHERE workflow_id = %s ORDER BY created_at
            """, (workflow_id,))
            
            nodes = []
            for node_row in cursor.fetchall():
                node = dict(node_row)
                node['position'] = {'x': node_row['position_x'], 'y': node_row['position_y']}
                nodes.append(node)
            
            # Build workflow response
            workflow = dict(workflow_row)
            workflow['nodes'] = nodes
            workflow['static_data'] = json.loads(workflow_row['static_data'] or '{}')
            workflow['tags'] = workflow_row['tags'] or []
            
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to get workflow: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def list_workflows(self, user_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """List workflows for a user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("""
                SELECT COUNT(*) as total FROM workflows WHERE user_id = %s
            """, (user_id,))
            
            total_count = cursor.fetchone()['total']
            
            # Get workflows
            cursor.execute("""
                SELECT id, name, description, active, version, tags, created_at, updated_at
                FROM workflows 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
            
            workflows = []
            for row in cursor.fetchall():
                workflows.append(dict(row))
            
            return {
                'workflows': workflows,
                'total_count': total_count,
                'has_more': (offset + limit) < total_count
            }
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def create_execution(self, execution_data: Dict[str, Any]) -> str:
        """Create a new execution record."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Generate execution ID
            execution_id = str(uuid.uuid4())
            current_time = int(datetime.now().timestamp())
            
            # Insert execution
            cursor.execute("""
                INSERT INTO workflow_executions (
                    id, execution_id, workflow_id, status, mode, triggered_by,
                    input_data, metadata, start_time, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                str(uuid.uuid4()),
                execution_id,
                execution_data.get('workflow_id'),
                execution_data.get('status', 'NEW'),
                execution_data.get('mode', 'MANUAL'),
                execution_data.get('triggered_by'),
                json.dumps(execution_data.get('input_data', {})),
                json.dumps(execution_data.get('metadata', {})),
                current_time,
                datetime.now()
            ))
            
            conn.commit()
            logger.info(f"Execution created in database: {execution_id}")
            return execution_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create execution: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution by ID."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM workflow_executions WHERE execution_id = %s
            """, (execution_id,))
            
            execution_row = cursor.fetchone()
            if not execution_row:
                return None
            
            execution = dict(execution_row)
            execution['input_data'] = json.loads(execution_row['input_data'] or '{}')
            execution['metadata'] = json.loads(execution_row['metadata'] or '{}')
            
            return execution
            
        except Exception as e:
            logger.error(f"Failed to get execution: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def update_execution_status(self, execution_id: str, status: str, end_time: Optional[int] = None):
        """Update execution status."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if end_time:
                cursor.execute("""
                    UPDATE workflow_executions 
                    SET status = %s, end_time = %s, updated_at = %s
                    WHERE execution_id = %s
                """, (status, end_time, datetime.now(), execution_id))
            else:
                cursor.execute("""
                    UPDATE workflow_executions 
                    SET status = %s, updated_at = %s
                    WHERE execution_id = %s
                """, (status, datetime.now(), execution_id))
            
            conn.commit()
            logger.info(f"Execution status updated: {execution_id} -> {status}")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to update execution status: {e}")
            raise
        finally:
            if cursor:
                cursor.close() 