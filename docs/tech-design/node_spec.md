# 节点规范系统技术设计

## 📋 概述

本文档描述了工作流引擎节点规范系统的技术设计。该系统解决了当前节点类型和子类型仅以枚举形式定义，缺乏参数模式、输入输出端口定义和验证规则的问题。

节点规范系统是工作流引擎的核心架构组件，它统一管理:
- **节点类型定义**: 每个节点类型的参数、端口、验证规则
- **端口系统**: 输入输出端口的类型安全和连接验证
- **数据格式规范**: 端口间数据传输的结构化定义
- **参数验证**: 节点配置的完整性检查

## 🎯 问题描述

### 当前问题
1. **缺失参数模式**: 没有正式定义每个节点类型需要什么参数
2. **未定义端口规范**: 每个节点的输入输出端口定义不清晰
3. **缺乏端口类型安全**: 节点连接时无法验证端口类型兼容性
4. **缺乏验证**: 对节点配置没有类型检查或验证
5. **开发体验差**: 没有自动补全或参数文档
6. **实现不一致**: Protocol Buffer定义与实际执行器实现不匹配
7. **数据映射缺失**: 无法定义节点间数据如何转换和验证

### 当前状态示例
```python
# 目前节点配置方式，没有任何验证
node.parameters = {
    "code": "print('hello')",      # 无类型检查
    "language": "python",          # 无枚举验证
    "timeout": "invalid_value"     # 无格式验证
}
```

## 🏗️ 解决方案

### 基于代码的规范系统
我们提出**基于代码**的方案，将所有节点规范定义为共享代码库中的Python类，而不是存储在数据库中。

#### 为什么选择基于代码？
- **版本控制**: 所有变更在Git中跟踪，有完整的代码审查流程
- **类型安全**: 完整的Python类型提示和IDE支持
- **性能**: 启动时加载一次，运行时从内存访问
- **简单性**: 无需数据库依赖
- **开发体验**: 自动补全和内联文档

## 🏛️ 架构设计

### 目录结构
```
apps/backend/shared/node_specs/
├── __init__.py
├── base.py                    # 基础规范类
├── registry.py                # 中央规范注册器
├── validator.py               # 规范验证逻辑
└── definitions/
    ├── __init__.py
    ├── trigger_nodes.py       # 触发器节点规范
    ├── ai_agent_nodes.py      # AI代理节点规范
    ├── action_nodes.py        # 动作节点规范
    ├── flow_nodes.py          # 流程控制节点规范
    ├── tool_nodes.py          # 工具节点规范
    ├── memory_nodes.py        # 记忆节点规范
    └── human_loop_nodes.py    # 人机交互节点规范
```

### 核心数据结构

#### 基础规范类
```python
@dataclass
class ParameterDef:
    name: str
    type: ParameterType
    required: bool = False
    default_value: Optional[str] = None
    enum_values: Optional[List[str]] = None
    description: str = ""
    validation_pattern: Optional[str] = None

@dataclass
class InputPortSpec:
    name: str
    type: str                    # ConnectionType (MAIN, AI_TOOL, AI_MEMORY, etc.)
    required: bool = False
    description: str = ""
    max_connections: int = 1     # 最大连接数，-1表示无限制
    data_format: Optional[DataFormat] = None
    validation_schema: Optional[str] = None  # JSON Schema for validation

@dataclass
class OutputPortSpec:
    name: str
    type: str                    # ConnectionType
    description: str = ""
    max_connections: int = -1    # -1 = 无限制
    data_format: Optional[DataFormat] = None
    validation_schema: Optional[str] = None  # JSON Schema for validation

@dataclass
class NodeSpec:
    node_type: str
    subtype: str
    version: str = "1.0.0"
    description: str = ""
    parameters: List[ParameterDef] = None
    input_ports: List[InputPortSpec] = None
    output_ports: List[OutputPortSpec] = None
    examples: Optional[List[Dict[str, Any]]] = None
```

#### 参数类型
```python
class ParameterType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    JSON = "json"
    FILE = "file"
    URL = "url"
    EMAIL = "email"
    CRON_EXPRESSION = "cron"
```

