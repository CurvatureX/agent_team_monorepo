"""
Optimized Workflow Agent State Manager with connection pooling and batch operations
"""

import json
import logging
import time
from typing import Any, Dict, Optional, List
from datetime import datetime

from workflow_agent.core.config import settings
from workflow_agent.models.workflow_agent_state import WorkflowAgentStateModel, WorkflowStageEnum

logger = logging.getLogger(__name__)

# Import Supabase client
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not available")

# Redis for caching (optional optimization)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available for caching")


class WorkflowAgentStateManager:
    """
    Optimized state manager with connection pooling and batch operations
    """

    def __init__(self):
        self.table_name = "workflow_agent_states"
        self.supabase_client = None
        self.redis_client = None
        self._init_supabase_client()
        self._init_redis_client()
        
        # Cache for frequently accessed data
        self._local_cache = {}
        self._cache_ttl = 300  # 5 minutes

    def _init_supabase_client(self):
        """Initialize Supabase client with optimized connection pooling"""
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase not available, using mock state management")
            return

        try:
            supabase_url = settings.SUPABASE_URL
            supabase_key = settings.SUPABASE_SECRET_KEY

            if not supabase_url or not supabase_key:
                logger.warning("Missing Supabase configuration")
                return

            # Create client - Supabase Python SDK doesn't support advanced pooling options yet
            # Just use the basic client for now
            self.supabase_client = create_client(supabase_url, supabase_key)
            
            logger.info(f"Supabase client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")

    def _init_redis_client(self):
        """Initialize Redis client for caching"""
        if not REDIS_AVAILABLE:
            return
            
        try:
            self.redis_client = redis.Redis(
                host='redis',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                connection_pool=redis.ConnectionPool(
                    max_connections=10,
                    host='redis',
                    port=6379,
                    db=0
                )
            )
            self.redis_client.ping()
            logger.info("Redis client initialized for caching")
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
            self.redis_client = None

    def create_state_optimized(
        self,
        session_id: str,
        user_id: str,
        initial_stage: WorkflowStageEnum,
        access_token: str,
        workflow_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Optimized state creation with single database transaction
        """
        if not self.supabase_client:
            logger.warning("Supabase client not available")
            return session_id

        try:
            start_time = time.time()
            
            # Create complete state in one go (avoid multiple round trips)
            state_data = {
                "session_id": session_id,
                "user_id": user_id,
                "stage": initial_stage.value,
                "intent_summary": "",
                "conversations": [],
                "debug_loop_count": 0,
                "created_at": int(time.time() * 1000),
                "updated_at": int(time.time() * 1000)
            }
            
            # Single database call (synchronous)
            result = self.supabase_client.table(self.table_name).insert(state_data).execute()
            
            if result and result.data and len(result.data) > 0:
                state_id = result.data[0]["id"]
                
                # Cache the new state
                self._cache_state(session_id, result.data[0])
                
                elapsed = time.time() - start_time
                logger.info(f"Created workflow_agent_state in {elapsed:.2f}s", extra={"state_id": state_id})
                return state_id
            
            return None

        except Exception as e:
            logger.error(f"Failed to create workflow_agent_state: {e}")
            return None

    def get_state_by_session_cached(
        self, session_id: str, access_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get state with caching to reduce database calls
        """
        # Check local cache first
        cache_key = f"state:{session_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for session {session_id}")
            return cached

        # Check Redis cache if available
        if self.redis_client:
            try:
                redis_cached = self.redis_client.get(cache_key)
                if redis_cached:
                    state = json.loads(redis_cached)
                    logger.debug(f"Redis cache hit for session {session_id}")
                    return state
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        # Fallback to database
        if not self.supabase_client:
            return self._get_mock_state(session_id)

        try:
            start_time = time.time()
            
            result = (
                self.supabase_client.table(self.table_name)
                .select("*")
                .eq("session_id", session_id)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )

            if result.data and len(result.data) > 0:
                state = result.data[0]
                workflow_state = self._db_to_workflow_state(state)
                
                # Cache the result
                self._cache_state(session_id, workflow_state)
                
                elapsed = time.time() - start_time
                logger.debug(f"Retrieved workflow_agent_state in {elapsed:.2f}s", extra={"session_id": session_id})
                return workflow_state
            
            return None

        except Exception as e:
            logger.error(f"Failed to get workflow_agent_state: {e}")
            return None

    def save_full_state_batch(
        self, 
        session_id: str, 
        workflow_state: Dict[str, Any], 
        access_token: str
    ) -> bool:
        """
        Optimized state saving with batch updates
        """
        if not self.supabase_client:
            return True

        try:
            start_time = time.time()
            
            # Prepare all updates in one structure
            updates = {
                "stage": workflow_state.get("stage"),
                "previous_stage": workflow_state.get("previous_stage"),
                "intent_summary": workflow_state.get("intent_summary", ""),
                "conversations": workflow_state.get("conversations", []),
                "debug_result": self._convert_debug_result_to_text(workflow_state.get("debug_result")),
                "debug_loop_count": workflow_state.get("debug_loop_count", 0),
                "template_workflow": workflow_state.get("template_workflow"),
                "workflow_id": workflow_state.get("workflow_id"),
                "final_error_message": workflow_state.get("final_error_message"),
                "updated_at": int(time.time() * 1000),
            }

            # Check if state exists first
            existing = (
                self.supabase_client.table(self.table_name)
                .select("id")
                .eq("session_id", session_id)
                .limit(1)
                .execute()
            )
            
            if existing.data and len(existing.data) > 0:
                # Update existing record
                state_id = existing.data[0]["id"]
                result = (
                    self.supabase_client.table(self.table_name)
                    .update(updates)
                    .eq("id", state_id)
                    .execute()
                )
            else:
                # Create new record
                create_data = {
                    "session_id": session_id,
                    "user_id": workflow_state.get("user_id", "anonymous"),
                    **updates
                }
                result = (
                    self.supabase_client.table(self.table_name)
                    .insert(create_data)
                    .execute()
                )

            if result.data:
                # Update cache
                self._cache_state(session_id, result.data[0])
                
                elapsed = time.time() - start_time
                logger.debug(f"Saved workflow_agent_state in {elapsed:.2f}s", extra={"session_id": session_id})
                return True
            
            return False

        except Exception as e:
            logger.error(f"Failed to save workflow_agent_state: {e}")
            return False

    def batch_get_states(
        self, 
        session_ids: List[str], 
        access_token: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple states in a single query
        """
        if not self.supabase_client:
            return {sid: self._get_mock_state(sid) for sid in session_ids}

        try:
            # Get all states in one query
            result = (
                self.supabase_client.table(self.table_name)
                .select("*")
                .in_("session_id", session_ids)
                .execute()
            )

            states = {}
            if result.data:
                for state in result.data:
                    session_id = state["session_id"]
                    states[session_id] = self._db_to_workflow_state(state)
                    # Cache each state
                    self._cache_state(session_id, states[session_id])

            return states

        except Exception as e:
            logger.error(f"Failed to batch get states: {e}")
            return {}

    def _cache_state(self, session_id: str, state: Dict[str, Any]):
        """Cache state in memory and Redis"""
        cache_key = f"state:{session_id}"
        
        # Local cache
        self._local_cache[cache_key] = {
            "data": state,
            "timestamp": time.time()
        }
        
        # Redis cache if available
        if self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    self._cache_ttl,
                    json.dumps(state)
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from local cache if not expired"""
        if cache_key in self._local_cache:
            cached = self._local_cache[cache_key]
            if time.time() - cached["timestamp"] < self._cache_ttl:
                return cached["data"]
            else:
                del self._local_cache[cache_key]
        return None

    def _get_mock_state(self, session_id: str) -> Dict[str, Any]:
        """Return mock state for testing"""
        return {
            "session_id": session_id,
            "user_id": "mock_user",
            "stage": "clarification",
            "intent_summary": "",
            "conversations": [],
            "debug_loop_count": 0,
        }

    def _db_to_workflow_state(self, db_state: dict) -> dict:
        """Convert database state to workflow state"""
        mock_model = WorkflowAgentStateModel(
            session_id=db_state.get("session_id", ""),
            user_id=db_state.get("user_id", "anonymous"),
            stage=WorkflowStageEnum(db_state.get("stage", "clarification")),
            previous_stage=WorkflowStageEnum(db_state["previous_stage"]) if db_state.get("previous_stage") else None,
            intent_summary=db_state.get("intent_summary", ""),
            conversations=db_state.get("conversations", []),
            debug_result=db_state.get("debug_result"),
            debug_loop_count=db_state.get("debug_loop_count", 0),
            template_workflow=db_state.get("template_workflow"),
            workflow_id=db_state.get("workflow_id"),
            final_error_message=db_state.get("final_error_message"),
        )

        if db_state.get("id"):
            mock_model.id = db_state["id"]
        if db_state.get("created_at"):
            mock_model.created_at = db_state["created_at"]
        if db_state.get("updated_at"):
            mock_model.updated_at = db_state["updated_at"]

        return mock_model.to_workflow_state()
    
    def _convert_debug_result_to_text(self, debug_result) -> Optional[str]:
        """Convert debug_result dict to text for DB storage"""
        if debug_result is None:
            return None
        if isinstance(debug_result, str):
            return debug_result
        if isinstance(debug_result, dict):
            return json.dumps(debug_result)
        return str(debug_result)

    # Backward compatibility methods
    def create_state(self, *args, **kwargs):
        """Use optimized version"""
        return self.create_state_optimized(*args, **kwargs)
    
    def get_state_by_session(self, *args, **kwargs):
        """Use cached version"""
        return self.get_state_by_session_cached(*args, **kwargs)
    
    def save_full_state(self, *args, **kwargs):
        """Use batch version"""
        return self.save_full_state_batch(*args, **kwargs)
    
    def delete_state_by_session(self, session_id: str, access_token: str) -> bool:
        """Delete state and clear cache"""
        cache_key = f"state:{session_id}"
        
        # Clear caches
        if cache_key in self._local_cache:
            del self._local_cache[cache_key]
        
        if self.redis_client:
            try:
                self.redis_client.delete(cache_key)
            except:
                pass
        
        if not self.supabase_client:
            return True

        try:
            self.supabase_client.table(self.table_name).delete().eq("session_id", session_id).execute()
            logger.info(f"Deleted workflow_agent_state for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete state: {e}")
            return False


def get_workflow_agent_state_manager() -> WorkflowAgentStateManager:
    """Get optimized WorkflowAgentStateManager instance"""
    return WorkflowAgentStateManager()