#!/usr/bin/env python3
"""
自动运行的业务日志系统演示
展示新的日志分离效果
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
    """设置技术日志器"""
    tech_logger = logging.getLogger("workflow_engine.demo_technical")

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "🔧 TECH | %(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    tech_logger.addHandler(handler)
    tech_logger.setLevel(logging.DEBUG)
    tech_logger.propagate = False

    return tech_logger


def main():
    """主演示函数"""

    print("=" * 80)
    print("🧪 业务日志系统演示 - 新的清晰日志分离")
    print("=" * 80)
    print()

    # 创建日志器
    execution_id = f"demo-{int(time.time())}"
    business_logger = create_business_logger(execution_id, "客户服务自动化")
    tech_logger = setup_technical_logger()

    print("🎯 即将展示:")
    print("   🔄 WORKFLOW | ... = 业务日志 (用户友好，中文描述)")
    print("   🔧 TECH | ...     = 技术日志 (开发调试，英文详情)")
    print()

    # 工作流开始
    business_logger.log_separator("工作流执行开始")
    business_logger.workflow_started(3, "客户支持请求")
    tech_logger.debug("Starting workflow execution: customer-service-automation")
    tech_logger.debug("Workflow definition loaded with 3 nodes")

    time.sleep(0.5)

    # 步骤1: AI分析
    step_name = "AI智能分析"
    business_logger.step_started(1, 3, step_name, "AI_AGENT", "使用ChatGPT分析客户请求")

    input_data = {"content": "我的订单#12345还没发货，已经等了3天了", "system_prompt": "分析客户请求类型和紧急程度"}
    key_inputs = NodeExecutionBusinessLogger.extract_key_inputs(
        "AI_AGENT", "OPENAI_CHATGPT", input_data
    )
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug(f"Node ai_analysis executing with OpenAI client")
    tech_logger.debug(f"Input parameters: model=gpt-4, temperature=0.3")

    time.sleep(1)

    output_data = {
        "content": "请求类型：物流查询\\n紧急程度：中等\\n建议：立即查询订单状态",
        "metadata": {"token_usage": {"total": 156}},
    }
    key_outputs = NodeExecutionBusinessLogger.extract_key_outputs(
        "AI_AGENT", "OPENAI_CHATGPT", output_data
    )
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 1.2, "SUCCESS")

    tech_logger.debug("AI analysis completed successfully")
    tech_logger.debug(f"Token usage: 156 total, execution time: 1.2s")

    time.sleep(0.5)

    # 步骤2: Slack通知
    step_name = "Slack团队通知"
    business_logger.step_started(2, 3, step_name, "EXTERNAL_ACTION", "通知客服团队处理")

    input_data = {"channel": "#customer-support", "message": "新客户请求：订单查询 - 优先级中等"}
    key_inputs = NodeExecutionBusinessLogger.extract_key_inputs(
        "EXTERNAL_ACTION", "SLACK", input_data
    )
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug("Connecting to Slack API")
    tech_logger.debug("Sending message to channel: #customer-support")

    time.sleep(0.8)

    output_data = {"success": True, "message_ts": "1704723456.789"}
    key_outputs = NodeExecutionBusinessLogger.extract_key_outputs(
        "EXTERNAL_ACTION", "SLACK", output_data
    )
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 0.8, "SUCCESS")

    tech_logger.debug("Slack message sent successfully")
    tech_logger.debug(f"Message timestamp: 1704723456.789")

    time.sleep(0.5)

    # 步骤3: 邮件确认
    step_name = "发送确认邮件"
    business_logger.step_started(3, 3, step_name, "EXTERNAL_ACTION", "向客户发送处理确认")

    input_data = {
        "recipient": "customer@example.com",
        "subject": "订单查询确认",
        "content": "我们已收到您的查询，正在处理中...",
    }
    key_inputs = NodeExecutionBusinessLogger.extract_key_inputs(
        "EXTERNAL_ACTION", "EMAIL", input_data
    )
    business_logger.step_input_summary(step_name, key_inputs)

    tech_logger.debug("Initializing SMTP connection")
    tech_logger.debug("Preparing email with template: customer_confirmation")

    time.sleep(1.5)

    output_data = {"success": True, "message_id": "msg_abc123"}
    key_outputs = NodeExecutionBusinessLogger.extract_key_outputs(
        "EXTERNAL_ACTION", "EMAIL", output_data
    )
    business_logger.step_output_summary(step_name, key_outputs, success=True)
    business_logger.step_completed(step_name, 1.5, "SUCCESS")

    tech_logger.debug("Email sent successfully via SMTP")
    tech_logger.debug(f"Message ID: msg_abc123")

    # 工作流完成
    business_logger.log_separator("工作流执行完成")
    business_logger.workflow_completed(3, 3, 3.5, "SUCCESS")

    tech_logger.debug("Workflow execution completed successfully")
    tech_logger.debug("Cleaning up execution context and resources")

    print()
    print("=" * 80)
    print("📊 日志分离效果对比")
    print("=" * 80)
    print()
    print("✅ 业务日志 (🔄 WORKFLOW) 特点:")
    print("   • 使用中文，便于用户理解")
    print("   • 显示具体的业务步骤和结果")
    print("   • 重点突出输入输出的关键信息")
    print("   • 清晰的进度和状态指示")
    print()
    print("✅ 技术日志 (🔧 TECH) 特点:")
    print("   • 英文技术详情，便于开发调试")
    print("   • 包含系统内部状态和参数")
    print("   • DEBUG级别，生产环境可关闭")
    print("   • 保留完整的技术信息追踪")
    print()
    print("🎯 解决的问题:")
    print("   ❌ 之前：业务信息和技术细节混杂，用户看不懂")
    print("   ✅ 现在：完全分离，用户友好的业务日志 + 详细的技术日志")
    print()

    # 演示错误场景
    print("🚨 错误场景演示:")
    print("-" * 40)

    error_business_logger = create_business_logger(f"error-{int(time.time())}", "邮件发送测试")
    error_business_logger.step_started(1, 1, "批量邮件", "EXTERNAL_ACTION", "发送营销邮件")
    error_business_logger.step_input_summary("批量邮件", {"收件人": "150位用户", "模板": "营销推广V2"})

    tech_logger.error("SMTP connection timeout after 30 seconds")
    tech_logger.error("Failed to establish connection to mail server")

    error_business_logger.step_error("批量邮件", "SMTP connection timeout", "邮件服务器连接超时，请联系技术支持")
    error_business_logger.step_completed("批量邮件", 30.0, "ERROR")
    error_business_logger.workflow_completed(1, 0, 30.0, "ERROR")

    print()
    print("✅ 错误处理也是分离的:")
    print("   • 业务日志：用户友好的错误说明和建议")
    print("   • 技术日志：详细的错误堆栈和调试信息")
    print()
    print("🎊 业务日志系统演示完成!")


if __name__ == "__main__":
    main()