#### 数据格式规范
```python
@dataclass
class DataFormat:
    mime_type: str = "application/json"
    schema: Optional[str] = None        # JSON Schema（已包含required字段定义）
    examples: Optional[List[str]] = None

@dataclass
class ConnectionSpec:
    """连接规范，定义两个端口间的数据映射规则"""
    source_port: str
    target_port: str
    connection_type: str             # ConnectionType
    data_mapping: Optional['DataMappingSpec'] = None
    validation_required: bool = True

@dataclass
class DataMappingSpec:
    """数据映射规范，定义端口间数据转换规则"""
    mapping_type: str                # DIRECT, FIELD_MAPPING, TEMPLATE, TRANSFORM
    field_mappings: Optional[List['FieldMappingSpec']] = None
    transform_script: Optional[str] = None
    static_values: Optional[Dict[str, str]] = None
    description: str = ""

@dataclass
class FieldMappingSpec:
    """字段映射规范"""
    source_field: str                # JSONPath格式的源字段路径
    target_field: str                # 目标字段路径
    required: bool = False
    default_value: Optional[str] = None
    transform: Optional['FieldTransformSpec'] = None

@dataclass
class FieldTransformSpec:
    """字段转换规范"""
    type: str                        # NONE, STRING_FORMAT, FUNCTION, CONDITION, REGEX
    transform_value: str
    options: Optional[Dict[str, str]] = None
```

## 📝 规范示例

### 🤖 AI代理节点规范 (革新版本)

#### 新的供应商驱动方法
不再使用固定角色（如 ROUTER_AGENT），现在采用基于供应商的节点，功能通过系统提示词定义：

```python
# 旧方法：固定角色
"AI_AGENT_NODE.ROUTER_AGENT"
"AI_AGENT_NODE.TASK_ANALYZER"

# 新方法：灵活的供应商节点
"AI_AGENT_NODE.GEMINI_NODE"    # Google Gemini
"AI_AGENT_NODE.OPENAI_NODE"    # OpenAI GPT
"AI_AGENT_NODE.CLAUDE_NODE"    # Anthropic Claude
```

#### OpenAI节点规范示例
```python
OPENAI_NODE_SPEC = NodeSpec(
    node_type="AI_AGENT_NODE",
    subtype="OPENAI_NODE",
    description="OpenAI GPT AI agent with customizable behavior via system prompt",
    parameters=[
        ParameterDef(
            name="system_prompt",
            type=ParameterType.STRING,
            required=True,
            description="System prompt that defines the AI agent's role, behavior, and instructions"
        ),
        ParameterDef(
            name="model_version",
            type=ParameterType.ENUM,
            required=False,
            default_value="gpt-4",
            enum_values=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"],
            description="Specific OpenAI model version to use"
        ),
        ParameterDef(
            name="temperature",
            type=ParameterType.FLOAT,
            required=False,
            default_value="0.7",
            description="Controls randomness in AI responses (0.0 = deterministic, 1.0 = creative)",
            validation_pattern=r"^(0(\.\d+)?|1(\.0+)?)$"
        ),
        ParameterDef(
            name="max_tokens",
            type=ParameterType.INTEGER,
            required=False,
            default_value="2048",
            description="Maximum number of tokens in the AI response"
        ),
        # OpenAI-specific parameters
        ParameterDef(
            name="presence_penalty",
            type=ParameterType.FLOAT,
            required=False,
            default_value="0.0",
            description="Penalty for new topics (−2.0 to 2.0)",
            validation_pattern=r"^-?([01](\.\d+)?|2(\.0+)?)$"
        ),
        ParameterDef(
            name="frequency_penalty",
            type=ParameterType.FLOAT,
            required=False,
            default_value="0.0",
            description="Penalty for repeated content (−2.0 to 2.0)",
            validation_pattern=r"^-?([01](\.\d+)?|2(\.0+)?)$"
        )
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type="MAIN",
            required=True,
            description="Input data and context for the AI agent",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"message": "string", "context": "object", "variables": "object"}',
                examples=[
                    '{"message": "Analyze this data", "context": {"user_id": "123"}, "variables": {"data": [1,2,3]}}',
                    '{"message": "Route customer inquiry", "context": {"department": "support"}, "variables": {"urgency": "high"}}'
                ]
            ),
            validation_schema='{"type": "object", "properties": {"message": {"type": "string"}, "context": {"type": "object"}, "variables": {"type": "object"}}, "required": ["message"]}'
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type="MAIN",
            description="AI agent response and metadata",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"response": "string", "metadata": "object", "usage": "object", "processing_time": "number"}',
                examples=['{"response": "Based on the analysis...", "metadata": {"model": "gpt-4", "temperature": 0.7}, "usage": {"prompt_tokens": 50, "completion_tokens": 100}, "processing_time": 2.5}']
            ),
            validation_schema='{"type": "object", "properties": {"response": {"type": "string"}, "metadata": {"type": "object"}, "usage": {"type": "object"}, "processing_time": {"type": "number"}}, "required": ["response"]}'
        ),
        OutputPortSpec(
            name="error",
            type="ERROR",
            description="Error output when AI processing fails"
        )
    ],
    examples=[
        {
            "name": "Customer Service Router",
            "description": "Route customer inquiries to appropriate departments",
            "system_prompt": """You are a customer service routing assistant. Based on the customer's message, determine the appropriate department:
- "billing" for payment/invoice issues
- "technical" for product problems
- "sales" for new purchases
- "general" for everything else

Respond with JSON: {"department": "...", "confidence": 0.95, "reason": "..."}""",
            "input_example": {"message": "I need help with my invoice", "context": {"customer_tier": "premium"}},
            "expected_output": '{"department": "billing", "confidence": 0.98, "reason": "Customer mentioned invoice which is a billing matter"}'
        }
    ]
)
```

