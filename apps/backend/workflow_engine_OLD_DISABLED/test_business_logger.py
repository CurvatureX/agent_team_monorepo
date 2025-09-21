#!/usr/bin/env python3
"""
测试脚本：验证新的业务日志系统

这个脚本演示新的日志分离系统如何工作：
1. 业务日志 - 用户友好的工作流执行信息
2. 技术日志 - 开发调试用的详细信息

运行此脚本查看两种日志的区别。
"""

import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict

# 设置路径以便导入模块
sys.path.insert(0, "/Users/jingweizhang/Workspace/agent_team_monorepo/apps/backend/workflow_engine")

from workflow_engine.utils.business_logger import (
    NodeExecutionBusinessLogger,
    create_business_logger,
)


def setup_technical_logger():
    """设置技术日志器 - 模拟execution_engine中的技术日志"""
    tech_logger = logging.getLogger("workflow_engine.test_technical")

    # 创建独立的handler避免与业务日志混杂
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "🔧 TECH | %(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    tech_logger.addHandler(handler)
    tech_logger.setLevel(logging.DEBUG)
    tech_logger.propagate = False

    return tech_logger


def demo_workflow_execution():
    """模拟完整的工作流执行过程"""

    print("=" * 80)
    print("🧪 业务日志系统测试演示")
    print("=" * 80)
    print()

    # 创建日志器
    execution_id = f"test-{int(time.time())}"
    business_logger = create_business_logger(execution_id, "客户服务自动化测试")
    tech_logger = setup_technical_logger()

    print("📋 本次测试将演示以下场景:")
    print("   1. 工作流开始 - 包含3个步骤")
    print("   2. AI智能分析客户请求")
    print("   3. 发送Slack通知")
    print("   4. 发送确认邮件")
    print("   5. 工作流完成摘要")
    print()
    print("👀 注意观察两种日志的区别:")
    print("   🔄 WORKFLOW | ... = 业务日志 (用户友好)")
    print("   🔧 TECH | ...     = 技术日志 (开发调试)")
    print()
    input("按回车键开始演示...")
    print()

    # 1. 工作流开始
    business_logger.log_separator("工作流执行开始")
    business_logger.workflow_started(3, "客户支持请求")
    tech_logger.debug("[TECH] Starting workflow execution: test-workflow-123")
    tech_logger.debug("[TECH] Workflow definition keys: ['name', 'nodes', 'connections']")
    tech_logger.debug("[TECH] Initial data keys: ['customer_request', 'user_id', 'priority']")

    time.sleep(1)

    # 2. 第一个步骤 - AI分析
    step_name = "AI智能分析"
    business_logger.step_started(1, 3, step_name, "AI_AGENT", "使用ChatGPT分析客户请求内容")

    # 输入数据
    input_data = {
        "content": "我的订单还没有发货，订单号是#12345，已经3天了，请帮我查一下",
        "system_prompt": "你是专业的客服助手，请分析客户请求的类型和紧急程度",
        "model_version": "gpt-4o",
        "temperature": 0.3,
    }
    key_inputs = NodeExecutionBusinessLogger.extract_key_inputs(
        "AI_AGENT", "OPENAI_CHATGPT", input_data
    )
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug(f"[TECH] Node ai_analysis_node input data: {input_data}")
    tech_logger.debug("[TECH] Created executor: OpenAINodeExecutor")
    tech_logger.debug("[TECH] Executing ai_analysis_node with OpenAINodeExecutor (async: False)")

    time.sleep(2)

    # AI处理结果
    output_data = {
        "content": "客户请求类型：物流查询\\n紧急程度：中等\\n建议处理：立即查询订单状态并回复\\n预计处理时间：5分钟",
        "metadata": {
            "token_usage": {"total": 156, "input": 89, "output": 67},
            "model": "gpt-4o",
            "processing_time": 1.8,
        },
    }
    key_outputs = NodeExecutionBusinessLogger.extract_key_outputs(
        "AI_AGENT", "OPENAI_CHATGPT", output_data
    )
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 1.8, "SUCCESS")

    tech_logger.debug(
        "[TECH] Node ai_analysis_node execution result: status=SUCCESS, duration=1.80s"
    )
    tech_logger.debug(f"[TECH] Node ai_analysis_node output_data: {output_data}")

    time.sleep(1)

    # 3. 第二个步骤 - Slack通知
    step_name = "发送Slack通知"
    business_logger.step_started(2, 3, step_name, "EXTERNAL_ACTION", "向客服团队发送Slack消息")

    input_data = {
        "channel": "#customer-support",
        "message": "🚨 新的客户请求需要处理\\n客户：张三\\n问题：物流查询 - 订单#12345\\n紧急程度：中等",
        "action": "send_message",
    }
    key_inputs = NodeExecutionBusinessLogger.extract_key_inputs(
        "EXTERNAL_ACTION", "SLACK", input_data
    )
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug(f"[TECH] Node slack_notification input data: {input_data}")

    time.sleep(1.5)

    output_data = {
        "success": True,
        "message_ts": "1704723456.789",
        "channel": "#customer-support",
        "text": "🚨 新的客户请求需要处理...",
    }
    key_outputs = NodeExecutionBusinessLogger.extract_key_outputs(
        "EXTERNAL_ACTION", "SLACK", output_data
    )
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 1.5, "SUCCESS")

    tech_logger.debug(
        "[TECH] Node slack_notification execution result: status=SUCCESS, duration=1.50s"
    )

    time.sleep(1)

    # 4. 第三个步骤 - 邮件发送
    step_name = "发送确认邮件"
    business_logger.step_started(3, 3, step_name, "EXTERNAL_ACTION", "向客户发送处理确认邮件")

    input_data = {
        "recipient": "zhangsan@example.com",
        "subject": "订单查询确认 - 订单#12345",
        "content": "尊敬的客户，我们已收到您的订单查询请求，正在为您处理中...",
    }
    key_inputs = NodeExecutionBusinessLogger.extract_key_inputs(
        "EXTERNAL_ACTION", "EMAIL", input_data
    )
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug(f"[TECH] Node email_confirmation input data: {input_data}")

    time.sleep(2)

    output_data = {"success": True, "message_id": "msg_abc123def456", "delivery_status": "sent"}
    key_outputs = NodeExecutionBusinessLogger.extract_key_outputs(
        "EXTERNAL_ACTION", "EMAIL", output_data
    )
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 2.0, "SUCCESS")

    tech_logger.debug(
        "[TECH] Node email_confirmation execution result: status=SUCCESS, duration=2.00s"
    )

    time.sleep(0.5)

    # 5. 工作流完成
    business_logger.log_separator("工作流执行完成")
    business_logger.workflow_completed(3, 3, 5.3, "SUCCESS")

    tech_logger.debug(
        "[TECH] Workflow execution summary: test-workflow-123 | Status: completed | Nodes: 3/3 successful | Errors: 0"
    )

    print()
    print("=" * 80)
    print("🎉 演示完成！")
    print("=" * 80)
    print()
    print("📊 日志分离效果总结:")
    print()
    print("✅ 业务日志特点:")
    print("   • 用中文描述，用户易理解")
    print("   • 重点显示步骤进展和关键结果")
    print("   • 清晰的输入输出摘要")
    print("   • 执行时间和状态一目了然")
    print()
    print("✅ 技术日志特点:")
    print("   • 包含完整的技术细节")
    print("   • 便于开发调试和问题排查")
    print("   • DEBUG级别，生产环境可关闭")
    print("   • 保留原有的详细信息")
    print()
    print("🎯 解决的问题:")
    print("   ❌ 之前：技术日志和业务信息混杂，用户难以理解")
    print("   ✅ 现在：完全分离，用户只看业务日志，开发者可查看技术日志")
    print()


