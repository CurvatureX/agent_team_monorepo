"""
Log Formatters for Workflow Execution

This module provides various formatters to display workflow execution logs
in different formats suitable for different use cases:
- Console output for development/debugging
- Structured JSON for APIs
- HTML for web interfaces
- Markdown for documentation
- Detailed analysis reports
"""

from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .execution_logger import ExecutionLogEntry, ExecutionLogLevel, NodeExecutionPhase


class OutputFormat(str, Enum):
    """Available output formats"""

    CONSOLE = "console"
    CONSOLE_COMPACT = "console_compact"
    CONSOLE_DETAILED = "console_detailed"
    JSON = "json"
    JSON_PRETTY = "json_pretty"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"
    TABLE = "table"


class BaseLogFormatter(ABC):
    """Base class for log formatters"""

    @abstractmethod
    def format_entries(self, entries: List[ExecutionLogEntry], **kwargs) -> str:
        """Format a list of log entries"""
        pass

    @abstractmethod
    def format_summary(self, summary: Dict[str, Any], **kwargs) -> str:
        """Format an execution summary"""
        pass


class ConsoleFormatter(BaseLogFormatter):
    """Console-friendly formatter with colors and indentation"""

    # ANSI color codes
    COLORS = {
        ExecutionLogLevel.TRACE: "\033[90m",  # Gray
        ExecutionLogLevel.DEBUG: "\033[36m",  # Cyan
        ExecutionLogLevel.INFO: "\033[37m",  # White
        ExecutionLogLevel.PROGRESS: "\033[92m",  # Bright Green
        ExecutionLogLevel.WARNING: "\033[93m",  # Bright Yellow
        ExecutionLogLevel.ERROR: "\033[91m",  # Bright Red
        ExecutionLogLevel.CRITICAL: "\033[95m",  # Bright Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    def __init__(self, use_colors: bool = True, detailed: bool = False, compact: bool = False):
        self.use_colors = use_colors
        self.detailed = detailed
        self.compact = compact

    def format_entries(self, entries: List[ExecutionLogEntry], **kwargs) -> str:
        """Format log entries for console output"""
        if not entries:
            return "No log entries found."

        lines = []
        current_execution = None
        current_node = None

        for entry in entries:
            # Add execution separator
            if current_execution != entry.execution_id:
                if current_execution is not None:
                    lines.append("")
                lines.append(self._format_execution_header(entry.execution_id))
                current_execution = entry.execution_id
                current_node = None

            # Add node separator
            if entry.node_context and current_node != entry.node_context.node_id:
                lines.append(self._format_node_header(entry.node_context))
                current_node = entry.node_context.node_id

            # Format the actual log entry
            lines.append(self._format_entry(entry))

        return "\n".join(lines)

    def format_summary(self, summary: Dict[str, Any], **kwargs) -> str:
        """Format execution summary for console"""
        lines = [
            self._colorize("=== EXECUTION SUMMARY ===", self.BOLD),
            f"Execution ID: {summary['execution_id'][:8]}...",
            f"Total Logs: {summary['total_logs']:,}",
            "",
            self._colorize("Node Statistics:", self.BOLD),
        ]

        stats = summary["node_statistics"]
        lines.extend(
            [
                f"  Total Nodes: {stats['total_nodes']}",
                f"  {self._colorize('✓ Completed:', self.COLORS[ExecutionLogLevel.PROGRESS])} {stats['completed_nodes']}",
                f"  {self._colorize('✗ Failed:', self.COLORS[ExecutionLogLevel.ERROR])} {stats['failed_nodes']}",
                f"  {self._colorize('⏳ In Progress:', self.COLORS[ExecutionLogLevel.WARNING])} {stats['in_progress_nodes']}",
            ]
        )

        if summary.get("performance"):
            perf = summary["performance"]
            lines.extend(
                [
                    "",
                    self._colorize("Performance:", self.BOLD),
                    f"  Total Duration: {perf['total_duration_ms']:.1f}ms",
                    f"  Average Node: {perf['average_node_duration_ms']:.1f}ms",
                    f"  Fastest Node: {perf['fastest_node_ms']:.1f}ms",
                    f"  Slowest Node: {perf['slowest_node_ms']:.1f}ms",
                ]
            )

        return "\n".join(lines)

    def _format_execution_header(self, execution_id: str) -> str:
        """Format execution header"""
        short_id = execution_id[:8] + "..."
        header = f"WORKFLOW EXECUTION: {short_id}"
        if self.use_colors:
            return f"{self.BOLD}{self.COLORS[ExecutionLogLevel.PROGRESS]}{header}{self.RESET}"
        return header

    def _format_node_header(self, context) -> str:
        """Format node header"""
        header = f"  📦 NODE: {context.node_name} ({context.node_type}.{context.node_subtype})"
        if self.use_colors:
            return f"{self.DIM}{header}{self.RESET}"
        return header

    def _format_entry(self, entry: ExecutionLogEntry) -> str:
        """Format individual log entry"""
        timestamp = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S.%f")[:-3]

        if self.compact:
            return self._format_compact_entry(entry, timestamp)
        elif self.detailed:
            return self._format_detailed_entry(entry, timestamp)
        else:
            return self._format_standard_entry(entry, timestamp)

    def _format_compact_entry(self, entry: ExecutionLogEntry, timestamp: str) -> str:
        """Format compact log entry"""
        level_symbol = {
            ExecutionLogLevel.TRACE: "🔍",
            ExecutionLogLevel.DEBUG: "🐛",
            ExecutionLogLevel.INFO: "ℹ️",
            ExecutionLogLevel.PROGRESS: "⏳",
            ExecutionLogLevel.WARNING: "⚠️",
            ExecutionLogLevel.ERROR: "❌",
            ExecutionLogLevel.CRITICAL: "🚨",
        }.get(entry.level, "📝")

        line = f"    {level_symbol} {timestamp} {entry.message}"
        return self._colorize(line, self.COLORS[entry.level])

    def _format_standard_entry(self, entry: ExecutionLogEntry, timestamp: str) -> str:
        """Format standard log entry"""
        level_str = entry.level.value.ljust(8)
        indent = "      " if entry.node_context else "    "

        line = f"{indent}[{timestamp}] {level_str} {entry.message}"

        # Add context information
        if entry.node_context and entry.node_context.phase:
            phase_symbol = {
                NodeExecutionPhase.QUEUED: "⏸️",
                NodeExecutionPhase.STARTING: "🔄",
                NodeExecutionPhase.VALIDATING_INPUTS: "✅",
                NodeExecutionPhase.PROCESSING: "⚡",
                NodeExecutionPhase.WAITING_HUMAN: "👤",
                NodeExecutionPhase.COMPLETING: "🏁",
                NodeExecutionPhase.COMPLETED: "✅",
                NodeExecutionPhase.FAILED: "❌",
                NodeExecutionPhase.TIMEOUT: "⏰",
            }.get(entry.node_context.phase, "")

            if phase_symbol:
                line += f" {phase_symbol}"

        return self._colorize(line, self.COLORS[entry.level])

    def _format_detailed_entry(self, entry: ExecutionLogEntry, timestamp: str) -> str:
        """Format detailed log entry with full context"""
        lines = [self._format_standard_entry(entry, timestamp)]

        if entry.node_context:
            ctx = entry.node_context
            lines.append(f"        Phase: {ctx.phase.value}")

            if ctx.input_parameters:
                lines.append(f"        Inputs: {self._format_parameters(ctx.input_parameters)}")

            if ctx.output_parameters:
                lines.append(f"        Outputs: {self._format_parameters(ctx.output_parameters)}")

            if ctx.duration_ms:
                lines.append(f"        Duration: {ctx.duration_ms:.1f}ms")

        if entry.structured_data:
            lines.append(f"        Data: {json.dumps(entry.structured_data, indent=2)}")

        return "\n".join(lines)

    def _format_parameters(self, params: Dict[str, Any], max_length: int = 100) -> str:
        """Format parameters with truncation"""
        if not params:
            return "{}"

        formatted = json.dumps(params, ensure_ascii=False)
        if len(formatted) > max_length:
            return formatted[:max_length] + "..."
        return formatted

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if self.use_colors:
            return f"{color}{text}{self.RESET}"
        return text


class JsonFormatter(BaseLogFormatter):
    """JSON formatter for API responses and structured data"""

    def __init__(self, pretty: bool = False):
        self.pretty = pretty

    def format_entries(self, entries: List[ExecutionLogEntry], **kwargs) -> str:
        """Format entries as JSON"""
        data = [entry.to_dict() for entry in entries]

        if self.pretty:
            return json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return json.dumps(data, ensure_ascii=False, default=str)

    def format_summary(self, summary: Dict[str, Any], **kwargs) -> str:
        """Format summary as JSON"""
        if self.pretty:
            return json.dumps(summary, indent=2, ensure_ascii=False, default=str)
        return json.dumps(summary, ensure_ascii=False, default=str)


class HtmlFormatter(BaseLogFormatter):
    """HTML formatter for web interfaces"""

    def format_entries(self, entries: List[ExecutionLogEntry], **kwargs) -> str:
        """Format entries as HTML"""
        if not entries:
            return "<p>No log entries found.</p>"

        html_parts = [
            """<div class="workflow-logs">
            <style>
                .workflow-logs { font-family: 'Monaco', 'Consolas', monospace; font-size: 12px; }
                .log-entry { margin: 2px 0; padding: 4px 8px; border-left: 3px solid transparent; }
                .log-entry.TRACE { border-color: #666; color: #666; }
                .log-entry.DEBUG { border-color: #00CED1; color: #00CED1; }
                .log-entry.INFO { border-color: #FFF; color: #FFF; }
                .log-entry.PROGRESS { border-color: #32CD32; color: #32CD32; font-weight: bold; }
                .log-entry.WARNING { border-color: #FFD700; color: #FFD700; }
                .log-entry.ERROR { border-color: #FF6B6B; color: #FF6B6B; font-weight: bold; }
                .log-entry.CRITICAL { border-color: #FF1493; color: #FF1493; font-weight: bold; }
                .timestamp { color: #888; }
                .node-context { margin-left: 20px; font-size: 10px; color: #AAA; }
                .execution-header { font-weight: bold; color: #32CD32; margin: 10px 0 5px 0; }
                .node-header { color: #00CED1; margin: 5px 0 2px 10px; }
                .workflow-logs { background: #1e1e1e; padding: 15px; border-radius: 5px; }
            </style>"""
        ]

        current_execution = None
        current_node = None

        for entry in entries:
            # Add execution header
            if current_execution != entry.execution_id:
                if current_execution is not None:
                    html_parts.append("<br>")
                html_parts.append(
                    f'<div class="execution-header">🚀 EXECUTION: {entry.execution_id[:8]}...</div>'
                )
                current_execution = entry.execution_id
                current_node = None

            # Add node header
            if entry.node_context and current_node != entry.node_context.node_id:
                html_parts.append(
                    f'<div class="node-header">📦 {entry.node_context.node_name} '
                    f"({entry.node_context.node_type}.{entry.node_context.node_subtype})</div>"
                )
                current_node = entry.node_context.node_id

            # Format entry
            timestamp = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S.%f")[:-3]
            phase_info = ""
            if entry.node_context and entry.node_context.phase:
                phase_symbols = {
                    NodeExecutionPhase.QUEUED: "⏸️",
                    NodeExecutionPhase.STARTING: "🔄",
                    NodeExecutionPhase.VALIDATING_INPUTS: "✅",
                    NodeExecutionPhase.PROCESSING: "⚡",
                    NodeExecutionPhase.WAITING_HUMAN: "👤",
                    NodeExecutionPhase.COMPLETING: "🏁",
                    NodeExecutionPhase.COMPLETED: "✅",
                    NodeExecutionPhase.FAILED: "❌",
                    NodeExecutionPhase.TIMEOUT: "⏰",
                }
                symbol = phase_symbols.get(entry.node_context.phase, "")
                phase_info = f" {symbol}"

            html_parts.append(
                f'<div class="log-entry {entry.level.value}">'
                f'<span class="timestamp">[{timestamp}]</span> '
                f"{entry.level.value.ljust(8)} {entry.message}{phase_info}"
                f"</div>"
            )

            # Add context details
            if entry.node_context:
                ctx = entry.node_context
                if ctx.input_parameters or ctx.output_parameters:
                    html_parts.append('<div class="node-context">')
                    if ctx.input_parameters:
                        params_json = json.dumps(ctx.input_parameters, indent=2)
                        html_parts.append(
                            f'<div>📥 Inputs: <pre style="display:inline">{params_json}</pre></div>'
                        )
                    if ctx.output_parameters:
                        params_json = json.dumps(ctx.output_parameters, indent=2)
                        html_parts.append(
                            f'<div>📤 Outputs: <pre style="display:inline">{params_json}</pre></div>'
                        )
                    html_parts.append("</div>")

        html_parts.append("</div>")
        return "".join(html_parts)

    def format_summary(self, summary: Dict[str, Any], **kwargs) -> str:
        """Format summary as HTML"""
        stats = summary["node_statistics"]
        perf = summary.get("performance", {})

        html = f"""
        <div class="execution-summary" style="font-family: Arial, sans-serif; padding: 20px; background: #f8f9fa; border-radius: 8px;">
            <h3 style="color: #333; margin-top: 0;">📊 Execution Summary</h3>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div>
                    <h4 style="color: #555;">Basic Info</h4>
                    <p><strong>Execution ID:</strong> {summary['execution_id'][:8]}...</p>
                    <p><strong>Total Logs:</strong> {summary['total_logs']:,}</p>
                </div>

                <div>
                    <h4 style="color: #555;">Node Statistics</h4>
                    <p>📦 <strong>Total:</strong> {stats['total_nodes']}</p>
                    <p>✅ <strong>Completed:</strong> <span style="color: #28a745;">{stats['completed_nodes']}</span></p>
                    <p>❌ <strong>Failed:</strong> <span style="color: #dc3545;">{stats['failed_nodes']}</span></p>
                    <p>⏳ <strong>In Progress:</strong> <span style="color: #ffc107;">{stats['in_progress_nodes']}</span></p>
                </div>
            </div>
        """

        if perf:
            html += f"""
            <div>
                <h4 style="color: #555;">⚡ Performance</h4>
                <p><strong>Total Duration:</strong> {perf['total_duration_ms']:.1f}ms</p>
                <p><strong>Average Node:</strong> {perf['average_node_duration_ms']:.1f}ms</p>
                <p><strong>Fastest Node:</strong> {perf['fastest_node_ms']:.1f}ms</p>
                <p><strong>Slowest Node:</strong> {perf['slowest_node_ms']:.1f}ms</p>
            </div>
            """

        html += "</div>"
        return html


class MarkdownFormatter(BaseLogFormatter):
    """Markdown formatter for documentation"""

    def format_entries(self, entries: List[ExecutionLogEntry], **kwargs) -> str:
        """Format entries as Markdown"""
        if not entries:
            return "No log entries found."

        lines = ["# Workflow Execution Log\n"]
        current_execution = None
        current_node = None

        for entry in entries:
            # Add execution section
            if current_execution != entry.execution_id:
                if current_execution is not None:
                    lines.append("")
                lines.append(f"## 🚀 Execution: `{entry.execution_id[:8]}...`\n")
                current_execution = entry.execution_id
                current_node = None

            # Add node subsection
            if entry.node_context and current_node != entry.node_context.node_id:
                lines.append(f"### 📦 Node: {entry.node_context.node_name}")
                lines.append(
                    f"**Type:** `{entry.node_context.node_type}.{entry.node_context.node_subtype}`\n"
                )
                current_node = entry.node_context.node_id

            # Format entry
            timestamp = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S.%f")[:-3]
            level_emoji = {
                ExecutionLogLevel.TRACE: "🔍",
                ExecutionLogLevel.DEBUG: "🐛",
                ExecutionLogLevel.INFO: "ℹ️",
                ExecutionLogLevel.PROGRESS: "⏳",
                ExecutionLogLevel.WARNING: "⚠️",
                ExecutionLogLevel.ERROR: "❌",
                ExecutionLogLevel.CRITICAL: "🚨",
            }.get(entry.level, "📝")

            lines.append(f"- {level_emoji} **[{timestamp}]** {entry.message}")

            # Add context
            if entry.node_context:
                ctx = entry.node_context
                if ctx.input_parameters:
                    lines.append(
                        f"  - 📥 **Inputs:** ```json\n{json.dumps(ctx.input_parameters, indent=2)}\n```"
                    )
                if ctx.output_parameters:
                    lines.append(
                        f"  - 📤 **Outputs:** ```json\n{json.dumps(ctx.output_parameters, indent=2)}\n```"
                    )
                if ctx.duration_ms:
                    lines.append(f"  - ⏱️ **Duration:** {ctx.duration_ms:.1f}ms")

            lines.append("")

        return "\n".join(lines)

    def format_summary(self, summary: Dict[str, Any], **kwargs) -> str:
        """Format summary as Markdown"""
        stats = summary["node_statistics"]
        perf = summary.get("performance", {})

        md = f"""# 📊 Execution Summary

## Basic Information
- **Execution ID:** `{summary['execution_id'][:8]}...`
- **Total Logs:** {summary['total_logs']:,}

## Node Statistics
- 📦 **Total Nodes:** {stats['total_nodes']}
- ✅ **Completed:** {stats['completed_nodes']}
- ❌ **Failed:** {stats['failed_nodes']}
- ⏳ **In Progress:** {stats['in_progress_nodes']}
"""

        if perf:
            md += f"""
## ⚡ Performance Metrics
- **Total Duration:** {perf['total_duration_ms']:.1f}ms
- **Average Node Duration:** {perf['average_node_duration_ms']:.1f}ms
- **Fastest Node:** {perf['fastest_node_ms']:.1f}ms
- **Slowest Node:** {perf['slowest_node_ms']:.1f}ms
"""

        return md


class LogFormatterFactory:
    """Factory for creating log formatters"""

    _formatters = {
        OutputFormat.CONSOLE: lambda: ConsoleFormatter(use_colors=True),
        OutputFormat.CONSOLE_COMPACT: lambda: ConsoleFormatter(use_colors=True, compact=True),
        OutputFormat.CONSOLE_DETAILED: lambda: ConsoleFormatter(use_colors=True, detailed=True),
        OutputFormat.JSON: lambda: JsonFormatter(pretty=False),
        OutputFormat.JSON_PRETTY: lambda: JsonFormatter(pretty=True),
        OutputFormat.HTML: lambda: HtmlFormatter(),
        OutputFormat.MARKDOWN: lambda: MarkdownFormatter(),
    }

    @classmethod
    def create(cls, format_type: OutputFormat, **kwargs) -> BaseLogFormatter:
        """Create a formatter of the specified type"""
        if format_type not in cls._formatters:
            raise ValueError(f"Unsupported format: {format_type}")

        formatter = cls._formatters[format_type]()
        return formatter

    @classmethod
    def get_available_formats(cls) -> List[OutputFormat]:
        """Get list of available formats"""
        return list(cls._formatters.keys())


__all__ = [
    "OutputFormat",
    "BaseLogFormatter",
    "ConsoleFormatter",
    "JsonFormatter",
    "HtmlFormatter",
    "MarkdownFormatter",
    "LogFormatterFactory",
]
