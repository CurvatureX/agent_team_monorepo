# 节点规范系统使用指南

## 概述

节点规范系统 (`node_specs`) 提供了一个统一的方式来定义、验证和使用工作流节点。它确保了不同服务之间的一致性，并提供了类型安全和自动化验证功能。

## 核心组件

### 1. NodeSpec - 节点规范定义
```python
from shared.node_specs.base import NodeSpec, ParameterDef, ParameterType

# 每个节点都有完整的规范定义
spec = NodeSpec(
    node_type="AI_AGENT_NODE",
    subtype="OPENAI_NODE",
    description="OpenAI GPT model agent",
    parameters=[...],
    input_ports=[...],
    output_ports=[...]
)
```

### 2. NodeSpecRegistry - 规范注册表
```python
from shared.node_specs import node_spec_registry

# 获取特定节点的规范
spec = node_spec_registry.get_spec("AI_AGENT_NODE", "OPENAI_NODE")

# 列出所有可用的节点规范
all_specs = node_spec_registry.list_all_specs()
```

### 3. NodeSpecValidator - 验证器
```python
# 验证节点配置
errors = node_spec_registry.validate_node(node)
if errors:
    print(f"Validation errors: {errors}")
```

## 使用场景

### 场景1: 在 Workflow Engine 中验证节点

**位置**: `workflow_engine/nodes/`

```python
# 在节点执行器中使用规范
class AIAgentNodeExecutor(BaseNodeExecutor):
    def _get_node_spec(self):
        if node_spec_registry and self.subtype:
            return node_spec_registry.get_spec("AI_AGENT_NODE", self.subtype)
        return None
    
    def validate(self, node):
        # 使用规范系统进行验证
        if node_spec_registry:
            return node_spec_registry.validate_node(node)
        return []
    
    def execute(self, context):
        spec = self._get_node_spec()
        if spec:
            # 使用规范中的默认值
            temperature = context.get_parameter(
                "temperature", 
                spec.get_parameter("temperature").default_value
            )
```

### 场景2: 在 Workflow Agent 中生成节点配置

**位置**: `workflow_agent/agents/`

```python
def generate_node_config(node_type: str, subtype: str) -> Dict:
    """根据规范生成节点配置"""
    spec = node_spec_registry.get_spec(node_type, subtype)
    if not spec:
        raise ValueError(f"Unknown node type: {node_type}.{subtype}")
    
    config = {
        "type": node_type,
        "subtype": subtype,
        "parameters": {}
    }
    
    # 填充默认参数
    for param in spec.parameters:
        if param.default_value is not None:
            config["parameters"][param.name] = param.default_value
    
    return config
```

### 场景3: 在 API Gateway 中验证请求

**位置**: `api-gateway/app/api/`

```python
from shared.node_specs import node_spec_registry

async def create_workflow(request: CreateWorkflowRequest):
    """创建工作流前验证所有节点"""
    errors = []
    
    for node in request.nodes:
        # 使用规范验证节点
        node_errors = node_spec_registry.validate_node(node)
        if node_errors:
            errors.extend([f"Node {node.id}: {e}" for e in node_errors])
    
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})
    
    # 继续创建工作流...
```

### 场景4: 生成 API 文档

```python
def generate_api_docs():
    """自动生成节点 API 文档"""
    docs = []
    
    for spec_key, spec in node_spec_registry.list_all_specs().items():
        doc = {
            "type": spec.node_type,
            "subtype": spec.subtype,
            "description": spec.description,
            "parameters": []
        }
        
        for param in spec.parameters:
            param_doc = {
                "name": param.name,
                "type": param.type.value,
                "required": param.required,
                "default": param.default_value,
                "description": param.description
            }
            if param.enum_values:
                param_doc["enum"] = param.enum_values
            doc["parameters"].append(param_doc)
        
        docs.append(doc)
    
    return docs
```

### 场景5: 前端表单生成

```python
def get_node_form_schema(node_type: str, subtype: str):
    """为前端生成表单 schema"""
    spec = node_spec_registry.get_spec(node_type, subtype)
    if not spec:
        return None
    
    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    for param in spec.parameters:
        prop = {
            "title": param.name.replace("_", " ").title(),
            "description": param.description
        }
        
        if param.type == ParameterType.STRING:
            prop["type"] = "string"
        elif param.type == ParameterType.INTEGER:
            prop["type"] = "integer"
        elif param.type == ParameterType.FLOAT:
            prop["type"] = "number"
        elif param.type == ParameterType.BOOLEAN:
            prop["type"] = "boolean"
        elif param.type == ParameterType.ENUM:
            prop["type"] = "string"
            prop["enum"] = param.enum_values
        
        if param.default_value is not None:
            prop["default"] = param.default_value
        
        schema["properties"][param.name] = prop
        
        if param.required:
            schema["required"].append(param.name)
    
    return schema
```

