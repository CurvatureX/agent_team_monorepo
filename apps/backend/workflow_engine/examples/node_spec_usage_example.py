"""
节点规范系统使用示例

这个示例展示了如何在 Workflow Engine 中使用节点规范系统来：
1. 验证节点配置
2. 自动生成参数文档
3. 创建类型安全的节点
4. 在运行时进行参数验证
"""

import json
from typing import Dict, Any, List
from shared.node_specs import node_spec_registry
from workflow_engine.nodes.base import BaseNodeExecutor, NodeExecutionContext


# ===== 场景1: 在节点执行器中使用规范进行验证 =====

class ImprovedAIAgentNodeExecutor(BaseNodeExecutor):
    """改进版的AI节点执行器，完全集成节点规范"""
    
    def __init__(self):
        super().__init__()
        self.subtype = None
    
    def _get_node_spec(self):
        """动态获取当前子类型的节点规范"""
        if self.subtype and node_spec_registry:
            return node_spec_registry.get_spec("AI_AGENT_NODE", self.subtype)
        return None
    
    def validate(self, node: Any) -> List[str]:
        """使用节点规范进行完整验证"""
        self.subtype = node.subtype
        
        # 使用规范系统进行验证
        if node_spec_registry:
            errors = node_spec_registry.validate_node(node)
            if errors:
                return errors
        
        # 额外的业务逻辑验证
        if node.subtype == "OPENAI_NODE":
            # 检查API密钥是否配置
            import os
            if not os.getenv("OPENAI_API_KEY"):
                return ["OpenAI API key not configured"]
        
        return []
    
    def execute(self, context: NodeExecutionContext):
        """执行时使用规范验证参数"""
        # 获取规范
        spec = self._get_node_spec()
        if spec:
            # 使用规范中的默认值
            temperature = context.get_parameter("temperature", 
                spec.get_parameter("temperature").default_value)
            max_tokens = context.get_parameter("max_tokens",
                spec.get_parameter("max_tokens").default_value)
            
            # 验证参数范围
            if temperature < 0 or temperature > 1:
                return self._create_error_result("Temperature must be between 0 and 1")
        
        # 继续执行...
        return self._create_success_result({"status": "executed"})


# ===== 场景2: 创建工作流时使用规范生成正确的节点配置 =====

def create_ai_workflow_with_specs():
    """使用节点规范创建类型安全的工作流"""
    
    # 1. 获取节点规范
    openai_spec = node_spec_registry.get_spec("AI_AGENT_NODE", "OPENAI_NODE")
    http_spec = node_spec_registry.get_spec("ACTION_NODE", "HTTP_REQUEST")
    
    # 2. 根据规范创建节点配置
    nodes = []
    
    # 创建 OpenAI 节点
    openai_node = {
        "id": "ai-1",
        "name": "DataAnalyzer",
        "type": "AI_AGENT_NODE",
        "subtype": "OPENAI_NODE",
        "parameters": {}
    }
    
    # 从规范中填充默认参数
    for param in openai_spec.parameters:
        if param.default_value is not None:
            openai_node["parameters"][param.name] = param.default_value
    
    # 设置必需参数
    openai_node["parameters"]["system_prompt"] = """
    You are a data analyst. Analyze the provided data and return insights in JSON format:
    {
        "summary": "brief summary",
        "key_findings": ["finding1", "finding2"],
        "recommendations": ["rec1", "rec2"]
    }
    """
    
    nodes.append(openai_node)
    
    # 创建 HTTP 节点
    http_node = {
        "id": "http-1",
        "name": "SendResults",
        "type": "ACTION_NODE",
        "subtype": "HTTP_REQUEST",
        "parameters": {
            "url": "https://api.example.com/results",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "timeout": 30
        }
    }
    
    nodes.append(http_node)
    
    # 3. 验证节点配置
    for node in nodes:
        node_obj = type('Node', (), node)()  # 创建简单对象
        errors = node_spec_registry.validate_node(node_obj)
        if errors:
            print(f"Validation errors for {node['name']}: {errors}")
        else:
            print(f"✅ Node {node['name']} is valid")
    
    # 4. 创建工作流
    workflow = {
        "name": "Data Analysis Pipeline",
        "nodes": nodes,
        "connections": {
            "connections": {
                "DataAnalyzer": {
                    "connection_types": {
                        "main": {
                            "connections": [{
                                "node": "SendResults",
                                "type": "MAIN"
                            }]
                        }
                    }
                }
            }
        }
    }
    
    return workflow


# ===== 场景3: 动态参数验证和类型转换 =====