#### 系统提示词示例
通过系统提示词实现无限功能可能性：

```python
# 数据分析代理
data_analyst_prompt = """
你是高级数据分析师。分析提供的数据集：
1. 统计概览：均值、中位数、标准差
2. 趋势分析：识别模式和异常
3. 业务洞察：数据对业务决策的意义
4. 数据质量评估
5. 具体可行的建议

以结构化JSON格式输出，包含置信度评分。
"""

# 代码审查代理
code_reviewer_prompt = """
你是资深软件工程师，进行代码安全审查：
- 安全漏洞：SQL注入、XSS、命令注入
- 性能问题：算法复杂度、资源使用
- 最佳实践：代码风格、设计模式
- 潜在bug：逻辑错误、边界条件

提供具体的行号和改进建议。
"""
```

### 触发器节点规范
```python
CRON_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="CRON",
    description="基于Cron表达式的定时触发器",
    parameters=[
        ParameterDef(
            name="cron_expression",
            type=ParameterType.CRON_EXPRESSION,
            required=True,
            description="Cron时间表达式",
            validation_pattern=r"^(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)$"
        ),
        ParameterDef(
            name="timezone",
            type=ParameterType.STRING,
            required=False,
            default_value="UTC",
            description="时区设置"
        )
    ],
    input_ports=[],  # 触发器节点没有输入端口
    output_ports=[
        OutputPortSpec(
            name="main",
            type="MAIN",
            description="定时触发的输出数据",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"trigger_time": "string", "execution_id": "string"}'
            )
        )
    ]
)
```

### 流程控制节点规范
```python
IF_NODE_SPEC = NodeSpec(
    node_type="FLOW_NODE",
    subtype="IF",
    description="条件判断节点，根据条件选择执行分支",
    parameters=[
        ParameterDef(
            name="condition",
            type=ParameterType.STRING,
            required=True,
            description="判断条件表达式"
        ),
        ParameterDef(
            name="condition_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="javascript",
            enum_values=["javascript", "python", "jsonpath"],
            description="条件表达式类型"
        )
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type="MAIN",
            required=True,
            description="条件判断的输入数据"
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="true",
            type="MAIN",
            description="条件为真时的输出"
        ),
        OutputPortSpec(
            name="false",
            type="MAIN",
            description="条件为假时的输出"
        )
    ]
)
```

## 🔧 注册器系统