def demo_error_scenario():
    """演示错误场景的日志"""

    print("\n" + "=" * 80)
    print("🚨 错误场景演示")
    print("=" * 80)
    print()

    execution_id = f"error-test-{int(time.time())}"
    business_logger = create_business_logger(execution_id, "邮件发送失败测试")
    tech_logger = setup_technical_logger()

    business_logger.workflow_started(2, "定时任务")

    # 第一步成功
    business_logger.step_started(1, 2, "数据准备", "ACTION", "准备邮件发送数据")
    business_logger.step_input_summary("数据准备", {"数据源": "customer_database", "查询条件": "未发送通知的用户"})
    business_logger.step_output_summary("数据准备", {"找到用户": 150, "数据状态": "准备完成"}, success=True)
    business_logger.step_completed("数据准备", 0.8, "SUCCESS")

    # 第二步失败
    business_logger.step_started(2, 2, "批量邮件发送", "EXTERNAL_ACTION", "发送营销邮件给用户")
    business_logger.step_input_summary("批量邮件发送", {"收件人数量": 150, "邮件模板": "marketing_template_v2"})

    tech_logger.error(
        "[TECH] Node bulk_email_send error: SMTP connection failed: Connection timeout after 30s"
    )
    tech_logger.debug("[TECH] Node bulk_email_send execution result: status=ERROR, duration=30.5s")

    # 业务日志记录用户友好的错误
    business_logger.step_error(
        "批量邮件发送", "SMTP connection failed: Connection timeout after 30s", "邮件服务器连接失败，请检查网络或联系管理员"
    )
    business_logger.step_completed("批量邮件发送", 30.5, "ERROR")

    business_logger.workflow_completed(2, 1, 31.3, "ERROR")

    print("\n📝 错误日志特点:")
    print("   • 业务日志提供用户友好的错误解释")
    print("   • 技术日志保留完整的错误堆栈")
    print("   • 明确区分技术错误和用户提示")


if __name__ == "__main__":
    # 运行演示
    demo_workflow_execution()

    # 询问是否演示错误场景
    print()
    choice = input("是否演示错误场景？(y/N): ").lower().strip()
    if choice == "y" or choice == "yes":
        demo_error_scenario()

    print("\n🎊 业务日志系统测试完成！")
    print("\n💡 下一步:")
    print("   1. 在实际workflow执行中测试")
    print("   2. 根据需要调整日志格式")
    print("   3. 配置生产环境的日志级别")
