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
            logger.error("Failed to initialize Supabase client", extra={"error": str(e)})

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
                logger.warning("Supabase not available, using mock state", extra={"session_id": session_id})
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
                "previous_stage": None,
                "execution_history": [],
                "intent_summary": "",
                "workflow_context": workflow_context,
                "conversations": [],
                "identified_gaps": [],
                "gap_status": "no_gap",
                "current_workflow": None,
                "template_workflow": None,
                "debug_result": None,
                "debug_loop_count": 0,
                "template_id": None,
                "clarification_context": {
                    "purpose": "initial_intent",
                    "collected_info": {},
                    "pending_questions": [],
                    "origin": "create"
                },
                "gap_negotiation_count": 0,
                "selected_alternative": None
            }
            
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
                
                # 处理 current_workflow 字段 (现在直接是JSONB，不需要解析)
                if "current_workflow" not in latest_state:
                    latest_state["current_workflow"] = None
                
                # 处理 debug_result 字段
                if "debug_result" in latest_state and latest_state["debug_result"]:
                    try:
                        if isinstance(latest_state["debug_result"], str):
                            latest_state["debug_result"] = json.loads(latest_state["debug_result"])
                    except json.JSONDecodeError:
                        pass  # Keep as string if not valid JSON
                
                # All fields should exist in database, no defaults needed
                
                logger.debug("Retrieved workflow_agent_state", extra={"session_id": session_id})
                return latest_state
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
            
            # 确保更新时间戳
            updates["updated_at"] = int(time.time() * 1000)
            
            result = self.supabase_client.table(self.table_name)\
                .update(updates)\
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
        db_state = {}
        
        # 直接字段映射 (基于state.py的WorkflowState)
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
            "debug_loop_count": "debug_loop_count",
            "template_id": "template_id",
            "current_workflow": "current_workflow",
            "template_workflow": "template_workflow",
            "gap_negotiation_count": "gap_negotiation_count",
            "selected_alternative": "selected_alternative",
        }
        
        for state_key, db_key in field_mappings.items():
            if state_key in workflow_state:
                db_state[db_key] = workflow_state[state_key]
        
        # current_workflow 现在直接存为JSONB，不需要转换
        
        # 处理 WorkflowStage 枚举类型
        if "stage" in workflow_state:
            stage_value = workflow_state["stage"]
            if hasattr(stage_value, 'value'):  # 是枚举类型
                db_state["stage"] = stage_value.value
            else:
                db_state["stage"] = str(stage_value)
        
        if "previous_stage" in workflow_state:
            prev_stage_value = workflow_state["previous_stage"]
            if prev_stage_value is not None:
                if hasattr(prev_stage_value, 'value'):  # 是枚举类型
                    db_state["previous_stage"] = prev_stage_value.value
                else:
                    db_state["previous_stage"] = str(prev_stage_value)
        
        # 处理 GapStatus 枚举类型
        if "gap_status" in workflow_state:
            gap_value = workflow_state["gap_status"]
            if hasattr(gap_value, 'value'):  # 是枚举类型
                db_state["gap_status"] = gap_value.value
            else:
                db_state["gap_status"] = str(gap_value)
        
        # debug_result 现在直接存为JSONB，不需要转换
        if "debug_result" in workflow_state:
            db_state["debug_result"] = workflow_state["debug_result"]
        
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
            "previous_stage": None,
            "conversations": [],
            "intent_summary": "",
            "current_workflow": None,
            "template_workflow": None,
            "identified_gaps": [],
            "gap_status": "no_gap",
            "workflow_context": {"origin": "create", "requirements": {}},
            "clarification_context": {
                "purpose": "initial_intent",
                "collected_info": {},
                "pending_questions": [],
                "origin": "create"
            },
            "debug_result": None,
            "debug_loop_count": 0,
            "execution_history": [],
            "template_id": None,
            "gap_negotiation_count": 0,
            "selected_alternative": None,
            "created_at": int(time.time() * 1000),
            "updated_at": int(time.time() * 1000)
        }


# 全局状态管理器实例
workflow_agent_state_manager = WorkflowAgentStateManager()


def get_workflow_agent_state_manager() -> WorkflowAgentStateManager:
    """获取全局 workflow_agent 状态管理器实例"""
    return workflow_agent_state_manager