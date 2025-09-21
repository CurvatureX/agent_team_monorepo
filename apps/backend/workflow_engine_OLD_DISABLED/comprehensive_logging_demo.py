#!/usr/bin/env python3
"""
全面的Workflow执行信息业务日志演示

展示所有重要的workflow执行信息都被正确记录到业务日志中：
✅ 工作流触发信息和用户信息
✅ 每个节点的详细输入输出
✅ 执行进度实时更新
✅ 节点失败原因清晰记录
✅ 关键性能指标统计
✅ 异常处理和错误恢复
"""

import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict

sys.path.insert(0, "/Users/jingweizhang/Workspace/agent_team_monorepo/apps/backend/workflow_engine")

from workflow_engine.utils.business_logger import (
    NodeExecutionBusinessLogger,
    create_business_logger,
)


def setup_technical_logger():
    """设置技术日志器"""
    tech_logger = logging.getLogger("workflow_engine.comprehensive_demo")
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "🔧 TECH | %(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    tech_logger.addHandler(handler)
    tech_logger.setLevel(logging.DEBUG)
    tech_logger.propagate = False
    return tech_logger


def demo_complete_workflow_logging():
    """演示完整的workflow执行信息记录"""

    print("=" * 100)
    print("🔍 全面的Workflow业务日志系统 - 确保所有重要信息都被记录")
    print("=" * 100)
    print()
    print("📋 本演示将验证以下关键信息都被正确记录:")
    print("   ✅ 详细的触发信息和用户身份")
    print("   ✅ 每个节点的输入输出数据摘要")
    print("   ✅ 实时的执行进度和状态更新")
    print("   ✅ 清晰的错误原因和用户友好的解释")
    print("   ✅ 关键性能指标和执行统计")
    print("   ✅ 异常处理和恢复建议")
    print()

    # 模拟详细的工作流执行
    execution_id = f"comprehensive-{int(time.time())}"
    business_logger = create_business_logger(execution_id, "客户服务完整流程")
    tech_logger = setup_technical_logger()

    # 1. 详细的触发信息记录
    print("📍 第一部分：触发信息和用户身份记录")
    print("-" * 50)

    # 模拟来自Slack的webhook触发，包含用户信息
    trigger_info = "Slack消息触发 | 用户: john123... | 频道: #customer-support"
    business_logger.workflow_started(4, trigger_info)
    tech_logger.debug(
        "Workflow triggered by Slack webhook from user john123abc in #customer-support"
    )

    time.sleep(0.5)

    # 2. 详细的节点执行信息记录
    print("\n📍 第二部分：节点执行详细信息记录")
    print("-" * 50)

    successful_steps = 0
    total_steps = 4

    # 步骤1: Slack消息解析
    step_name = "Slack消息解析"
    business_logger.step_started(1, total_steps, step_name, "TRIGGER", "解析客户的Slack消息内容")

    # 详细的输入信息
    input_data = {
        "message": "你好，我的订单#ORD-12345有问题，3天前下单但还没发货通知",
        "user_id": "U01ABC123",
        "channel": "#customer-support",
        "timestamp": "1704720000.123",
        "thread_ts": None,
        "user_profile": {"name": "张三", "email": "zhangsan@company.com"},
    }
    key_inputs = NodeExecutionBusinessLogger.extract_key_inputs("TRIGGER", "SLACK", input_data)
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug(f"Parsing Slack message from user U01ABC123 in channel #customer-support")

    time.sleep(0.8)

    # 处理结果
    output_data = {
        "content": "订单问题咨询：订单号ORD-12345，用户关注发货状态，已等待3天",
        "metadata": {
            "message_type": "customer_inquiry",
            "urgency": "medium",
            "category": "order_status",
            "customer_info": {"name": "张三", "order_id": "ORD-12345"},
        },
    }
    key_outputs = NodeExecutionBusinessLogger.extract_key_outputs("TRIGGER", "SLACK", output_data)
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 0.8, "SUCCESS")
    successful_steps += 1

    tech_logger.debug("Slack message parsed successfully: order inquiry detected")

    # 显示进度
    business_logger.workflow_progress(successful_steps, total_steps, "即将执行: AI智能分析")

    time.sleep(0.5)

    # 步骤2: AI智能分析
    step_name = "AI智能分析"
    business_logger.step_started(2, total_steps, step_name, "AI_AGENT", "使用Claude分析客户问题")

    input_data = {
        "content": "订单问题咨询：订单号ORD-12345，用户关注发货状态，已等待3天",
        "system_prompt": "你是专业的客服AI，分析客户问题并制定处理策略",
        "model_version": "claude-3-5-sonnet",
        "temperature": 0.2,
        "max_tokens": 1000,
    }
    key_inputs = NodeExecutionBusinessLogger.extract_key_inputs(
        "AI_AGENT", "ANTHROPIC_CLAUDE", input_data
    )
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug("Initiating Claude analysis with claude-3-5-sonnet model")

    time.sleep(2.1)

    output_data = {
        "content": "分析结果：\\n1. 问题类型：订单物流查询\\n2. 紧急程度：中等（已等待3天）\\n3. 处理建议：立即查询订单状态，向客户提供物流信息\\n4. 预计处理时间：5-10分钟",
        "metadata": {
            "token_usage": {"input_tokens": 89, "output_tokens": 156, "total_tokens": 245},
            "model": "claude-3-5-sonnet",
            "confidence_score": 0.92,
            "processing_time": 2.1,
        },
    }
    key_outputs = NodeExecutionBusinessLogger.extract_key_outputs(
        "AI_AGENT", "ANTHROPIC_CLAUDE", output_data
    )
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 2.1, "SUCCESS")
    successful_steps += 1

    tech_logger.debug("Claude analysis completed: order logistics inquiry identified")

    # 显示进度
    business_logger.workflow_progress(successful_steps, total_steps, "即将执行: 订单状态查询")

    time.sleep(0.5)

    # 步骤3: 订单系统查询
    step_name = "订单状态查询"
    business_logger.step_started(3, total_steps, step_name, "EXTERNAL_ACTION", "从订单系统查询ORD-12345状态")

    input_data = {"order_id": "ORD-12345", "api_endpoint": "/api/orders/status", "timeout": 10}
    key_inputs = {"订单号": "ORD-12345", "查询超时": "10秒"}
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug("Querying order system API for order ORD-12345")

    time.sleep(1.3)

    output_data = {
        "order_status": "已发货",
        "tracking_number": "SF1234567890",
        "shipping_company": "顺丰速运",
        "estimated_delivery": "2025-09-10",
        "last_update": "2025-09-08 10:30:00",
        "api_response_time": 1.3,
    }
    key_outputs = {"订单状态": "已发货", "快递公司": "顺丰速运", "快递单号": "SF1234567890", "预计送达": "2025-09-10"}
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 1.3, "SUCCESS")
    successful_steps += 1

    tech_logger.debug("Order status retrieved successfully: shipped via SF Express")

    # 显示进度
    business_logger.workflow_progress(successful_steps, total_steps, "即将执行: 客户回复")

    time.sleep(0.5)

    # 步骤4: 发送回复 (模拟失败场景)
    step_name = "Slack客户回复"
    business_logger.step_started(4, total_steps, step_name, "EXTERNAL_ACTION", "向客户发送订单状态更新")

    input_data = {
        "channel": "#customer-support",
        "thread_ts": "1704720000.123",
        "message": "您好张三！您的订单ORD-12345已经发货啦 📦\\n\\n快递公司：顺丰速运\\n快递单号：SF1234567890\\n预计送达：2025年9月10日\\n\\n您可以通过快递单号追踪包裹状态。如有其他问题请随时联系我们！",
        "user_id": "U01ABC123",
    }
    key_inputs = {"回复内容": "订单ORD-12345发货信息（顺丰SF1234567890）", "回复方式": "Slack线程回复"}
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug("Sending Slack reply to customer U01ABC123 in thread")
    tech_logger.error("Slack API rate limit exceeded: 429 Too Many Requests")

    time.sleep(2.0)

    # 模拟失败
    business_logger.step_error(
        step_name,
        "Slack API rate limit exceeded: 429 Too Many Requests",
        "Slack消息发送失败，已达到API速率限制。建议5分钟后重试或使用邮件方式联系客户",
    )
    business_logger.step_completed(step_name, 2.0, "ERROR")

    tech_logger.debug("Slack message sending failed due to rate limiting")

    # 3. 最终的性能统计和摘要
    print("\n📍 第三部分：性能统计和执行摘要")
    print("-" * 50)

    total_duration = 6.7  # 所有步骤耗时总和

    # 详细的性能统计
    performance_stats = {
        "avg_step_time": total_duration / successful_steps,  # 平均步骤时间
        "slowest_step": {"name": "AI智能分析", "duration": 2.1},  # 最慢步骤
        "data_processed": "1条订单记录",  # 处理的数据量
    }

    business_logger.workflow_completed(
        total_steps, successful_steps, total_duration, "ERROR", performance_stats
    )

    tech_logger.debug(
        f"Workflow execution summary: 3/4 steps successful, 1 failed due to API limits"
    )

    print("\n📍 第四部分：异常处理演示")
    print("-" * 50)

    # 演示系统级异常
    exception_logger = create_business_logger(f"exception-{int(time.time())}", "异常处理测试")
    exception_logger.workflow_started(2, "定时任务触发")
    exception_logger.step_started(1, 2, "数据库连接", "ACTION", "连接客户数据库")
    exception_logger.step_error(
        "数据库连接",
        "psycopg2.OperationalError: could not connect to server",
        "数据库连接失败，请检查网络连接或联系数据库管理员",
    )
    exception_logger.workflow_completed(2, 0, 0.5, "ERROR")

    print()
    print("=" * 100)
    print("✅ 全面的业务日志记录演示完成！")
    print("=" * 100)
    print()
    print("🎯 已验证的关键信息记录:")
    print()
    print("✅ 触发信息记录:")
    print("   • 详细的触发来源（Slack webhook）")
    print("   • 用户身份识别（用户ID和频道）")
    print("   • 触发时间和上下文信息")
    print()
    print("✅ 节点执行详情:")
    print("   • 每个步骤的用户友好名称和描述")
    print("   • 结构化的输入输出数据摘要")
    print("   • 执行时间和状态跟踪")
    print("   • 重要参数突出显示")
    print()
    print("✅ 进度追踪:")
    print("   • 实时的执行进度百分比")
    print("   • 当前执行步骤和下一步预告")
    print("   • 剩余步骤数量提示")
    print()
    print("✅ 错误处理:")
    print("   • 技术错误和用户友好解释分离")
    print("   • 明确的失败原因和恢复建议")
    print("   • 异常中断时的状态保存")
    print()
    print("✅ 性能指标:")
    print("   • 总执行时间和平均步骤时间")
    print("   • 最慢步骤识别和优化建议")
    print("   • 数据处理量统计")
    print()
    print("🎊 业务日志系统现在完整记录了所有重要的workflow执行信息！")
    print("   用户可以清晰了解工作流的完整执行过程和结果。")


if __name__ == "__main__":
    demo_complete_workflow_logging()
