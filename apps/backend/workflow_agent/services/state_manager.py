"""
Workflow Agent State Manager
在 workflow_agent 服务中管理 workflow_agent_state 的 CRUD 操作
"""

import time
from typing import Any, Dict, Optional

from workflow_agent.core.config import settings
from workflow_agent.models.workflow_agent_state import WorkflowAgentStateModel, WorkflowStageEnum
from shared.logging_config import get_logger

logger = get_logger(__name__)

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

            if not supabase_url or not supabase_key:
                logger.warning("Missing Supabase configuration, using mock state management")
                return

            self.supabase_client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")

    def create_state(
        self,
        session_id: str,
        user_id: str,
        initial_stage: WorkflowStageEnum,
        access_token: str,
        workflow_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        创建新的 workflow_agent_state 记录

        Returns:
            State ID if successful, None if failed
        """
        if not self.supabase_client:
            logger.warning("Supabase client not available, using mock create_state")
            # 返回 mock session_id，让流程继续
            return session_id

        try:
            logger.info(
                "Creating workflow_agent_state",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "initial_stage": initial_stage.value,
                },
            )

            # Create model instance for validation
            state_model = WorkflowAgentStateModel(
                session_id=session_id,
                user_id=user_id,
                stage=initial_stage,
                intent_summary="",
                conversations=[],
                debug_loop_count=0,
            )

            # Convert to database format
            state_data = state_model.to_db_dict()

            result = self.supabase_client.table(self.table_name).insert(state_data).execute()

            if result.data and len(result.data) > 0:
                state_id = result.data[0]["id"]
                logger.info("Created workflow_agent_state", extra={"state_id": state_id})
                return state_id
            else:
                logger.error("Failed to create workflow_agent_state: No data returned")
                return None

        except Exception as e:
            logger.error(f"Failed to create workflow_agent_state: {e}")
            return None

    def get_state_by_session(
        self, session_id: str, access_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        根据 session_id 获取最新的 workflow_agent_state

        Returns:
            Workflow state dict if found, None if not found
        """
        if not self.supabase_client:
            logger.warning(
                "Supabase client not available, using mock get_state_by_session"
            )
            # 返回基本的 mock 状态，让流程继续
            return {
                "session_id": session_id,
                "user_id": "mock_user",
                "stage": "clarification",
                "intent_summary": "",
                "conversations": [],
                "debug_loop_count": 0,
                # current_workflow is not included - it's runtime-only
            }

        try:
            logger.debug(
                "Getting workflow_agent_state by session",
                extra={"session_id": session_id},
            )

            result = (
                self.supabase_client.table(self.table_name)
                .select("*")
                .eq("session_id", session_id)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )

            if result.data and len(result.data) > 0:
                # 返回最新的状态记录
                latest_state = max(result.data, key=lambda x: x.get("updated_at", 0))

                # Create model from DB data using the helper method
                workflow_state = self._db_to_workflow_state(latest_state)

                logger.debug("Retrieved workflow_agent_state", extra={"session_id": session_id})
                return workflow_state
            else:
                logger.debug("No workflow_agent_state found", extra={"session_id": session_id})
                return None

        except Exception as e:
            logger.error(
                f"Failed to get workflow_agent_state: {e}",
                extra={"session_id": session_id},
            )
            return None

    def save_full_state(
        self, session_id: str, workflow_state: Dict[str, Any], access_token: str
    ) -> bool:
        """
        保存完整的 workflow_state 到数据库
        如果记录存在则更新，不存在则创建

        Returns:
            True if successful, False if failed
        """
        if not self.supabase_client:
            logger.warning("Supabase client not available, using mock save_full_state")
            return True

        try:
            logger.debug("Saving full workflow_agent_state", extra={"session_id": session_id})

            # 先检查是否存在记录
            current_state = self.get_state_by_session(session_id, access_token)

            if current_state:
                # 更新现有记录

                state_id = current_state["id"]

                # Filter updates to only include persistent fields (matching actual DDL)
                filtered_updates = {
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
                    # NOTE: current_workflow is NOT saved - it's transient runtime data
                }

                result = (
                    self.supabase_client.table(self.table_name)
                    .update(filtered_updates)
                    .eq("id", state_id)
                    .execute()
                )

                if result.data and len(result.data) > 0:
                    logger.debug("Updated workflow_agent_state", extra={"session_id": session_id})
                    return True
                else:
                    logger.error("Failed to update workflow_agent_state: No data returned")
                    return False

            else:
                # 创建新状态
                state_id = self.create_state(
                    session_id=session_id,
                    user_id=workflow_state.get("user_id", "anonymous"),
                    initial_stage=WorkflowStageEnum(workflow_state.get("stage", "clarification")),
                    access_token=access_token,
                    workflow_context=workflow_state.get("workflow_context"),
                )

                return state_id is not None

        except Exception as e:
            logger.error(
                f"Failed to save workflow_agent_state: {e}",
                extra={"session_id": session_id},
            )
            return False

    def delete_state_by_session(self, session_id: str, access_token: str) -> bool:
        """
        删除指定 session_id 的所有 workflow_agent_state 记录

        Returns:
            True if successful, False if failed
        """
        if not self.supabase_client:
            logger.warning("Supabase client not available, using mock delete_state")
            return True

        try:
            logger.info("Deleting workflow_agent_state", extra={"session_id": session_id})

            (
                self.supabase_client.table(self.table_name)
                .delete()
                .eq("session_id", session_id)
                .execute()
            )

            logger.info("Deleted workflow_agent_state", extra={"session_id": session_id})
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete workflow_agent_state: {e}",
                extra={"session_id": session_id},
            )
            return False

    def _workflow_to_db_state(self, workflow_state: Dict[str, Any]) -> dict:
        """转换工作流状态为数据库状态

        Args:
            workflow_state: 工作流状态字典

        Returns:
            准备好的数据库字段字典
        """
        # Use model to handle conversion
        state_model = WorkflowAgentStateModel.from_workflow_state(workflow_state)
        return state_model.to_db_dict()

    def _db_to_workflow_state(self, db_state: dict) -> dict:
        """转换数据库状态为workflow状态"""
        # Create model from DB data (matching actual DDL fields)
        mock_model = WorkflowAgentStateModel(
            session_id=db_state.get("session_id", ""),
            user_id=db_state.get("user_id", "anonymous"),
            stage=WorkflowStageEnum(db_state.get("stage", "clarification")),
            previous_stage=WorkflowStageEnum(db_state["previous_stage"]) if db_state.get("previous_stage") else None,
            intent_summary=db_state.get("intent_summary", ""),
            conversations=db_state.get("conversations", []),
            debug_result=db_state.get("debug_result"),  # Text from DB
            debug_loop_count=db_state.get("debug_loop_count", 0),
            template_workflow=db_state.get("template_workflow"),
            workflow_id=db_state.get("workflow_id"),
            final_error_message=db_state.get("final_error_message"),
        )

        # Set optional fields if they exist
        if db_state.get("id"):
            mock_model.id = db_state["id"]
        if db_state.get("created_at"):
            mock_model.created_at = db_state["created_at"]
        if db_state.get("updated_at"):
            mock_model.updated_at = db_state["updated_at"]

        # Return as WorkflowState format with derived fields
        return mock_model.to_workflow_state()
    
    def _convert_debug_result_to_text(self, debug_result) -> Optional[str]:
        """Convert debug_result dict to text for DB storage"""
        if debug_result is None:
            return None
        if isinstance(debug_result, str):
            return debug_result
        if isinstance(debug_result, dict):
            import json
            return json.dumps(debug_result)
        return str(debug_result)


def get_workflow_agent_state_manager() -> WorkflowAgentStateManager:
    """获取 WorkflowAgentStateManager 实例"""
    return WorkflowAgentStateManager()
