#!/usr/bin/env python3
"""
ExecutionService状态管理增强补丁
对现有ExecutionService进行最小侵入性的状态管理增强
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def enhance_execution_service_status_management(execution_service):
    """
    增强ExecutionService的状态管理功能

    Args:
        execution_service: 现有的ExecutionService实例
    """

    # 保存原始方法
    original_update_status = execution_service._update_execution_status

    async def enhanced_update_execution_status(
        execution_id: str, status: str, error_message: str = None, max_retries: int = 3
    ):
        """增强的状态更新方法 - 带重试和通知"""

        for attempt in range(max_retries):
            try:
                # 获取旧状态用于通知
                from shared.models.db_models import ExecutionModel

                db_execution = (
                    execution_service.db.query(ExecutionModel)
                    .filter(ExecutionModel.execution_id == execution_id)
                    .first()
                )

                old_status = db_execution.status if db_execution else "UNKNOWN"

                # 调用原始更新方法
                original_update_status(execution_id, status, error_message)

                # 添加状态变更日志
                logger.info(f"✅ Enhanced status update: {execution_id} [{old_status} → {status}]")

                # 异步记录业务日志（不阻塞主流程）
                asyncio.create_task(
                    log_status_change_to_business_log(
                        execution_id, old_status, status, error_message
                    )
                )

                return True

            except Exception as e:
                logger.warning(
                    f"Status update attempt {attempt + 1} failed for {execution_id}: {e}"
                )
                execution_service.db.rollback()

                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # 指数退避
                else:
                    logger.error(
                        f"❌ Failed to update status after {max_retries} attempts: {execution_id}"
                    )
                    raise

    # 替换原始方法
    execution_service._update_execution_status_enhanced = enhanced_update_execution_status

    # 添加超时检测方法
    async def detect_stalled_executions(timeout_hours: int = 2):
        """检测并处理超时执行"""
        try:
            from sqlalchemy import func

            from shared.models.db_models import ExecutionModel, ExecutionStatus

            timeout_threshold = timeout_hours * 3600
            current_time = int(datetime.now().timestamp())

            stalled_executions = (
                execution_service.db.query(ExecutionModel)
                .filter(
                    ExecutionModel.status == ExecutionStatus.RUNNING.value,
                    ExecutionModel.start_time < current_time - timeout_threshold,
                )
                .all()
            )

            for execution in stalled_executions:
                runtime_hours = (current_time - execution.start_time) / 3600
                logger.warning(
                    f"⏰ Stalled execution detected: {execution.execution_id} "
                    f"(running {runtime_hours:.1f}h)"
                )

                # 使用增强的状态更新
                await enhanced_update_execution_status(
                    execution.execution_id,
                    ExecutionStatus.ERROR.value,
                    f"Execution timeout after {runtime_hours:.1f} hours",
                )

            return len(stalled_executions)

        except Exception as e:
            logger.error(f"Failed to detect stalled executions: {e}")
            return 0

    execution_service.detect_stalled_executions = detect_stalled_executions

    # 添加状态一致性检查
    async def check_status_consistency():
        """检查状态一致性"""
        try:
            from sqlalchemy import text

            # 查找不一致的记录
            inconsistent_query = text(
                """
                SELECT execution_id, status, start_time, end_time
                FROM workflow_executions
                WHERE (status = 'RUNNING' AND end_time IS NOT NULL)
                   OR (status IN ('SUCCESS', 'ERROR', 'CANCELED') AND end_time IS NULL)
                LIMIT 50
            """
            )

            inconsistent_records = execution_service.db.execute(inconsistent_query).fetchall()

            fixed_count = 0
            for record in inconsistent_records:
                logger.warning(f"Status inconsistency found: {record.execution_id}")

                # 简单修复：为已完成的执行添加结束时间
                if record.status in ["SUCCESS", "ERROR", "CANCELED"] and not record.end_time:
                    from shared.models.db_models import ExecutionModel

                    db_execution = (
                        execution_service.db.query(ExecutionModel)
                        .filter(ExecutionModel.execution_id == record.execution_id)
                        .first()
                    )

                    if db_execution:
                        db_execution.end_time = int(datetime.now().timestamp())
                        execution_service.db.commit()
                        fixed_count += 1
                        logger.info(f"✅ Fixed missing end_time for {record.execution_id}")

            return {"inconsistent_found": len(inconsistent_records), "fixed": fixed_count}

        except Exception as e:
            logger.error(f"Status consistency check failed: {e}")
            return {"inconsistent_found": 0, "fixed": 0}

    execution_service.check_status_consistency = check_status_consistency

    logger.info("✅ ExecutionService status management enhanced")
    return execution_service


async def log_status_change_to_business_log(
    execution_id: str, old_status: str, new_status: str, error_message: Optional[str] = None
):
    """记录状态变更到业务日志"""
    try:
        from workflow_engine.services.unified_log_service import get_unified_log_service

        status_emoji = {
            "NEW": "🆕",
            "RUNNING": "🚀",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "PAUSED": "⏸️",
            "CANCELED": "🚫",
        }

        emoji = status_emoji.get(new_status, "📊")
        user_message = f"{emoji} 执行状态: {old_status} → {new_status}"

        if error_message and new_status == "ERROR":
            user_message += f" | {error_message}"

        log_service = get_unified_log_service()
        await log_service.add_business_log(
            execution_id=execution_id,
            event_type="status_change",
            technical_message=f"Status: {old_status} → {new_status}",
            user_friendly_message=user_message,
            display_priority=7,
            is_milestone=new_status in ["RUNNING", "SUCCESS", "ERROR"],
            data={
                "old_status": old_status,
                "new_status": new_status,
                "error_message": error_message,
                "timestamp": datetime.now().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Failed to log status change: {e}")


class ExecutionStatusMonitor:
    """执行状态监控器 - 后台任务"""

    def __init__(self, execution_service):
        self.execution_service = execution_service
        self.running = False
        self.check_interval = 300  # 5分钟

    async def start_monitoring(self):
        """启动状态监控"""
        if self.running:
            return

        self.running = True
        logger.info("🔍 Starting execution status monitoring")

        while self.running:
            try:
                # 检测超时执行
                stalled_count = await self.execution_service.detect_stalled_executions()
                if stalled_count > 0:
                    logger.info(f"Detected and handled {stalled_count} stalled executions")

                # 检查状态一致性
                consistency_result = await self.execution_service.check_status_consistency()
                if consistency_result["fixed"] > 0:
                    logger.info(f"Fixed {consistency_result['fixed']} status inconsistencies")

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Status monitoring error: {e}")
                await asyncio.sleep(60)  # 出错后短暂等待

    async def stop_monitoring(self):
        """停止状态监控"""
        self.running = False
        logger.info("⏹️ Stopped execution status monitoring")


# 使用示例和集成指南
def integrate_enhanced_status_management():
    """集成增强状态管理的示例"""

    print("🔧 ExecutionService状态管理增强集成指南")
    print("=" * 60)

    integration_code = """
