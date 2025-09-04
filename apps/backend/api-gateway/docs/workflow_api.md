# Workflow API Documentation

This document provides detailed information about the Workflow API endpoints, which are used for managing and executing workflows.

**Base URL**: `/api/v1/workflow`

**Authentication**:
*Currently, there is no authentication layer implemented for these endpoints. This is a planned future enhancement.*

---

## Node Templates

### 1. List all available node templates

-   **Endpoint**: `GET /node-templates/`
-   **Description**: Retrieves a list of all available node templates that can be used to build a workflow.
-   **Example Request**:
    ```bash
    curl "http://localhost:8000/api/v1/workflow/node-templates/"
    ```
-   **Success Response**: `200 OK`
    -   Returns a list of `NodeTemplateResponse` objects.
-   **Error Response**:
    -   `500 Internal Server Error`: If an unexpected error occurs.
-   **`NodeTemplateResponse` Structure**:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | string | Unique identifier for the template. |
| `name` | string | Display name of the template. |
| `description`| string | Optional description of what the node does. |
| `category` | string | Category for grouping templates (e.g., "AI", "Action"). |
| `node_type` | string | The main type of the node (e.g., `ACTION_NODE`). |
| `node_subtype`| string | The specific subtype of the node (e.g., `ACTION_SEND_HTTP_REQUEST`). |
| `version` | string | Optional version of the template. |
| `is_system_template`| boolean | Whether this is a system-provided template. |
| `default_parameters`| object | A key-value map of default parameters for the node. |
| `required_parameters`| array of strings | A list of parameter keys that are required for the node. |
| `parameter_schema`| object | A JSON schema defining the structure and validation rules for the node's parameters. |

---

## Workflow Management

### 1. Create a new workflow

-   **Endpoint**: `POST /`
-   **Description**: Creates a new workflow definition.
-   **Request Body**: `application/json`

| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `name` | string | Name of the workflow. | Yes |
| `description`| string | Optional description for the workflow. | No |
| `nodes` | array of Node objects | A list of nodes that define the workflow's structure. See [Node Structure](#node-structure) below. | Yes |
| `connections`| ConnectionsMap object | An object defining the connections between nodes. See [ConnectionsMap Structure](#connectionsmap-structure) below. | Yes |

-   **Example Request**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/workflow/" \
         -H "Content-Type: application/json" \
         -d '{
              "name": "My First Workflow",
              "description": "A simple workflow to process data.",
              "nodes": [
                {
                  "id": "start-node",
                  "name": "Start",
                  "type": "TRIGGER_NODE",
                  "subtype": "TRIGGER_MANUAL",
                  "position": {"x": 100, "y": 100}
                },
                {
                  "id": "action-node-1",
                  "name": "HTTP Request",
                  "type": "ACTION_NODE",
                  "subtype": "ACTION_SEND_HTTP_REQUEST",
                  "parameters": {
                    "url": "https://api.example.com/data"
                  },
                  "position": {"x": 300, "y": 100}
                }
              ],
              "connections": {
                "connections": {
                  "start-node": {
                    "connection_types": {
                      "MAIN": {
                        "connections": [
                          {
                            "node": "action-node-1",
                            "type": "MAIN",
                            "index": 0
                          }
                        ]
                      }
                    }
                  }
                }
              }
            }'
    ```
-   **Success Response**: `201 Created`
    -   Returns a `WorkflowResponse` object containing the details of the newly created workflow, including its `workflow_id`.
-   **Error Response**:
    -   `500 Internal Server Error`: If an unexpected error occurs during creation.

### 2. Get a workflow by ID

-   **Endpoint**: `GET /{workflow_id}`
-   **Description**: Retrieves a specific workflow by its unique ID.
-   **Path Parameters**:
    -   `workflow_id` (string, required): The unique identifier of the workflow to retrieve.
-   **Example Request**:
    ```bash
    curl "http://localhost:8000/api/v1/workflow/123e4567-e89b-12d3-a456-426614174000"
    ```
-   **Success Response**: `200 OK`
    -   Returns a `WorkflowResponse` object.
-   **Error Responses**:
    -   `404 Not Found`: If no workflow with the specified ID exists.
    -   `500 Internal Server Error`: If an unexpected error occurs.

### 3. Update a workflow

-   **Endpoint**: `PUT /{workflow_id}`
-   **Description**: Updates an existing workflow. You can provide one or more fields to update.
-   **Path Parameters**:
    -   `workflow_id` (string, required): The ID of the workflow to update.
-   **Request Body**: `application/json` (At least one field is required)

| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `name` | string | The new name for the workflow. | No |
| `description`| string | The new description for the workflow. | No |
| `nodes` | array of Node objects | The new list of nodes. See [Node Structure](#node-structure). | No |
| `connections`| ConnectionsMap object | The new connections map. See [ConnectionsMap Structure](#connectionsmap-structure). | No |

-   **Example Request**:
    ```bash
    curl -X PUT "http://localhost:8000/api/v1/workflow/123e4567-e89b-12d3-a456-426614174000" \
         -H "Content-Type: application/json" \
         -d '{
              "description": "An updated description for my workflow."
            }'
    ```
-   **Success Response**: `200 OK`
    -   Returns the updated `WorkflowResponse` object.
-   **Error Responses**:
    -   `400 Bad Request`: If the request body is empty.
    -   `500 Internal Server Error`: If an unexpected error occurs.

### 4. Delete a workflow

-   **Endpoint**: `DELETE /{workflow_id}`
-   **Description**: Deletes a workflow by its ID.
-   **Path Parameters**:
    -   `workflow_id` (string, required): The ID of the workflow to delete.
-   **Example Request**:
    ```bash
    curl -X DELETE "http://localhost:8000/api/v1/workflow/123e4567-e89b-12d3-a456-426614174000"
    ```
-   **Success Response**: `204 No Content`
-   **Error Response**:
    -   `500 Internal Server Error`: If an unexpected error occurs.

### 5. List workflows

-   **Endpoint**: `GET /`
-   **Description**: Retrieves a list of all workflows for a specific user.
-   **Query Parameters**:
    -   `user_id` (string, required): The ID of the user whose workflows to list.
-   **Example Request**:
    ```bash
    curl "http://localhost:8000/api/v1/workflow/?user_id=user-123"
    ```
-   **Success Response**: `200 OK`
    -   Returns a list of `WorkflowResponse` objects.
-   **Error Response**:
    -   `500 Internal Server Error`: If an unexpected error occurs.

---

## Data Structures

### Node Structure

A `Node` object defines a single step in the workflow.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | string | A unique identifier for the node. |
| `name` | string | The display name of the node. |
| `type` | string (enum) | The main type of the node. See [NodeType Enum](#nodetype-enum). |
| `subtype` | string (enum) | The specific subtype of the node. See [NodeSubtype Enum](#nodesubtype-enum). |
| `position` | Position object | The x and y coordinates of the node on the canvas. |
| `parameters` | object | A key-value map of parameters specific to the node's subtype. |
| `disabled` | boolean | Whether the node is disabled. |
| `credentials` | object | A key-value map of credentials required by the node. |

### ConnectionsMap Structure

A `ConnectionsMap` object defines how nodes are connected to each other. It's a nested map structure:
`{ "connections": { "source_node_id": { "connection_types": { "MAIN": { "connections": [...] } } } } }`

-   **`connections`**: The root object.
-   **`source_node_id`**: The ID of the node where the connection originates.
-   **`connection_types`**: A map where keys are connection types (e.g., `MAIN`, `AI_TOOL`).
-   **`connections` (array)**: An array of `Connection` objects.

A `Connection` object has the following structure:

| Field | Type | Description |
| :--- | :--- | :--- |
| `node` | string | The ID of the target node. |
| `type` | string (enum) | The type of the connection. See [ConnectionType Enum](#connectiontype-enum). |
| `index` | integer | The input port index on the target node. |

---

## Enums

### NodeType Enum
- `TRIGGER_NODE`
- `AI_AGENT_NODE`
- `EXTERNAL_ACTION_NODE`
- `ACTION_NODE`
- `FLOW_NODE`
- `HUMAN_IN_THE_LOOP_NODE`
- `TOOL_NODE`
- `MEMORY_NODE`

### NodeSubtype Enum
<details>
<summary>Click to expand</summary>

- **Trigger Subtypes**
  - `TRIGGER_CHAT`
  - `TRIGGER_WEBHOOK`
  - `TRIGGER_CRON`
  - `TRIGGER_MANUAL`
  - `TRIGGER_EMAIL`
  - `TRIGGER_FORM`
  - `TRIGGER_CALENDAR`
- **AI Agent Subtypes**
  - `AI_ROUTER_AGENT`
  - `AI_TASK_ANALYZER`
  - `AI_DATA_INTEGRATOR`
  - `AI_REPORT_GENERATOR`
  - `AI_REMINDER_DECISION`
  - `AI_WEEKLY_REPORT`
- **External Action Subtypes**
  - `EXTERNAL_GITHUB`
  - `EXTERNAL_GOOGLE_CALENDAR`
  - `EXTERNAL_TRELLO`
  - `EXTERNAL_EMAIL`
  - `EXTERNAL_SLACK`
  - `EXTERNAL_API_CALL`
  - `EXTERNAL_WEBHOOK`
  - `EXTERNAL_NOTIFICATION`
- **Action Subtypes**
  - `ACTION_RUN_CODE`
  - `ACTION_SEND_HTTP_REQUEST`
  - `ACTION_PARSE_IMAGE`
  - `ACTION_WEB_SEARCH`
  - `ACTION_DATABASE_OPERATION`
  - `ACTION_FILE_OPERATION`
  - `ACTION_DATA_TRANSFORMATION`
- **Flow Control Subtypes**
  - `FLOW_IF`
  - `FLOW_FILTER`
  - `FLOW_LOOP`
  - `FLOW_MERGE`
  - `FLOW_SWITCH`
  - `FLOW_WAIT`
- **Human in the Loop Subtypes**
  - `HUMAN_GMAIL`
  - `HUMAN_SLACK`
  - `HUMAN_DISCORD`
  - `HUMAN_TELEGRAM`
  - `HUMAN_APP`
- **Tool Subtypes**
  - `TOOL_GOOGLE_CALENDAR_MCP`
  - `TOOL_NOTION_MCP`
  - `TOOL_CALENDAR`
  - `TOOL_EMAIL`
  - `TOOL_HTTP`
  - `TOOL_CODE_EXECUTION`
- **Memory Subtypes**
  - `MEMORY_SIMPLE`
  - `MEMORY_BUFFER`
  - `MEMORY_KNOWLEDGE`
  - `MEMORY_VECTOR_STORE`
  - `MEMORY_DOCUMENT`
  - `MEMORY_EMBEDDING`

</details>

### ConnectionType Enum
<details>
<summary>Click to expand</summary>

- `MAIN`
- `AI_AGENT`
- `AI_CHAIN`
- `AI_DOCUMENT`
- `AI_EMBEDDING`
- `AI_LANGUAGE_MODEL`
- `AI_MEMORY`
- `AI_OUTPUT_PARSER`
- `AI_RETRIEVER`
- `AI_RERANKER`
- `AI_TEXT_SPLITTER`
- `AI_TOOL`
- `AI_VECTOR_STORE`

</details>

---

## Workflow Execution

### 1. Execute a workflow

-   **Endpoint**: `POST /{workflow_id}/execute`
-   **Description**: Triggers an execution of a specific workflow. Supports executing from a specific node instead of starting from trigger nodes.
-   **Path Parameters**:
    -   `workflow_id` (string, required): The ID of the workflow to execute.
-   **Request Body**: `application/json`

| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `inputs` | object | Key-value pairs representing the initial inputs for the workflow. | Yes |
| `start_from_node` | string | **NEW**: Specify which node to start execution from. If omitted, execution starts from trigger nodes. | No |
| `skip_trigger_validation` | boolean | **NEW**: Whether to skip trigger validation when starting from a specific node. Default: false | No |
| `settings` | object | Optional execution settings for the workflow. | No |
| `metadata` | object | Optional metadata for the execution. | No |

-   **Example Request (Standard Execution)**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/workflow/123e4567-e89b-12d3-a456-426614174000/execute" \
         -H "Content-Type: application/json" \
         -d '{
              "inputs": {
                "initial_data": "some value",
                "user_parameter": 123
              }
            }'
    ```

