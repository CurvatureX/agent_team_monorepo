"""
Script to insert sample node knowledge data into Supabase vector store
This demonstrates how to populate the RAG system with node knowledge
"""

import asyncio
import json
from typing import Dict, List

from langchain_openai import OpenAIEmbeddings
from supabase import create_client

from ..core.config import settings

# Sample node knowledge data
SAMPLE_NODE_KNOWLEDGE = [
    {
        "node_type": "TRIGGER_EMAIL",
        "node_subtype": "TRIGGER_EMAIL_GMAIL",
        "title": "Gmail邮件触发器",
        "description": "监控Gmail邮箱中的新邮件，支持过滤条件和实时触发",
        "content": """
Gmail邮件触发器是最常用的工作流入口之一。它可以：

核心功能：
- 实时监控Gmail邮箱
- 支持多种过滤条件（发件人、主题、标签等）
- 自动解析邮件内容和附件
- 支持多个邮箱账户

配置要求：
- Gmail API凭证
- OAuth2认证
- 邮箱访问权限

最佳实践：
- 使用标签过滤减少不必要的触发
- 设置合理的轮询间隔
- 启用错误重试机制
- 配置邮件内容解析规则

常见用例：
- 客服邮件自动处理
- 订单确认邮件处理
- 新用户注册通知
- 文档协作通知
        """,
        "metadata": {
            "complexity": "low",
            "setup_time": "15分钟",
            "reliability": "high",
            "capabilities": ["email_monitoring", "real_time_trigger", "content_parsing"],
            "configuration_requirements": ["gmail_oauth", "api_credentials"],
            "best_practices": ["使用标签过滤优化性能", "设置合理的轮询频率", "配置错误处理机制"],
            "use_case": "email_automation",
            "example_config": {
                "provider": "gmail",
                "poll_interval": "*/5 * * * *",
                "filters": {"has_label": "workflow", "from_contains": "@company.com"},
            },
        },
    },
    {
        "node_type": "AI_TASK_ANALYZER",
        "node_subtype": "AI_CONTENT_ANALYZER",
        "title": "AI任务分析器",
        "description": "使用AI分析文本内容，提取关键信息和意图，支持多种分析任务",
        "content": """
AI任务分析器是智能工作流的核心组件，提供强大的内容理解能力。

核心功能：
- 文本内容理解和分类
- 意图识别和情感分析
- 关键信息提取
- 置信度评估
- 多语言支持

配置要求：
- OpenAI API密钥
- 自定义提示模板
- 分析规则配置

技术特点：
- 支持GPT-4/GPT-3.5
- 可配置提示工程
- 结构化输出格式
- 批量处理能力

最佳实践：
- 设计清晰的提示模板
- 配置置信度阈值
- 使用示例数据训练
- 实施结果验证机制

应用场景：
- 客服邮件分类
- 文档内容分析
- 用户反馈处理
- 订单信息提取
        """,
        "metadata": {
            "complexity": "medium",
            "setup_time": "30分钟",
            "reliability": "high",
            "capabilities": ["ai_analysis", "content_classification", "intent_recognition"],
            "configuration_requirements": ["openai_api_key", "prompt_template"],
            "best_practices": ["优化提示工程提高准确率", "设置合适的置信度阈值", "使用结构化输出格式"],
            "use_case": "content_analysis",
            "example_config": {
                "model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 1000,
                "prompt_template": "分析以下内容的意图和关键信息：{content}",
            },
        },
    },
    {
        "node_type": "EXTERNAL_SLACK",
        "node_subtype": "SLACK_MESSAGE_SENDER",
        "title": "Slack消息发送器",
        "description": "向Slack频道或用户发送消息，支持富文本格式和文件附件",
        "content": """
Slack消息发送器实现与Slack平台的无缝集成，支持多种消息类型。

核心功能：
- 发送频道消息
- 私信用户
- 富文本格式支持
- 文件和图片附件
- 消息模板化

配置要求：
- Slack Bot Token
- 频道权限配置
- 消息格式设置

集成特点：
- 支持Slack Block Kit
- 交互式消息组件
- 消息线程管理
- 批量消息发送

最佳实践：
- 使用消息模板提高一致性
- 配置适当的通知频率
- 设置消息优先级
- 实施消息去重机制

典型应用：
- 任务完成通知
- 错误告警消息
- 日报周报发送
- 团队协作通知
        """,
        "metadata": {
            "complexity": "low",
            "setup_time": "10分钟",
            "reliability": "high",
            "capabilities": ["slack_integration", "message_sending", "notification"],
            "configuration_requirements": ["slack_bot_token", "channel_permissions"],
            "best_practices": ["使用Block Kit创建丰富的消息格式", "避免消息轰炸，设置合理频率", "使用线程组织相关消息"],
            "use_case": "team_notification",
            "example_config": {
                "token": "${SLACK_BOT_TOKEN}",
                "channel": "#general",
                "message_template": "工作流完成: {workflow_name}",
                "thread_ts": null,
            },
        },
    },
    {
        "node_type": "EXTERNAL_NOTION",
        "node_subtype": "NOTION_DATABASE_WRITER",
        "title": "Notion数据库写入器",
        "description": "向Notion数据库添加新记录，支持多种属性类型和关系映射",
        "content": """
Notion数据库写入器实现与Notion工作空间的深度集成，支持复杂的数据操作。

核心功能：
- 创建数据库页面
- 更新页面属性
- 文件上传管理
- 关系字段处理
- 批量数据操作

配置要求：
- Notion Integration Token
- 数据库访问权限
- 字段映射配置

数据类型支持：
- 文本、数字、日期
- 选择项和多选项
- 关系和公式字段
- 文件和媒体内容

最佳实践：
- 预先规划数据库结构
- 使用模板页面提高效率
- 实施数据验证机制
- 配置字段映射规则

应用场景：
- 项目管理记录
- 客户信息管理
- 知识库构建
- 任务跟踪系统
        """,
        "metadata": {
            "complexity": "medium",
            "setup_time": "20分钟",
            "reliability": "high",
            "capabilities": ["notion_integration", "database_operations", "data_storage"],
            "configuration_requirements": ["notion_token", "database_id", "field_mapping"],
            "best_practices": ["使用结构化的字段映射", "实施数据验证确保质量", "合理使用关系字段"],
            "use_case": "data_management",
            "example_config": {
                "token": "${NOTION_TOKEN}",
                "database_id": "abc123...",
                "properties": {
                    "title": {"type": "title"},
                    "status": {"type": "select"},
                    "due_date": {"type": "date"},
                },
            },
        },
    },
    {
        "node_type": "FLOW_IF",
        "node_subtype": "CONDITIONAL_ROUTER",
        "title": "条件路由器",
        "description": "基于条件表达式控制工作流分支，支持复杂的逻辑判断",
        "content": """
条件路由器是工作流控制的核心组件，实现智能的分支逻辑。

核心功能：
- 条件表达式评估
- 多分支路由控制
- 复杂逻辑运算
- 动态条件判断
- 嵌套条件支持

配置要求：
- 条件表达式定义
- 分支路径配置
- 默认处理路径

表达式支持：
- 比较运算符 (>, <, ==, !=)
- 逻辑运算符 (&&, ||, !)
- 字符串匹配和正则
- 数组和对象操作

最佳实践：
- 保持条件简单明确
- 提供默认分支处理
- 使用有意义的变量名
- 添加详细的注释说明

典型场景：
- 邮件优先级分类
- 用户权限检查
- 数据质量验证
- 业务规则执行
        """,
        "metadata": {
            "complexity": "low",
            "setup_time": "5分钟",
            "reliability": "high",
            "capabilities": ["flow_control", "conditional_logic", "routing"],
            "configuration_requirements": ["condition_expression", "branch_paths"],
            "best_practices": ["保持条件表达式简单清晰", "总是提供else分支", "使用描述性的变量名"],
            "use_case": "workflow_control",
            "example_config": {
                "condition": "{{data.confidence}} > 0.7",
                "true_path": "high_confidence_handler",
                "false_path": "manual_review",
            },
        },
    },
]