# 1. 在ExecutionService初始化时增强
from workflow_engine.services.execution_service import ExecutionService
from execution_service_status_enhancement import enhance_execution_service_status_management

def create_enhanced_execution_service(db):
    service = ExecutionService(db)
    enhanced_service = enhance_execution_service_status_management(service)
    return enhanced_service

# 2. 启动后台状态监控
async def start_status_monitoring(execution_service):
    monitor = ExecutionStatusMonitor(execution_service)
    monitoring_task = asyncio.create_task(monitor.start_monitoring())
    return monitoring_task

# 3. 在主应用中集成
async def main():
    db = get_database_session()
    execution_service = create_enhanced_execution_service(db)

    # 启动状态监控
    monitoring_task = await start_status_monitoring(execution_service)

    # 应用主逻辑...

    # 关闭时停止监控
    await monitor.stop_monitoring()
    monitoring_task.cancel()

# 4. 手动调用增强功能
async def manual_status_check(execution_service):
    # 检测超时执行
    stalled_count = await execution_service.detect_stalled_executions()
    print(f"Found {stalled_count} stalled executions")

    # 检查状态一致性
    consistency = await execution_service.check_status_consistency()
    print(f"Consistency check: {consistency}")
    """

    print(integration_code)

    print("\n📋 集成检查清单:")
    checklist = [
        "✅ 导入增强模块",
        "✅ 在服务初始化时调用enhance_execution_service_status_management()",
        "✅ 启动ExecutionStatusMonitor后台任务",
        "✅ 在应用关闭时停止监控",
        "✅ 配置日志级别以查看状态更新",
        "🔧 可选: 添加状态变更WebSocket通知",
        "🔧 可选: 配置监控报警机制",
    ]

    for item in checklist:
        print(f"  {item}")

    print(f"\n⚡ 预期效果:")
    effects = [
        "状态更新失败时自动重试",
        "状态变更自动记录到业务日志",
        "自动检测和处理超时执行",
        "自动修复状态一致性问题",
        "详细的状态变更日志记录",
        "后台持续监控异常状态",
    ]

    for effect in effects:
        print(f"  ✅ {effect}")


if __name__ == "__main__":
    integrate_enhanced_status_management()
