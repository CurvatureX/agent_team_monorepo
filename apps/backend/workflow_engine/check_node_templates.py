#!/usr/bin/env python3
"""
检查node_templates表的状态，确认外部API节点是否已正确添加
"""

import json
import os
import sys
from typing import Any, Dict, List

# 加载环境变量
from dotenv import load_dotenv

# 加载.env文件
env_path = (
    "/Users/bytedance/personal/curvaturex/agent_team_monorepo/apps/backend/workflow_engine/.env"
)
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量从: {env_path}")
else:
    print(f"⚠️ 环境变量文件不存在: {env_path}")

# 添加路径以便导入
sys.path.append(".")
sys.path.append("/Users/bytedance/personal/curvaturex/agent_team_monorepo/apps/backend")


def check_database_connection():
    """检查数据库连接"""
    try:
        from sqlalchemy import text

        from workflow_engine.models.database import get_db_session

        with get_db_session() as db:
            result = db.execute(text("SELECT 1")).fetchone()
            if result:
                print("✅ 数据库连接成功")
                return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

    return False


def check_node_templates_table():
    """检查node_templates表结构"""
    try:
        from sqlalchemy import text

        from workflow_engine.models.database import get_db_session

        with get_db_session() as db:
            # 检查表是否存在
            result = db.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'node_templates'
                );
            """
                )
            ).fetchone()

            if not result[0]:
                print("❌ node_templates表不存在")
                return False

            print("✅ node_templates表存在")

            # 检查表结构
            columns_result = db.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'node_templates'
                ORDER BY ordinal_position;
            """
                )
            ).fetchall()

            print("\n📋 表结构:")
            for row in columns_result:
                print(f"   {row[0]} ({row[1]}) - {'NULL' if row[2] == 'YES' else 'NOT NULL'}")

            return True

    except Exception as e:
        print(f"❌ 检查node_templates表失败: {e}")
        return False


def check_external_api_nodes():
    """检查外部API节点是否存在"""
    try:
        from sqlalchemy import text

        from workflow_engine.models.database import get_db_session

        expected_nodes = ["GOOGLE_CALENDAR", "GITHUB", "SLACK", "EMAIL", "API_CALL"]

        with get_db_session() as db:
            # 查询现有的外部API节点
            result = db.execute(
                text(
                    """
                SELECT
                    template_id,
                    name,
                    node_type,
                    node_subtype,
                    category,
                    is_system_template,
                    created_at
                FROM public.node_templates
                WHERE node_type = 'EXTERNAL_ACTION_NODE'
                ORDER BY node_subtype;
            """
                )
            ).fetchall()

            print(f"\n🔍 外部API节点检查结果:")
            print(f"期望节点数: {len(expected_nodes)}")
            print(f"实际节点数: {len(result)}")

            if len(result) == 0:
                print("❌ 没有找到任何外部API节点模板")
                return False, []

            existing_nodes = []
            print("\n📋 现有外部API节点:")
            for row in result:
                template_id, name, node_type, node_subtype, category, is_system, created_at = row
                existing_nodes.append(node_subtype)
                status = "✅" if node_subtype in expected_nodes else "⚠️"
                print(f"   {status} {node_subtype}: {name} (ID: {template_id})")
                print(f"      分类: {category}, 系统模板: {is_system}, 创建时间: {created_at}")

            # 检查缺失的节点
            missing_nodes = [node for node in expected_nodes if node not in existing_nodes]
            if missing_nodes:
                print(f"\n❌ 缺失的节点: {missing_nodes}")
                return False, missing_nodes
            else:
                print(f"\n✅ 所有外部API节点都已存在!")
                return True, []

    except Exception as e:
        print(f"❌ 检查外部API节点失败: {e}")
        return False, []