async def insert_node_knowledge():
    """Insert sample node knowledge data into Supabase"""

    # Initialize clients
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL, openai_api_key=settings.OPENAI_API_KEY
    )

    print("Inserting node knowledge data...")

    for knowledge in SAMPLE_NODE_KNOWLEDGE:
        try:
            # Generate embedding for the content
            content_text = f"{knowledge['title']} {knowledge['description']} {knowledge['content']}"
            embedding = await embeddings.aembed_query(content_text)

            # Prepare data for insertion
            data = {
                "node_type": knowledge["node_type"],
                "node_subtype": knowledge["node_subtype"],
                "title": knowledge["title"],
                "description": knowledge["description"],
                "content": knowledge["content"],
                "embedding": embedding,
                "metadata": knowledge["metadata"],
            }

            # Insert into Supabase
            result = supabase.table("node_knowledge_vectors").insert(data).execute()

            print(f"✅ Inserted: {knowledge['title']}")

        except Exception as e:
            print(f"❌ Failed to insert {knowledge['title']}: {str(e)}")

    print("Node knowledge insertion completed!")


async def test_rag_search():
    """Test the RAG search functionality"""
    from core.vector_store import get_node_knowledge_rag

    rag = get_node_knowledge_rag()

    print("\n🔍 Testing RAG search functionality...")

    # Test capability search
    print("\n1. Testing capability recommendations:")
    capabilities = ["email_monitoring", "ai_analysis", "slack_integration"]
    result = await rag.get_capability_recommendations(capabilities)
    print(f"Coverage score: {result['coverage_score']}")
    print(f"Total matches: {result['total_matches']}")

    # Test node type suggestions
    print("\n2. Testing node type suggestions:")
    suggestions = await rag.get_node_type_suggestions(
        "analyze customer emails and send notifications to Slack"
    )
    for suggestion in suggestions[:3]:
        print(f"- {suggestion['node_type']}: {suggestion['description']}")

    # Test integration guidance
    print("\n3. Testing integration guidance:")
    guidance = await rag.get_integration_guidance("slack", {"data_direction": "output"})
    print(f"Found {len(guidance['specific_guidance'])} specific guidance items")
    print(f"Found {len(guidance['best_practices'])} best practices")

    print("\n✅ RAG testing completed!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_rag_search())
    else:
        asyncio.run(insert_node_knowledge())
