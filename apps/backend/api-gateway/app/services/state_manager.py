"""
State Manager for Workflow Agent States
Handles persistence and retrieval of workflow agent conversation states

Updated to follow current API Gateway design patterns:
- Uses direct Supabase client operations instead of repository pattern
- Supports RLS with create_user_supabase_client for authenticated users
- Falls back to admin client for unauthenticated operations
- Consistent error handling and logging patterns
"""

import json
import time
from typing import Any, Dict, List, Optional

from app.core.database import create_user_supabase_client, get_supabase_admin
import logging

logger = logging.getLogger("app.services.state_manager")


class WorkflowStateManager:
    """
    Manages workflow agent states with RLS support
    Handles conversion between protobuf AgentState and database storage
    """

    def __init__(self):
        self.table_name = "workflow_agent_states"
    
    def _get_client(self, access_token: Optional[str] = None):
        """
        Get appropriate Supabase client based on access token
        
        Args:
            access_token: User's JWT token for RLS operations
            
        Returns:
            Supabase client or None if failed to create
        """
        if access_token:
            return create_user_supabase_client(access_token)
        else:
            return get_supabase_admin()

    def create_state(
        self,
        session_id: str,
        user_id: str,
        initial_stage: str = "clarification",
        clarification_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a new workflow agent state

        Args:
            session_id: Unique session identifier
            user_id: User identifier (can be "anonymous" for guest sessions)
            initial_stage: Starting workflow stage
            clarification_context: Initial clarification context
            workflow_context: Initial workflow context
            access_token: User's JWT token for RLS

        Returns:
            State ID if successful, None if failed
        """
        try:
            current_time = int(time.time() * 1000)

            # Default contexts if not provided
            if clarification_context is None:
                clarification_context = {"origin": "create", "pending_questions": []}

            if workflow_context is None:
                workflow_context = {
                    "origin": "create",
                    "source_workflow_id": "",
                    "modification_intent": "",
                }

            state_data = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": current_time,
                "updated_at": current_time,
                "stage": initial_stage,
                "execution_history": [],
                "intent_summary": "",
                "clarification_context": clarification_context,
                "workflow_context": workflow_context,
                "conversations": [],
                "identified_gaps": [],
                "gap_status": "no_gap",
                "gap_resolution": "",
                "current_workflow_json": "",
                "debug_result": "",
                "debug_loop_count": 0,
            }

            # Get appropriate client based on access token
            client = self._get_client(access_token)
            if not client:
                logger.error("Failed to create database client")
                return None

            result = client.table(self.table_name).insert(state_data).execute()
            
            if result.data:
                state_id = result.data[0]["id"]
                logger.info(f"Created workflow state for session {session_id}: {state_id}")
                return state_id
            else:
                logger.error(f"Failed to create workflow state for session {session_id}")
                return None

        except Exception as e:
            logger.error(f"Error creating workflow state for session {session_id}: {e}")
            return None

    def get_state_by_session(
        self, session_id: str, access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get workflow state by session ID

        Args:
            session_id: Session identifier
            access_token: User's JWT token for RLS

        Returns:
            State data if found, None if not found or error
        """
        try:
            # Get appropriate client based on access token
            client = self._get_client(access_token)
            if not client:
                logger.error("Failed to create database client")
                return None

            result = client.table(self.table_name).select("*").eq("session_id", session_id).execute()
            
            if result.data:
                # Return the most recent state for this session
                states = result.data
                latest_state = max(states, key=lambda x: x.get("updated_at", 0))
                logger.debug(f"Retrieved workflow state for session {session_id}")
                return latest_state
            else:
                logger.debug(f"No workflow state found for session {session_id}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving workflow state for session {session_id}: {e}")
            return None

    def get_state_by_id(
        self, state_id: str, access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get workflow state by state ID

        Args:
            state_id: State identifier
            access_token: User's JWT token for RLS

        Returns:
            State data if found, None if not found or error
        """
        try:
            # Get appropriate client based on access token
            client = self._get_client(access_token)
            if not client:
                logger.error("Failed to create database client")
                return None

            result = client.table(self.table_name).select("*").eq("id", state_id).execute()
            
            if result.data:
                state = result.data[0]
                logger.debug(f"Retrieved workflow state by ID {state_id}")
                return state
            else:
                logger.debug(f"No workflow state found with ID {state_id}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving workflow state by ID {state_id}: {e}")
            return None

    def update_state(
        self, session_id: str, updates: Dict[str, Any], access_token: Optional[str] = None
    ) -> bool:
        """
        Update workflow state for a session

        Args:
            session_id: Session identifier
            updates: Dictionary of fields to update
            access_token: User's JWT token for RLS

        Returns:
            True if successful, False if failed
        """
        try:
            # Get current state first
            current_state = self.get_state_by_session(session_id, access_token)
            if not current_state:
                logger.error(f"Cannot update - no state found for session {session_id}")
                return False

            state_id = current_state["id"]

            # Ensure updated_at timestamp is set
            updates["updated_at"] = int(time.time() * 1000)

            # Get appropriate client based on access token
            client = self._get_client(access_token)
            if not client:
                logger.error("Failed to create database client")
                return False

            result = client.table(self.table_name).update(updates).eq("id", state_id).execute()
            
            if result.data:
                logger.info(f"Updated workflow state for session {session_id}")
                return True
            else:
                logger.error(f"Failed to update workflow state for session {session_id}")
                return False

        except Exception as e:
            logger.error(f"Error updating workflow state for session {session_id}: {e}")
            return False

    def save_full_state(
        self, session_id: str, workflow_state: Dict[str, Any], access_token: Optional[str] = None
    ) -> bool:
        """
        Save complete workflow state (equivalent to protobuf AgentState)

        Args:
            session_id: Session identifier
            workflow_state: Complete workflow state dictionary
            access_token: User's JWT token for RLS

        Returns:
            True if successful, False if failed
        """
        try:
            # Check if state exists
            existing_state = self.get_state_by_session(session_id, access_token)

            if existing_state:
                # Update existing state
                updates = self._prepare_state_for_db(workflow_state)
                return self.update_state(session_id, updates, access_token)
            else:
                # Create new state
                user_id = workflow_state.get("user_id", "anonymous")
                state_id = self.create_state(
                    session_id=session_id,
                    user_id=user_id,
                    initial_stage=workflow_state.get("stage", "clarification"),
                    clarification_context=workflow_state.get("clarification_context"),
                    workflow_context=workflow_state.get("workflow_context"),
                    access_token=access_token,
                )

                if state_id:
                    # Update with full state data
                    updates = self._prepare_state_for_db(workflow_state)
                    return self.update_state(session_id, updates, access_token)

                return False

        except Exception as e:
            logger.error(f"Error saving full workflow state for session {session_id}: {e}")
            return False

    def get_user_states(
        self, user_id: str, access_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all workflow states for a user

        Args:
            user_id: User identifier
            access_token: User's JWT token for RLS

        Returns:
            List of workflow states for the user
        """
        try:
            # Get appropriate client based on access token
            client = self._get_client(access_token)
            if not client:
                logger.error("Failed to create database client")
                return []

            result = client.table(self.table_name).select("*").eq("user_id", user_id).execute()
            
            states = result.data if result.data else []
            logger.debug(f"Retrieved {len(states)} workflow states for user {user_id}")
            return states

        except Exception as e:
            logger.error(f"Error retrieving workflow states for user {user_id}: {e}")
            return []

    def delete_state(self, session_id: str, access_token: Optional[str] = None) -> bool:
        """
        Delete workflow state by session ID

        Args:
            session_id: Session identifier
            access_token: User's JWT token for RLS

        Returns:
            True if successful, False if failed
        """
        try:
            # Get current state to find the ID
            current_state = self.get_state_by_session(session_id, access_token)
            if not current_state:
                logger.error(f"Cannot delete - no state found for session {session_id}")
                return False

            state_id = current_state["id"]

            # Get appropriate client based on access token
            client = self._get_client(access_token)
            if not client:
                logger.error("Failed to create database client")
                return False

            result = client.table(self.table_name).delete().eq("id", state_id).execute()

            # Supabase delete operation is considered successful if it executes without error
            # The data field may be empty even for successful deletions
            logger.info(f"Deleted workflow state for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting workflow state for session {session_id}: {e}")
            return False

    def _prepare_state_for_db(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare workflow state for database storage
        Handles JSON serialization and field mapping

        Args:
            workflow_state: Complete workflow state

        Returns:
            Dictionary prepared for database storage
        """
        db_state = {}

        # Direct field mappings
        field_mappings = {
            "session_id": "session_id",
            "user_id": "user_id",
            "created_at": "created_at",
            "updated_at": "updated_at",
            "stage": "stage",
            "previous_stage": "previous_stage",
            "execution_history": "execution_history",
            "intent_summary": "intent_summary",
            "identified_gaps": "identified_gaps",
            "gap_status": "gap_status",
            "gap_resolution": "gap_resolution",
            "current_workflow": "current_workflow_json",
            "debug_result": "debug_result",
            "debug_loop_count": "debug_loop_count",
        }

        for state_key, db_key in field_mappings.items():
            if state_key in workflow_state:
                value = workflow_state[state_key]
                if db_key == "current_workflow_json" and isinstance(value, (dict, list)):
                    db_state[db_key] = json.dumps(value)
                else:
                    db_state[db_key] = value

        # JSON field mappings
        json_fields = {
            "clarification_context": "clarification_context",
            "workflow_context": "workflow_context",
            "conversations": "conversations",
            "rag": "rag_context",
        }

        for state_key, db_key in json_fields.items():
            if state_key in workflow_state:
                value = workflow_state[state_key]
                if isinstance(value, (dict, list)):
                    db_state[db_key] = value  # Let repository handle JSON serialization
                else:
                    db_state[db_key] = value

        return db_state


# Global state manager instance
workflow_state_manager = WorkflowStateManager()


def get_state_manager() -> WorkflowStateManager:
    """Get the global workflow state manager instance"""
    return workflow_state_manager
