"""
统一的响应处理器 - 消除重复代码
处理不同stage的响应格式转换
"""

import structlog
from typing import Dict, Any, Optional, List

logger = structlog.get_logger("response_processor")


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
            "negotiation": UnifiedResponseProcessor._process_negotiation,
            "gap_analysis": UnifiedResponseProcessor._process_gap_analysis,
            "alternative_generation": UnifiedResponseProcessor._process_alternative_generation,
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
    def _process_negotiation(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理协商阶段响应"""
        conversations = agent_state.get("conversations", [])
        alternatives = agent_state.get("alternatives", [])
        
        latest_message = ""
        if conversations:
            for conv in reversed(conversations):
                if isinstance(conv, dict) and conv.get("role") == "assistant":
                    latest_message = conv.get("text", "")
                    break
        
        # 如果有替代方案，返回alternatives类型
        if alternatives:
            return {
                "type": "alternatives",
                "content": {
                    "text": latest_message,
                    "stage": "negotiation", 
                    "alternatives": alternatives
                }
            }
        else:
            return {
                "type": "ai_message",
                "content": {
                    "text": latest_message or "正在进行需求协商...",
                    "stage": "negotiation"
                }
            }
    
    @staticmethod
    def _process_gap_analysis(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理差距分析阶段响应"""
        conversations = agent_state.get("conversations", [])
        gaps = agent_state.get("gaps", [])
        
        latest_message = ""
        if conversations:
            for conv in reversed(conversations):
                if isinstance(conv, dict) and conv.get("role") == "assistant":
                    latest_message = conv.get("text", "")
                    break
        
        return {
            "type": "ai_message",
            "content": {
                "text": latest_message or "正在分析技术差距...",
                "stage": "gap_analysis",
                "gaps": gaps
            }
        }
    
    @staticmethod
    def _process_alternative_generation(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理替代方案生成阶段响应"""
        conversations = agent_state.get("conversations", [])
        alternatives = agent_state.get("alternatives", [])
        
        latest_message = ""
        if conversations:
            for conv in reversed(conversations):
                if isinstance(conv, dict) and conv.get("role") == "assistant":
                    latest_message = conv.get("text", "")
                    break
        
        if alternatives:
            return {
                "type": "alternatives",
                "content": {
                    "text": latest_message,
                    "stage": "alternative_generation",
                    "alternatives": alternatives
                }
            }
        else:
            return {
                "type": "ai_message", 
                "content": {
                    "text": latest_message or "正在生成替代方案...",
                    "stage": "alternative_generation"
                }
            }
    
    @staticmethod
    def _process_workflow_generation(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流生成阶段响应"""
        conversations = agent_state.get("conversations", [])
        current_workflow = agent_state.get("current_workflow")
        
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
        debug_result = agent_state.get("debug_result", "")
        debug_loop_count = agent_state.get("debug_loop_count", 0)
        current_workflow = agent_state.get("current_workflow")
        
        latest_message = ""
        if conversations:
            for conv in reversed(conversations):
                if isinstance(conv, dict) and conv.get("role") == "assistant":
                    latest_message = conv.get("text", "")
                    break
        
        # 如果有调试后的工作流，返回workflow类型
        if current_workflow and debug_result:
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
                    "stage": "debug",
                    "debug_result": debug_result,
                    "debug_loop_count": debug_loop_count
                }
            }
        else:
            return {
                "type": "ai_message",
                "content": {
                    "text": latest_message or f"正在调试工作流 (第{debug_loop_count}次)...",
                    "stage": "debug",
                    "debug_result": debug_result,
                    "debug_loop_count": debug_loop_count
                }
            }
    
    @staticmethod
    def _process_completed(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理完成阶段响应"""
        conversations = agent_state.get("conversations", [])
        current_workflow = agent_state.get("current_workflow")
        
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