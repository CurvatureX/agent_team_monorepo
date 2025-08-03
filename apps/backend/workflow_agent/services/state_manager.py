"""
Workflow Agent State Manager
在 workflow_agent 服务中管理 workflow_agent_state 的 CRUD 操作
"""

import json
import time
from typing import Any, Dict, List, Optional

from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not available")


class WorkflowAgentStateManager:
    """
    在 workflow_agent 服务中管理 workflow_agent_state 表的 CRUD 操作
    根据 req2.md 要求，所有状态管理都在 workflow_agent 服务内部完成
    """

    def __init__(self):
        self.table_name = "workflow_agent_states"
        self.supabase_client = None
        self._init_supabase_client()
    
    def _init_supabase_client(self):
        """初始化 Supabase 客户端"""
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase not available, using mock state management")
            return
            
        try:
            supabase_url = settings.SUPABASE_URL
            supabase_key = settings.SUPABASE_SECRET_KEY
            
            if supabase_url and supabase_key:
                self.supabase_client = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized successfully")
            else:
                logger.warning("Supabase credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")

    def create_state(
        self,
        session_id: str,
        user_id: str = "anonymous",
        initial_stage: str = "clarification",
        workflow_context: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> Optional[str]:
        """
        创建新的 workflow_agent_state 记录
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            initial_stage: 初始阶段
            workflow_context: 工作流上下文
            access_token: 用户令牌
            
        Returns:
            创建成功返回 state_id，失败返回 None
        """
        try:
            if not self.supabase_client:
                logger.warning(f"Supabase not available, using mock state for session {session_id}")
                return session_id  # 返回 mock ID
            
            current_time = int(time.time() * 1000)
            
            # 默认的工作流上下文
            if workflow_context is None:
                workflow_context = {
                    "origin": "create",
                    "source_workflow_id": ""
                }
            
            state_data = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": current_time,
                "updated_at": current_time,
                "stage": initial_stage,
                "execution_history": [],
                "intent_summary": "",
                "workflow_context": workflow_context,
                "conversations": [],
                # Using legacy fields in database
                "gaps": [],  # Maps to identified_gaps in code
                "alternatives": [],  # Not used anymore
                "current_workflow_json": "",
                "debug_result": "",
                "debug_loop_count": 0,
                "clarification_context": {
                    "purpose": "initial_intent",
                    "origin": workflow_context.get("origin", "create"),
                    "pending_questions": [],
                    "collected_info": {}
                }
            }
            
            result = self.supabase_client.table(self.table_name).insert(state_data).execute()
            
            if result.data:
                state_id = result.data[0]["id"]
                logger.info(f"Created workflow_agent_state for session {session_id}: {state_id}")
                return state_id
            else:
                logger.error(f"Failed to create workflow_agent_state for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating workflow_agent_state for session {session_id}: {e}")
            return None

    def get_state_by_session(self, session_id: str, access_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        根据 session_id 获取 workflow_agent_state
        
        Args:
            session_id: 会话 ID
            access_token: 用户令牌
            
        Returns:
            状态数据字典，失败返回 None
        """
        try:
            if not self.supabase_client:
                logger.warning(f"Supabase not available, returning mock state for session {session_id}")
                return self._get_mock_state(session_id)
            
            result = self.supabase_client.table(self.table_name)\
                .select("*")\
                .eq("session_id", session_id)\
                .execute()
            
            if result.data:
                # 返回最新的状态记录
                latest_state = max(result.data, key=lambda x: x.get("updated_at", 0))
                
                # 处理 current_workflow_json 字段
                if "current_workflow_json" in latest_state and latest_state["current_workflow_json"]:
                    try:
                        latest_state["current_workflow"] = json.loads(latest_state["current_workflow_json"])
                    except json.JSONDecodeError:
                        latest_state["current_workflow"] = {}
                else:
                    latest_state["current_workflow"] = {}
                
                # Map legacy database fields to new field names
                if "gaps" in latest_state:
                    latest_state["identified_gaps"] = latest_state.get("gaps", [])
                    # Keep gaps field for backward compatibility
                if "alternatives" in latest_state:
                    # Remove alternatives as it's not used anymore
                    pass
                # Set default values for new fields not in database
                latest_state["gap_status"] = latest_state.get("gap_status", "no_gap")
                
                logger.debug(f"Retrieved workflow_agent_state for session {session_id}")
                return latest_state
            else:
                logger.debug(f"No workflow_agent_state found for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving workflow_agent_state for session {session_id}: {e}")
            return None

    def update_state(
        self, 
        session_id: str, 
        updates: Dict[str, Any], 
        access_token: Optional[str] = None
    ) -> bool:
        """
        更新 workflow_agent_state
        
        Args:
            session_id: 会话 ID
            updates: 更新的字段
            access_token: 用户令牌
            
        Returns:
            更新成功返回 True，失败返回 False
        """
        try:
            if not self.supabase_client:
                logger.warning(f"Supabase not available, mock updating state for session {session_id}")
                return True  # Mock 成功
            
            # 获取当前状态以找到记录 ID
            current_state = self.get_state_by_session(session_id, access_token)
            if not current_state:
                logger.error(f"Cannot update - no workflow_agent_state found for session {session_id}")
                return False
            
            state_id = current_state["id"]
            
            # 确保更新时间戳
            updates["updated_at"] = int(time.time() * 1000)
            
            result = self.supabase_client.table(self.table_name)\
                .update(updates)\
                .eq("id", state_id)\
                .execute()
            
            if result.data:
                logger.info(f"Updated workflow_agent_state for session {session_id}")
                return True
            else:
                logger.error(f"Failed to update workflow_agent_state for session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating workflow_agent_state for session {session_id}: {e}")
            return False

    def save_full_state(
        self, 
        session_id: str, 
        workflow_state: Dict[str, Any], 
        access_token: Optional[str] = None
    ) -> bool:
        """
        保存完整的工作流状态
        
        Args:
            session_id: 会话 ID
            workflow_state: 完整的状态数据
            access_token: 用户令牌
            
        Returns:
            保存成功返回 True，失败返回 False
        """
        try:
            # 检查状态是否存在
            existing_state = self.get_state_by_session(session_id, access_token)
            
            if existing_state:
                # 更新现有状态
                updates = self._prepare_state_for_db(workflow_state)
                return self.update_state(session_id, updates, access_token)
            else:
                # 创建新状态
                user_id = workflow_state.get("user_id", "anonymous")
                workflow_context = workflow_state.get("workflow_context")
                
                state_id = self.create_state(
                    session_id=session_id,
                    user_id=user_id,
                    initial_stage=workflow_state.get("stage", "clarification"),
                    workflow_context=workflow_context,
                    access_token=access_token,
                )
                
                if state_id:
                    # 用完整状态数据更新
                    updates = self._prepare_state_for_db(workflow_state)
                    return self.update_state(session_id, updates, access_token)
                
                return False
                
        except Exception as e:
            logger.error(f"Error saving full workflow_agent_state for session {session_id}: {e}")
            return False

    def delete_state(self, session_id: str, access_token: Optional[str] = None) -> bool:
        """
        删除 workflow_agent_state
        
        Args:
            session_id: 会话 ID
            access_token: 用户令牌
            
        Returns:
            删除成功返回 True，失败返回 False
        """
        try:
            if not self.supabase_client:
                logger.warning(f"Supabase not available, mock deleting state for session {session_id}")
                return True  # Mock 成功
            
            # 获取当前状态以找到记录 ID
            current_state = self.get_state_by_session(session_id, access_token)
            if not current_state:
                logger.error(f"Cannot delete - no workflow_agent_state found for session {session_id}")
                return False
            
            state_id = current_state["id"]
            
            result = self.supabase_client.table(self.table_name)\
                .delete()\
                .eq("id", state_id)\
                .execute()
            
            logger.info(f"Deleted workflow_agent_state for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting workflow_agent_state for session {session_id}: {e}")
            return False

    def _prepare_state_for_db(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备状态数据以供数据库存储
        
        Args:
            workflow_state: 完整的工作流状态
            
        Returns:
            准备好的数据库字段字典
        """
        db_state = {}
        
        # 直接字段映射
        field_mappings = {
            "session_id": "session_id",
            "user_id": "user_id", 
            "created_at": "created_at",
            "updated_at": "updated_at",
            "stage": "stage",
            "execution_history": "execution_history",
            "intent_summary": "intent_summary",
            # Map new field names to legacy database columns
            "identified_gaps": "gaps",  # Using legacy column name
            # "gap_status": "gap_status",  # Not in database yet - skip for now
            # gap_resolution removed - using gap_status instead
            "debug_result": "debug_result",
            "debug_loop_count": "debug_loop_count",
        }
        
        for state_key, db_key in field_mappings.items():
            if state_key in workflow_state:
                db_state[db_key] = workflow_state[state_key]
        
        # 处理 current_workflow
        if "current_workflow" in workflow_state:
            value = workflow_state["current_workflow"]
            if isinstance(value, dict):
                db_state["current_workflow_json"] = json.dumps(value)
            else:
                db_state["current_workflow_json"] = str(value) if value else ""
        
        # 处理 WorkflowStage 枚举类型
        if "stage" in workflow_state:
            stage_value = workflow_state["stage"]
            if hasattr(stage_value, 'value'):  # 是枚举类型
                db_state["stage"] = stage_value.value
            else:
                db_state["stage"] = str(stage_value)
        
        # JSON 字段
        json_fields = {
            "workflow_context": "workflow_context",
            "conversations": "conversations", 
            "clarification_context": "clarification_context"
        }
        
        for state_key, db_key in json_fields.items():
            if state_key in workflow_state:
                db_state[db_key] = workflow_state[state_key]
        
        return db_state

    def _get_mock_state(self, session_id: str) -> Dict[str, Any]:
        """返回模拟状态（用于没有 Supabase 的情况）"""
        return {
            "id": f"mock_{session_id}",
            "session_id": session_id,
            "user_id": "anonymous",
            "stage": "clarification",
            "conversations": [],
            "intent_summary": "",
            "current_workflow": None,
            # Using legacy fields in database
            "gaps": [],  # Maps to identified_gaps in code
            "alternatives": [],  # Not used anymore
            "workflow_context": {"origin": "create", "source_workflow_id": ""},
            "clarification_context": {
                "purpose": "initial_intent",
                "origin": "create", 
                "pending_questions": [],
                "collected_info": {}
            },
            "created_at": int(time.time() * 1000),
            "updated_at": int(time.time() * 1000)
        }


# 全局状态管理器实例
workflow_agent_state_manager = WorkflowAgentStateManager()


def get_workflow_agent_state_manager() -> WorkflowAgentStateManager:
    """获取全局 workflow_agent 状态管理器实例"""
    return workflow_agent_state_manager