def check_node_parameters():
    """检查节点参数schema的完整性"""
    try:
        from sqlalchemy import text

        from workflow_engine.models.database import get_db_session

        with get_db_session() as db:
            result = db.execute(
                text(
                    """
                SELECT
                    node_subtype,
                    template_id,
                    parameter_schema,
                    required_parameters,
                    default_parameters
                FROM public.node_templates
                WHERE node_type = 'EXTERNAL_ACTION_NODE'
                ORDER BY node_subtype;
            """
                )
            ).fetchall()

            print(f"\n🔧 节点参数schema检查:")

            schema_issues = []
            for row in result:
                node_subtype, template_id, param_schema, required_params, default_params = row

                print(f"\n📋 {node_subtype} ({template_id}):")

                # 检查parameter_schema
                if param_schema:
                    try:
                        schema = (
                            json.loads(param_schema)
                            if isinstance(param_schema, str)
                            else param_schema
                        )
                        properties_count = len(schema.get("properties", {}))
                        print(f"   ✅ Parameter Schema: {properties_count} 个参数")
                    except Exception as e:
                        print(f"   ❌ Parameter Schema解析错误: {e}")
                        schema_issues.append(f"{node_subtype}: parameter_schema解析失败")
                else:
                    print(f"   ❌ Parameter Schema: 缺失")
                    schema_issues.append(f"{node_subtype}: parameter_schema缺失")

                # 检查required_parameters
                if required_params:
                    print(f"   ✅ Required Parameters: {len(required_params)} 个")
                else:
                    print(f"   ⚠️ Required Parameters: 无")

                # 检查default_parameters
                if default_params:
                    try:
                        defaults = (
                            json.loads(default_params)
                            if isinstance(default_params, str)
                            else default_params
                        )
                        print(f"   ✅ Default Parameters: {len(defaults)} 个")
                    except:
                        print(f"   ⚠️ Default Parameters: 解析错误")
                else:
                    print(f"   ⚠️ Default Parameters: 无")

            if schema_issues:
                print(f"\n❌ Schema问题:")
                for issue in schema_issues:
                    print(f"   • {issue}")
                return False
            else:
                print(f"\n✅ 所有节点的参数schema都正常!")
                return True

    except Exception as e:
        print(f"❌ 检查节点参数失败: {e}")
        return False


def apply_migration_if_needed(missing_nodes: List[str]) -> bool:
    """如果有缺失的节点，应用迁移脚本"""
    if not missing_nodes:
        return True

    print(f"\n🔧 检测到缺失节点，准备应用迁移脚本...")

    migration_file = "/Users/bytedance/personal/curvaturex/agent_team_monorepo/apps/backend/workflow_engine/database/migrations/insert_external_api_node_templates.sql"

    if not os.path.exists(migration_file):
        print(f"❌ 迁移脚本不存在: {migration_file}")
        return False

    try:
        from sqlalchemy import text

        from workflow_engine.models.database import get_db_session

        # 读取迁移脚本
        with open(migration_file, "r", encoding="utf-8") as f:
            migration_sql = f.read()

        # 执行迁移
        with get_db_session() as db:
            # 将SQL按照分号分割并执行
            sql_statements = [stmt.strip() for stmt in migration_sql.split(";") if stmt.strip()]

            for stmt in sql_statements:
                if stmt.strip() and not stmt.strip().startswith("--"):
                    try:
                        db.execute(text(stmt))
                        db.commit()
                    except Exception as e:
                        if "duplicate key value" in str(e).lower():
                            print(f"⚠️ 跳过重复记录: {str(e)[:100]}...")
                            db.rollback()
                        else:
                            raise e

            print(f"✅ 迁移脚本执行完成!")
            return True

    except Exception as e:
        print(f"❌ 应用迁移脚本失败: {e}")
        return False


def main():
    """主检查函数"""
    print("🔍 开始检查node_templates表状态...\n")

    # 1. 检查数据库连接
    if not check_database_connection():
        print("\n❌ 数据库连接失败，请检查DATABASE_URL配置")
        return False

    # 2. 检查表结构
    if not check_node_templates_table():
        print("\n❌ node_templates表检查失败")
        return False

    # 3. 检查外部API节点
    nodes_ok, missing_nodes = check_external_api_nodes()

    # 4. 如果有缺失节点，尝试应用迁移
    if not nodes_ok:
        if not apply_migration_if_needed(missing_nodes):
            return False

        # 重新检查
        print(f"\n🔄 重新检查外部API节点...")
        nodes_ok, missing_nodes = check_external_api_nodes()

        if not nodes_ok:
            print(f"❌ 迁移后仍有缺失节点: {missing_nodes}")
            return False

    # 5. 检查参数schema
    if not check_node_parameters():
        print(f"\n❌ 节点参数schema检查失败")
        return False

    print(f"\n🎉 node_templates表检查完成!")
    print(f"✅ 所有外部API节点都已正确配置")
    print(f"✅ 参数schema完整且有效")
    print(f"✅ 数据库状态良好")

    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print(f"\n✅ 检查完成 - node_templates表状态正常")
            sys.exit(0)
        else:
            print(f"\n❌ 检查失败 - 请查看上面的错误信息")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⏹️ 用户中断检查")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 检查过程中发生意外错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