-   **Example Request (Start from Specific Node)**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/workflow/123e4567-e89b-12d3-a456-426614174000/execute" \
         -H "Content-Type: application/json" \
         -d '{
              "inputs": {
                "message": "Test input for AI node",
                "priority": "high"
              },
              "start_from_node": "ai_message_classification",
              "skip_trigger_validation": true
            }'
    ```
-   **Success Response**: `200 OK`
    -   Returns a `WorkflowExecutionResponse` object containing the `execution_id`.
-   **Error Response**:
    -   `500 Internal Server Error`: If an unexpected error occurs.

### 2. Get execution status

-   **Endpoint**: `GET /executions/{execution_id}`
-   **Description**: Retrieves the current status and result of a workflow execution.
-   **Path Parameters**:
    -   `execution_id` (string, required): The ID of the execution to query.
-   **Example Request**:
    ```bash
    curl "http://localhost:8000/api/v1/workflow/executions/exec_abc123"
    ```
-   **Success Response**: `200 OK`
    -   Returns an `ExecutionStatusResponse` object with the current `status` and `result`.
-   **Error Response**:
    -   `500 Internal Server Error`: If an unexpected error occurs.

### 3. Cancel a running execution

-   **Endpoint**: `POST /executions/{execution_id}/cancel`
-   **Description**: Requests the cancellation of a running workflow execution.
-   **Path Parameters**:
    -   `execution_id` (string, required): The ID of the execution to cancel.
-   **Example Request**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/workflow/executions/exec_abc123/cancel"
    ```
-   **Success Response**: `200 OK`
    -   Returns a JSON object, e.g., `{"success": true, "message": "Cancellation request sent"}`.
-   **Error Responses**:
    -   `400 Bad Request`: If the cancellation fails (e.g., execution already completed).
    -   `500 Internal Server Error`: If an unexpected error occurs.

### 4. Get execution history

-   **Endpoint**: `GET /{workflow_id}/history`
-   **Description**: Retrieves the execution history for a specific workflow.
-   **Path Parameters**:
    -   `workflow_id` (string, required): The ID of the workflow.
-   **Example Request**:
    ```bash
    curl "http://localhost:8000/api/v1/workflow/123e4567-e89b-12d3-a456-426614174000/history"
    ```
-   **Success Response**: `200 OK`
    -   Returns an `ExecutionHistoryResponse` object containing a list of execution records.
-   **Error Response**:
    -   `500 Internal Server Error`: If an unexpected error occurs. 