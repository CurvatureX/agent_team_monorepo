"""
Action node specifications.

This module defines specifications for all ACTION_NODE subtypes including
code execution, HTTP requests, data processing, and various action-based operations.
"""

from ...models.node_enums import ActionSubtype, NodeType
from ..base import (
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)

# Run Code - execute code in various languages
RUN_CODE_SPEC = NodeSpec(
    node_type=NodeType.ACTION,
    subtype=ActionSubtype.RUN_CODE,
    description="Execute code in various programming languages",
    display_name="Code Execution",
    category="actions",
    template_id="action_code_exec",
    parameters=[
        ParameterDef(
            name="code", type=ParameterType.STRING, required=True, description="Code to execute"
        ),
        ParameterDef(
            name="language",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["python", "javascript", "bash", "sql", "r", "julia"],
            description="Programming language",
        ),
        ParameterDef(
            name="timeout",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Execution timeout in seconds",
        ),
        ParameterDef(
            name="environment",
            type=ParameterType.ENUM,
            required=False,
            default_value="sandboxed",
            enum_values=["sandboxed", "container", "local"],
            description="Execution environment",
        ),
        ParameterDef(
            name="capture_output",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to capture stdout/stderr",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Input data for code execution",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"variables": "object", "stdin": "string", "files": "object"}',
                examples=[
                    '{"variables": {"x": 10, "y": 20}, "stdin": "input data", "files": {"data.csv": "content"}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"variables": {"type": "object"}, "stdin": {"type": "string"}, "files": {"type": "object"}}}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Code execution result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"stdout": "string", "stderr": "string", "return_code": "number", "result": "object", "execution_time": "number"}',
                examples=[
                    '{"stdout": "Hello World", "stderr": "", "return_code": 0, "result": {"output": 30}, "execution_time": 0.5}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"stdout": {"type": "string"}, "stderr": {"type": "string"}, "return_code": {"type": "number"}, "result": {"type": "object"}, "execution_time": {"type": "number"}}, "required": ["return_code"]}',
        ),
        OutputPortSpec(
            name="error", type=ConnectionType.ERROR, description="Error output when execution fails"
        ),
    ],
)


# HTTP Request - make HTTP API calls
HTTP_REQUEST_SPEC = NodeSpec(
    node_type=NodeType.ACTION,
    subtype=ActionSubtype.HTTP_REQUEST,
    description="Make HTTP requests to external APIs",
    display_name="HTTP Request",
    category="actions",
    template_id="action_http_request",
    parameters=[
        ParameterDef(
            name="url",
            type=ParameterType.URL,
            required=True,
            description="Target URL for the HTTP request",
        ),
        ParameterDef(
            name="method",
            type=ParameterType.ENUM,
            required=False,
            default_value="GET",
            enum_values=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
            description="HTTP method",
        ),
        ParameterDef(
            name="headers",
            type=ParameterType.JSON,
            required=False,
            description="HTTP headers as JSON object",
        ),
        ParameterDef(
            name="authentication",
            type=ParameterType.ENUM,
            required=False,
            default_value="none",
            enum_values=["none", "bearer", "basic", "api_key", "oauth2"],
            description="Authentication method",
        ),
        ParameterDef(
            name="timeout",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Request timeout in seconds",
        ),
        ParameterDef(
            name="retry_attempts",
            type=ParameterType.INTEGER,
            required=False,
            default_value=3,
            description="Number of retry attempts on failure",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Request body and dynamic parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"body": "object", "query_params": "object", "path_params": "object"}',
                examples=[
                    '{"body": {"name": "John", "email": "john@example.com"}, "query_params": {"limit": 10}, "path_params": {"id": "123"}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"body": {"type": "object"}, "query_params": {"type": "object"}, "path_params": {"type": "object"}}}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="HTTP response data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"status_code": "number", "headers": "object", "body": "object", "response_time": "number"}',
                examples=[
                    '{"status_code": 200, "headers": {"content-type": "application/json"}, "body": {"result": "success"}, "response_time": 0.25}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"status_code": {"type": "number"}, "headers": {"type": "object"}, "body": {"type": "object"}, "response_time": {"type": "number"}}, "required": ["status_code"]}',
        ),
        OutputPortSpec(
            name="error", type=ConnectionType.ERROR, description="Error output for failed requests"
        ),
    ],
)


# Parse Image - extract information from images
PARSE_IMAGE_SPEC = NodeSpec(
    node_type=NodeType.ACTION,
    subtype="PARSE_IMAGE",
    description="Extract text and information from images using OCR and AI",
    parameters=[
        ParameterDef(
            name="extraction_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="ocr",
            enum_values=["ocr", "description", "objects", "text_analysis", "table_extraction"],
            description="Type of information to extract",
        ),
        ParameterDef(
            name="language",
            type=ParameterType.STRING,
            required=False,
            default_value="auto",
            description="Language for OCR (auto-detect if not specified)",
        ),
        ParameterDef(
            name="confidence_threshold",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.5,
            description="Minimum confidence threshold for results",
        ),
        ParameterDef(
            name="output_format",
            type=ParameterType.ENUM,
            required=False,
            default_value="structured",
            enum_values=["raw", "structured", "markdown", "json"],
            description="Format of extracted information",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Image data or URL",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"image_url": "string", "image_data": "string", "image_format": "string"}',
                examples=[
                    '{"image_url": "https://example.com/image.jpg", "image_data": null, "image_format": "jpeg"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"image_url": {"type": "string"}, "image_data": {"type": "string"}, "image_format": {"type": "string"}}, "anyOf": [{"required": ["image_url"]}, {"required": ["image_data"]}]}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Extracted information from image",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"extracted_text": "string", "objects": "array", "confidence": "number", "processing_time": "number"}',
                examples=[
                    '{"extracted_text": "Invoice #12345\\nTotal: $100.00", "objects": [{"type": "text", "bbox": [10, 10, 100, 30]}], "confidence": 0.95, "processing_time": 2.3}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"extracted_text": {"type": "string"}, "objects": {"type": "array"}, "confidence": {"type": "number"}, "processing_time": {"type": "number"}}, "required": ["confidence"]}',
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when image processing fails",
        ),
    ],
)


# Web Search - search the web for information
WEB_SEARCH_SPEC = NodeSpec(
    node_type=NodeType.ACTION,
    subtype=ActionSubtype.WEB_SEARCH,
    description="Search the web for information using search engines",
    parameters=[
        ParameterDef(
            name="search_engine",
            type=ParameterType.ENUM,
            required=False,
            default_value="google",
            enum_values=["google", "bing", "duckduckgo", "custom"],
            description="Search engine to use",
        ),
        ParameterDef(
            name="max_results",
            type=ParameterType.INTEGER,
            required=False,
            default_value=10,
            description="Maximum number of search results",
        ),
        ParameterDef(
            name="result_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="web",
            enum_values=["web", "images", "news", "videos", "academic"],
            description="Type of search results",
        ),
        ParameterDef(
            name="safe_search",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Enable safe search filtering",
        ),
        ParameterDef(
            name="language",
            type=ParameterType.STRING,
            required=False,
            default_value="en",
            description="Language code for search results",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Search query and parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"query": "string", "filters": "object", "location": "string"}',
                examples=[
                    '{"query": "best restaurants in NYC", "filters": {"date": "recent"}, "location": "New York"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"query": {"type": "string"}, "filters": {"type": "object"}, "location": {"type": "string"}}, "required": ["query"]}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Search results",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"results": "array", "total_results": "number", "search_time": "number", "query_used": "string"}',
                examples=[
                    '{"results": [{"title": "Best NYC Restaurants", "url": "https://example.com", "snippet": "Top rated restaurants..."}], "total_results": 1000, "search_time": 0.5, "query_used": "best restaurants in NYC"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"results": {"type": "array"}, "total_results": {"type": "number"}, "search_time": {"type": "number"}, "query_used": {"type": "string"}}, "required": ["results"]}',
        ),
        OutputPortSpec(
            name="error", type=ConnectionType.ERROR, description="Error output when search fails"
        ),
    ],
)


# Database Operation - perform database operations
DATABASE_OPERATION_SPEC = NodeSpec(
    node_type=NodeType.ACTION,
    subtype=ActionSubtype.DATABASE_OPERATION,
    description="Perform database operations (SELECT, INSERT, UPDATE, DELETE)",
    parameters=[
        ParameterDef(
            name="operation_type",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["select", "insert", "update", "delete", "execute"],
            description="Type of database operation",
        ),
        ParameterDef(
            name="query",
            type=ParameterType.STRING,
            required=True,
            description="SQL query or operation to execute",
        ),
        ParameterDef(
            name="database_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="postgresql",
            enum_values=["postgresql", "mysql", "sqlite", "mongodb", "redis"],
            description="Type of database system",
        ),
        ParameterDef(
            name="connection_string",
            type=ParameterType.STRING,
            required=False,
            description="Database connection string (use credentials for sensitive data)",
        ),
        ParameterDef(
            name="transaction",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Execute within a transaction",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Query parameters and data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"parameters": "object", "data": "object", "batch_data": "array"}',
                examples=[
                    '{"parameters": {"user_id": 123, "status": "active"}, "data": {"name": "John"}, "batch_data": [{"id": 1}, {"id": 2}]}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"parameters": {"type": "object"}, "data": {"type": "object"}, "batch_data": {"type": "array"}}}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Database operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"rows": "array", "affected_rows": "number", "execution_time": "number", "columns": "array"}',
                examples=[
                    '{"rows": [{"id": 1, "name": "John"}], "affected_rows": 1, "execution_time": 0.05, "columns": ["id", "name"]}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"rows": {"type": "array"}, "affected_rows": {"type": "number"}, "execution_time": {"type": "number"}, "columns": {"type": "array"}}}',
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when database operation fails",
        ),
    ],
)


# File Operation - file system operations
FILE_OPERATION_SPEC = NodeSpec(
    node_type=NodeType.ACTION,
    subtype=ActionSubtype.FILE_OPERATION,
    description="Perform file system operations (read, write, copy, delete)",
    parameters=[
        ParameterDef(
            name="operation",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["read", "write", "delete", "copy", "move", "list"],
            description="Operation type",
        ),
        ParameterDef(
            name="file_path",
            type=ParameterType.STRING,
            required=True,
            description="Path to the file or directory",
        ),
        ParameterDef(
            name="encoding",
            type=ParameterType.STRING,
            required=False,
            default_value="utf-8",
            description="File encoding for text operations",
        ),
        ParameterDef(
            name="content",
            type=ParameterType.STRING,
            required=False,
            description="File content (for write operations)",
        ),
        ParameterDef(
            name="create_directories",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Create parent directories if they don't exist",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="File content and operation parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"content": "string", "binary_content": "string", "destination": "string", "permissions": "string"}',
                examples=[
                    '{"content": "Hello World", "binary_content": null, "destination": "/backup/file.txt", "permissions": "644"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"content": {"type": "string"}, "binary_content": {"type": "string"}, "destination": {"type": "string"}, "permissions": {"type": "string"}}}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="File operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"success": "boolean", "content": "string", "file_info": "object", "files": "array"}',
                examples=[
                    '{"success": true, "content": "file content", "file_info": {"size": 1024, "modified": "2025-01-28T10:30:00Z"}, "files": ["file1.txt", "file2.txt"]}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"success": {"type": "boolean"}, "content": {"type": "string"}, "file_info": {"type": "object"}, "files": {"type": "array"}}, "required": ["success"]}',
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when file operation fails",
        ),
    ],
)


# Data Transformation - transform and process data
DATA_TRANSFORMATION_SPEC = NodeSpec(
    node_type=NodeType.ACTION,
    subtype=ActionSubtype.DATA_TRANSFORMATION,
    description="Transform and process data using various operations",
    display_name="Data Transformation",
    category="actions",
    template_id="action_data_transform",
    parameters=[
        ParameterDef(
            name="transformation_type",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["filter", "map", "reduce", "sort", "group", "join", "aggregate", "custom"],
            description="Type of data transformation",
        ),
        ParameterDef(
            name="transformation_rule",
            type=ParameterType.STRING,
            required=True,
            description="Transformation rule or expression",
        ),
        ParameterDef(
            name="input_format",
            type=ParameterType.ENUM,
            required=False,
            default_value="json",
            enum_values=["json", "csv", "xml", "yaml", "text"],
            description="Input data format",
        ),
        ParameterDef(
            name="output_format",
            type=ParameterType.ENUM,
            required=False,
            default_value="json",
            enum_values=["json", "csv", "xml", "yaml", "text"],
            description="Output data format",
        ),
        ParameterDef(
            name="error_handling",
            type=ParameterType.ENUM,
            required=False,
            default_value="skip",
            enum_values=["skip", "fail", "default_value"],
            description="How to handle transformation errors",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Data to transform",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "metadata": "object", "options": "object"}',
                examples=[
                    '{"data": [{"name": "John", "age": 25}, {"name": "Jane", "age": 30}], "metadata": {"source": "users"}, "options": {"preserve_order": true}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"data": {"type": "object"}, "metadata": {"type": "object"}, "options": {"type": "object"}}, "required": ["data"]}',
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Transformed data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"transformed_data": "object", "metadata": "object", "transformation_stats": "object"}',
                examples=[
                    '{"transformed_data": [{"name": "John", "category": "young"}], "metadata": {"source": "users"}, "transformation_stats": {"processed": 2, "filtered": 1}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"transformed_data": {"type": "object"}, "metadata": {"type": "object"}, "transformation_stats": {"type": "object"}}, "required": ["transformed_data"]}',
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when transformation fails",
        ),
    ],
)


# Send Email - Simple email sending action
SEND_EMAIL_SPEC = NodeSpec(
    node_type=NodeType.ACTION,
    subtype="SEND_EMAIL",  # Might not be in enum yet
    description="Send email notifications",
    display_name="Send Email",
    category="actions",
    template_id="action_send_email",
    parameters=[
        ParameterDef(
            name="to",
            type=ParameterType.STRING,
            required=True,
            description="Recipient email address",
        ),
        ParameterDef(
            name="subject",
            type=ParameterType.STRING,
            required=True,
            description="Email subject",
        ),
        ParameterDef(
            name="body",
            type=ParameterType.STRING,
            required=True,
            description="Email body content",
        ),
        ParameterDef(
            name="from_address",
            type=ParameterType.STRING,
            required=False,
            description="Sender email address",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Email content and recipients",
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Email send result",
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Email send error",
        ),
    ],
)