### 中央注册器
```python
class NodeSpecRegistry:
    def __init__(self):
        self._specs: Dict[str, NodeSpec] = {}
        self._port_compatibility_cache: Dict[str, bool] = {}
        self._load_all_specs()

    def get_spec(self, node_type: str, subtype: str) -> Optional[NodeSpec]:
        """获取节点规范"""
        key = f"{node_type}.{subtype}"
        return self._specs.get(key)

    def get_specs_by_type(self, node_type: str) -> List[NodeSpec]:
        """获取指定类型的所有规范"""
        return [spec for spec in self._specs.values() if spec.node_type == node_type]

    def validate_node(self, node) -> List[str]:
        """验证节点配置"""
        spec = self.get_spec(node.type, node.subtype)
        if not spec:
            return [f"未知节点类型: {node.type}.{node.subtype}"]

        return self._validate_against_spec(node, spec)

    def validate_connection(self, source_node, source_port: str,
                          target_node, target_port: str) -> List[str]:
        """验证端口连接兼容性"""
        errors = []

        source_spec = self.get_spec(source_node.type, source_node.subtype)
        target_spec = self.get_spec(target_node.type, target_node.subtype)

        if not source_spec or not target_spec:
            return ["无法找到节点规范进行连接验证"]

        # 查找源输出端口
        source_output_port = None
        for port in source_spec.output_ports:
            if port.name == source_port:
                source_output_port = port
                break

        if not source_output_port:
            errors.append(f"源节点 {source_node.id} 没有输出端口 '{source_port}'")
            return errors

        # 查找目标输入端口
        target_input_port = None
        for port in target_spec.input_ports:
            if port.name == target_port:
                target_input_port = port
                break

        if not target_input_port:
            errors.append(f"目标节点 {target_node.id} 没有输入端口 '{target_port}'")
            return errors

        # 验证端口类型兼容性
        if source_output_port.type != target_input_port.type:
            errors.append(f"端口类型不兼容: {source_output_port.type} -> {target_input_port.type}")

        return errors

    def get_port_spec(self, node_type: str, subtype: str,
                     port_name: str, port_direction: str) -> Optional[Union[InputPortSpec, OutputPortSpec]]:
        """获取特定端口的规范"""
        spec = self.get_spec(node_type, subtype)
        if not spec:
            return None

        ports = spec.input_ports if port_direction == "input" else spec.output_ports
        for port in ports:
            if port.name == port_name:
                return port

        return None

# 全局单例实例
node_spec_registry = NodeSpecRegistry()
```

### 验证系统
```python
class NodeSpecValidator:
    @staticmethod
    def validate_parameters(node, spec: NodeSpec) -> List[str]:
        """验证节点参数"""
        errors = []

        # 检查必需参数
        for param_def in spec.parameters:
            if param_def.required and param_def.name not in node.parameters:
                errors.append(f"缺少必需参数: {param_def.name}")
                continue

            # 验证参数类型和格式
            if param_def.name in node.parameters:
                value = node.parameters[param_def.name]
                param_errors = NodeSpecValidator._validate_parameter_value(value, param_def)
                errors.extend(param_errors)

        return errors

    @staticmethod
    def validate_ports(node, spec: NodeSpec) -> List[str]:
        """验证节点端口配置"""
        errors = []

        # 验证输入端口
        required_inputs = {p.name for p in spec.input_ports if p.required}
        actual_inputs = {p.name for p in getattr(node, 'input_ports', [])}

        missing_inputs = required_inputs - actual_inputs
        for missing in missing_inputs:
            errors.append(f"缺少必需的输入端口: {missing}")

        # 验证输出端口
        expected_outputs = {p.name for p in spec.output_ports}
        actual_outputs = {p.name for p in getattr(node, 'output_ports', [])}

        missing_outputs = expected_outputs - actual_outputs
        for missing in missing_outputs:
            errors.append(f"缺少预期的输出端口: {missing}")

        return errors

    @staticmethod
    def validate_port_data(port_spec: Union[InputPortSpec, OutputPortSpec],
                          data: Dict[str, Any]) -> List[str]:
        """验证端口数据格式"""
        errors = []

        if port_spec.validation_schema:
            try:
                import jsonschema
                import json

                schema = json.loads(port_spec.validation_schema)
                jsonschema.validate(data, schema)
            except jsonschema.ValidationError as e:
                errors.append(f"数据格式验证失败: {e.message}")
            except Exception as e:
                errors.append(f"Schema验证错误: {str(e)}")

        # 必需字段验证已包含在validation_schema中，此处不需要重复检查

        return errors

    @staticmethod
    def _has_field(data: Dict[str, Any], field_path: str) -> bool:
        """检查数据中是否存在指定字段"""
        try:
            keys = field_path.split('.')
            current = data
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return False
            return True
        except:
            return False

    @staticmethod
    def _validate_parameter_value(value: str, param_def: ParameterDef) -> List[str]:
        """验证参数值"""
        errors = []

        if param_def.type == ParameterType.INTEGER:
            try:
                int(value)
            except ValueError:
                errors.append(f"参数 {param_def.name} 必须是整数")

        elif param_def.type == ParameterType.FLOAT:
            try:
                float(value)
            except ValueError:
                errors.append(f"参数 {param_def.name} 必须是浮点数")

        elif param_def.type == ParameterType.BOOLEAN:
            if value.lower() not in ['true', 'false', '1', '0']:
                errors.append(f"参数 {param_def.name} 必须是布尔值")

        elif param_def.type == ParameterType.ENUM:
            if param_def.enum_values and value not in param_def.enum_values:
                errors.append(f"参数 {param_def.name} 必须是以下值之一: {param_def.enum_values}")

        elif param_def.type == ParameterType.JSON:
            try:
                import json
                json.loads(value)
            except json.JSONDecodeError:
                errors.append(f"参数 {param_def.name} 必须是有效的JSON")

        # 验证正则表达式模式
        if param_def.validation_pattern:
            import re
            if not re.match(param_def.validation_pattern, value):
                errors.append(f"参数 {param_def.name} 格式不正确")

        return errors
```

