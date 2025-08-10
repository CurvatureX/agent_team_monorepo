# 工作流 API 入参/出参与 URL 总结

## 1. 创建工作流（Create Workflow）

- **URL**  
  `POST /api/v1/app/workflows/`

- **请求体（Request Body）**
  ```json
  {
    "name": "string",
    "description": "string",
    "nodes": [
      {
        "id": "string",
        "name": "string",
        "type": "string",
        "subtype": "string",
        "type_version": 1,
        "position": { "x": 0, "y": 0 },
        "parameters": { "additionalProp1": "string" },
        "credentials": { "additionalProp1": "string" },
        "disabled": false,
        "on_error": "continue",
        "retry_policy": { "max_tries": 3, "wait_between_tries": 5 },
        "notes": { "additionalProp1": "string" },
        "webhooks": ["string"]
      }
    ],
    "connections": { "additionalProp1": {} },
    "settings": {
      "timezone": { "additionalProp1": "string" },
      "save_execution_progress": true,
      "save_manual_executions": true,
      "timeout": 3600,
      "error_policy": "continue",
      "caller_policy": "workflow"
    },
    "static_data": { "additionalProp1": "string" },
    "tags": ["string"],
    "user_id": "string",
    "session_id": "string"
  }

 • 返回体（Response Body）{
  "workflow": {
    "created_at": "2025-08-07T06:52:08.595Z",
    "updated_at": "2025-08-07T06:52:08.595Z",
    "id": "string",
    "user_id": "string",
    "name": "string",
    "description": "string",
    "type": "sequential",
    "status": "draft",
    "version": 1,
    "nodes": [ ... ],
    "edges": [ ... ],
    "variables": { "additionalProp1": {} },
    "settings": { "additionalProp1": {} },
    "tags": ["string"],
    "execution_count": 0,
    "last_execution": "string"
  },
  "message": "string"
}

2. 获取工作流（Get Workflow）
 • URL
‎⁠GET /api/v1/app/workflows/{workflow_id}⁠
 • 请求参数
 ▫ 路径参数：‎⁠workflow_id⁠（string）
 • 返回体（Response Body）{
  "workflow": {
    "created_at": "2025-08-07T06:52:08.582Z",
    "updated_at": "2025-08-07T06:52:08.582Z",
    "id": "string",
    "user_id": "string",
    "name": "string",
    "description": "string",
    "type": "sequential",
    "status": "draft",
    "version": 1,
    "nodes": [ ... ],
    "edges": [ ... ],
    "variables": { "additionalProp1": {} },
    "settings": { "additionalProp1": {} },
    "tags": ["string"],
    "execution_count": 0,
    "last_execution": "string"
  },
  "message": "string"
}

3. 更新工作流（Update Workflow）
 • URL
‎⁠PUT /api/v1/app/workflows/{workflow_id}⁠
 • 请求体（Request Body）{
  "workflow_id": "string",
  "name": "string",
  "description": "string",
  "nodes": [
    {
      "id": "string",
      "name": "string",
      "type": "string",
      "subtype": "string",
      "type_version": 1,
      "position": { "x": 0, "y": 0 },
      "parameters": { "additionalProp1": "string" },
      "credentials": { "additionalProp1": "string" },
      "disabled": false,
      "on_error": "continue",
      "retry_policy": { "max_tries": 3, "wait_between_tries": 5 },
      "notes": { "additionalProp1": "string" },
      "webhooks": ["string"]
    }
  ],
  "connections": { "additionalProp1": {} },
  "settings": {
    "timezone": { "additionalProp1": "string" },
    "save_execution_progress": true,
    "save_manual_executions": true,
    "timeout": 3600,
    "error_policy": "continue",
    "caller_policy": "workflow"
  },
  "static_data": { "additionalProp1": "string" },
  "tags": ["string"],
  "active": true,
  "user_id": "string",
  "session_id": "string"
}

 • 返回体（Response Body）{
  "workflow": {
    "created_at": "2025-08-07T06:52:08.586Z",
    "updated_at": "2025-08-07T06:52:08.586Z",
    "id": "string",
    "user_id": "string",
    "name": "string",
    "description": "string",
    "type": "sequential",
    "status": "draft",
    "version": 1,
    "nodes": [ ... ],
    "edges": [ ... ],
    "variables": { "additionalProp1": {} },
    "settings": { "additionalProp1": {} },
    "tags": ["string"],
    "execution_count": 0,
    "last_execution": "string"
  },
  "message": "string"
}

结构差异小结
 • Create/Update 请求体：字段多为业务配置，Update 多了 ‎⁠workflow_id⁠ 和 ‎⁠active⁠ 字段。
 • Get/返回体：包含更多运行态和统计字段（如 ‎⁠execution_count⁠、‎⁠last_execution⁠、‎⁠status⁠、‎⁠version⁠）。
 • 字段风格：有些字段类型、命名、嵌套方式不统一，部分字段仅在某些接口出现。

建议：如需接口契约更统一，建议收敛字段、统一命名、精简冗余，避免重复和歧义。