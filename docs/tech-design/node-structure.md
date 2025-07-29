# Node Structure Definition

## 参数配置说明

**重要区分：节点配置参数 vs 运行时数据**

### 📝 节点配置参数 (Node Configuration Parameters)

- **静态配置**：在设计工作流时设置，定义节点的行为方式
- **包含内容**：
  - 认证信息 (API keys, tokens, credentials)
  - 行为设置 (操作类型、超时时间、重试次数)
  - 默认值和模板 (可被运行时数据覆盖)
  - 连接配置 (存储类型、服务器地址)
  - 处理选项 (是否启用某功能、输出格式)

### 🔄 运行时数据 (Runtime Data)

- **动态数据**：每次执行时通过工作流数据流传递
- **包含内容**：
  - 具体的业务数据 (用户 ID、文件路径、消息内容)
  - 从上游节点传入的处理结果
  - 基于条件动态确定的值

### 💡 设计原则

- 节点参数只包含**如何执行**的配置信息
- 具体**执行什么内容**的数据通过工作流传递
- 支持模板表达式 (如 `{{$json.field}}`) 来动态引用运行时数据

---

## 节点类型概览

工作流系统包含以下 8 种核心节点类型：

## 1. Trigger Node (触发器节点)

**形状**: Semi-rounded box

### 子节点类型:

#### Chat Trigger

**参数配置:**

- `channel`: string - 聊天频道标识符（如 Slack/Discord/Teams 频道 ID）
- `allowedUsers`: `array<string>` - 允许触发的用户 ID 列表
- `triggerPhrase`: string - 触发短语或关键词
- `supportedMediaTypes`: `array<enum>` - 支持的媒体类型 (text/image/audio/video/file)
- `maxFileSize`: integer - 最大文件大小（MB，适用于所有媒体类型）-
- `enableOCR`: boolean - 是否启用图片 OCR 文字识别
- `enableSpeechToText`: boolean - 是否启用音频语音转文字
- `enableVideoAnalysis`: boolean - 是否启用视频内容分析
- `maxDuration`: integer - 最大媒体时长（秒，适用于音频/视频）
- `autoReply`: boolean - 是否自动回复
- `responseFormat`: enum - 响应格式 (text/json/structured)

#### Webhook Trigger

**参数配置:**

- `httpMethod`: enum - HTTP 方法 (GET/POST/PUT/DELETE/PATCH)
- `path`: string - 监听路径（如 /webhook/my-trigger）
- `authentication`: enum - 认证方式 (none/basic_auth/header_auth/query_auth)
- `authUsername`: string - 基础认证用户名
- `authPassword`: string - 基础认证密码
- `authHeaderName`: string - 认证头名称
- `authHeaderValue`: string - 认证头值
- `respond`: enum - 响应方式 (immediately/when_last_node_finishes/using_respond_node)
- `responseCode`: integer - HTTP 响应状态码 (默认 200)
- `responseHeaders`: `map<string, string>` - 响应头
- `responseBody`: string - 立即响应的内容
- `responseData`: enum - 响应数据格式，仅在 respond 为 when_last_node_finishes 时生效
  - `first_entry_json` - 返回最后节点的第一个数据项作为 JSON 对象
  - `all_entries_array` - 返回最后节点的所有数据项作为 JSON 数组
  - `last_node_data` - 返回最后节点的完整数据结构

#### Cron Trigger

**参数配置:**

- `cron_expression`: string - Cron 表达式
- `timezone`: string - 时区
- `max_executions`: integer - 最大执行次数
- `start_date`: datetime - 开始日期
- `end_date`: datetime - 结束日期
- `description`: string - 任务描述

---

## 2. AI Agent Node (AI 代理节点)

**形状**: Rectangle node featuring two connection points, linkable to Memory and Tool components

**架构革新**: 从硬编码角色转向灵活的提供商驱动架构

### 子节点类型 (Provider-Based Architecture):

#### Gemini Node (AI_GEMINI_NODE)
Google Gemini AI 代理，功能完全由系统提示词定义

**参数配置:**
- `system_prompt`: text - **核心参数**：定义AI代理的角色、行为和指令
- `model_version`: enum - 模型版本 (gemini-pro/gemini-pro-vision/gemini-ultra)
- `temperature`: float - 创造性参数 (0.0-1.0)
- `max_tokens`: integer - 最大生成 token 数
- `top_p`: float - 核采样参数 (0.0-1.0)
- `top_k`: integer - 候选词数量限制
- `safety_settings`: object - 安全设置配置
- `response_format`: enum - 响应格式 (text/json/structured)
- `timeout_seconds`: integer - 请求超时时间
- `retry_attempts`: integer - 重试次数

