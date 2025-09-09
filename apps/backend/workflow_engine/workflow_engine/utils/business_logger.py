"""
业务日志记录器 - 专门用于记录用户友好的workflow执行信息
与技术日志完全分离，提供清晰的工作流执行状态追踪
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class WorkflowBusinessLogger:
    """
    专门的业务日志记录器，用于记录用户友好的工作流执行信息

    特点:
    1. 完全独立的日志器，避免与技术日志混杂
    2. 专注于业务可理解的信息
    3. 结构化的入参出参记录
    4. 明确的执行状态和错误信息
    """

    def __init__(self, execution_id: str, workflow_name: str = "Unnamed Workflow"):
        """初始化业务日志记录器"""
        # 创建独立的业务日志器
        self.business_logger = logging.getLogger(f"workflow_business.{execution_id}")

        # 确保使用独立的handler，避免与根日志器混杂
        if not self.business_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "🔄 WORKFLOW | %(asctime)s | %(message)s", datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            handler.setLevel(logging.INFO)
            self.business_logger.addHandler(handler)
            self.business_logger.setLevel(logging.INFO)
            # 防止日志传播到父logger
            self.business_logger.propagate = False

        self.execution_id = execution_id
        self.workflow_name = workflow_name
        self.start_time = datetime.now()

    def workflow_started(self, total_steps: int, trigger_info: Optional[str] = None):
        """记录工作流开始"""
        trigger_msg = f" | 触发方式: {trigger_info}" if trigger_info else ""
        self.business_logger.info(
            f"🚀 工作流开始执行: {self.workflow_name} | 总步骤数: {total_steps}{trigger_msg} | 执行ID: {self.execution_id[:8]}..."
        )

    def step_started(
        self,
        step_number: int,
        total_steps: int,
        step_name: str,
        node_type: str,
        description: Optional[str] = None,
    ):
        """记录步骤开始"""
        desc_msg = f" | {description}" if description else ""
        self.business_logger.info(
            f"📍 步骤 [{step_number}/{total_steps}] {step_name} ({node_type}){desc_msg}"
        )

    def step_input_summary(self, step_name: str, key_inputs: Dict[str, Any]):
        """记录步骤输入摘要"""
        if not key_inputs:
            self.business_logger.info(f"📥 {step_name} | 输入: (无)")
            return

        input_items = []
        for key, value in key_inputs.items():
            formatted_value = self._format_business_value(value)
            input_items.append(f"{key}: {formatted_value}")

        self.business_logger.info(f"📥 {step_name} | 输入: {' | '.join(input_items)}")

    def step_output_summary(
        self, step_name: str, key_outputs: Dict[str, Any], success: bool = True
    ):
        """记录步骤输出摘要"""
        icon = "📤" if success else "❌"
        status = "完成" if success else "失败"

        if not key_outputs:
            self.business_logger.info(f"{icon} {step_name} | {status}: (无输出)")
            return

        output_items = []
        for key, value in key_outputs.items():
            formatted_value = self._format_business_value(value)
            output_items.append(f"{key}: {formatted_value}")

        self.business_logger.info(f"{icon} {step_name} | {status}: {' | '.join(output_items)}")

    def step_completed(self, step_name: str, duration_seconds: float, status: str = "SUCCESS"):
        """记录步骤完成"""
        if status == "SUCCESS":
            icon = "✅"
            status_text = "成功完成"
        elif status == "PAUSED":
            icon = "⏸️"
            status_text = "暂停等待"
        else:
            icon = "❌"
            status_text = "执行失败"

        self.business_logger.info(
            f"{icon} {step_name} | {status_text} | 耗时: {duration_seconds:.1f}秒"
        )

    def step_error(
        self, step_name: str, error_message: str, user_friendly_reason: Optional[str] = None
    ):
        """记录步骤错误"""
        reason = user_friendly_reason or error_message
        self.business_logger.error(f"💥 {step_name} | 执行失败: {reason}")

        # 提供技术错误信息（单独一行，便于过滤）
        self.business_logger.error(f"🔧 技术错误详情: {error_message}")

    def workflow_completed(
        self,
        total_steps: int,
        successful_steps: int,
        total_duration_seconds: float,
        final_status: str = "SUCCESS",
        performance_stats: Optional[Dict[str, Any]] = None,
    ):
        """记录工作流完成"""
        failed_steps = total_steps - successful_steps

        if final_status == "SUCCESS":
            icon = "🎉"
            status_text = "全部完成"
        elif final_status == "PAUSED":
            icon = "⏸️"
            status_text = "暂停中"
        else:
            icon = "💥"
            status_text = "执行失败"

        # 基本完成信息
        completion_msg = (
            f"{icon} 工作流{status_text}: {self.workflow_name} | "
            f"成功: {successful_steps}/{total_steps} | "
            f"失败: {failed_steps} | "
            f"总耗时: {total_duration_seconds:.1f}秒"
        )

        # 添加性能统计信息
        if performance_stats:
            if "avg_step_time" in performance_stats:
                avg_time = performance_stats["avg_step_time"]
                completion_msg += f" | 平均步骤时间: {avg_time:.1f}秒"
            if "slowest_step" in performance_stats:
                slowest = performance_stats["slowest_step"]
                completion_msg += f" | 最慢步骤: {slowest['name']} ({slowest['duration']:.1f}秒)"
            if "data_processed" in performance_stats:
                data_size = performance_stats["data_processed"]
                completion_msg += f" | 处理数据: {data_size}"

        self.business_logger.info(completion_msg)

    def workflow_progress(
        self, completed_steps: int, total_steps: int, current_step_name: Optional[str] = None
    ):
        """记录工作流进度"""
        progress = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        current_msg = f" | 当前: {current_step_name}" if current_step_name else ""

        self.business_logger.info(
            f"📊 执行进度: {progress:.0f}% ({completed_steps}/{total_steps}){current_msg}"
        )

    def log_separator(self, title: Optional[str] = None):
        """记录分隔符，用于区分不同的执行阶段"""
        if title:
            self.business_logger.info(f"{'='*20} {title} {'='*20}")
        else:
            self.business_logger.info("=" * 50)

    def _format_business_value(self, value: Any, max_length: int = 100) -> str:
        """格式化业务值，用于显示给用户"""
        if value is None:
            return "空"
        elif isinstance(value, bool):
            return "是" if value else "否"
        elif isinstance(value, str):
            if len(value) > max_length:
                return f'"{value[:max_length]}..." ({len(value)}字符)'
            return f'"{value}"'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, dict):
            if not value:
                return "{空对象}"
            # 显示字典的关键信息
            key_count = len(value)
            if key_count <= 3:
                items = [f"{k}: {self._format_business_value(v, 30)}" for k, v in value.items()]
                return "{" + ", ".join(items) + "}"
            else:
                first_keys = list(value.keys())[:2]
                items = [f"{k}: {self._format_business_value(value[k], 30)}" for k in first_keys]
                return "{" + ", ".join(items) + f", ...+{key_count-2}项" + "}"
        elif isinstance(value, list):
            if not value:
                return "[空列表]"
            count = len(value)
            if count <= 3:
                items = [self._format_business_value(item, 30) for item in value]
                return "[" + ", ".join(items) + "]"
            else:
                first_items = [self._format_business_value(value[i], 30) for i in range(2)]
                return "[" + ", ".join(first_items) + f", ...+{count-2}项" + "]"
        else:
            return f"<{type(value).__name__}: {str(value)[:50]}>"


class NodeExecutionBusinessLogger:
    """
    节点执行业务日志记录器
    为不同节点类型生成用户友好的描述信息
    """

    @staticmethod
    def generate_step_description(
        node_type: str, node_subtype: str, parameters: Dict[str, Any]
    ) -> str:
        """根据节点类型生成用户友好的步骤描述"""

        if node_type == "AI_AGENT":
            if node_subtype == "OPENAI_CHATGPT":
                return "使用ChatGPT处理文本"
            elif node_subtype == "ANTHROPIC_CLAUDE":
                return "使用Claude分析内容"
            else:
                return f"AI智能处理 ({node_subtype})"

        elif node_type == "EXTERNAL_ACTION":
            if node_subtype == "SLACK":
                action = parameters.get("action", "send_message")
                if action == "send_message":
                    return "发送Slack消息"
                elif action == "get_messages":
                    return "获取Slack消息"
                else:
                    return f"Slack操作: {action}"
            elif node_subtype == "EMAIL":
                return "发送邮件"
            elif node_subtype == "GITHUB":
                return "GitHub操作"
            else:
                return f"外部服务调用 ({node_subtype})"

        elif node_type == "ACTION":
            if node_subtype == "HTTP_REQUEST":
                method = parameters.get("method", "GET")
                return f"HTTP {method} 请求"
            elif node_subtype == "DATA_TRANSFORM":
                return "数据转换处理"
            else:
                return f"内部操作 ({node_subtype})"

        elif node_type == "FLOW":
            if node_subtype == "IF":
                return "条件判断"
            elif node_subtype == "SWITCH":
                return "多分支选择"
            elif node_subtype == "FILTER":
                return "数据筛选"
            else:
                return f"流程控制 ({node_subtype})"

        elif node_type == "TRIGGER":
            if node_subtype == "MANUAL":
                return "手动触发"
            elif node_subtype == "WEBHOOK":
                return "网络钩子触发"
            elif node_subtype == "SLACK":
                return "Slack消息触发"
            else:
                return f"触发器 ({node_subtype})"

        elif node_type == "HUMAN_IN_THE_LOOP":
            return "等待人工处理"

        elif node_type == "TOOL":
            return "工具调用"

        elif node_type == "MEMORY":
            return "记忆存储/检索"

        else:
            return f"{node_type} 节点"

    @staticmethod
    def extract_key_inputs(
        node_type: str, node_subtype: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取节点的关键输入信息"""
        key_inputs = {}

        if node_type == "AI_AGENT":
            if "content" in input_data:
                key_inputs["内容"] = input_data["content"]
            if "system_prompt" in input_data:
                key_inputs["系统提示"] = input_data["system_prompt"]

        elif node_type == "EXTERNAL_ACTION":
            if node_subtype == "SLACK":
                if "message" in input_data:
                    key_inputs["消息"] = input_data["message"]
                if "channel" in input_data:
                    key_inputs["频道"] = input_data["channel"]
            elif node_subtype == "EMAIL":
                if "recipient" in input_data:
                    key_inputs["收件人"] = input_data["recipient"]
                if "subject" in input_data:
                    key_inputs["主题"] = input_data["subject"]

        elif node_type == "ACTION":
            if node_subtype == "HTTP_REQUEST":
                if "url" in input_data:
                    key_inputs["URL"] = input_data["url"]
                if "method" in input_data:
                    key_inputs["方法"] = input_data["method"]

        elif node_type == "FLOW":
            if "condition" in input_data:
                key_inputs["条件"] = input_data["condition"]
            if "filter_condition" in input_data:
                key_inputs["筛选条件"] = input_data["filter_condition"]

        # 如果没有特定的关键字段，显示最重要的通用字段
        if not key_inputs:
            for key in ["content", "message", "data", "text", "value"]:
                if key in input_data:
                    key_inputs[key] = input_data[key]
                    break

        return key_inputs

    @staticmethod
    def extract_key_outputs(
        node_type: str, node_subtype: str, output_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取节点的关键输出信息"""
        key_outputs = {}

        if node_type == "AI_AGENT":
            if "content" in output_data:
                key_outputs["生成内容"] = output_data["content"]
            if "metadata" in output_data and isinstance(output_data["metadata"], dict):
                if "token_usage" in output_data["metadata"]:
                    key_outputs["Token使用量"] = output_data["metadata"]["token_usage"]

        elif node_type == "EXTERNAL_ACTION":
            if node_subtype == "SLACK":
                if "success" in output_data:
                    key_outputs["发送状态"] = "成功" if output_data["success"] else "失败"
                if "message_ts" in output_data:
                    key_outputs["消息时间戳"] = output_data["message_ts"]
            elif node_subtype == "EMAIL":
                if "success" in output_data:
                    key_outputs["发送状态"] = "成功" if output_data["success"] else "失败"
                if "message_id" in output_data:
                    key_outputs["消息ID"] = output_data["message_id"]

        elif node_type == "ACTION":
            if node_subtype == "HTTP_REQUEST":
                if "status_code" in output_data:
                    key_outputs["状态码"] = output_data["status_code"]
                if "response_time" in output_data:
                    key_outputs["响应时间"] = f"{output_data['response_time']}ms"

        elif node_type == "FLOW":
            if "filtered_count" in output_data:
                key_outputs["筛选结果"] = f"{output_data['filtered_count']}项"
            if "condition_result" in output_data:
                key_outputs["条件结果"] = "通过" if output_data["condition_result"] else "未通过"

        # 通用输出字段
        if not key_outputs:
            for key in ["result", "content", "success", "status", "count"]:
                if key in output_data:
                    key_outputs[key] = output_data[key]
                    break

        return key_outputs


def create_business_logger(
    execution_id: str, workflow_name: str = "Unnamed Workflow"
) -> WorkflowBusinessLogger:
    """
    创建业务日志记录器的工厂函数
    """
    return WorkflowBusinessLogger(execution_id, workflow_name)
