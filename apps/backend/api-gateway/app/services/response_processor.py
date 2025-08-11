"""
统一的响应处理器 - 消除重复代码
处理不同stage的响应格式转换
"""

from typing import Dict, Any, Optional, List

from shared.logging_config import get_logger
logger = get_logger("app.services.response_processor")


class UnifiedResponseProcessor:
    """统一的响应处理器，处理所有stage的响应格式"""
    
    @staticmethod
    def process_stage_response(stage: str, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据stage处理响应
        
        Args:
            stage: 当前阶段
            agent_state: Agent状态数据
            
        Returns:
            处理后的响应数据
        """
        processors = {
            "clarification": UnifiedResponseProcessor._process_clarification,
            "workflow_generation": UnifiedResponseProcessor._process_workflow_generation,
            "debug": UnifiedResponseProcessor._process_debug,
            "completed": UnifiedResponseProcessor._process_completed
        }
        
        processor = processors.get(stage, UnifiedResponseProcessor._process_clarification)
        return processor(agent_state)
    
    @staticmethod
    def _process_clarification(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理澄清阶段响应"""
        conversations = agent_state.get("conversations", [])
        latest_message = ""
        
        if conversations:
            # 获取最新的assistant消息
            for conv in reversed(conversations):
                if isinstance(conv, dict) and conv.get("role") == "assistant":
                    latest_message = conv.get("text", "")
                    break
        
        # 检查是否有待解决的问题
        clarification_context = agent_state.get("clarification_context", {})
        pending_questions = clarification_context.get("pending_questions", [])
        
        return {
            "type": "ai_message",
            "content": {
                "text": latest_message or "正在分析您的需求，请稍候...",
                "stage": "clarification",
                "pending_questions": pending_questions,
                "clarification_context": clarification_context
            }
        }
    
    
    @staticmethod
    def _process_workflow_generation(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流生成阶段响应"""
        conversations = agent_state.get("conversations", [])
        current_workflow = agent_state.get("current_workflow_json") or agent_state.get("current_workflow")
        
        latest_message = ""
        if conversations:
            for conv in reversed(conversations):
                if isinstance(conv, dict) and conv.get("role") == "assistant":
                    latest_message = conv.get("text", "")
                    break
        
        # 如果有工作流数据，返回workflow类型
        if current_workflow:
            # 确保workflow是dict格式
            workflow_data = current_workflow
            if isinstance(current_workflow, str):
                try:
                    import json
                    workflow_data = json.loads(current_workflow)
                except (json.JSONDecodeError, TypeError):
                    logger.error("Failed to parse workflow JSON")
                    workflow_data = {"error": "Invalid workflow data"}
            
            return {
                "type": "workflow",
                "workflow": workflow_data,
                "content": {
                    "text": latest_message,
                    "stage": "workflow_generation"
                }
            }
        else:
            return {
                "type": "ai_message",
                "content": {
                    "text": latest_message or "正在生成工作流...",
                    "stage": "workflow_generation"
                }
            }
    
    @staticmethod
    def _process_debug(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理调试阶段响应"""
        conversations = agent_state.get("conversations", [])
        debug_result = agent_state.get("debug_result", {})
        debug_loop_count = agent_state.get("debug_loop_count", 0)
        current_workflow = agent_state.get("current_workflow_json") or agent_state.get("current_workflow")
        
        latest_message = ""
        if conversations:
            for conv in reversed(conversations):
                if isinstance(conv, dict) and conv.get("role") == "assistant":
                    latest_message = conv.get("text", "")
                    break
        
        # 根据debug_result构建消息
        if isinstance(debug_result, dict):
            if debug_result.get("success"):
                debug_status = "✅ SUCCESS: 工作流验证通过"
            else:
                debug_status = f"❌ ERROR: {debug_result.get('error', '工作流存在问题')}"
        else:
            debug_status = "正在验证工作流..."
        
        # 如果没有最新消息，使用debug状态
        if not latest_message:
            latest_message = debug_status
        elif debug_result:
            # 如果有debug结果，将状态追加到消息
            latest_message = f"{latest_message}\n\n{debug_status}"
        
        # 如果有调试后的工作流，返回workflow类型
        if current_workflow:
            workflow_data = current_workflow
            if isinstance(current_workflow, str):
                try:
                    import json
                    workflow_data = json.loads(current_workflow)
                except (json.JSONDecodeError, TypeError):
                    logger.error("Failed to parse workflow JSON in debug")
                    workflow_data = {"error": "Invalid workflow data"}
            
            return {
                "type": "workflow",
                "workflow": workflow_data,
                "content": {
                    "text": latest_message,
                    "stage": "debug"
                }
            }
        else:
            return {
                "type": "ai_message",
                "content": {
                    "text": latest_message or f"正在调试工作流 (第{debug_loop_count+1}次)...",
                    "stage": "debug"
                }
            }
    
    @staticmethod
    def _process_completed(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理完成阶段响应"""
        conversations = agent_state.get("conversations", [])
        current_workflow = agent_state.get("current_workflow_json") or agent_state.get("current_workflow")
        
        latest_message = ""
        if conversations:
            for conv in reversed(conversations):
                if isinstance(conv, dict) and conv.get("role") == "assistant":
                    latest_message = conv.get("text", "")
                    break
        
        # 完成阶段总是返回最终的工作流
        if current_workflow:
            workflow_data = current_workflow
            if isinstance(current_workflow, str):
                try:
                    import json
                    workflow_data = json.loads(current_workflow)
                except (json.JSONDecodeError, TypeError):
                    logger.error("Failed to parse final workflow JSON")
                    workflow_data = {"error": "Invalid workflow data"}
            
            return {
                "type": "workflow",
                "workflow": workflow_data,
                "content": {
                    "text": latest_message or "工作流已完成生成",
                    "stage": "completed"
                }
            }
        else:
            # 如果没有工作流数据，可能是错误情况
            return {
                "type": "error",
                "content": {
                    "message": "工作流生成未完成",
                    "error_code": "WORKFLOW_GENERATION_FAILED",
                    "stage": "completed"
                }
            }
    
    @staticmethod
    def create_error_response(error_message: str, error_code: str = "UNKNOWN_ERROR", stage: str = "unknown") -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "type": "error",
            "content": {
                "message": error_message,
                "error_code": error_code,
                "stage": stage,
                "is_recoverable": True
            }
        }
    
    @staticmethod
    def create_status_response(message: str, stage: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建状态响应"""
        return {
            "type": "status",
            "content": {
                "message": message,
                "stage": stage,
                "metadata": metadata or {}
            }
        }