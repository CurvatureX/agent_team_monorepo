#!/usr/bin/env python3
"""
统一日志系统使用示例
展示如何同时记录技术调试日志和用户友好业务日志
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# 设置路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_engine.services.unified_log_service import (
    create_legacy_compatible_logger,
    get_unified_log_service,
)


async def demo_unified_logging():
    """统一日志系统演示"""

    print("=" * 80)
    print("🔄 统一日志系统演示 - 同时支持技术和业务日志")
    print("=" * 80)
    print()

    execution_id = f"demo-unified-{int(time.time())}"
    log_service = get_unified_log_service()

    print(f"📋 执行ID: {execution_id}")
    print()

    # 1. 业务日志记录 - 用户友好信息
    print("📍 第一部分：业务日志记录 (用户友好)")
    print("-" * 50)

    # 工作流开始 - 里程碑事件
    await log_service.add_business_log(
        execution_id=execution_id,
        event_type="workflow_started",
        technical_message="Starting customer service workflow with 4 nodes",
        user_friendly_message="🚀 开始执行客户服务工作流 (共4个步骤)",
        display_priority=10,  # 最高优先级
        is_milestone=True,
        total_steps=4,
    )

    print("✅ 已记录: 工作流开始里程碑事件")

    # 步骤1 - AI分析
    await log_service.add_business_log(
        execution_id=execution_id,
        event_type="step_started",
        technical_message="AI analysis step initiated",
        user_friendly_message="📍 步骤 [1/4] AI智能分析 - 分析客户请求内容",
        display_priority=7,  # 高优先级
        step_number=1,
        total_steps=4,
        progress_percentage=25.0,
        node_name="AI分析",
        node_type="AI_AGENT",
    )

    print("✅ 已记录: 步骤1开始 - AI智能分析")

    # 步骤1完成
    await log_service.add_business_log(
        execution_id=execution_id,
        event_type="step_completed",
        technical_message="AI analysis completed successfully",
        user_friendly_message="✅ AI智能分析完成 - 识别为订单查询请求",
        display_priority=7,
        step_number=1,
        total_steps=4,
        progress_percentage=25.0,
        duration_seconds=2,
        node_name="AI分析",
    )

    print("✅ 已记录: 步骤1完成 - AI智能分析")

    await asyncio.sleep(0.5)

    # 2. 技术日志记录 - 详细调试信息
    print("\n📍 第二部分：技术日志记录 (详细调试)")
    print("-" * 50)

    # OpenAI API调用详情
    await log_service.add_technical_log(
        execution_id=execution_id,
        level="DEBUG",
        message="OpenAI API call initiated",
        event_type="step_input",
        node_id="ai_analysis_node_001",
        node_name="AI分析",
        node_type="AI_AGENT",
        technical_details={
            "api_endpoint": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4",
            "temperature": 0.2,
            "max_tokens": 1000,
            "request_id": "req_abc123def456",
        },
        performance_metrics={
            "request_start_time": datetime.now().isoformat(),
            "request_timeout": 30,
        },
    )

    print("✅ 已记录: OpenAI API调用开始详情")

    # API响应详情
    await log_service.add_technical_log(
        execution_id=execution_id,
        level="INFO",
        message="OpenAI API response received successfully",
        event_type="step_output",
        node_id="ai_analysis_node_001",
        duration_seconds=2,
        technical_details={
            "response_status": 200,
            "token_usage": {"prompt_tokens": 156, "completion_tokens": 89, "total_tokens": 245},
            "model_used": "gpt-4",
            "finish_reason": "stop",
        },
        performance_metrics={
            "response_time_ms": 1850,
            "tokens_per_second": 48.1,
            "latency_p95": 1923,
        },
    )

    print("✅ 已记录: OpenAI API响应详情和性能指标")

    # 错误场景 - 技术错误
    await log_service.add_technical_log(
        execution_id=execution_id,
        level="ERROR",
        message="Slack API rate limit exceeded",
        event_type="step_error",
        node_id="slack_notification_node",
        node_name="Slack通知",
        technical_details={
            "status_code": 429,
            "error_code": "rate_limited",
            "retry_after": 60,
            "api_endpoint": "/api/chat.postMessage",
            "request_headers": {
                "authorization": "Bearer xoxb-***",
                "content-type": "application/json",
            },
        },
        stack_trace="Traceback (most recent call last):\\n  File 'slack_node.py', line 45, in send_message\\n    response = requests.post(...)\\nSlackAPIError: rate_limited",
    )

    print("✅ 已记录: Slack API错误和技术堆栈信息")

    # 对应的业务错误日志
    await log_service.add_business_log(
        execution_id=execution_id,
        event_type="step_error",
        technical_message="Slack notification failed due to rate limiting",
        user_friendly_message="💥 Slack通知发送失败 - API速率限制，请稍后重试",
        level="ERROR",
        display_priority=9,  # 错误事件高优先级
        node_name="Slack通知",
        step_number=4,
        total_steps=4,
    )

    print("✅ 已记录: 对应的用户友好错误信息")

    await asyncio.sleep(0.5)

    # 3. 查询不同类型的日志
    print("\n📍 第三部分：分类日志查询演示")
    print("-" * 50)

    # 查询业务日志 - 前端用户界面
    print("🔍 查询业务日志 (用户界面):")
    business_logs = await log_service.get_business_logs(
        execution_id=execution_id, min_priority=5, limit=10
    )

    for i, log in enumerate(business_logs, 1):
        priority_icon = "🔥" if log.get("display_priority", 5) >= 8 else "📋"
        milestone_icon = "⭐" if log.get("is_milestone", False) else ""
        message = log.get("user_friendly_message") or log.get("message")
        print(f"  {i}. {priority_icon}{milestone_icon} {message}")

    print(f"   共找到 {len(business_logs)} 条业务日志")

    # 查询技术日志 - 开发调试
    print("\n🔍 查询技术日志 (开发调试):")
    technical_logs = await log_service.get_technical_logs(execution_id=execution_id, limit=5)

    for i, log in enumerate(technical_logs, 1):
        level = log.get("level", "INFO")
        level_icon = "❌" if level == "ERROR" else "🔧" if level == "DEBUG" else "ℹ️"
        message = log.get("message", "")
        print(f"  {i}. {level_icon} [{level}] {message}")

        # 显示技术细节
        tech_details = log.get("technical_details", {})
        if tech_details:
            key_details = []
            if "status_code" in tech_details:
                key_details.append(f"状态码: {tech_details['status_code']}")
            if "response_time_ms" in tech_details:
                key_details.append(f"响应时间: {tech_details['response_time_ms']}ms")
            if "model" in tech_details:
                key_details.append(f"模型: {tech_details['model']}")
            if key_details:
                print(f"      💡 {' | '.join(key_details)}")

    print(f"   共找到 {len(technical_logs)} 条技术日志")

    # 查询里程碑事件 - 执行概览（通过业务日志获取）
    print("\n🔍 查询里程碑事件 (执行概览):")
    milestone_result = await log_service.get_business_logs(
        execution_id=execution_id, min_priority=7, milestones_only=True, limit=50, page=1  # 高优先级
    )

    for i, log in enumerate(milestone_result.data, 1):
        message = log.get("user_friendly_message") or log.get("message")
        timestamp = log.get("timestamp", "")[:19].replace("T", " ")
        print(f"  {i}. ⭐ {message} ({timestamp})")

    print(f"   共找到 {len(milestone_result.data)} 个里程碑事件")

    # 4. 兼容性演示
    print("\n📍 第四部分：与现有BusinessLogger兼容性")
    print("-" * 50)

    # 使用兼容性接口
    legacy_logger = create_legacy_compatible_logger(execution_id, "兼容性测试工作流")

    await legacy_logger.workflow_started(3, "API触发")
    print("✅ 使用兼容接口记录工作流开始")

    await legacy_logger.step_completed("数据处理", 1.5, "SUCCESS")
    print("✅ 使用兼容接口记录步骤完成")

    # 验证兼容性日志
    compat_logs = await log_service.get_business_logs(execution_id, min_priority=5)
    compat_count = len(
        [log for log in compat_logs if "兼容性" in log.get("user_friendly_message", "")]
    )
    print(f"✅ 兼容性日志已正确记录: {compat_count} 条")

    print()
    print("=" * 80)
    print("🎉 统一日志系统演示完成！")
    print("=" * 80)
    print()
    print("📊 总结统计:")

    # 最终统计
    all_business = await log_service.get_business_logs(
        execution_id, min_priority=1, limit=1000, page=1
    )
    all_technical = await log_service.get_technical_logs(execution_id, limit=1000, page=1)
    all_milestones = await log_service.get_business_logs(
        execution_id, min_priority=7, milestones_only=True, limit=1000, page=1
    )

    print(f"   📋 业务日志: {len(all_business.data)} 条")
    print(f"   🔧 技术日志: {len(all_technical.data)} 条")
    print(f"   ⭐ 里程碑事件: {len(all_milestones.data)} 个")
    print(f"   📝 总计: {len(all_business.data) + len(all_technical.data)} 条日志")
    print()
    print("🎯 使用场景验证:")
    print("   ✅ 前端用户界面 → 查询业务日志 (中文友好)")
    print("   ✅ 开发调试界面 → 查询技术日志 (详细信息)")
    print("   ✅ AI Agent分析 → 获取结构化技术数据")
    print("   ✅ 执行概览界面 → 显示里程碑事件")
    print("   ✅ 现有代码兼容 → 无缝迁移支持")


async def demo_api_usage():
    """演示如何通过API查询分类日志"""

    print("\n" + "=" * 60)
    print("🌐 API查询示例")
    print("=" * 60)
    print()

    execution_id = "demo-api-example"

    print("📋 前端业务日志查询:")
    print("   GET /v1/workflows/executions/{}/logs/business?min_priority=5".format(execution_id))
    print("   → 返回用户友好的中文日志，适合前端展示")
    print()

    print("🔧 技术调试日志查询:")
    print(
        "   GET /v1/workflows/executions/{}/logs/technical?include_stack_trace=true".format(
            execution_id
        )
    )
    print("   → 返回详细技术信息，适合开发调试")
    print()

    print("⭐ 里程碑事件查询:")
    print(
        "   GET /v1/workflows/executions/{}/logs/business?milestones_only=true&min_priority=7".format(
            execution_id
        )
    )
    print("   → 返回关键执行节点，适合进度概览（通过业务日志过滤获取）")
    print()

    print("🔄 数据迁移:")
    print("   POST /v1/workflows/executions/{}/logs/migrate".format(execution_id))
    print("   → 将现有ExecutionLog迁移到统一格式")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_unified_logging())
    demo_api_usage()

    print("\n🚀 统一日志系统已准备就绪！")
    print("   您现在可以:")
    print('   1. 运行数据库迁移: python -c "from migrations.add_unified_log_fields import *"')
    print("   2. 启动服务: python -m workflow_engine.main")
    print("   3. 测试API: curl http://localhost:8002/docs")
    print("   4. 集成现有代码: 使用 create_legacy_compatible_logger()")
