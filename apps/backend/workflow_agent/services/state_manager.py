"""
Workflow Agent State Manager
在 workflow_agent 服务中管理 workflow_agent_state 的 CRUD 操作
"""

import time
from typing import Any, Dict, Optional

import logging

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
            logger.error("Failed to initialize Supabase client", extra={"error": str(e)})

    def create_state(
        self,
        session_id: str,
        user_id: str = "anonymous",
        initial_stage: str = "clarification",
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
                logger.warning("Supabase not available, using mock state", extra={"session_id": session_id})
                return session_id  # 返回 mock ID
            
            # Create model instance for validation
            state_model = WorkflowAgentStateModel(
                session_id=session_id,
                user_id=user_id,
                stage=WorkflowStageEnum(initial_stage),
                previous_stage=None,
                intent_summary="",
                conversations=[],
                current_workflow=None,
                debug_loop_count=0,
                final_error_message=None
            )
            
            # Convert to DB format
            state_data = state_model.to_db_dict()
            
            result = self.supabase_client.table(self.table_name).insert(state_data).execute()
            
            if result.data:
                state_id = result.data[0]["id"]
                logger.info("Created workflow_agent_state", extra={"session_id": session_id, "state_id": state_id})
                return state_id
            else:
                logger.error("Failed to create workflow_agent_state", extra={"session_id": session_id})
                return None
                
        except Exception as e:
            logger.error("Error creating workflow_agent_state", extra={"session_id": session_id, "error": str(e)})
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
                logger.warning("Supabase not available, returning mock state", extra={"session_id": session_id})
                return self._get_mock_state(session_id)
            
            result = self.supabase_client.table(self.table_name)\
                .select("*")\
                .eq("session_id", session_id)\
                .execute()
            
            if result.data:
                # 返回最新的状态记录
                latest_state = max(result.data, key=lambda x: x.get("updated_at", 0))
                
                # Create model from DB data for validation
                state_model = WorkflowAgentStateModel(**latest_state)
                
                # Convert to WorkflowState format with derived fields
                workflow_state = state_model.to_workflow_state()
                
                logger.debug("Retrieved workflow_agent_state", extra={"session_id": session_id})
                return workflow_state
            else:
                logger.debug("No workflow_agent_state found", extra={"session_id": session_id})
                return None
                
        except Exception as e:
            logger.error("Error retrieving workflow_agent_state", extra={"session_id": session_id, "error": str(e)})
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
                logger.warning("Supabase not available, mock updating state", extra={"session_id": session_id})
                return True  # Mock 成功
            
            # 获取当前状态以找到记录 ID
            current_state = self.get_state_by_session(session_id, access_token)
            if not current_state:
                logger.error("Cannot update - no workflow_agent_state found", extra={"session_id": session_id})
                return False
            
            state_id = current_state["id"]
            
            # Filter updates to only include persistent fields
            persistent_fields = [
                "stage", "previous_stage", "intent_summary", "conversations",
                "current_workflow", "debug_loop_count", "final_error_message"
            ]
            
            filtered_updates = {k: v for k, v in updates.items() if k in persistent_fields}
            
            # 确保更新时间戳
            filtered_updates["updated_at"] = int(time.time() * 1000)
            
            result = self.supabase_client.table(self.table_name)\
                .update(filtered_updates)\
                .eq("id", state_id)\
                .execute()
            
            if result.data:
                logger.info("Updated workflow_agent_state", extra={"session_id": session_id})
                return True
            else:
                logger.error("Failed to update workflow_agent_state", extra={"session_id": session_id})
                return False
                
        except Exception as e:
            logger.error("Error updating workflow_agent_state", extra={"session_id": session_id, "error": str(e)})
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
            # Create model from workflow state
            state_model = WorkflowAgentStateModel.from_workflow_state(workflow_state)
            
            # 检查状态是否存在
            existing_state = self.get_state_by_session(session_id, access_token)
            
            if existing_state:
                # 更新现有状态 - only update persistent fields
                updates = state_model.to_db_dict()
                return self.update_state(session_id, updates, access_token)
            else:
                # 创建新状态
                state_id = self.create_state(
                    session_id=session_id,
                    user_id=state_model.user_id or "anonymous",
                    initial_stage=state_model.stage.value,
                )
                
                if state_id:
                    # 用完整状态数据更新
                    updates = state_model.to_db_dict()
                    return self.update_state(session_id, updates, access_token)
                
                return False
                
        except Exception as e:
            logger.error("Error saving full workflow_agent_state", extra={"session_id": session_id, "error": str(e)})
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
                logger.warning("Supabase not available, mock deleting state", extra={"session_id": session_id})
                return True  # Mock 成功
            
            # 获取当前状态以找到记录 ID
            current_state = self.get_state_by_session(session_id, access_token)
            if not current_state:
                logger.error("Cannot delete - no workflow_agent_state found", extra={"session_id": session_id})
                return False
            
            state_id = current_state["id"]
            
            result = self.supabase_client.table(self.table_name)\
                .delete()\
                .eq("id", state_id)\
                .execute()
            
            logger.info("Deleted workflow_agent_state", extra={"session_id": session_id})
            return True
            
        except Exception as e:
            logger.error("Error deleting workflow_agent_state", extra={"session_id": session_id, "error": str(e)})
            return False

    def _prepare_state_for_db(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备状态数据以供数据库存储
        
        Args:
            workflow_state: 完整的工作流状态
            
        Returns:
            准备好的数据库字段字典
        """
        # Use model to handle conversion
        state_model = WorkflowAgentStateModel.from_workflow_state(workflow_state)
        return state_model.to_db_dict()

    def _get_mock_state(self, session_id: str) -> Dict[str, Any]:
        """返回模拟状态（用于没有 Supabase 的情况）"""
        # Create a mock model with minimal data
        mock_model = WorkflowAgentStateModel(
            session_id=session_id,
            user_id="anonymous",
            stage=WorkflowStageEnum.CLARIFICATION,
            previous_stage=None,
            intent_summary="",
            conversations=[],
            current_workflow=None,
            debug_loop_count=0,
            final_error_message=None
        )
        
        # Return as WorkflowState format with derived fields
        return mock_model.to_workflow_state()


# 全局状态管理器实例
workflow_agent_state_manager = WorkflowAgentStateManager()


def get_workflow_agent_state_manager() -> WorkflowAgentStateManager:
    """获取全局 workflow_agent 状态管理器实例"""
    return workflow_agent_state_manager