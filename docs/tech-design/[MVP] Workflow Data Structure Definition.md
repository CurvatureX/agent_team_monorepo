# [MVP] Workflow 节点的数据结构定义

## 模块定义

### 模块定义 & 解释

![svgviewer-output (2)](/Users/bytedance/Downloads/flow-definition.svg)



##### 1.工作流核心模块 (Workflow Core Module) - 工作流的整体定义和管理

Workflow模块作为最核心的模块之一，负责整体工作流的生成以及调度

- Workflow: 工作流定义，包含节点、连接、设置等

- WorkflowSettings: 工作流配置，包含错误策略、超时等

- Position: 节点位置信息

```protobuf
// ============================================================================
// 工作流核心模块 (Workflow Core Module)
// ============================================================================

// 工作流定义
message Workflow {
  string id = 1;
  string name = 2;
  bool active = 3;
  repeated Node nodes = 4;
  ConnectionsMap connections = 5;
  WorkflowSettings settings = 6;
  map<string, string> static_data = 7;
  map<string, string> pin_data = 8;
  int64 created_at = 9;
  int64 updated_at = 10;
  string version = 11;
  repeated string tags = 12;
}

// 工作流设置
message WorkflowSettings {
  map<string, string> timezone = 1;
  bool save_execution_progress = 2;
  bool save_manual_executions = 3;
  int32 timeout = 4;
  ErrorPolicy error_policy = 5;
  CallerPolicy caller_policy = 6;
}

// 错误处理策略
enum ErrorPolicy {
  STOP_WORKFLOW = 0;
  CONTINUE_REGULAR_OUTPUT = 1;
  CONTINUE_ERROR_OUTPUT = 2;
}

// 调用者策略
enum CallerPolicy {
  WORKFLOW_MAIN = 0;
  WORKFLOW_SUB = 1;
}

```

##### 2. 节点模块 (Node Module) - 定义工作流中的执行单元

```protobuf
// ============================================================================
// 节点模块 (Node Module)
// ============================================================================
message Node {
  string id = 1;
  string name = 2;
  string type = 3;
  int32 type_version = 4;
  Position position = 5;
  bool disabled = 6;
  map<string, string> parameters = 7;
  map<string, string> credentials = 8;
  ErrorHandling on_error = 9;
  RetryPolicy retry_policy = 10;
  map<string, string> notes = 11;
  repeated string webhooks = 12;
}

// 节点位置
message Position {
  float x = 1;
  float y = 2;
}

// 错误处理方式
enum ErrorHandling {
  STOP_WORKFLOW_ON_ERROR = 0;
  CONTINUE_REGULAR_OUTPUT_ON_ERROR = 1;
  CONTINUE_ERROR_OUTPUT_ON_ERROR = 2;
}

// 重试策略
message RetryPolicy {
  int32 max_tries = 1;
  int32 wait_between_tries = 2;
}
```

- Node: 节点定义，包含类型、参数、位置、错误处理等

- RetryPolicy: 重试策略配置

- ErrorHandling: 错误处理方式枚举

##### 3. 连接系统模块 (Connection System Module)  - 负责节点间的数据流和控制流

```protobuf
// ============================================================================
// 连接系统模块 (Connection System Module)
// ============================================================================

// 连接映射 (nodeName -> connectionType -> connections)
message ConnectionsMap {
  map<string, NodeConnections> connections = 1;
}

// 节点连接定义
message NodeConnections {
  map<string, ConnectionArray> connection_types = 1;
}

// 连接数组
message ConnectionArray {
  repeated Connection connections = 1;
}

// 单个连接定义
message Connection {
  string node = 1;              // 目标节点名
  ConnectionType type = 2;      // 连接类型
  int32 index = 3;             // 端口索引
}

// 连接类型枚举
enum ConnectionType {
  MAIN = 0;
  AI_AGENT = 1;
  AI_CHAIN = 2;
  AI_DOCUMENT = 3;
  AI_EMBEDDING = 4;
  AI_LANGUAGE_MODEL = 5;
  AI_MEMORY = 6;
  AI_OUTPUT_PARSER = 7;
  AI_RETRIEVER = 8;
  AI_RERANKER = 9;
  AI_TEXT_SPLITTER = 10;
  AI_TOOL = 11;
  AI_VECTOR_STORE = 12;
}

```

- ConnectionsMap: 连接映射，核心的数据流控制

- Connection: 单个连接定义

- ConnectionType: 12种连接类型，包括main、ai_tool、ai_memory等

##### 4. 执行系统模块 (Execution System Module) - 管理工作流的执行状态和过程

