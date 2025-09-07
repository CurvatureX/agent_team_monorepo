"""
Enhanced logging formatter for workflow engine with clean, hierarchical output.
Focuses on highlighting node inputs/outputs while reducing verbose technical details.
"""

import json
import logging
from typing import Any, Dict, List, Optional


class WorkflowLogFormatter:
    """Utility class for consistent workflow logging with emphasis on node I/O."""

    # Log levels for different types of information
    CRITICAL = "🚨"  # Errors and failures
    SUCCESS = "✅"  # Successful operations
    PROCESS = "⚙️"  # Processing steps
    INPUT = "📥"  # Node inputs
    OUTPUT = "📤"  # Node outputs
    WORKFLOW = "🔄"  # Workflow-level events
    NODE = "🟦"  # Node-level events
    DEBUG = "🔍"  # Debug information (reduced)

    @staticmethod
    def format_workflow_start(workflow_id: str, execution_id: str, node_count: int) -> str:
        """Format workflow execution start message."""
        return f"{WorkflowLogFormatter.WORKFLOW} Starting workflow execution: {execution_id[:8]}... ({node_count} nodes)"

    @staticmethod
    def format_workflow_complete(
        execution_id: str, status: str, total_nodes: int, successful_nodes: int, errors: int
    ) -> str:
        """Format workflow completion summary."""
        icon = (
            WorkflowLogFormatter.SUCCESS if status == "completed" else WorkflowLogFormatter.CRITICAL
        )
        return f"{icon} Workflow {execution_id[:8]}... {status.upper()} | Nodes: {successful_nodes}/{total_nodes} | Errors: {errors}"

    @staticmethod
    def format_node_start(
        node_id: str, node_name: str, node_type: str, node_subtype: str, step: int, total: int
    ) -> str:
        """Format node execution start."""
        return (
            f"{WorkflowLogFormatter.NODE} [{step}/{total}] {node_name} ({node_type}.{node_subtype})"
        )

    @staticmethod
    def format_node_complete(
        node_id: str, status: str, execution_time_ms: Optional[int] = None
    ) -> str:
        """Format node execution completion."""
        icon = (
            WorkflowLogFormatter.SUCCESS if status == "SUCCESS" else WorkflowLogFormatter.CRITICAL
        )
        time_str = f" ({execution_time_ms}ms)" if execution_time_ms else ""
        return f"{icon} Node '{node_id}' {status}{time_str}"

    @staticmethod
    def format_node_input(
        node_id: str, input_data: Dict[str, Any], important_keys: Optional[List[str]] = None
    ) -> List[str]:
        """Format node input data with emphasis on important keys."""
        if not input_data:
            return [f"{WorkflowLogFormatter.INPUT} {node_id} input: (empty)"]

        lines = [f"{WorkflowLogFormatter.INPUT} {node_id} input:"]

        # Show important keys first
        if important_keys:
            for key in important_keys:
                if key in input_data:
                    value = WorkflowLogFormatter._format_value(input_data[key])
                    lines.append(f"  • {key}: {value}")

        # Show other keys (non-important)
        other_keys = [k for k in input_data.keys() if not important_keys or k not in important_keys]
        if other_keys and len(other_keys) <= 3:
            for key in other_keys:
                value = WorkflowLogFormatter._format_value(input_data[key])
                lines.append(f"  • {key}: {value}")
        elif other_keys:
            lines.append(f"  • (+{len(other_keys)} additional keys)")

        return lines

    @staticmethod
    def format_node_output(
        node_id: str, output_data: Dict[str, Any], important_keys: Optional[List[str]] = None
    ) -> List[str]:
        """Format node output data with emphasis on important keys."""
        if not output_data:
            return [f"{WorkflowLogFormatter.OUTPUT} {node_id} output: (empty)"]

        lines = [f"{WorkflowLogFormatter.OUTPUT} {node_id} output:"]

        # Show important keys first with emphasis
        if important_keys:
            for key in important_keys:
                if key in output_data:
                    value = WorkflowLogFormatter._format_value(output_data[key])
                    lines.append(f"  ► {key}: {value}")

        # Show other keys
        other_keys = [
            k for k in output_data.keys() if not important_keys or k not in important_keys
        ]
        if other_keys and len(other_keys) <= 3:
            for key in other_keys:
                value = WorkflowLogFormatter._format_value(output_data[key])
                lines.append(f"  • {key}: {value}")
        elif other_keys:
            lines.append(f"  • (+{len(other_keys)} additional keys)")

        return lines

    @staticmethod
    def format_error(context: str, error: str) -> str:
        """Format error message."""
        return f"{WorkflowLogFormatter.CRITICAL} {context}: {error}"

    @staticmethod
    def format_process_step(step: str, details: str = "") -> str:
        """Format processing step."""
        return f"{WorkflowLogFormatter.PROCESS} {step}" + (f": {details}" if details else "")

    @staticmethod
    def _format_value(value: Any, max_length: int = 150) -> str:
        """Format a value for logging with appropriate truncation."""
        if value is None:
            return "null"
        elif isinstance(value, str):
            if len(value) > max_length:
                return f'"{value[:max_length]}..." ({len(value)} chars)'
            return f'"{value}"'
        elif isinstance(value, (dict, list)):
            try:
                json_str = json.dumps(value, ensure_ascii=False)
                if len(json_str) > max_length:
                    return f"{json_str[:max_length]}... ({len(json_str)} chars)"
                return json_str
            except:
                return f"{type(value).__name__}(...)"
        else:
            return str(value)

    @staticmethod
    def get_important_keys_for_node_type(node_type: str, node_subtype: str) -> Dict[str, List[str]]:
        """Get important input/output keys for different node types."""
        key_map = {
            ("AI_AGENT", "OPENAI_CHATGPT"): {
                "input": ["system_prompt", "content", "model_version", "temperature"],
                "output": ["content", "metadata"],
            },
            ("AI_AGENT", "ANTHROPIC_CLAUDE"): {
                "input": ["system_prompt", "content", "model_version", "temperature"],
                "output": ["content", "metadata"],
            },
            ("EXTERNAL_ACTION", "SLACK"): {
                "input": ["channel", "message", "action"],
                "output": ["success", "message_ts", "text", "channel"],
            },
            ("TRIGGER", "SLACK"): {
                "input": ["message", "channel", "user_id"],
                "output": ["content", "metadata"],
            },
            ("FLOW", "FILTER"): {
                "input": ["filter_condition"],
                "output": ["filtered_count", "original_count"],
            },
        }

        return key_map.get(
            (node_type, node_subtype),
            {"input": ["content", "message", "data"], "output": ["content", "result", "success"]},
        )