#### OpenAI Node (AI_OPENAI_NODE)
OpenAI GPT AI 代理，功能完全由系统提示词定义

**参数配置:**
- `system_prompt`: text - **核心参数**：定义AI代理的角色、行为和指令
- `model_version`: enum - 模型版本 (gpt-4/gpt-4-turbo/gpt-3.5-turbo/gpt-4-vision-preview)
- `temperature`: float - 创造性参数 (0.0-2.0)
- `max_tokens`: integer - 最大生成 token 数
- `top_p`: float - 核采样参数 (0.0-1.0)
- `presence_penalty`: float - 存在惩罚 (-2.0-2.0)
- `frequency_penalty`: float - 频率惩罚 (-2.0-2.0)
- `response_format`: enum - 响应格式 (text/json/structured)
- `timeout_seconds`: integer - 请求超时时间
- `retry_attempts`: integer - 重试次数

#### Claude Node (AI_CLAUDE_NODE)
Anthropic Claude AI 代理，功能完全由系统提示词定义

**参数配置:**
- `system_prompt`: text - **核心参数**：定义AI代理的角色、行为和指令
- `model_version`: enum - 模型版本 (claude-3-opus/claude-3-sonnet/claude-3-haiku/claude-2.1)
- `temperature`: float - 创造性参数 (0.0-1.0)
- `max_tokens`: integer - 最大生成 token 数
- `top_p`: float - 核采样参数 (0.0-1.0)
- `top_k`: integer - 候选词数量限制
- `stop_sequences`: array<string> - 停止序列
- `response_format`: enum - 响应格式 (text/json/structured)
- `timeout_seconds`: integer - 请求超时时间
- `retry_attempts`: integer - 重试次数

### 通用连接配置:
- `memory_connection`: string - 连接的 Memory 节点 ID
- `tool_connections`: array<string> - 连接的 Tool 节点 ID 列表
- `streaming`: boolean - 是否流式响应
- `on_error`: enum - 节点执行失败时的操作 (stop_workflow/continue)

### 系统提示词示例:

**数据分析代理 (使用 Gemini)**:
```
您是一名高级数据分析师，专精统计分析和商业智能。

任务：分析提供的数据集并提供可操作的洞察。

分析要求：
1. 统计概览：均值、中位数、标准差、四分位数
2. 趋势分析：识别模式、季节性和异常值
3. 相关性分析：变量间的关键关系
4. 商业洞察：模式对商业决策的意义
5. 数据质量：完整性、准确性、潜在问题
6. 建议：具体的、可操作的下一步

输出格式：结构化 JSON，包含上述各个要求的章节。
置信水平：为每个洞察包含置信分数 (0-1)。
```

**客户服务路由代理 (使用 OpenAI)**:
```
您是一个智能客户服务路由系统。

任务：分析客户询问并路由到适当的部门。

路由规则：
- "billing" → 付款问题、发票、退款、订阅问题
- "technical" → 产品错误、功能问题、集成帮助
- "sales" → 新购买、升级、价格咨询
- "general" → 一般问题、反馈、投诉

分析过程：
1. 从客户消息中提取关键意图和实体
2. 考虑紧急程度 (low/medium/high/critical)
3. 识别客户等级 (basic/premium/enterprise)
4. 应用路由规则并给出置信分数

响应格式：
{
  "department": "billing|technical|sales|general",
  "confidence": 0.95,
  "urgency": "low|medium|high|critical",
  "reasoning": "路由决策的简要解释",
  "suggested_response": "推荐给客户的首次回复"
}
```

---

## 3. External Action Node (外部动作节点)

**形状**: Square node

### 子节点类型:

#### GitHub Node

**参数配置:**

- `github_token`: string - GitHub 访问令牌
- `repository`: string - 仓库名 (owner/repo)
- `action_type`: enum - 操作类型 (create_issue/create_pr/comment/merge/close)
- `timeout`: integer - 请求超时时间（秒）

#### Google Calendar Node

**参数配置:**

- `google_credentials`: string - Google 凭证
- `calendar_id`: string - 日历 ID
- `action_type`: enum - 操作类型 (create_event/update_event/delete_event/list_events)
- `timezone`: string - 默认时区
- `timeout`: integer - 请求超时时间（秒）

#### Trello Node

**参数配置:**

- `trello_api_key`: string - Trello API 密钥
- `trello_token`: string - Trello 令牌
- `action_type`: enum - 操作类型 (create_card/update_card/move_card/delete_card)
- `default_board_id`: string - 默认看板 ID（可被运行时数据覆盖）
- `timeout`: integer - 请求超时时间（秒）

#### Email Node

**参数配置:**

