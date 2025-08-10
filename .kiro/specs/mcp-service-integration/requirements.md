# Requirements Document

## Introduction

This feature adds Model Context Protocol (MCP) service endpoints to the API Gateway, enabling external systems to discover and invoke available tools through standardized REST endpoints. The MCP service will expose tool discovery and invocation capabilities, starting with node knowledge retrieval and Elasticsearch search functionality.

## Requirements

### Requirement 1

**User Story:** As an external system or client, I want to discover available MCP tools, so that I can understand what capabilities are available for invocation.

#### Acceptance Criteria

1. WHEN a client sends a GET request to `/mcp/tools` THEN the system SHALL return a JSON response containing all available tools
2. WHEN the tools list is returned THEN each tool SHALL include name, description, and parameter schema
3. WHEN the tools list is returned THEN the response SHALL follow OpenAPI/JSON Schema standards for parameter definitions
4. WHEN the endpoint is called THEN the system SHALL return HTTP 200 status code for successful requests

### Requirement 2

**User Story:** As an external system or client, I want to invoke specific MCP tools with parameters, so that I can execute tool functionality remotely.

#### Acceptance Criteria

1. WHEN a client sends a POST request to `/mcp/invoke` with valid tool_name and params THEN the system SHALL execute the specified tool
2. WHEN the tool execution is successful THEN the system SHALL return the tool results in JSON format
3. WHEN an invalid tool_name is provided THEN the system SHALL return HTTP 400 with error message "unknown tool"
4. WHEN tool execution fails THEN the system SHALL return HTTP 500 with appropriate error details
5. WHEN required parameters are missing THEN the system SHALL return HTTP 400 with validation error details

### Requirement 3

**User Story:** As a system administrator, I want the node knowledge retriever tool to fetch knowledge for specified nodes, so that external systems can access node information.

#### Acceptance Criteria

1. WHEN the node_knowledge_retriever tool is invoked with node_names parameter THEN the system SHALL retrieve knowledge for each specified node
2. WHEN include_metadata parameter is true THEN the system SHALL include metadata information in the response
3. WHEN include_metadata parameter is false or omitted THEN the system SHALL exclude metadata from the response
4. WHEN node_names parameter is empty or missing THEN the system SHALL return HTTP 400 with error "node_names is required"
5. WHEN knowledge retrieval succeeds THEN the system SHALL return success status, results array, and total_nodes count

### Requirement 4

**User Story:** As a developer, I want proper error handling and logging for MCP endpoints, so that issues can be diagnosed and resolved quickly.

#### Acceptance Criteria

1. WHEN any MCP endpoint encounters an error THEN the system SHALL log the error with appropriate context
2. WHEN validation errors occur THEN the system SHALL return structured error responses with clear messages
3. WHEN internal errors occur THEN the system SHALL return generic error messages without exposing sensitive details
4. WHEN requests are processed THEN the system SHALL log request details for monitoring and debugging