class CleanWorkflowLogger:
    """Logger wrapper that uses WorkflowLogFormatter for consistent output."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.formatter = WorkflowLogFormatter()

    def workflow_start(self, workflow_id: str, execution_id: str, node_count: int):
        """Log workflow start."""
        msg = self.formatter.format_workflow_start(workflow_id, execution_id, node_count)
        self.logger.info(msg)

    def workflow_complete(
        self, execution_id: str, status: str, total_nodes: int, successful_nodes: int, errors: int
    ):
        """Log workflow completion."""
        msg = self.formatter.format_workflow_complete(
            execution_id, status, total_nodes, successful_nodes, errors
        )
        self.logger.info(msg)

    def node_start(
        self, node_id: str, node_name: str, node_type: str, node_subtype: str, step: int, total: int
    ):
        """Log node execution start."""
        msg = self.formatter.format_node_start(
            node_id, node_name, node_type, node_subtype, step, total
        )
        self.logger.info(msg)

    def node_complete(self, node_id: str, status: str, execution_time_ms: Optional[int] = None):
        """Log node execution completion."""
        msg = self.formatter.format_node_complete(node_id, status, execution_time_ms)
        self.logger.info(msg)

    def node_input(
        self, node_id: str, node_type: str, node_subtype: str, input_data: Dict[str, Any]
    ):
        """Log node input data."""
        important_keys = self.formatter.get_important_keys_for_node_type(
            node_type, node_subtype
        ).get("input", [])
        lines = self.formatter.format_node_input(node_id, input_data, important_keys)
        for line in lines:
            self.logger.info(line)

    def node_output(
        self, node_id: str, node_type: str, node_subtype: str, output_data: Dict[str, Any]
    ):
        """Log node output data."""
        important_keys = self.formatter.get_important_keys_for_node_type(
            node_type, node_subtype
        ).get("output", [])
        lines = self.formatter.format_node_output(node_id, output_data, important_keys)
        for line in lines:
            self.logger.info(line)

    def process_step(self, step: str, details: str = ""):
        """Log processing step."""
        msg = self.formatter.format_process_step(step, details)
        self.logger.info(msg)

    def error(self, context: str, error: str):
        """Log error."""
        msg = self.formatter.format_error(context, error)
        self.logger.error(msg)

    def debug(self, message: str):
        """Log debug information (only when debug level is enabled)."""
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"{WorkflowLogFormatter.DEBUG} {message}")