## 🔗 集成点

### Protocol Buffer Schema更新

为了支持统一的端口系统，需要更新 `apps/backend/shared/proto/engine/workflow.proto`:

```protobuf
// 端口定义 - 基于NodeSpec生成
message InputPort {
  string name = 1;           // 端口名称
  string type = 2;           // ConnectionType
  bool required = 3;         // 是否必需
  string description = 4;    // 端口描述
  int32 max_connections = 5; // 最大连接数
  string validation_schema = 6; // JSON Schema验证
}

message OutputPort {
  string name = 1;           // 端口名称
  string type = 2;           // ConnectionType
  string description = 3;    // 端口描述
  int32 max_connections = 4; // 最大连接数
  string validation_schema = 5; // JSON Schema验证
}

// 增强的节点定义
message Node {
  string id = 1;
  string name = 2;
  NodeType type = 3;
  NodeSubtype subtype = 4;
  int32 type_version = 5;
  Position position = 6;
  bool disabled = 7;
  map<string, string> parameters = 8;
  map<string, string> credentials = 9;
  ErrorHandling on_error = 10;
  RetryPolicy retry_policy = 11;
  map<string, string> notes = 12;
  repeated string webhooks = 13;

  // 端口定义 - 基于NodeSpec自动生成
  repeated InputPort input_ports = 14;
  repeated OutputPort output_ports = 15;
}

// 增强的连接定义 - 支持数据映射
message Connection {
  string node = 1;              // 目标节点名
  ConnectionType type = 2;      // 连接类型
  int32 index = 3;             // 端口索引（向后兼容）
  string source_port = 4;      // 源端口名称
  string target_port = 5;      // 目标端口名称
  DataMapping data_mapping = 6; // 数据映射规则
}

// 数据映射定义
message DataMapping {
  MappingType type = 1;
  repeated FieldMapping field_mappings = 2;
  string transform_script = 3;
  map<string, string> static_values = 4;
  string description = 5;
}

enum MappingType {
  DIRECT = 0;
  FIELD_MAPPING = 1;
  TEMPLATE = 2;
  TRANSFORM = 3;
}

message FieldMapping {
  string source_field = 1;
  string target_field = 2;
  FieldTransform transform = 3;
  bool required = 4;
  string default_value = 5;
}

message FieldTransform {
  TransformType type = 1;
  string transform_value = 2;
  map<string, string> options = 3;
}

enum TransformType {
  NONE = 0;
  STRING_FORMAT = 1;
  JSON_PATH = 2;
  REGEX = 3;
  FUNCTION = 4;
  CONDITION = 5;
}
```

### 工作流引擎集成
```python
# 在BaseNodeExecutor中
class BaseNodeExecutor(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.spec = self._get_node_spec()

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """获取此执行器的规范"""
        # 派生类应该实现此方法或使用注册器
        return None

    def validate(self, node: Any) -> List[str]:
        """根据规范验证节点"""
        if self.spec:
            return node_spec_registry.validate_node(node)
        return []

    def get_input_port_specs(self) -> List[InputPortSpec]:
        """获取输入端口规范"""
        return self.spec.input_ports if self.spec else []

    def get_output_port_specs(self) -> List[OutputPortSpec]:
        """获取输出端口规范"""
        return self.spec.output_ports if self.spec else []

    def validate_input_data(self, port_name: str, data: Dict[str, Any]) -> List[str]:
        """验证输入端口数据"""
        if not self.spec:
            return []

        port_spec = None
        for port in self.spec.input_ports:
            if port.name == port_name:
                port_spec = port
                break

        if not port_spec:
            return [f"未知输入端口: {port_name}"]

        return NodeSpecValidator.validate_port_data(port_spec, data)

# 在具体执行器中
class AIAgentNodeExecutor(BaseNodeExecutor):
    def __init__(self, node_subtype: str):
        self.node_subtype = node_subtype
        super().__init__()

    def _get_node_spec(self) -> Optional[NodeSpec]:
        return node_spec_registry.get_spec("AI_AGENT_NODE", self.node_subtype)
```