```protobuf
// ============================================================================
// 执行系统模块 (Execution System Module)
// ============================================================================

// 执行数据
message ExecutionData {
  string execution_id = 1;
  string workflow_id = 2;
  ExecutionStatus status = 3;
  int64 start_time = 4;
  int64 end_time = 5;
  RunData run_data = 6;
  ExecutionMode mode = 7;
  string triggered_by = 8;
  map<string, string> metadata = 9;
}

// 执行状态
enum ExecutionStatus {
  NEW = 0;
  RUNNING = 1;
  SUCCESS = 2;
  ERROR = 3;
  CANCELED = 4;
  WAITING = 5;
}

// 执行模式
enum ExecutionMode {
  MANUAL = 0;
  TRIGGER = 1;
  WEBHOOK = 2;
  RETRY = 3;
}

// 运行数据
message RunData {
  map<string, NodeRunData> node_data = 1;
}

// 节点运行数据
message NodeRunData {
  repeated TaskData tasks = 1;
}

// 任务数据
message TaskData {
  int64 start_time = 1;
  int64 execution_time = 2;
  string source = 3;
  repeated NodeExecutionData data = 4;
  map<string, string> execution_status = 5;
  ErrorData error = 6;
}

// 节点执行数据
message NodeExecutionData {
  repeated DataItem data = 1;
  map<string, string> metadata = 2;
}

// 数据项
message DataItem {
  map<string, string> json_data = 1;
  repeated BinaryData binary_data = 2;
  bool paused = 3;
  map<string, string> metadata = 4;
}

// 二进制数据
message BinaryData {
  string property_name = 1;
  bytes data = 2;
  string mime_type = 3;
  string file_name = 4;
  int64 file_size = 5;
}

// 错误数据
message ErrorData {
  string message = 1;
  string stack = 2;
  string name = 3;
  int32 line_number = 4;
  map<string, string> context = 5;
}
```

- ExecutionData: 执行数据，包含状态、时间、结果等

- RunData: 运行数据，按节点组织

- TaskData: 任务数据，包含执行时间、状态等

##### 5. AI系统模块 (AI System Module) - AI Agent 和相关组件

```protobuf
// ============================================================================
// AI系统模块 (AI System Module)
// ============================================================================

// AI Agent 配置
message AIAgentConfig {
  string agent_type = 1;
  string prompt = 2;
  AILanguageModel language_model = 3;
  repeated AITool tools = 4;
  AIMemory memory = 5;
  map<string, string> parameters = 6;
}

// AI 语言模型
message AILanguageModel {
  string model_type = 1;
  string model_name = 2;
  float temperature = 3;
  int32 max_tokens = 4;
  map<string, string> parameters = 5;
}

// AI 工具
message AITool {
  string tool_type = 1;
  string tool_name = 2;
  string description = 3;
  map<string, string> parameters = 4;
}

// AI 记忆
message AIMemory {
  string memory_type = 1;
  int32 max_tokens = 2;
  map<string, string> parameters = 3;
}

```

- AIAgentConfig: AI Agent配置

- AILanguageModel: AI语言模型配置

- AITool: AI工具定义

- AIMemory: AI记忆系统

##### 6.触发器模块 (Trigger Module)

```protobuf
// ============================================================================
// 触发器模块 (Trigger Module)
// ============================================================================

// 触发器定义
message Trigger {
  string trigger_id = 1;
  TriggerType type = 2;
  string node_name = 3;
  map<string, string> configuration = 4;
  bool active = 5;
  Schedule schedule = 6;
}

// 触发器类型
enum TriggerType {
  WEBHOOK = 0;
  CRON = 1;
  MANUAL = 2;
  EMAIL = 3;
  FORM = 4;
  CALENDAR = 5;
}

// 调度配置
message Schedule {
  string cron_expression = 1;
  string timezone = 2;
  int64 next_execution = 3;
}
```

- Trigger: 触发器定义

- Schedule: 调度配置

##### 7. 集成系统模块 (Integration System Module)

```protobuf
// ============================================================================
// 集成系统模块 (Integration System Module)
// ============================================================================

// 第三方集成
message Integration {
  string integration_id = 1;
  string integration_type = 2;
  string name = 3;
  string version = 4;
  map<string, string> configuration = 5;
  CredentialConfig credentials = 6;
  repeated string supported_operations = 7;
}

// 凭证配置
message CredentialConfig {
  string credential_type = 1;
  string credential_id = 2;
  map<string, string> credential_data = 3;
}
```

- Integration: 第三方集成定义

- CredentialConfig: 凭证配置管理



### 模块工作流

![svgviewer-output (4)](/Users/bytedance/Downloads/module-workflow.svg)



## UseCase - 秘书Agent

##### 时序图

![svgviewer-output (3)](/Users/bytedance/Downloads/agent-case.svg)



##### 工作流

![svgviewer-output (6)](/Users/bytedance/Downloads/agent-case-flow.svg)