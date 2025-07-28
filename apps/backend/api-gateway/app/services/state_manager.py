"""
State Manager for Workflow Agent States
Handles persistence and retrieval of workflow agent conversation states
"""

import json
import time
from typing import Optional, Dict, Any, List
from app.database import SupabaseRepository
import structlog

logger = structlog.get_logger("state_manager")


class WorkflowStateManager:
    """
    Manages workflow agent states with RLS support
    Handles conversion between protobuf AgentState and database storage
    """

    def __init__(self):
        self.repo = SupabaseRepository("workflow_agent_states")

    def create_state(
        self, 
        session_id: str, 
        user_id: str, 
        initial_stage: str = "clarification",
        clarification_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None
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
                clarification_context = {
                    "origin": "create",
                    "pending_questions": []
                }
            
            if workflow_context is None:
                workflow_context = {
                    "origin": "create",
                    "source_workflow_id": "",
                    "modification_intent": ""
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
                "gaps": [],
                "alternatives": [],
                "current_workflow_json": "",
                "debug_result": "",
                "debug_loop_count": 0
            }

            result = self.repo.create(state_data, access_token)
            if result:
                logger.info("Created workflow state for session", session_id=session_id)
                return result["id"]
            else:
                logger.error("Failed to create workflow state for session", session_id=session_id)
                return None

        except Exception as e:
            logger.error("Error creating workflow state", error=str(e))
            return None

    def get_state_by_session(self, session_id: str, access_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get workflow state by session ID
        
        Args:
            session_id: Session identifier
            access_token: User's JWT token for RLS
            
        Returns:
            State data if found, None if not found or error
        """
        try:
            states = self.repo.get_by_session_id(session_id, access_token)
            if states:
                # Return the most recent state for this session
                latest_state = max(states, key=lambda x: x.get("updated_at", 0))
                logger.debug("Retrieved workflow state for session", session_id=session_id)
                return latest_state
            else:
                logger.debug("No workflow state found for session", session_id=session_id)
                return None

        except Exception as e:
            logger.error("Error retrieving workflow state for session", session_id=session_id, error=str(e))
            return None

    def get_state_by_id(self, state_id: str, access_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get workflow state by state ID
        
        Args:
            state_id: State identifier
            access_token: User's JWT token for RLS
            
        Returns:
            State data if found, None if not found or error
        """
        try:
            state = self.repo.get_by_id(state_id, access_token)
            if state:
                logger.debug("Retrieved workflow state by ID", state_id=state_id)
                return state
            else:
                logger.debug("No workflow state found with ID", state_id=state_id)
                return None

        except Exception as e:
            logger.error("Error retrieving workflow state by ID", state_id=state_id, error=str(e))
            return None

    def update_state(
        self, 
        session_id: str, 
        updates: Dict[str, Any], 
        access_token: Optional[str] = None
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
                logger.error("Cannot update - no state found for session", session_id=session_id)
                return False

            state_id = current_state["id"]
            
            # Ensure updated_at timestamp is set
            updates["updated_at"] = int(time.time() * 1000)
            
            # Handle JSON fields properly
            if "clarification_context" in updates and isinstance(updates["clarification_context"], dict):
                updates["clarification_context"] = json.dumps(updates["clarification_context"])
            
            if "workflow_context" in updates and isinstance(updates["workflow_context"], dict):
                updates["workflow_context"] = json.dumps(updates["workflow_context"])
                
            if "conversations" in updates and isinstance(updates["conversations"], list):
                updates["conversations"] = json.dumps(updates["conversations"])
                
            if "alternatives" in updates and isinstance(updates["alternatives"], list):
                updates["alternatives"] = json.dumps(updates["alternatives"])
                
            if "rag_context" in updates and isinstance(updates["rag_context"], dict):
                updates["rag_context"] = json.dumps(updates["rag_context"])

            result = self.repo.update(state_id, updates, access_token)
            if result:
                logger.info("Updated workflow state for session", session_id=session_id)
                return True
            else:
                logger.error("Failed to update workflow state for session", session_id=session_id)
                return False

        except Exception as e:
            logger.error("Error updating workflow state for session", session_id=session_id, error=str(e))
            return False

    def save_full_state(
        self, 
        session_id: str, 
        workflow_state: Dict[str, Any], 
        access_token: Optional[str] = None
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
                    access_token=access_token
                )
                
                if state_id:
                    # Update with full state data
                    updates = self._prepare_state_for_db(workflow_state)
                    return self.update_state(session_id, updates, access_token)
                
                return False

        except Exception as e:
            logger.error("Error saving full workflow state for session", session_id=session_id, error=str(e))
            return False

    def get_user_states(self, user_id: str, access_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all workflow states for a user
        
        Args:
            user_id: User identifier
            access_token: User's JWT token for RLS
            
        Returns:
            List of workflow states for the user
        """
        try:
            states = self.repo.get_by_user_id(user_id, access_token)
            logger.debug("Retrieved workflow states for user", user_id=user_id, count=len(states))
            return states

        except Exception as e:
            logger.error("Error retrieving workflow states for user", user_id=user_id, error=str(e))
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
                logger.error("Cannot delete - no state found for session", session_id=session_id)
                return False

            state_id = current_state["id"]
            result = self.repo.delete(state_id, access_token)
            
            if result:
                logger.info("Deleted workflow state for session", session_id=session_id)
                return True
            else:
                logger.error("Failed to delete workflow state for session", session_id=session_id)
                return False

        except Exception as e:
            logger.error("Error deleting workflow state for session", session_id=session_id, error=str(e))
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
            "gaps": "gaps",
            "current_workflow": "current_workflow_json",
            "debug_result": "debug_result",
            "debug_loop_count": "debug_loop_count"
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
            "alternatives": "alternatives",
            "rag": "rag_context"
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