### 连接验证器增强
```python
class WorkflowValidator:
    def __init__(self):
        self.node_registry = node_spec_registry
        self.data_mapper = DataMappingProcessor()

    def validate_workflow(self, workflow) -> List[str]:
        """验证完整工作流"""
        errors = []

        # 验证节点配置
        for node in workflow.nodes:
            node_errors = self.validate_node(node)
            errors.extend(node_errors)

        # 验证连接
        connection_errors = self.validate_connections(workflow)
        errors.extend(connection_errors)

        return errors

    def validate_node(self, node) -> List[str]:
        """验证单个节点"""
        return self.node_registry.validate_node(node)

    def validate_connections(self, workflow) -> List[str]:
        """验证节点连接"""
        errors = []

        for node_name, node_connections in workflow.connections.connections.items():
            source_node = self._find_node_by_name(workflow.nodes, node_name)
            if not source_node:
                continue

            for connection_type, connection_array in node_connections.connection_types.items():
                for connection in connection_array.connections:
                    target_node = self._find_node_by_name(workflow.nodes, connection.node)
                    if not target_node:
                        errors.append(f"连接目标节点不存在: {connection.node}")
                        continue

                    # 验证端口连接
                    source_port = getattr(connection, 'source_port', 'main')
                    target_port = getattr(connection, 'target_port', 'main')

                    port_errors = self.node_registry.validate_connection(
                        source_node, source_port, target_node, target_port
                    )
                    errors.extend(port_errors)

                    # 验证数据映射
                    if hasattr(connection, 'data_mapping') and connection.data_mapping:
                        mapping_errors = self._validate_data_mapping(
                            source_node, target_node, connection.data_mapping
                        )
                        errors.extend(mapping_errors)

        return errors

    def _validate_data_mapping(self, source_node, target_node, data_mapping) -> List[str]:
        """验证数据映射配置"""
        errors = []

        # 这里可以添加数据映射规则的验证逻辑
        # 例如验证字段路径、转换脚本语法等

        return errors
```

### API网关集成
```python
@router.get("/node-types")
async def get_node_types():
    """获取所有节点类型和子类型"""
    result = {}
    for spec in node_spec_registry.list_all_specs():
        if spec.node_type not in result:
            result[spec.node_type] = []
        result[spec.node_type].append({
            "subtype": spec.subtype,
            "description": spec.description
        })
    return result

@router.get("/node-types/{node_type}/{subtype}/spec")
async def get_node_spec(node_type: str, subtype: str):
    """获取特定节点的详细规范"""
    spec = node_spec_registry.get_spec(node_type, subtype)
    if not spec:
        raise HTTPException(404, "未找到节点规范")

    return {
        "type": spec.node_type,
        "subtype": spec.subtype,
        "description": spec.description,
        "version": spec.version,
        "parameters": [
            {
                "name": p.name,
                "type": p.type.value,
                "required": p.required,
                "default_value": p.default_value,
                "description": p.description,
                "enum_values": p.enum_values,
                "validation_pattern": p.validation_pattern
            }
            for p in spec.parameters
        ],
        "input_ports": [
            {
                "name": p.name,
                "type": p.type,
                "required": p.required,
                "description": p.description,
                "max_connections": p.max_connections,
                "data_format": p.data_format.__dict__ if p.data_format else None,
                "validation_schema": p.validation_schema
            }
            for p in spec.input_ports
        ],
        "output_ports": [
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "max_connections": p.max_connections,
                "data_format": p.data_format.__dict__ if p.data_format else None,
                "validation_schema": p.validation_schema
            }
            for p in spec.output_ports
        ],
        "examples": spec.examples
    }

@router.post("/workflows/{workflow_id}/validate")
async def validate_workflow(workflow_id: str, workflow_data: dict):
    """验证工作流配置"""
    validator = WorkflowValidator()
    errors = validator.validate_workflow(workflow_data)

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

@router.post("/connections/validate")
async def validate_connection(
    source_node_type: str,
    source_subtype: str,
    source_port: str,
    target_node_type: str,
    target_subtype: str,
    target_port: str
):
    """验证端口连接兼容性"""
    # 模拟节点对象
    source_node = type('Node', (), {
        'type': source_node_type,
        'subtype': source_subtype,
        'id': 'source'
    })()

    target_node = type('Node', (), {
        'type': target_node_type,
        'subtype': target_subtype,
        'id': 'target'
    })()

    errors = node_spec_registry.validate_connection(
        source_node, source_port, target_node, target_port
    )

    return {
        "compatible": len(errors) == 0,
        "errors": errors
    }
```