- `email_provider`: enum - 邮件提供商 (gmail/outlook/smtp)
- `smtp_server`: string - SMTP 服务器
- `smtp_port`: integer - SMTP 端口
- `username`: string - 用户名
- `password`: string - 密码
- `default_from_email`: string - 默认发件人邮箱
- `use_html`: boolean - 是否支持 HTML 格式
- `enable_attachments`: boolean - 是否启用附件功能
- `timeout`: integer - 发送超时时间（秒）

#### Slack Node

**参数配置:**

- `slack_token`: string - Slack 机器人令牌
- `actionType`: enum - 操作类型 (send_message/upload_file/create_channel/invite_user)
- `default_channel`: string - 默认频道名或 ID（可被运行时数据覆盖）
- `asUser`: boolean - 是否以用户身份发送
- `timeout`: integer - 请求超时时间（秒）

---

## 4. Action Node (动作节点)

**形状**: Square node

### 子节点类型:

#### Run Code Node

**参数配置:**

- `language`: enum - 编程语言 (python/javascript/java/golang)
- `code`: text - 要执行的代码
- `timeout`: integer - 执行超时时间（秒）
- `environment_variables`: `map<string, string>` - 环境变量
- `input_data`: text - 输入数据
- `continue_on_fail`: boolean - 失败时是否继续

#### Send HTTP Request Node

**参数配置:**

- `url`: string - 请求 URL
- `method`: enum - HTTP 方法 (GET/POST/PUT/DELETE/PATCH)
- `headers`: `map<string, string>` - 请求头
- `query_parameters`: `map<string, string>` - 查询参数
- `body`: text - 请求体
- `body_type`: enum - 请求体类型 (json/form/raw/binary)
- `authentication`: enum - 认证方式 (none/api_key/bearer_token/basic_auth/oauth)
- `api_key`: string - API 密钥
- `bearer_token`: string - Bearer 令牌
- `username`: string - 基础认证用户名
- `password`: string - 基础认证密码
- `timeout`: integer - 请求超时时间（秒）
- `follow_redirects`: boolean - 是否跟随重定向
- `verify_ssl`: boolean - 是否验证 SSL 证书

#### Parse Media Node

**参数配置:**

- `mediaSource`: enum - 媒体源类型 (url/file/base64/chat_upload)
- `parseType`: enum - 解析类型 (ocr/object_detection/speech_to_text/scene_analysis/extract_text)
- `language`: string - 默认识别语言（OCR/语音识别用）
- `confidenceThreshold`: float - 置信度阈值 (0.0-1.0)
- `extractFrames`: boolean - 是否提取视频关键帧
- `frameInterval`: integer - 帧提取间隔（秒）
- `extractMetadata`: boolean - 是否提取文件元数据
- `outputFormat`: enum - 输出格式 (text/json/structured)
- `timeout`: integer - 处理超时时间（秒）

#### Web Search Node

**参数配置:**

- `search_engine`: enum - 搜索引擎 (google/bing/duckduckgo)
- `api_key`: string - 搜索引擎 API 密钥
- `query`: string - 搜索查询
- `result_count`: integer - 返回结果数量
- `language`: string - 搜索语言
- `region`: string - 搜索地区
- `safe_search`: enum - 安全搜索 (off/moderate/strict)
- `result_type`: enum - 结果类型 (web/images/videos/news)
- `time_filter`: enum - 时间过滤 (all/day/week/month/year)

#### File Operations Node

**参数配置:**

- `operationType`: enum - 操作类型 (upload/download/convert/compress/extract/metadata)
- `sourcePath`: string - 源文件路径
- `destinationPath`: string - 目标路径
- `storageType`: enum - 存储类型 (local/s3/gcs/azure/dropbox/google_drive)
- `bucketName`: string - 存储桶名称（云存储用）
- `accessKey`: string - 访问密钥
- `targetFormat`: string - 目标格式（转换操作用）
- `compressionLevel`: integer - 压缩级别 (1-9)
- `maxFileSize`: integer - 最大文件大小（MB）
- `allowedTypes`: `array<string>` - 允许的文件类型
- `virusScan`: boolean - 是否进行病毒扫描
- `extractMetadata`: boolean - 是否提取元数据
- `enableBackup`: boolean - 是否启用备份

---

## 5. Flow Node (流程控制节点)

**形状**: Rectangle node

### 子节点类型:

#### If Node

**参数配置:**

- `condition_type`: enum - 条件类型 (javascript/jsonpath/simple)
- `condition_expression`: string - 条件表达式
- `true_branch`: string - 条件为真时的分支
- `false_branch`: string - 条件为假时的分支
- `comparison_operation`: enum - 比较操作 (equals/not_equals/greater/less/contains/regex)
- `value1`: string - 比较值 1
- `value2`: string - 比较值 2

