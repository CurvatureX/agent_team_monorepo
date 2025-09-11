"""
Robust Workflow Execution Status Manager
健壮的工作流执行状态管理器 - 确保状态及时准确更新
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

# Import existing models and enums
try:
    from shared.models.db_models import ExecutionModel, ExecutionStatus

    from .unified_log_service import get_unified_log_service
except ImportError:
    # Fallback for when imports are not available
    ExecutionModel = None
    ExecutionStatus = None


logger = logging.getLogger(__name__)


class RobustStatusManager:
    """健壮的状态管理器"""

    def __init__(self, db: Session):
        self.db = db
        self.unified_log_service = get_unified_log_service()
        self.status_change_callbacks = {}
        self.max_retries = 3
        self.retry_delay_base = 1  # 秒

    async def update_execution_status_with_retry(
        self,
        execution_id: str,
        new_status: str,
        error_message: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> bool:
        """
        带重试机制的状态更新

        Args:
            execution_id: 执行ID
            new_status: 新状态
            error_message: 错误信息（可选）
            max_retries: 最大重试次数（可选，默认3次）

        Returns:
            bool: 更新是否成功
        """
        max_retries = max_retries or self.max_retries

        for attempt in range(max_retries):
            try:
                success = await self._attempt_status_update(execution_id, new_status, error_message)
                if success:
                    return True

            except Exception as e:
                logger.warning(
                    f"Status update attempt {attempt + 1}/{max_retries} failed for {execution_id}: {e}"
                )
                self.db.rollback()

                if attempt < max_retries - 1:
                    # 指数退避策略
                    delay = self.retry_delay_base * (2**attempt)
                    await asyncio.sleep(delay)

        logger.error(f"Failed to update status for {execution_id} after {max_retries} attempts")
        return False

    async def _attempt_status_update(
        self, execution_id: str, new_status: str, error_message: Optional[str]
    ) -> bool:
        """单次状态更新尝试"""
        # 获取执行记录
        db_execution = (
            self.db.query(ExecutionModel)
            .filter(ExecutionModel.execution_id == execution_id)
            .first()
        )

        if not db_execution:
            logger.error(f"Execution record not found: {execution_id}")
            return False

        # 记录旧状态用于通知
        old_status = db_execution.status

        # 验证状态转换是否合法
        if not self._is_valid_status_transition(old_status, new_status):
            logger.warning(
                f"Invalid status transition: {old_status} → {new_status} for {execution_id}"
            )

        # 更新状态
        db_execution.status = new_status
        db_execution.updated_at = datetime.now()

        # 设置错误信息
        if error_message:
            db_execution.error_message = error_message

        # 设置结束时间
        if new_status in [
            ExecutionStatus.SUCCESS.value,
            ExecutionStatus.ERROR.value,
            ExecutionStatus.CANCELED.value,
        ]:
            db_execution.end_time = int(datetime.now().timestamp())

        # 提交事务
        self.db.commit()

        # 记录状态变更日志
        logger.info(f"✅ Status updated: {execution_id} [{old_status} → {new_status}]")

        # 异步发送通知（不阻塞主流程）
        asyncio.create_task(
            self._notify_status_change(execution_id, old_status, new_status, error_message)
        )

        return True

    def _is_valid_status_transition(self, old_status: str, new_status: str) -> bool:
        """验证状态转换是否合法"""
        # 定义合法的状态转换
        valid_transitions = {
            "NEW": ["RUNNING", "CANCELED"],
            "RUNNING": ["SUCCESS", "ERROR", "PAUSED", "CANCELED"],
            "PAUSED": ["RUNNING", "CANCELED", "ERROR"],
            "SUCCESS": [],  # 终态
            "ERROR": [],  # 终态
            "CANCELED": [],  # 终态
        }

        allowed_new_states = valid_transitions.get(old_status, [])
        return new_status in allowed_new_states or old_status == new_status

    async def _notify_status_change(
        self,
        execution_id: str,
        old_status: str,
        new_status: str,
        error_message: Optional[str] = None,
    ):
        """发送状态变更通知"""
        try:
            # 1. 记录业务日志
            status_emoji = {
                "RUNNING": "🚀",
                "SUCCESS": "✅",
                "ERROR": "❌",
                "PAUSED": "⏸️",
                "CANCELED": "🚫",
            }

            emoji = status_emoji.get(new_status, "📊")
            user_message = f"{emoji} 执行状态更新: {old_status} → {new_status}"

            if error_message and new_status == "ERROR":
                user_message += f" | 错误: {error_message}"

            await self.unified_log_service.add_business_log(
                execution_id=execution_id,
                event_type="status_change",
                technical_message=f"Execution status changed from {old_status} to {new_status}",
                user_friendly_message=user_message,
                display_priority=7,  # 高优先级
                is_milestone=new_status in ["RUNNING", "SUCCESS", "ERROR"],
                data={
                    "old_status": old_status,
                    "new_status": new_status,
                    "error_message": error_message,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # 2. 触发状态变更回调
            if execution_id in self.status_change_callbacks:
                callback = self.status_change_callbacks[execution_id]
                try:
                    await callback(old_status, new_status, error_message)
                except Exception as e:
                    logger.error(f"Status change callback failed for {execution_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to notify status change for {execution_id}: {e}")

    def register_status_callback(self, execution_id: str, callback):
        """注册状态变更回调"""
        self.status_change_callbacks[execution_id] = callback

    def unregister_status_callback(self, execution_id: str):
        """注销状态变更回调"""
        self.status_change_callbacks.pop(execution_id, None)


class ExecutionTimeoutManager:
    """执行超时管理器"""

    def __init__(self, db: Session, status_manager: RobustStatusManager):
        self.db = db
        self.status_manager = status_manager
        self.timeout_thresholds = {
            "default": 2 * 3600,  # 2小时默认超时
            "long_running": 8 * 3600,  # 8小时长期任务超时
        }
        self.running = False

    async def start_monitoring(self):
        """启动超时监控"""
        if self.running:
            return

        self.running = True
        logger.info("🕐 Starting execution timeout monitoring")

        while self.running:
            try:
                await self.detect_and_handle_timeouts()
                await asyncio.sleep(300)  # 每5分钟检查一次
            except Exception as e:
                logger.error(f"Timeout monitoring error: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再继续

    async def stop_monitoring(self):
        """停止超时监控"""
        self.running = False
        logger.info("⏹️ Stopped execution timeout monitoring")

    async def detect_and_handle_timeouts(self):
        """检测并处理超时执行"""
        timeout_threshold = self.timeout_thresholds["default"]
        current_time = int(datetime.now().timestamp())
        cutoff_time = current_time - timeout_threshold

        # 查询可能超时的执行
        stalled_executions = (
            self.db.query(ExecutionModel)
            .filter(
                ExecutionModel.status == ExecutionStatus.RUNNING.value,
                ExecutionModel.start_time < cutoff_time,
            )
            .all()
        )

        for execution in stalled_executions:
            runtime_hours = (current_time - execution.start_time) / 3600
            logger.warning(
                f"⏰ Stalled execution detected: {execution.execution_id} "
                f"(running for {runtime_hours:.1f} hours)"
            )

            # 标记为超时错误
            await self.status_manager.update_execution_status_with_retry(
                execution.execution_id,
                ExecutionStatus.ERROR.value,
                f"Execution timeout - no activity for {runtime_hours:.1f} hours",
            )


class StatusConsistencyChecker:
    """状态一致性检查器"""

    def __init__(self, db: Session, status_manager: RobustStatusManager):
        self.db = db
        self.status_manager = status_manager

    async def check_and_fix_inconsistencies(self) -> Dict[str, List[str]]:
        """检查并修复状态不一致"""
        inconsistencies = {"fixed": [], "investigated": [], "errors": []}

        # 1. 检查状态与时间戳不一致
        issues = await self._find_status_timestamp_inconsistencies()
        for issue in issues:
            try:
                fixed = await self._fix_status_timestamp_issue(issue)
                if fixed:
                    inconsistencies["fixed"].append(f"{issue.execution_id}: 修复时间戳不一致")
                else:
                    inconsistencies["investigated"].append(f"{issue.execution_id}: 需要人工检查")
            except Exception as e:
                inconsistencies["errors"].append(f"{issue.execution_id}: {e}")

        # 2. 检查孤立的RUNNING状态
        orphaned_running = await self._find_orphaned_running_executions()
        for execution in orphaned_running:
            try:
                # 检查是否真的还在运行
                if await self._is_execution_actually_running(execution.execution_id):
                    inconsistencies["investigated"].append(f"{execution.execution_id}: 确实在运行")
                else:
                    # 标记为错误状态
                    await self.status_manager.update_execution_status_with_retry(
                        execution.execution_id,
                        ExecutionStatus.ERROR.value,
                        "Execution appears to be orphaned - marked as error",
                    )
                    inconsistencies["fixed"].append(f"{execution.execution_id}: 修复孤立执行")
            except Exception as e:
                inconsistencies["errors"].append(f"{execution.execution_id}: {e}")

        return inconsistencies

    async def _find_status_timestamp_inconsistencies(self):
        """查找状态与时间戳不一致的记录"""
        return self.db.execute(
            text(
                """
            SELECT execution_id, status, start_time, end_time
            FROM workflow_executions
            WHERE (status = 'RUNNING' AND end_time IS NOT NULL)
               OR (status IN ('SUCCESS', 'ERROR', 'CANCELED') AND end_time IS NULL)
               OR (start_time > end_time AND end_time IS NOT NULL)
            ORDER BY updated_at DESC
            LIMIT 100
        """
            )
        ).fetchall()

    async def _find_orphaned_running_executions(self):
        """查找孤立的RUNNING状态执行"""
        # 查找超过6小时仍在RUNNING的执行
        six_hours_ago = int((datetime.now() - timedelta(hours=6)).timestamp())

        return (
            self.db.query(ExecutionModel)
            .filter(
                ExecutionModel.status == ExecutionStatus.RUNNING.value,
                ExecutionModel.start_time < six_hours_ago,
            )
            .all()
        )

    async def _fix_status_timestamp_issue(self, issue) -> bool:
        """修复状态时间戳问题"""
        # 这里实现具体的修复逻辑
        # 返回True表示已修复，False表示需要人工干预
        if issue.status == "RUNNING" and issue.end_time:
            # RUNNING状态但有结束时间，可能是SUCCESS或ERROR未正确更新
            # 需要更多信息判断真实状态，此处返回False让人工检查
            return False

        if issue.status in ["SUCCESS", "ERROR", "CANCELED"] and not issue.end_time:
            # 已完成但没有结束时间，可以设置结束时间
            execution = (
                self.db.query(ExecutionModel)
                .filter(ExecutionModel.execution_id == issue.execution_id)
                .first()
            )
            if execution:
                execution.end_time = int(datetime.now().timestamp())
                self.db.commit()
                return True

        return False

    async def _is_execution_actually_running(self, execution_id: str) -> bool:
        """检查执行是否真的还在运行"""
        # 这里可以实现更复杂的检查逻辑
        # 例如检查进程、WebSocket连接、最后活动时间等
        # 目前简单返回False
        return False


# 集成到现有ExecutionService的装饰器
@asynccontextmanager
async def robust_status_context(execution_service):
    """为ExecutionService添加健壮状态管理的上下文管理器"""
    # 创建健壮状态管理器
    status_manager = RobustStatusManager(execution_service.db)
    timeout_manager = ExecutionTimeoutManager(execution_service.db, status_manager)
    consistency_checker = StatusConsistencyChecker(execution_service.db, status_manager)

    # 替换原有的状态更新方法
    original_update = execution_service._update_execution_status
    execution_service._update_execution_status = (
        lambda eid, status, error=None: asyncio.create_task(
            status_manager.update_execution_status_with_retry(eid, status, error)
        )
    )

    # 启动监控
    timeout_task = asyncio.create_task(timeout_manager.start_monitoring())

    try:
        yield {
            "status_manager": status_manager,
            "timeout_manager": timeout_manager,
            "consistency_checker": consistency_checker,
        }
    finally:
        # 清理资源
        await timeout_manager.stop_monitoring()
        timeout_task.cancel()

        # 恢复原有方法
        execution_service._update_execution_status = original_update


# 使用示例
async def enhanced_execution_service_example():
    """使用增强状态管理的示例"""
    from .execution_service import ExecutionService

    # 假设有一个执行服务实例
    execution_service = ExecutionService(db=None)  # 需要真实的db

    async with robust_status_context(execution_service) as managers:
        status_manager = managers["status_manager"]
        consistency_checker = managers["consistency_checker"]

        # 执行状态更新
        await status_manager.update_execution_status_with_retry("exec-123", "RUNNING")

        # 检查一致性
        inconsistencies = await consistency_checker.check_and_fix_inconsistencies()
        print(f"Fixed: {len(inconsistencies['fixed'])} issues")

        # 注册状态回调
        async def on_status_change(old, new, error):
            print(f"Status changed: {old} → {new}")

        status_manager.register_status_callback("exec-123", on_status_change)
