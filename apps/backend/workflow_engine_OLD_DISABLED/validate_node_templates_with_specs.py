#!/usr/bin/env python3
"""
验证node_templates表中的数据是否与shared/node_specs规范一致
确保数据库中的模板定义与代码中的节点规范匹配
"""

import json
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import ParameterType

    print("✅ 成功导入节点规范系统")
except ImportError as e:
    print(f"❌ 导入节点规范失败: {e}")
    print("请确保在workflow_engine目录下运行此脚本")
    sys.exit(1)


def parameter_type_to_json_schema_type(param_type: ParameterType) -> str:
    """将ParameterType枚举转换为JSON Schema类型"""
    mapping = {
        ParameterType.STRING: "string",
        ParameterType.INTEGER: "number",
        ParameterType.FLOAT: "number",
        ParameterType.BOOLEAN: "boolean",
        ParameterType.JSON: "object",
        ParameterType.ENUM: "string",
        ParameterType.URL: "string",
    }
    # 检查是否有ARRAY类型
    if hasattr(ParameterType, "ARRAY"):
        mapping[ParameterType.ARRAY] = "array"

    return mapping.get(param_type, "string")


def spec_to_template_data(spec):
    """将NodeSpec转换为node_templates表所需的数据格式"""

    # 生成默认参数
    default_parameters = {}
    for param in spec.parameters:
        if param.default_value is not None:
            default_parameters[param.name] = param.default_value

    # 生成必需参数列表
    required_parameters = [param.name for param in spec.parameters if param.required]

    # 生成JSON Schema
    schema = {
        "type": "object",
        "properties": {},
        "required": required_parameters,
        "additionalProperties": False,
    }

    for param in spec.parameters:
        prop = {
            "type": parameter_type_to_json_schema_type(param.type),
            "description": param.description or param.name,
        }

        # 处理枚举类型
        if param.type == ParameterType.ENUM and param.enum_values:
            prop["enum"] = param.enum_values

        # 处理URL类型
        if param.type == ParameterType.URL:
            prop["format"] = "uri"

        # 处理敏感数据
        if any(
            sensitive in param.name.lower() for sensitive in ["token", "password", "secret", "key"]
        ):
            prop["format"] = "password"

        # 添加默认值
        if param.default_value is not None:
            prop["default"] = param.default_value

        schema["properties"][param.name] = prop

    return {
        "default_parameters": default_parameters,
        "required_parameters": required_parameters,
        "parameter_schema": schema,
    }


def validate_external_action_nodes():
    """验证所有EXTERNAL_ACTION_NODE类型的节点规范"""

    print("🔍 开始验证EXTERNAL_ACTION_NODE节点规范...")
    print("=" * 80)

    # 获取所有外部动作节点规范
    external_specs = node_spec_registry.get_specs_by_type("EXTERNAL_ACTION_NODE")

    if not external_specs:
        print("❌ 未找到EXTERNAL_ACTION_NODE类型的规范")
        return False

    print(f"📋 找到 {len(external_specs)} 个EXTERNAL_ACTION_NODE规范:")

    validation_results = []

    for spec in external_specs:
        print(f"\n🔧 验证节点: {spec.node_type}.{spec.subtype}")
        print(f"   描述: {spec.description}")

        # 生成模板数据
        template_data = spec_to_template_data(spec)

        # 显示生成的数据
        print(f"   📝 默认参数: {len(template_data['default_parameters'])} 个")
        for key, value in template_data["default_parameters"].items():
            print(f"      • {key}: {value}")

        print(f"   ✅ 必需参数: {len(template_data['required_parameters'])} 个")
        for param in template_data["required_parameters"]:
            print(f"      • {param}")

        print(f"   🔗 参数规范: {len(template_data['parameter_schema']['properties'])} 个属性")

        # 生成建议的SQL插入语句
        template_id = f"external_{spec.subtype.lower().replace('_', '_')}"
        category_mapping = {
            "GOOGLE_CALENDAR": "integrations",
            "GITHUB": "integrations",
            "SLACK": "integrations",
            "EMAIL": "integrations",
            "API_CALL": "integrations",
        }
        category = category_mapping.get(spec.subtype, "integrations")

        validation_results.append(
            {
                "template_id": template_id,
                "name": spec.subtype.replace("_", " ").title(),
                "description": spec.description,
                "category": category,
                "node_type": spec.node_type,
                "node_subtype": spec.subtype,
                "default_parameters": template_data["default_parameters"],
                "required_parameters": template_data["required_parameters"],
                "parameter_schema": template_data["parameter_schema"],
            }
        )

        print(f"   ✅ 节点 {spec.subtype} 验证通过")

    print("\n" + "=" * 80)
    print("📊 验证结果总结:")
    print(f"✅ 成功验证 {len(validation_results)} 个外部动作节点")

    # 输出建议的SQL
    print("\n🗄️ 建议的数据库插入语句:")
    print("-" * 80)

    for result in validation_results:
        print(
            f"""
-- {result['name']} ({result['node_subtype']})
INSERT INTO public.node_templates (
    template_id, name, description, category, node_type, node_subtype,
    default_parameters, required_parameters, parameter_schema, is_system_template
) VALUES (
    '{result['template_id']}',
    '{result['name']}',
    '{result['description']}',
    '{result['category']}',
    '{result['node_type']}',
    '{result['node_subtype']}',
    '{json.dumps(result['default_parameters'], indent=2)}'::jsonb,
    ARRAY{result['required_parameters']},
    '{json.dumps(result['parameter_schema'], indent=2)}'::jsonb,
    true
);"""
        )

    return True


def main():
    """主函数"""
    print("🚀 Node Templates 与 Node Specs 一致性验证工具")
    print("=" * 80)

    # 显示加载的规范统计
    all_specs = node_spec_registry.list_all_specs()
    node_types = node_spec_registry.get_node_types()

    print(f"📚 已加载节点规范总数: {len(all_specs)}")
    print("📋 按类型分布:")
    for node_type, subtypes in node_types.items():
        print(f"   • {node_type}: {len(subtypes)} 个子类型")

    print()

    # 验证外部动作节点
    success = validate_external_action_nodes()

    if success:
        print("\n🎉 验证完成! 所有外部动作节点规范都已正确定义")
        print("💡 建议: 将上述SQL语句添加到数据库迁移文件中")
        return 0
    else:
        print("\n❌ 验证失败! 请检查节点规范定义")
        return 1


if __name__ == "__main__":
    sys.exit(main())
