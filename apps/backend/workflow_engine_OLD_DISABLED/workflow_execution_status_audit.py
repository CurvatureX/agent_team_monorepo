#!/usr/bin/env python3
"""
Workflow Execution Status Audit & Enhancement
确保workflow_executions表的status字段及时和准确更新的审计和增强脚本
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StatusUpdatePoint:
    """状态更新点"""

    location: str
    trigger: str
    old_status: str
    new_status: str
    critical: bool
    has_error_handling: bool
    description: str


class ExecutionStatusAudit:
    """执行状态审计器"""

    def __init__(self):
        self.status_points = self._identify_status_update_points()
        self.critical_gaps = []
        self.enhancement_recommendations = []

    def _identify_status_update_points(self) -> List[StatusUpdatePoint]:
        """识别所有状态更新点"""
        return [
            # 1. 工作流创建
            StatusUpdatePoint(
                location="ExecutionService.execute_workflow() - Line 72",
                trigger="Workflow execution request received",
                old_status="None",
                new_status="NEW",
                critical=True,
                has_error_handling=True,
                description="初始创建执行记录，状态设为NEW",
            ),
            # 2. 开始执行
            StatusUpdatePoint(
                location="ExecutionService._execute_workflow_sync() - Line 160",
                trigger="Background execution starts",
                old_status="NEW",
                new_status="RUNNING",
                critical=True,
                has_error_handling=True,
                description="后台执行开始前更新状态为RUNNING",
            ),
            # 3. 执行成功完成
            StatusUpdatePoint(
                location="ExecutionService._execute_workflow_background() - Line 776-777",
                trigger="Workflow completes successfully",
                old_status="RUNNING",
                new_status="SUCCESS",
                critical=True,
                has_error_handling=True,
                description="工作流正常完成，状态更新为SUCCESS",
            ),
            # 4. 执行失败
            StatusUpdatePoint(
                location="ExecutionService._execute_workflow_background() - Line 778-779",
                trigger="Workflow execution fails",
                old_status="RUNNING",
                new_status="ERROR",
                critical=True,
                has_error_handling=True,
                description="工作流执行失败，状态更新为ERROR",
            ),
            # 5. 暂停状态
            StatusUpdatePoint(
                location="ExecutionService._execute_workflow_background() - Line 782",
                trigger="Workflow pauses for human input",
                old_status="RUNNING",
                new_status="PAUSED",
                critical=True,
                has_error_handling=True,
                description="工作流暂停等待人工输入",
            ),
            # 6. 异常处理
            StatusUpdatePoint(
                location="ExecutionService._execute_workflow_background() - Line 815",
                trigger="Background execution exception",
                old_status="RUNNING",
                new_status="ERROR",
                critical=True,
                has_error_handling=True,
                description="后台执行异常，状态设为ERROR",
            ),
            # 7. 手动取消
            StatusUpdatePoint(
                location="ExecutionService.cancel_execution() - Line 269",
                trigger="User cancels execution",
                old_status="RUNNING|PAUSED",
                new_status="CANCELED",
                critical=True,
                has_error_handling=True,
                description="用户手动取消执行",
            ),
            # 8. 恢复执行
            StatusUpdatePoint(
                location="ExecutionService.resume_workflow() - Line 330",
                trigger="Resume from pause",
                old_status="PAUSED",
                new_status="RUNNING",
                critical=True,
                has_error_handling=False,  # 需要改进
                description="从暂停状态恢复执行",
            ),
        ]

    def audit_status_tracking(self) -> Dict[str, any]:
        """审计状态跟踪机制"""
        print("🔍 工作流执行状态跟踪审计")
        print("=" * 80)

        audit_results = {
            "total_status_points": len(self.status_points),
            "critical_points": len([p for p in self.status_points if p.critical]),
            "points_with_error_handling": len(
                [p for p in self.status_points if p.has_error_handling]
            ),
            "identified_gaps": [],
            "recommendations": [],
        }

        # 1. 分析关键状态更新点
        print("\n📋 关键状态更新点分析:")
        for i, point in enumerate(self.status_points, 1):
            status = "✅" if point.has_error_handling else "⚠️"
            critical = "🔥" if point.critical else "📝"
            print(f"  {i}. {status}{critical} {point.old_status} → {point.new_status}")
            print(f"     位置: {point.location}")
            print(f"     触发: {point.trigger}")
            print(f"     描述: {point.description}")

            if not point.has_error_handling:
                audit_results["identified_gaps"].append(f"缺少错误处理: {point.location}")
            print()

        # 2. 识别潜在问题
        print("\n🚨 识别的潜在问题:")
        gaps = [
            "数据库事务失败时状态可能不一致",
            "网络中断时状态更新可能丢失",
            "长时间运行的工作流状态可能过时",
            "并发执行时状态竞争条件",
            "系统重启后运行中的执行状态未恢复",
        ]

        for i, gap in enumerate(gaps, 1):
            print(f"  {i}. ⚠️ {gap}")
            audit_results["identified_gaps"].append(gap)

        # 3. 改进建议
        print("\n💡 状态跟踪改进建议:")
        recommendations = [
            "添加状态更新重试机制",
            "实现状态变更事件通知",
            "添加状态一致性检查",
            "实现执行超时检测",
            "添加状态历史记录",
            "实现故障恢复机制",
        ]

        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. 🔧 {rec}")
            audit_results["recommendations"].append(rec)

        return audit_results

    def generate_status_monitoring_queries(self):
        """生成状态监控查询"""
        print("\n📊 状态监控SQL查询:")
        print("-" * 50)

        queries = {
            "活跃执行统计": """
                SELECT status, COUNT(*) as count
                FROM workflow_executions
                WHERE created_at > NOW() - INTERVAL '1 hour'
                GROUP BY status
                ORDER BY count DESC;
            """,
            "长时间运行检测": """
                SELECT execution_id, workflow_id, status,
                       EXTRACT(EPOCH FROM NOW() - to_timestamp(start_time)) / 3600 as hours_running
                FROM workflow_executions
                WHERE status = 'RUNNING'
                  AND start_time < EXTRACT(EPOCH FROM NOW() - INTERVAL '2 hours')
                ORDER BY hours_running DESC;
            """,
            "状态异常检测": """
                SELECT execution_id, status, start_time, end_time,
                       CASE
                           WHEN status = 'RUNNING' AND end_time IS NOT NULL THEN '状态不一致'
                           WHEN status IN ('SUCCESS', 'ERROR') AND end_time IS NULL THEN '结束时间缺失'
                           ELSE '正常'
                       END as issue
                FROM workflow_executions
                WHERE created_at > NOW() - INTERVAL '24 hours'
                HAVING issue != '正常';
            """,
            "执行失败分析": """
                SELECT DATE(to_timestamp(start_time)) as date,
                       COUNT(CASE WHEN status = 'ERROR' THEN 1 END) as failed_count,
                       COUNT(*) as total_count,
                       ROUND(COUNT(CASE WHEN status = 'ERROR' THEN 1 END)::numeric / COUNT(*) * 100, 2) as failure_rate
                FROM workflow_executions
                WHERE start_time > EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days')
                GROUP BY DATE(to_timestamp(start_time))
                ORDER BY date DESC;
            """,
        }

        for name, query in queries.items():
            print(f"\n-- {name}")
            print(query.strip())


class ExecutionStatusEnhancer:
    """执行状态增强器"""

    def __init__(self):
        self.enhancements = []

    def design_robust_status_updates(self):
        """设计健壮的状态更新机制"""
        print("\n🛠 设计健壮的状态更新机制")
        print("=" * 80)

        print("\n1. 🔄 状态更新重试机制:")
        retry_mechanism = """
        async def update_execution_status_with_retry(
            self, execution_id: str, new_status: str,
            error_message: str = None, max_retries: int = 3
        ):
            for attempt in range(max_retries):
                try:
                    db_execution = self.db.query(ExecutionModel).filter(
                        ExecutionModel.execution_id == execution_id
                    ).first()

                    if not db_execution:
                        logger.error(f"Execution not found: {execution_id}")
                        return False

                    old_status = db_execution.status
                    db_execution.status = new_status
                    db_execution.updated_at = datetime.now()

                    if error_message:
                        db_execution.error_message = error_message

                    if new_status in ['SUCCESS', 'ERROR', 'CANCELED']:
                        db_execution.end_time = int(datetime.now().timestamp())

                    self.db.commit()

                    # 记录状态变更
                    logger.info(f"Status updated: {execution_id} {old_status} → {new_status}")

                    # 发送状态变更通知
                    await self._notify_status_change(execution_id, old_status, new_status)

                    return True

                except Exception as e:
                    logger.warning(f"Status update attempt {attempt + 1} failed: {e}")
                    self.db.rollback()
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # 指数退避

            logger.error(f"Failed to update status after {max_retries} attempts")
            return False
        """
        print(retry_mechanism)

        print("\n2. 📢 状态变更通知机制:")
        notification_mechanism = """
        async def _notify_status_change(self, execution_id: str, old_status: str, new_status: str):
            # WebSocket通知
            await self.websocket_manager.broadcast_status_update(
                execution_id, old_status, new_status
            )

            # 业务日志记录
            await self.unified_log_service.add_business_log(
                execution_id=execution_id,
                event_type="status_change",
                technical_message=f"Execution status changed from {old_status} to {new_status}",
                user_friendly_message=f"📊 执行状态更新: {old_status} → {new_status}",
                display_priority=7,
                is_milestone=new_status in ['RUNNING', 'SUCCESS', 'ERROR']
            )
        """
        print(notification_mechanism)

        print("\n3. 🕐 执行超时检测:")
        timeout_detection = """
        async def detect_stalled_executions(self):
            # 检测超时执行
            timeout_threshold = 2 * 3600  # 2小时
            current_time = int(datetime.now().timestamp())

            stalled_executions = self.db.query(ExecutionModel).filter(
                ExecutionModel.status == ExecutionStatus.RUNNING.value,
                ExecutionModel.start_time < current_time - timeout_threshold
            ).all()

            for execution in stalled_executions:
                logger.warning(f"Stalled execution detected: {execution.execution_id}")

                # 标记为超时
                await self.update_execution_status_with_retry(
                    execution.execution_id,
                    ExecutionStatus.ERROR.value,
                    "Execution timeout - no activity for 2 hours"
                )
        """
        print(timeout_detection)

        print("\n4. 🔧 状态一致性检查:")
        consistency_check = """
        async def check_status_consistency(self):
            # 检查状态不一致的记录
            inconsistent_records = self.db.execute(text('''
                SELECT execution_id, status, start_time, end_time
                FROM workflow_executions
                WHERE (status = 'RUNNING' AND end_time IS NOT NULL)
                   OR (status IN ('SUCCESS', 'ERROR') AND end_time IS NULL)
                   OR (start_time > end_time AND end_time IS NOT NULL)
            ''')).fetchall()

            for record in inconsistent_records:
                logger.warning(f"Status inconsistency: {record.execution_id}")

                # 自动修复逻辑
                if record.status == 'RUNNING' and record.end_time:
                    # 运行中但有结束时间，可能是未正确更新
                    await self._investigate_and_fix_status(record.execution_id)
        """
        print(consistency_check)


def main():
    """主函数 - 运行完整的状态审计和增强建议"""
    print("🚀 工作流执行状态跟踪 - 全面审计与增强")
    print("=" * 100)

    # 1. 执行审计
    auditor = ExecutionStatusAudit()
    audit_results = auditor.audit_status_tracking()

    # 2. 生成监控查询
    auditor.generate_status_monitoring_queries()

    # 3. 设计增强机制
    enhancer = ExecutionStatusEnhancer()
    enhancer.design_robust_status_updates()

    # 4. 总结报告
    print("\n" + "=" * 100)
    print("📋 审计总结报告")
    print("=" * 100)

    print(f"\n📊 统计信息:")
    print(f"   总状态更新点: {audit_results['total_status_points']}")
    print(f"   关键更新点: {audit_results['critical_points']}")
    print(f"   有错误处理: {audit_results['points_with_error_handling']}")
    print(f"   发现问题: {len(audit_results['identified_gaps'])}")

    print(f"\n🎯 关键行动项:")
    print("   1. ✅ 现有状态更新点基本完整")
    print("   2. 🔧 需要添加重试机制和错误处理")
    print("   3. 📢 实现状态变更通知系统")
    print("   4. 🕐 添加超时检测和自动恢复")
    print("   5. 🔍 部署状态监控查询")
    print("   6. 🧪 增加状态一致性检查")

    print(f"\n⚡ 实施优先级:")
    print("   🔥 高: 状态更新重试机制")
    print("   🔥 高: 超时检测和自动标记")
    print("   📋 中: 状态变更通知系统")
    print("   📋 中: 一致性检查定时任务")
    print("   📝 低: 状态历史记录功能")

    print(f"\n🚀 系统现状评估:")
    print("   ✅ 基础状态跟踪机制已实现")
    print("   ✅ 关键状态转换点已覆盖")
    print("   ⚠️ 缺少故障恢复机制")
    print("   ⚠️ 需要增强错误处理")
    print("   📈 建议实施监控和告警")


if __name__ == "__main__":
    main()