class ParameterValidator:
    """使用节点规范进行参数验证的工具类"""
    
    @staticmethod
    def validate_and_convert_parameters(node_type: str, subtype: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证并转换参数到正确的类型"""
        spec = node_spec_registry.get_spec(node_type, subtype)
        if not spec:
            raise ValueError(f"No spec found for {node_type}.{subtype}")
        
        validated_params = {}
        
        for param_def in spec.parameters:
            param_name = param_def.name
            param_value = params.get(param_name, param_def.default_value)
            
            # 检查必需参数
            if param_def.required and param_value is None:
                raise ValueError(f"Required parameter '{param_name}' is missing")
            
            # 类型转换
            if param_value is not None:
                if param_def.type.value == "integer":
                    validated_params[param_name] = int(param_value)
                elif param_def.type.value == "float":
                    validated_params[param_name] = float(param_value)
                elif param_def.type.value == "boolean":
                    validated_params[param_name] = bool(param_value)
                elif param_def.type.value == "json":
                    if isinstance(param_value, str):
                        validated_params[param_name] = json.loads(param_value)
                    else:
                        validated_params[param_name] = param_value
                else:
                    validated_params[param_name] = param_value
                
                # 枚举验证
                if param_def.enum_values and param_value not in param_def.enum_values:
                    raise ValueError(f"Parameter '{param_name}' must be one of {param_def.enum_values}")
        
        return validated_params


# ===== 场景4: API端点中使用规范 =====

from fastapi import HTTPException

async def validate_node_request(node_data: Dict[str, Any]):
    """在API端点中验证节点请求"""
    
    # 创建临时节点对象
    class TempNode:
        def __init__(self, data):
            self.type = data.get("type")
            self.subtype = data.get("subtype")
            self.parameters = data.get("parameters", {})
    
    node = TempNode(node_data)
    
    # 使用规范验证
    errors = node_spec_registry.validate_node(node)
    if errors:
        raise HTTPException(status_code=400, detail={
            "error": "Invalid node configuration",
            "details": errors
        })
    
    return {"status": "valid", "node": node_data}


# ===== 场景5: 生成参数文档 =====

def generate_node_documentation(node_type: str, subtype: str) -> str:
    """根据节点规范自动生成文档"""
    spec = node_spec_registry.get_spec(node_type, subtype)
    if not spec:
        return "No specification found"
    
    doc = f"# {node_type}.{subtype}\n\n"
    doc += f"{spec.description}\n\n"
    doc += "## Parameters\n\n"
    doc += "| Name | Type | Required | Default | Description |\n"
    doc += "|------|------|----------|---------|-------------|\n"
    
    for param in spec.parameters:
        required = "Yes" if param.required else "No"
        default = param.default_value if param.default_value is not None else "-"
        
        # 处理枚举类型
        param_type = param.type.value
        if param.enum_values:
            param_type = f"enum({', '.join(param.enum_values)})"
        
        doc += f"| {param.name} | {param_type} | {required} | {default} | {param.description} |\n"
    
    # 添加端口信息
    if spec.input_ports:
        doc += "\n## Input Ports\n\n"
        for port in spec.input_ports:
            doc += f"- **{port.name}** ({port.type}): {port.description}\n"
    
    if spec.output_ports:
        doc += "\n## Output Ports\n\n"
        for port in spec.output_ports:
            doc += f"- **{port.name}** ({port.type}): {port.description}\n"
    
    return doc


# ===== 场景6: 工作流验证服务 =====

class WorkflowValidationService:
    """使用节点规范验证整个工作流"""
    
    @staticmethod
    def validate_workflow(workflow: Dict[str, Any]) -> List[str]:
        """验证工作流中的所有节点"""
        errors = []
        
        # 验证每个节点
        for node in workflow.get("nodes", []):
            node_id = node.get("id", "unknown")
            
            # 创建节点对象
            class NodeObj:
                def __init__(self, n):
                    self.type = n.get("type")
                    self.subtype = n.get("subtype")
                    self.parameters = n.get("parameters", {})
                    self.name = n.get("name", "")
            
            node_obj = NodeObj(node)
            
            # 使用规范验证
            node_errors = node_spec_registry.validate_node(node_obj)
            for error in node_errors:
                errors.append(f"Node {node_id}: {error}")
        
        # 验证连接
        connections = workflow.get("connections", {})
        for source_name, conn_data in connections.items():
            # 查找源节点
            source_node = next((n for n in workflow["nodes"] if n.get("name") == source_name), None)
            if not source_node:
                errors.append(f"Connection source '{source_name}' not found in nodes")
                continue
            
            # 获取源节点规范
            source_spec = node_spec_registry.get_spec(
                source_node.get("type"), 
                source_node.get("subtype")
            )
            
            if source_spec:
                # 验证输出端口
                for conn_type, conns in conn_data.get("connection_types", {}).items():
                    output_port = next((p for p in source_spec.output_ports if p.name == conn_type), None)
                    if not output_port:
                        errors.append(f"Node {source_name} does not have output port '{conn_type}'")
        
        return errors


# ===== 使用示例 =====

if __name__ == "__main__":
    print("=== 节点规范系统使用示例 ===\n")
    
    # 1. 创建工作流
    print("1. 使用规范创建工作流:")
    workflow = create_ai_workflow_with_specs()
    print(json.dumps(workflow, indent=2))
    
    # 2. 验证参数
    print("\n2. 参数验证和转换:")
    try:
        params = {
            "system_prompt": "Analyze data",
            "temperature": "0.7",  # 字符串会被转换为浮点数
            "max_tokens": "2048",  # 字符串会被转换为整数
            "model_version": "gpt-4"
        }
        validated = ParameterValidator.validate_and_convert_parameters(
            "AI_AGENT_NODE", "OPENAI_NODE", params
        )
        print(f"✅ Validated parameters: {validated}")
    except ValueError as e:
        print(f"❌ Validation error: {e}")
    
    # 3. 生成文档
    print("\n3. 自动生成节点文档:")
    doc = generate_node_documentation("AI_AGENT_NODE", "CLAUDE_NODE")
    print(doc)
    
    # 4. 验证工作流
    print("\n4. 验证整个工作流:")
    validation_errors = WorkflowValidationService.validate_workflow(workflow)
    if validation_errors:
        print("❌ Workflow validation errors:")
        for error in validation_errors:
            print(f"  - {error}")
    else:
        print("✅ Workflow is valid!")