### 前端集成
```typescript
// 前端现在可以获取结构化的节点规范
interface NodeSpec {
  type: string;
  subtype: string;
  description: string;
  parameters: ParameterDef[];
  input_ports: PortSpec[];
  output_ports: PortSpec[];
}

// 基于规范自动生成表单
function generateNodeConfigForm(spec: NodeSpec) {
  return spec.parameters.map(param => {
    switch (param.type) {
      case 'enum':
        return <Select options={param.enum_values} required={param.required} />;
      case 'boolean':
        return <Checkbox defaultValue={param.default_value} />;
      case 'integer':
        return <NumberInput required={param.required} />;
      // ... 其他类型
    }
  });
}
```

## 📊 完整节点类型覆盖

### 计划规范

| 节点类型 | 子类型 | 状态 | 备注 |
|---------|--------|------|------|
| **TRIGGER_NODE** | MANUAL, WEBHOOK, CRON, CHAT, EMAIL, FORM, CALENDAR | ✅ 已实现 | 事件触发器 |
| **AI_AGENT_NODE** | GEMINI_NODE, OPENAI_NODE, CLAUDE_NODE | 🚀 **已革新** | **基于供应商的提示词驱动节点** |
| **ACTION_NODE** | RUN_CODE, HTTP_REQUEST, PARSE_IMAGE, WEB_SEARCH, DATABASE_OPERATION, FILE_OPERATION, DATA_TRANSFORMATION | ✅ 已实现 | 操作执行节点 |
| **FLOW_NODE** | IF, FILTER, LOOP, MERGE, SWITCH, WAIT | ✅ 已实现 | 流程控制节点 |
| **TOOL_NODE** | GOOGLE_CALENDAR_MCP, NOTION_MCP, CALENDAR, EMAIL, HTTP, CODE_EXECUTION | ⚠️ 计划中 | 工具集成节点 |
| **MEMORY_NODE** | SIMPLE, BUFFER, KNOWLEDGE, VECTOR_STORE, DOCUMENT, EMBEDDING | ⚠️ 计划中 | 记忆存储节点 |
| **HUMAN_IN_THE_LOOP_NODE** | GMAIL, SLACK, DISCORD, TELEGRAM, APP | ⚠️ 计划中 | 人机交互节点 |

### 🔥 AI代理节点革新说明

#### 旧方案问题
- ❌ 固定角色限制：`ROUTER_AGENT`, `TASK_ANALYZER`, `REPORT_GENERATOR` 等
- ❌ 功能受限于预定义逻辑
- ❌ 新需求需要编写新代码
- ❌ 无法充分利用不同AI供应商的特性

#### 新方案优势
- ✅ **供应商驱动**：基于 Gemini、OpenAI、Claude 三大供应商
- ✅ **提示词定义**：通过 `system_prompt` 参数实现任意功能
- ✅ **供应商特化**：每个供应商都有特定参数优化
- ✅ **无限扩展**：通过提示词创新实现任何AI任务

#### 供应商特性对比

| 供应商 | 模型版本 | 特殊能力 | 独有参数 |
|--------|----------|----------|----------|
| **GEMINI_NODE** | gemini-pro, gemini-pro-vision, gemini-ultra | 🎯 多模态、视觉处理 | safety_settings |
| **OPENAI_NODE** | gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o | 🧠 推理、结构化输出 | presence_penalty, frequency_penalty |
| **CLAUDE_NODE** | claude-3-haiku, claude-3-sonnet, claude-3-opus | 📚 长上下文、精确控制 | stop_sequences |

## 🚀 实施计划

### 第一阶段：基础架构与端口系统 (第1-2周)

#### Protocol Buffer更新
- [ ] 更新 `workflow.proto` 添加端口定义和数据映射消息
- [ ] 重新生成Python protobuf文件
- [ ] 更新现有Node和Connection消息结构

#### 节点规范系统
- [ ] 在 `shared/node_specs/base.py` 中创建基础规范类（包含端口规范）
- [ ] 在 `shared/node_specs/registry.py` 中实现注册器系统
- [ ] 在 `shared/node_specs/validator.py` 中创建验证框架
- [ ] 为基础功能建立单元测试

