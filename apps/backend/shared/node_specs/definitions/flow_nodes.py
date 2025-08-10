"""
Flow control node specifications.

This module defines specifications for all FLOW_NODE subtypes including
conditional logic, loops, filtering, merging, and other flow control operations.
"""

from ..base import (
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)

# IF node - conditional branching
IF_NODE_SPEC = NodeSpec(
    node_type="FLOW_NODE",
    subtype="IF",
    description="Conditional branching node that routes data based on conditions",
    parameters=[
        ParameterDef(
            name="condition",
            type=ParameterType.STRING,
            required=True,
            description="Condition expression to evaluate",
        ),
        ParameterDef(
            name="condition_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="javascript",
            enum_values=["javascript", "python", "jsonpath", "simple"],
            description="Type of condition expression",
        ),
        ParameterDef(
            name="strict_mode",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Use strict evaluation (fail on errors vs. return false)",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Input data for condition evaluation",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "context": "object"}',
                examples=[
                    '{"data": {"score": 85, "status": "active"}, "context": {"user_id": "123"}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"data": {"type": "object"}, "context": {"type": "object"}}}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="true",
            type=ConnectionType.MAIN,
            description="Output when condition is true",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "condition_result": "boolean", "evaluation_time": "number"}',
                examples=[
                    '{"data": {"score": 85}, "condition_result": true, "evaluation_time": 0.01}'
                ],
            ),
        ),
        OutputPortSpec(
            name="false",
            type=ConnectionType.MAIN,
            description="Output when condition is false",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "condition_result": "boolean", "evaluation_time": "number"}',
                examples=[
                    '{"data": {"score": 65}, "condition_result": false, "evaluation_time": 0.01}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when condition evaluation fails",
        ),
    ],
)


# Filter node - filter data based on criteria
FILTER_NODE_SPEC = NodeSpec(
    node_type="FLOW_NODE",
    subtype="FILTER",
    description="Filter data based on specified criteria",
    parameters=[
        ParameterDef(
            name="filter_expression",
            type=ParameterType.STRING,
            required=True,
            description="Filter expression to apply",
        ),
        ParameterDef(
            name="filter_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="javascript",
            enum_values=["javascript", "jsonpath", "simple"],
            description="Filter type",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Data to filter",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"items": "array", "metadata": "object"}',
                examples=[
                    '{"items": [{"name": "John", "age": 25}, {"name": "Jane", "age": 35}], "metadata": {"source": "users"}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"items": {"type": "array"}, "metadata": {"type": "object"}}, "required": ["items"]}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Filtered data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"filtered_items": "array", "original_count": "number", "filtered_count": "number", "metadata": "object"}',
                examples=[
                    '{"filtered_items": [{"name": "John", "age": 25}], "original_count": 2, "filtered_count": 1, "metadata": {"source": "users"}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"filtered_items": {"type": "array"}, "original_count": {"type": "number"}, "filtered_count": {"type": "number"}, "metadata": {"type": "object"}}, "required": ["filtered_items"]}',
        ),
        OutputPortSpec(
            name="excluded",
            type=ConnectionType.MAIN,
            description="Items that were filtered out",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"excluded_items": "array", "count": "number"}',
                examples=['{"excluded_items": [{"name": "Jane", "age": 35}], "count": 1}'],
            ),
        ),
    ],
)


# Loop node - iterate over data
LOOP_NODE_SPEC = NodeSpec(
    node_type="FLOW_NODE",
    subtype="LOOP",
    description="Iterate over data items or repeat operations",
    parameters=[
        ParameterDef(
            name="loop_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="foreach",
            enum_values=["foreach", "while", "for", "until"],
            description="Type of loop iteration",
        ),
        ParameterDef(
            name="condition",
            type=ParameterType.STRING,
            required=False,
            description="Loop condition (for while/until loops)",
        ),
        ParameterDef(
            name="max_iterations",
            type=ParameterType.INTEGER,
            required=False,
            default_value=1000,
            description="Maximum number of iterations (safety limit)",
        ),
        ParameterDef(
            name="parallel_execution",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Execute iterations in parallel",
        ),
        ParameterDef(
            name="batch_size",
            type=ParameterType.INTEGER,
            required=False,
            default_value=1,
            description="Number of items to process per iteration",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Data to iterate over",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"items": "array", "context": "object"}',
                examples=['{"items": [1, 2, 3, 4, 5], "context": {"operation": "square"}}'],
            ),
            validation_schema='{"type": "object", "properties": {"items": {"type": "array"}, "context": {"type": "object"}}, "required": ["items"]}',
        ),
        InputPortSpec(
            name="loop_body",
            type=ConnectionType.MAIN,
            required=False,
            description="Result from loop body execution",
            max_connections=1,
        ),
    ],
    output_ports=[
        OutputPortSpec(
            name="iteration",
            type=ConnectionType.MAIN,
            description="Current iteration data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"item": "object", "index": "number", "is_last": "boolean", "context": "object"}',
                examples=[
                    '{"item": 3, "index": 2, "is_last": false, "context": {"operation": "square"}}'
                ],
            ),
        ),
        OutputPortSpec(
            name="complete",
            type=ConnectionType.MAIN,
            description="All iteration results",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"results": "array", "total_iterations": "number", "execution_time": "number"}',
                examples=[
                    '{"results": [1, 4, 9, 16, 25], "total_iterations": 5, "execution_time": 0.5}'
                ],
            ),
        ),
    ],
)


