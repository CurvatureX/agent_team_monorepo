# Workflow API Documentation

This document provides detailed information about the Workflow API endpoints, which are used for managing and executing workflows.

**Base URL**: `/api/v1/workflow`

**Authentication**:
*Currently, there is no authentication layer implemented for these endpoints. This is a planned future enhancement.*

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
*A detailed list of all subtypes can be found in the `workflow.proto` file.*

### ConnectionType Enum
*A detailed list of all connection types can be found in the `workflow.proto` file.*

---

## Workflow Execution

### 1. Execute a workflow

-   **Endpoint**: `POST /{workflow_id}/execute`
-   **Description**: Triggers an execution of a specific workflow.
-   **Path Parameters**:
    -   `workflow_id` (string, required): The ID of the workflow to execute.
-   **Request Body**: `application/json`

| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `inputs` | object | Key-value pairs representing the initial inputs for the workflow. | Yes |

-   **Example Request**:
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