#### Filter Node

**参数配置:**

- `filter_type`: enum - 过滤类型 (javascript/jsonpath/simple)
- `filter_expression`: string - 过滤表达式
- `keep_only_set`: boolean - 是否仅保留匹配项
- `condition`: string - 过滤条件

#### Loop Node

**参数配置:**

- `loop_type`: enum - 循环类型 (for_each/while/times)
- `input_data`: string - 输入数据路径
- `max_iterations`: integer - 最大迭代次数
- `break_condition`: string - 跳出条件
- `batch_size`: integer - 批处理大小

#### Merge Node

**参数配置:**

- `merge_type`: enum - 合并类型 (append/merge/multiplex)
- `output_format`: enum - 输出格式 (array/object)
- `merge_key`: string - 合并键
- `wait_for_all`: boolean - 是否等待所有输入

#### Switch Node

**参数配置:**

- `mode`: enum - 模式 (expression/rules)
- `expression`: string - 切换表达式
- `rules`: `array&lt;object&gt;` - 规则配置
- `fallback_output`: integer - 默认输出端口

#### Wait Node

**参数配置:**

- `wait_type`: enum - 等待类型 (fixed_time/until_time/webhook)
- `duration`: integer - 等待时长（秒）
- `until_time`: datetime - 等待到指定时间
- `webhook_url`: string - 等待 Webhook URL
- `max_wait_time`: integer - 最大等待时间（秒）

---

## 6. Human-In-The-Loop Node (人机交互节点)

**形状**: 待定义

### 子节点类型:

#### Gmail Node

**参数配置:**

- `gmail_credentials`: string - Gmail 凭证
- `approval_subject`: string - 审批邮件主题
- `approval_body`: text - 审批邮件内容
- `approver_emails`: `array<string>` - 审批人邮箱
- `timeout_hours`: integer - 审批超时时间（小时）
- `auto_approve_after_timeout`: boolean - 超时后是否自动批准
- `response_format`: enum - 响应格式 (simple/detailed)

#### Slack Node

**参数配置:**

- `slack_token`: string - Slack 机器人令牌
- `approval_channel`: string - 审批频道
- `approver_users`: `array<string>` - 审批用户
- `approval_message`: text - 审批消息
- `approval_buttons`: `array<string>` - 审批按钮选项
- `timeout_minutes`: integer - 审批超时时间（分钟）
- `auto_approve_after_timeout`: boolean - 超时后是否自动批准

#### Discord Node

**参数配置:**

- `discord_token`: string - Discord 机器人令牌
- `guild_id`: string - 服务器 ID
- `channel_id`: string - 频道 ID
- `approval_message`: text - 审批消息
- `approver_roles`: `array<string>` - 审批角色
- `approval_reactions`: `array<string>` - 审批表情
- `timeout_minutes`: integer - 审批超时时间（分钟）

#### Telegram Node

**参数配置:**

- `telegram_token`: string - Telegram 机器人令牌
- `chat_id`: string - 聊天 ID
- `approval_message`: text - 审批消息
- `inline_keyboard`: `array&lt;object&gt;` - 内联键盘选项
- `timeout_minutes`: integer - 审批超时时间（分钟）

#### App Node

**参数配置:**

- `app_webhook_url`: string - 应用 Webhook URL
- `approval_form_url`: string - 审批表单 URL
- `approval_data`: object - 审批所需数据
- `callback_url`: string - 回调 URL
- `timeout_minutes`: integer - 审批超时时间（分钟）

---

## 7. Tool Node (工具节点)

**形状**: Circle

### 子节点类型:

#### Google Calendar MCP Node

**参数配置:**

- `mcp_server_url`: string - MCP 服务器 URL
- `google_credentials`: string - Google 凭证
- `default_calendar_id`: string - 默认日历 ID
- `timezone`: string - 时区
- `max_results`: integer - 最大结果数

#### Notion MCP Node

**参数配置:**

- `mcp_server_url`: string - MCP 服务器 URL
- `notion_token`: string - Notion 集成令牌
- `database_id`: string - 数据库 ID
- `page_id`: string - 页面 ID
- `property_mappings`: `map<string, string>` - 属性映射

---

## 8. Memory Node (记忆节点)

**形状**: Circle

### 子节点类型:

#### Simple Memory

**参数配置:**

- `memory_type`: enum - 内存类型 (session/persistent/temporary)
- `storage_duration`: integer - 存储时长（秒）
- `max_memory_size`: integer - 最大内存大小（KB）
- `clear_on_restart`: boolean - 重启时是否清空
- `encryption_enabled`: boolean - 是否加密存储