#### 端口系统集成
- [ ] 更新BaseNodeExecutor类集成端口规范
- [ ] 实现端口兼容性验证逻辑
- [ ] 创建端口数据验证器

### 第二阶段：核心节点规范定义 (第3周)
- [ ] 定义 TRIGGER_NODE 子类型规范
- [ ] 定义 AI_AGENT_NODE 子类型规范
- [ ] 定义 ACTION_NODE 子类型规范
- [ ] 定义 FLOW_NODE 子类型规范

### 第三阶段：其余规范与数据映射 (第4周)
- [ ] 定义 TOOL_NODE 子类型规范
- [ ] 定义 MEMORY_NODE 子类型规范
- [ ] 定义 HUMAN_IN_THE_LOOP_NODE 子类型规范
- [ ] 实现缺失的 EXTERNAL_ACTION_NODE 子类型

### 第四阶段：数据映射系统 (第5周)
- [ ] 实现DataMappingProcessor类
- [ ] 集成字段映射、模板转换、脚本转换
- [ ] 更新ConnectionExecutor支持数据映射
- [ ] 添加数据转换的监控和调试工具

### 第五阶段：完整集成 (第6周)
- [ ] 更新 BaseNodeExecutor 以使用规范
- [ ] 更新所有现有节点执行器
- [ ] 添加规范查询的API端点
- [ ] 更新工作流验证器以使用规范
- [ ] 创建现有工作流的迁移指南

### 第六阶段：文档和测试 (第7周)
- [ ] 编写全面的文档
- [ ] 创建规范示例和模板
- [ ] 添加集成测试
- [ ] 性能测试和优化

## 🧪 测试策略

### 单元测试
- 参数验证逻辑
- 端口规范验证
- 注册器功能
- 个别节点规范

### 集成测试
- 使用规范的工作流验证
- API端点功能
- 节点执行器集成
- 前端表单生成

### 测试数据
```python
# 测试示例
def test_router_agent_validation():
    node = create_test_node(
        type="AI_AGENT_NODE",
        subtype="ROUTER_AGENT",
        parameters={
            "prompt": "路由用户请求",
            "routing_options": {"support": "tech", "sales": "sales"}
            # 缺少temperature（可选，有默认值）
        }
    )

    errors = node_spec_registry.validate_node(node)
    assert len(errors) == 0  # 应该通过验证

def test_missing_required_parameter():
    node = create_test_node(
        type="AI_AGENT_NODE",
        subtype="ROUTER_AGENT",
        parameters={}  # 缺少必需参数
    )

    errors = node_spec_registry.validate_node(node)
    assert "缺少必需参数: prompt" in errors
    assert "缺少必需参数: routing_options" in errors
```

## 📈 优势

### 对开发者
1. **类型安全**: 完整的IDE支持和自动补全
2. **清晰文档**: 每个参数和端口都有文档
3. **验证**: 早期发现配置错误
4. **一致性**: 所有节点类型的标准化方法

### 对用户
1. **更好的UI**: 自动生成带验证的表单
2. **清晰指导**: 全面的参数描述和示例
3. **错误预防**: 在执行前捕获无效配置
4. **可发现性**: 容易探索可用的节点类型和功能

### 对系统
1. **可维护性**: 集中的规范管理
2. **可扩展性**: 容易添加新节点类型和参数
3. **一致性**: 所有节点的统一验证和行为
4. **性能**: 快速的内存访问规范

## 🔄 迁移策略

### 向后兼容
- 现有工作流继续正常工作
- 逐步迁移到使用规范
- 对现有API无破坏性更改

### 迁移步骤
1. **与现有代码一起部署规范**
2. **更新验证器使用规范（带回退）**
3. **添加基于规范的API端点**
4. **更新前端使用新端点**
5. **弃用旧的参数验证逻辑**

## 🎯 成功指标

### 开发指标
- [ ] 100%覆盖现有节点类型/子类型
- [ ] 少于100ms规范查找性能
- [ ] 迁移期间零破坏性更改
- [ ] 规范系统90%+测试覆盖率

### 用户体验指标
- [ ] 所有节点类型的自动生成表单
- [ ] 全面的验证错误消息
- [ ] 交互式API文档
- [ ] 开发者入门时间减少

---

**文档版本**: 1.0
**创建时间**: 2025-01-28
**作者**: Claude Code
**状态**: 设计阶段
**下次审查**: 2025-02-04
