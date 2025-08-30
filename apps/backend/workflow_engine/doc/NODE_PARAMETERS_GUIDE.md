# Workflow Engine 节点参数指南

本文档详细说明了 Workflow Engine 中所有支持的节点类型及其所需参数。

## 目录

1. [TRIGGER_NODE - 触发器节点](#trigger_node---触发器节点)
2. [AI_AGENT_NODE - AI代理节点](#ai_agent_node---ai代理节点)
3. [ACTION_NODE - 动作节点](#action_node---动作节点)
4. [FLOW_NODE - 流控制节点](#flow_node---流控制节点)
5. [EXTERNAL_ACTION_NODE - 外部动作节点](#external_action_node---外部动作节点)
6. [HUMAN_IN_THE_LOOP_NODE - 人在环中节点](#human_in_the_loop_node---人在环中节点)
7. [MEMORY_NODE - 内存节点](#memory_node---内存节点)
8. [TOOL_NODE - 工具节点](#tool_node---工具节点)

---

## TRIGGER_NODE - 触发器节点

触发器节点用于启动工作流的执行。

### TRIGGER_MANUAL - 手动触发

手动触发工作流。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| trigger_name | string | 否 | "Manual Trigger" | 触发器显示名称 |
| description | string | 否 | - | 触发器描述 |
| require_confirmation | boolean | 否 | false | 是否需要确认才能执行 |

### TRIGGER_CRON - 定时触发

基于 Cron 表达式的定时触发。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| cron_expression | string | 是 | - | Cron表达式，如"0 9 * * MON-FRI" |
| timezone | string | 否 | "UTC" | 时区 |
| enabled | boolean | 否 | true | 是否启用 |

### TRIGGER_WEBHOOK - Webhook触发

通过 HTTP Webhook 触发工作流。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| webhook_path | string | 否 | - | Webhook路径 |
| http_method | enum | 否 | "POST" | HTTP方法：GET, POST, PUT, PATCH, DELETE |
| authentication_required | boolean | 否 | true | 是否需要认证 |
| response_format | enum | 否 | "json" | 响应格式：json, text, html |

---

## AI_AGENT_NODE - AI代理节点

AI代理节点用于调用各种大语言模型。

### 通用参数

所有 AI 代理节点都支持以下通用参数：

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| system_prompt | string | 是 | - | 系统提示，定义AI代理角色和行为 |
| temperature | float | 否 | 0.7 | 随机性控制（0.0-1.0） |
| max_tokens | integer | 否 | 2048 | 最大生成token数 |
| top_p | float | 否 | 0.9 | 核采样参数（0.0-1.0） |
| response_format | enum | 否 | "text" | 响应格式：text, json, structured |
| timeout_seconds | integer | 否 | 30 | 超时时间（秒） |
| retry_attempts | integer | 否 | 3 | 重试次数 |

### OPENAI_NODE - OpenAI GPT模型

**额外参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| model_version | enum | 否 | "gpt-5-nano" | 模型版本：gpt-5, gpt-5-mini, gpt-5-nano, gpt-5-chat-latest, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano |
| presence_penalty | float | 否 | 0.0 | 存在惩罚（-2.0到2.0） |
| frequency_penalty | float | 否 | 0.0 | 频率惩罚（-2.0到2.0） |

### CLAUDE_NODE - Anthropic Claude模型

**额外参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| model_version | enum | 否 | "claude-3-5-haiku-20241022" | 模型版本：claude-sonnet-4-20250514, claude-3-5-haiku-20241022 |
| stop_sequences | json | 否 | - | 停止序列数组 |

### GEMINI_NODE - Google Gemini模型

**额外参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| model_version | enum | 否 | "gemini-2.5-flash-lite" | 模型版本：gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite |
| safety_settings | json | 否 | - | 安全过滤设置 |

---

## ACTION_NODE - 动作节点

动作节点用于执行各种操作。

### RUN_CODE - 代码执行

执行各种编程语言的代码。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| code | string | 是 | - | 要执行的代码 |
| language | enum | 是 | - | 编程语言：python, javascript, bash, sql, r, julia |
| timeout | integer | 否 | 30 | 执行超时（秒） |
| environment | enum | 否 | "sandboxed" | 执行环境：sandboxed, container, local |
| capture_output | boolean | 否 | true | 是否捕获输出 |

### HTTP_REQUEST - HTTP请求

发送 HTTP 请求。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| url | string | 是 | - | 目标URL |
| method | enum | 否 | "GET" | HTTP方法：GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS |
| headers | json | 否 | {} | HTTP头部 |
| data | json | 否 | {} | 请求数据 |
| timeout | integer | 否 | 30 | 请求超时（秒） |
| authentication | enum | 否 | "none" | 认证方式：none, bearer, basic, api_key, oauth2 |
| retry_attempts | integer | 否 | 3 | 重试次数 |

### DATA_TRANSFORMATION - 数据转换

转换和处理数据。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| transformation_type | enum | 是 | - | 转换类型：filter, map, reduce, sort, group, join, aggregate, custom |
| transformation_rule | string | 是 | - | 转换规则或表达式 |
| input_format | enum | 否 | "json" | 输入格式：json, csv, xml, yaml, text |
| output_format | enum | 否 | "json" | 输出格式：json, csv, xml, yaml, text |
| error_handling | enum | 否 | "skip" | 错误处理：skip, fail, default_value |

### FILE_OPERATION - 文件操作

文件系统操作。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| operation | enum | 是 | - | 操作类型：read, write, delete, copy, move, list |
| file_path | string | 是 | - | 文件路径 |
| content | string | 否 | - | 文件内容（写入时） |
| encoding | string | 否 | "utf-8" | 文件编码 |
| create_directories | boolean | 否 | true | 是否创建目录 |

---

## FLOW_NODE - 流控制节点

流控制节点用于控制工作流的执行流程。

### IF - 条件分支

根据条件表达式进行分支。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| condition | string | 是 | - | 条件表达式 |
| condition_type | enum | 否 | "javascript" | 条件类型：javascript, python, jsonpath, simple |
| strict_mode | boolean | 否 | false | 严格模式 |

### LOOP - 循环

循环执行节点。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| loop_type | enum | 否 | "foreach" | 循环类型：foreach, while, for, until |
| condition | string | 否 | - | 循环条件（while/until循环） |
| max_iterations | integer | 否 | 1000 | 最大迭代次数 |
| parallel_execution | boolean | 否 | false | 并行执行 |
| batch_size | integer | 否 | 1 | 批处理大小 |

### WAIT - 等待

等待特定条件或时间。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| wait_type | enum | 是 | - | 等待类型：fixed_delay, until_condition, until_time, for_signal |
| duration_seconds | integer | 否 | - | 等待时间（固定延迟） |
| wait_until | string | 否 | - | 等待条件或时间 |
| max_wait_seconds | integer | 否 | 3600 | 最大等待时间 |
| check_interval_seconds | integer | 否 | 10 | 检查间隔 |

### FILTER - 数据过滤

过滤数据集合。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| filter_expression | string | 是 | - | 过滤表达式 |
| filter_type | enum | 否 | "javascript" | 过滤类型：javascript, jsonpath, simple |

### MERGE - 数据合并

合并多个数据源。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| merge_strategy | enum | 否 | "concatenate" | 合并策略：concatenate, merge_objects, zip, custom |
| conflict_resolution | enum | 否 | "last_wins" | 冲突解决：first_wins, last_wins, error |

---

## EXTERNAL_ACTION_NODE - 外部动作节点

外部动作节点用于与外部服务集成。

### GITHUB - GitHub操作

执行 GitHub 相关操作。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| action | string | 是 | - | GitHub动作类型 |
| repository | string | 是 | - | 仓库名（owner/repo格式） |
| auth_token | string | 是 | - | GitHub访问令牌（敏感） |
| branch | string | 否 | - | 分支名 |
| title | string | 否 | - | 标题（issues或PR） |
| body | string | 否 | - | 内容（issues或PR） |

### EMAIL - 邮件操作

发送邮件。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| to | json | 是 | - | 收件人列表 |
| subject | string | 是 | - | 邮件主题 |
| body | string | 是 | - | 邮件正文 |
| cc | json | 否 | [] | 抄送列表 |
| bcc | json | 否 | [] | 密送列表 |
| attachments | json | 否 | [] | 附件列表 |
| html_body | boolean | 否 | false | 是否为HTML格式 |

### SLACK - Slack操作

发送 Slack 消息。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| channel | string | 是 | - | 频道ID或名称 |
| message | string | 是 | - | 消息内容 |
| bot_token | string | 是 | - | Slack Bot令牌（敏感） |
| attachments | json | 否 | [] | 消息附件 |
| thread_ts | string | 否 | - | 线程时间戳 |

### API_CALL - 通用API调用

调用任意 REST API。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| method | enum | 是 | "GET" | HTTP方法：GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS |
| url | string | 是 | - | API端点URL |
| headers | json | 否 | {} | HTTP头部 |
| query_params | json | 否 | {} | 查询参数 |
| body | json | 否 | - | 请求体数据 |
| timeout | integer | 否 | 30 | 超时时间（秒） |
| authentication | enum | 否 | "none" | 认证方式：none, bearer, basic, api_key |

---

## HUMAN_IN_THE_LOOP_NODE - 人在环中节点

需要人工干预的节点。

### HUMAN_APP - 应用内人工交互

在应用内请求人工干预。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| notification_type | enum | 是 | - | 通知类型：approval, input, review, confirmation |
| title | string | 否 | "Action Required" | 通知标题 |
| message | string | 是 | - | 通知消息内容 |
| timeout_minutes | integer | 否 | 60 | 超时分钟数 |
| priority | enum | 否 | "normal" | 优先级：low, normal, high, urgent |
| required_fields | json | 否 | [] | 需要用户输入的字段 |

### HUMAN_GMAIL - Gmail人工交互

通过 Gmail 请求人工审批。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| email_template | string | 是 | - | 邮件模板 |
| recipients | json | 是 | - | 收件人列表 |
| subject | string | 否 | "Workflow Approval Required" | 邮件主题 |
| timeout_hours | integer | 否 | 24 | 超时小时数 |
| approval_type | enum | 否 | "simple" | 审批类型：simple, detailed, custom |

### HUMAN_SLACK - Slack人工交互

通过 Slack 请求人工审批。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| channel | string | 是 | - | Slack频道 |
| message | string | 是 | - | 消息内容 |
| approval_buttons | json | 否 | ["Approve", "Reject"] | 审批按钮 |
| timeout_minutes | integer | 否 | 60 | 超时分钟数 |

---

## MEMORY_NODE - 内存节点

用于数据存储和检索。

### MEMORY_SIMPLE - 简单键值存储

简单的键值对存储。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| operation | enum | 是 | - | 操作类型：get, set, delete, exists |
| key | string | 是 | - | 存储键 |
| value | any | 否 | - | 存储值（set操作时） |
| provider | enum | 否 | "redis" | 提供商：redis, memcached, dynamodb, memory |
| ttl_seconds | integer | 否 | - | 生存时间（秒） |
| namespace | string | 否 | - | 命名空间或前缀 |

### MEMORY_VECTOR_STORE - 向量数据库

向量相似度搜索。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| operation | enum | 是 | - | 操作类型：store, search, delete, update |
| collection_name | string | 是 | - | 向量集合名称 |
| text | string | 否 | - | 要存储或搜索的文本 |
| metadata | json | 否 | {} | 元数据 |
| provider | enum | 否 | "supabase" | 提供商：supabase, pinecone, weaviate, chroma, qdrant |
| embedding_model | string | 否 | "text-embedding-ada-002" | 嵌入模型 |
| similarity_threshold | float | 否 | 0.7 | 相似度阈值 |
| max_results | integer | 否 | 10 | 最大结果数 |

### MEMORY_BUFFER - 缓冲区内存

会话缓冲区管理。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| operation | enum | 是 | - | 操作类型：add, get, clear, get_all |
| buffer_name | string | 否 | "default" | 缓冲区名称 |
| max_size | integer | 否 | 100 | 最大缓冲区大小 |
| window_size | integer | 否 | 10 | 窗口大小 |

### MEMORY_KNOWLEDGE - 知识存储

结构化知识管理。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| operation | enum | 是 | - | 操作类型：store, query, update, delete |
| knowledge_type | string | 是 | - | 知识类型 |
| content | json | 否 | - | 知识内容 |
| tags | json | 否 | [] | 标签列表 |
| expiry_time | string | 否 | - | 过期时间 |

---

## TOOL_NODE - 工具节点

专用工具节点。

### TOOL_HTTP - HTTP工具

HTTP 请求工具。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| method | enum | 是 | - | HTTP方法：GET, POST, PUT, DELETE, PATCH |
| url | string | 是 | - | 目标URL |
| headers | json | 否 | {} | HTTP头部 |
| timeout_seconds | integer | 否 | 30 | 超时时间 |
| follow_redirects | boolean | 否 | true | 是否跟随重定向 |
| verify_ssl | boolean | 否 | true | 是否验证SSL证书 |

### TOOL_CODE_EXECUTION - 代码执行工具

安全的代码执行环境。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| language | enum | 是 | - | 语言：python, javascript, bash |
| code | string | 是 | - | 要执行的代码 |
| packages | json | 否 | [] | 需要的包/库 |
| timeout_seconds | integer | 否 | 30 | 执行超时 |
| memory_limit_mb | integer | 否 | 512 | 内存限制（MB） |

### TOOL_GOOGLE_CALENDAR_MCP - Google日历MCP工具

通过 MCP 协议访问 Google 日历。

**参数：**
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| tool_name | string | 是 | - | MCP工具名称 |
| operation | string | 是 | - | 特定操作或方法 |
| parameters | json | 否 | {} | 操作参数 |
| server_url | string | 否 | - | MCP服务器URL |
| timeout_seconds | integer | 否 | 30 | 超时时间 |
| retry_attempts | integer | 否 | 3 | 重试次数 |

---

## 参数说明

### 数据类型

- **string**: 文本字符串
- **integer**: 整数
- **float**: 浮点数
- **boolean**: 布尔值（true/false）
- **enum**: 枚举值，只能从预定义的选项中选择
- **json**: JSON 对象或数组
- **url**: 有效的 URL 地址
- **any**: 任意类型

### 参数验证

1. **必需参数**：必须提供，否则节点验证失败
2. **可选参数**：有默认值，可以不提供
3. **敏感参数**：如 API 密钥、令牌等，在系统中会被安全处理

### 使用示例

执行单个节点时，可以通过 `override_parameters` 提供参数：

```json
{
  "user_id": "user-123",
  "input_data": {
    "prompt": "Hello"
  },
  "execution_context": {
    "override_parameters": {
      "method": "GET",
      "url": "https://api.example.com/data",
      "headers": {
        "Authorization": "Bearer token123"
      },
      "timeout": 60
    }
  }
}
```

### 注意事项

1. 参数名称区分大小写
2. 枚举值必须完全匹配（包括大小写）
3. JSON 类型的参数必须是有效的 JSON 格式
4. 某些参数可能依赖于其他参数（如 `loop_type` 为 "while" 时需要 `condition`）
5. 敏感参数应通过安全的方式传递，避免在日志中暴露

---

更新日期：2025-08-03