## 最佳实践

### 1. 始终使用规范验证

```python
# ❌ 不要硬编码验证逻辑
if "system_prompt" not in node.parameters:
    errors.append("Missing system_prompt")

# ✅ 使用规范系统
errors = node_spec_registry.validate_node(node)
```

### 2. 利用默认值

```python
# ❌ 不要硬编码默认值
temperature = node.parameters.get("temperature", 0.7)

# ✅ 从规范获取默认值
spec = node_spec_registry.get_spec(node.type, node.subtype)
param_def = spec.get_parameter("temperature")
temperature = node.parameters.get("temperature", param_def.default_value)
```

### 3. 类型转换

```python
# 使用规范进行类型转换
def convert_parameter_value(value: Any, param_def: ParameterDef) -> Any:
    if param_def.type == ParameterType.INTEGER:
        return int(value)
    elif param_def.type == ParameterType.FLOAT:
        return float(value)
    elif param_def.type == ParameterType.BOOLEAN:
        return bool(value)
    elif param_def.type == ParameterType.JSON:
        return json.loads(value) if isinstance(value, str) else value
    return value
```

### 4. 动态加载规范

```python
# 在服务启动时自动加载所有规范
def on_startup():
    # 规范会自动从 definitions/ 目录加载
    spec_count = len(node_spec_registry.list_all_specs())
    logger.info(f"Loaded {spec_count} node specifications")
```

## 扩展节点规范

### 添加新节点类型

1. 在 `definitions/` 目录创建或修改文件：

```python
# definitions/my_custom_nodes.py
from ..base import NodeSpec, ParameterDef, ParameterType

MY_CUSTOM_NODE = NodeSpec(
    node_type="CUSTOM_NODE",
    subtype="MY_SUBTYPE",
    description="My custom node",
    parameters=[
        ParameterDef(
            name="custom_param",
            type=ParameterType.STRING,
            required=True,
            description="A custom parameter"
        )
    ]
)
```

2. 规范会自动被注册表加载

### 添加自定义验证

```python
class CustomValidator:
    @staticmethod
    def validate_custom_logic(node, spec: NodeSpec) -> List[str]:
        errors = []
        
        # 基础规范验证
        errors.extend(node_spec_registry.validate_node(node))
        
        # 自定义业务逻辑验证
        if node.subtype == "MY_SUBTYPE":
            custom_param = node.parameters.get("custom_param")
            if custom_param and len(custom_param) < 10:
                errors.append("custom_param must be at least 10 characters")
        
        return errors
```

## 故障排除

### 问题1: 找不到节点规范

```python
spec = node_spec_registry.get_spec("NODE_TYPE", "SUBTYPE")
if spec is None:
    # 检查是否正确加载
    all_specs = node_spec_registry.list_all_specs()
    print(f"Available specs: {list(all_specs.keys())}")
```

### 问题2: 验证总是失败

```python
# 调试验证错误
node = MyNode(...)
errors = node_spec_registry.validate_node(node)
for error in errors:
    print(f"Validation error: {error}")

# 检查节点结构
print(f"Node type: {node.type}")
print(f"Node subtype: {node.subtype}")
print(f"Node parameters: {node.parameters}")
```

### 问题3: 默认值不生效

```python
# 确保正确获取参数定义
spec = node_spec_registry.get_spec(node_type, subtype)
param_def = spec.get_parameter("param_name")
if param_def:
    print(f"Default value: {param_def.default_value}")
    print(f"Type: {param_def.type}")
```

## 总结

节点规范系统提供了：
- 📋 **统一的节点定义** - 所有服务使用相同的节点规范
- ✅ **自动化验证** - 减少手动验证代码
- 📚 **自动文档生成** - 保持文档与代码同步
- 🔒 **类型安全** - 确保参数类型正确
- 🚀 **更好的开发体验** - 清晰的错误信息和默认值

通过使用这个系统，我们确保了整个工作流平台的一致性和可靠性。