# Merge node - combine multiple data streams
MERGE_NODE_SPEC = NodeSpec(
    node_type="FLOW_NODE",
    subtype="MERGE",
    description="Merge multiple data streams into a single output",
    parameters=[
        ParameterDef(
            name="merge_strategy",
            type=ParameterType.ENUM,
            required=False,
            default_value="concatenate",
            enum_values=["concatenate", "merge_objects", "zip", "custom"],
            description="Merge strategy",
        ),
        ParameterDef(
            name="conflict_resolution",
            type=ParameterType.ENUM,
            required=False,
            default_value="last_wins",
            enum_values=["first_wins", "last_wins", "error"],
            description="Conflict resolution",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="input1",
            type=ConnectionType.MAIN,
            required=True,
            description="First data stream",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "array", "metadata": "object"}',
                examples=['{"data": [{"id": 1, "name": "John"}], "metadata": {"source": "db1"}}'],
            ),
        ),
        InputPortSpec(
            name="input2",
            type=ConnectionType.MAIN,
            required=False,
            description="Second data stream",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "array", "metadata": "object"}',
                examples=['{"data": [{"id": 2, "name": "Jane"}], "metadata": {"source": "db2"}}'],
            ),
        ),
        InputPortSpec(
            name="additional",
            type=ConnectionType.MAIN,
            required=False,
            description="Additional data streams",
            max_connections=-1,  # Unlimited additional inputs
        ),
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Merged data result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"merged_data": "array", "input_counts": "object", "merge_stats": "object"}',
                examples=[
                    '{"merged_data": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}], "input_counts": {"input1": 1, "input2": 1}, "merge_stats": {"total_items": 2}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"merged_data": {"type": "array"}, "input_counts": {"type": "object"}, "merge_stats": {"type": "object"}}, "required": ["merged_data"]}',
        )
    ],
)


# Switch node - route to different outputs based on values
SWITCH_NODE_SPEC = NodeSpec(
    node_type="FLOW_NODE",
    subtype="SWITCH",
    description="Route data to different outputs based on switch values",
    parameters=[
        ParameterDef(
            name="switch_expression",
            type=ParameterType.STRING,
            required=True,
            description="Expression to evaluate for switching",
        ),
        ParameterDef(
            name="cases",
            type=ParameterType.JSON,
            required=True,
            description="Switch cases as JSON object (case_value: output_port)",
        ),
        ParameterDef(
            name="default_case",
            type=ParameterType.STRING,
            required=False,
            default_value="default",
            description="Default output port when no cases match",
        ),
        ParameterDef(
            name="expression_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="javascript",
            enum_values=["javascript", "jsonpath", "simple"],
            description="Type of switch expression",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Input data for switching",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "switch_value": "string"}',
                examples=[
                    '{"data": {"user_type": "premium", "action": "login"}, "switch_value": "premium"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"data": {"type": "object"}, "switch_value": {"type": "string"}}}',
        )
    ],
    output_ports=[
        OutputPortSpec(name="case1", type=ConnectionType.MAIN, description="Output for case 1"),
        OutputPortSpec(name="case2", type=ConnectionType.MAIN, description="Output for case 2"),
        OutputPortSpec(name="case3", type=ConnectionType.MAIN, description="Output for case 3"),
        OutputPortSpec(
            name="default",
            type=ConnectionType.MAIN,
            description="Default output when no cases match",
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when switch evaluation fails",
        ),
    ],
)


# Wait node - introduce delays or wait for conditions
WAIT_NODE_SPEC = NodeSpec(
    node_type="FLOW_NODE",
    subtype="WAIT",
    description="Wait for a specified time or condition before continuing",
    parameters=[
        ParameterDef(
            name="wait_type",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["fixed_delay", "until_condition", "until_time", "for_signal"],
            description="Type of wait operation",
        ),
        ParameterDef(
            name="duration_seconds",
            type=ParameterType.INTEGER,
            required=False,
            description="Duration to wait in seconds (for fixed_delay)",
        ),
        ParameterDef(
            name="wait_until",
            type=ParameterType.STRING,
            required=False,
            description="Condition or time to wait until",
        ),
        ParameterDef(
            name="max_wait_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=3600,
            description="Maximum time to wait before timeout",
        ),
        ParameterDef(
            name="check_interval_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=10,
            description="Interval between condition checks",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Input data to pass through after wait",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "wait_context": "object"}',
                examples=[
                    '{"data": {"message": "Hello"}, "wait_context": {"reason": "rate_limit"}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"data": {"type": "object"}, "wait_context": {"type": "object"}}}',
        ),
        InputPortSpec(
            name="signal",
            type=ConnectionType.MAIN,
            required=False,
            description="Signal input to resume execution",
            max_connections=1,
        ),
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Output after wait completes",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "wait_completed_at": "string", "actual_wait_time": "number"}',
                examples=[
                    '{"data": {"message": "Hello"}, "wait_completed_at": "2025-01-28T11:00:00Z", "actual_wait_time": 300}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"data": {"type": "object"}, "wait_completed_at": {"type": "string"}, "actual_wait_time": {"type": "number"}}, "required": ["data"]}',
        ),
        OutputPortSpec(
            name="timeout",
            type=ConnectionType.MAIN,
            description="Output when wait times out",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "timeout_at": "string", "waited_time": "number"}',
                examples=[
                    '{"data": {"message": "Hello"}, "timeout_at": "2025-01-28T12:00:00Z", "waited_time": 3600}'
                ],
            ),
        ),
    ],
)
