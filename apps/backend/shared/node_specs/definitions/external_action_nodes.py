"""
External Action Node Specifications.

Node specifications for EXTERNAL_ACTION_NODE type with all subtypes
that interact with external systems and platforms.
"""

from shared.node_specs.base import (
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)

# EXTERNAL_API_CALL Node Specification - Generic API Call
external_api_call_spec = NodeSpec(
    node_type="EXTERNAL_ACTION_NODE",
    subtype="EXTERNAL_API_CALL",
    description="Makes a generic HTTP API call",
    parameters=[
        ParameterDef(
            name="method",
            type=ParameterType.ENUM,
            description="HTTP request method",
            required=True,
            enum_values=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            default_value="GET",
        ),
        ParameterDef(
            name="url",
            type=ParameterType.URL,
            description="Target API endpoint URL",
            required=True,
        ),
        ParameterDef(
            name="headers",
            type=ParameterType.JSON,
            description="HTTP request headers",
            required=False,
            default_value="{}",
        ),
        ParameterDef(
            name="query_params",
            type=ParameterType.JSON,
            description="URL query parameters",
            required=False,
            default_value="{}",
        ),
        ParameterDef(
            name="body",
            type=ParameterType.JSON,
            description="HTTP request body data",
            required=False,
        ),
        ParameterDef(
            name="timeout",
            type=ParameterType.INTEGER,
            description="Request timeout in seconds",
            required=False,
            default_value="30",
        ),
        ParameterDef(
            name="authentication",
            type=ParameterType.ENUM,
            description="API authentication method",
            required=False,
            enum_values=["none", "bearer", "basic", "api_key"],
            default_value="none",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="trigger",
            type="execution",
            description="Trigger the API call",
            required=True,
        ),
        InputPortSpec(
            name="request_data",
            type="data",
            description="Dynamic request parameters",
            required=False,
        ),
    ],
    output_ports=[
        OutputPortSpec(
            name="success",
            type="execution",
            description="API call completed successfully",
        ),
        OutputPortSpec(
            name="error",
            type="execution",
            description="API call failed",
        ),
        OutputPortSpec(
            name="response",
            type="data",
            description="HTTP response data and metadata",
        ),
    ],
)

# EXTERNAL_WEBHOOK Node Specification - Webhook Calls
external_webhook_spec = NodeSpec(
    node_type="EXTERNAL_ACTION_NODE",
    subtype="EXTERNAL_WEBHOOK",
    description="Sends a webhook to an external service",
    parameters=[
        ParameterDef(
            name="url",
            type=ParameterType.URL,
            description="Target webhook endpoint URL",
            required=True,
        ),
        ParameterDef(
            name="payload",
            type=ParameterType.JSON,
            description="Webhook payload data",
            required=True,
        ),
        ParameterDef(
            name="method",
            type=ParameterType.ENUM,
            description="HTTP method for webhook",
            required=False,
            enum_values=["POST", "PUT", "PATCH"],
            default_value="POST",
        ),
        ParameterDef(
            name="headers",
            type=ParameterType.JSON,
            description="HTTP headers for webhook",
            required=False,
            default_value='{"Content-Type": "application/json"}',
        ),
        ParameterDef(
            name="retry_attempts",
            type=ParameterType.INTEGER,
            description="Number of retry attempts on failure",
            required=False,
            default_value="3",
        ),
        ParameterDef(
            name="retry_delay",
            type=ParameterType.INTEGER,
            description="Delay between retries in seconds",
            required=False,
            default_value="5",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="trigger",
            type="execution",
            description="Trigger the webhook",
            required=True,
        ),
        InputPortSpec(
            name="webhook_data",
            type="data",
            description="Dynamic webhook payload data",
            required=False,
        ),
    ],
    output_ports=[
        OutputPortSpec(
            name="success",
            type="execution",
            description="Webhook sent successfully",
        ),
        OutputPortSpec(
            name="error",
            type="execution",
            description="Webhook failed",
        ),
        OutputPortSpec(
            name="webhook_result",
            type="data",
            description="Webhook response and status",
        ),
    ],
)

# Export all external action node specifications
EXTERNAL_ACTION_NODE_SPECS = {
    "EXTERNAL_API_CALL": external_api_call_spec,
    "EXTERNAL_WEBHOOK": external_webhook_spec,
}
