# 测试模式说明

## 当前状态

workflow_scheduler 当前处于**内测模式**，所有触发器在满足条件时会发送邮件通知而不是实际执行 workflow。

## 邮件通知

- **目标邮箱**: z1771485029@gmail.com
- **通知内容**: 包含触发器类型、workflow ID、触发时间和相关数据
- **触发器类型**: 支持所有类型 (Cron, Manual, Webhook, Email, GitHub)

## 配置邮件发送

要启用实际的邮件发送，需要在 `.env` 文件中配置 SMTP 设置：

```bash
# SMTP 配置
SMTP_HOST=smtp.migadu.com
SMTP_PORT=465
SMTP_USERNAME=your-email@domain.com
SMTP_PASSWORD=your-app-password
SMTP_USE_SSL=true
SMTP_SENDER_EMAIL=your-email@domain.com
SMTP_SENDER_NAME=Workflow Scheduler
```

## 测试触发器

可以通过以下方式测试各种触发器：

### 1. 手动触发器
```bash
curl -X POST http://localhost:8003/api/v1/triggers/workflows/test-workflow/manual \
  -H "Content-Type: application/json" \
  -d '{"confirmation": true}'
```

### 2. Webhook 触发器
```bash
curl -X POST http://localhost:8000/api/v1/public/webhook/test-workflow \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "data": "sample"}'
```

### 3. 运行测试脚本
```bash
python test_notification.py
```

## 恢复正常执行模式

要切换回正常的 workflow 执行模式，需要：

### 1. 修改 BaseTrigger 类

在 `workflow_scheduler/app/triggers/base.py` 中：

```python
# 将当前的 _trigger_workflow 方法重命名为 _trigger_workflow_testing
async def _trigger_workflow_testing(self, trigger_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
    # 当前的通知逻辑...

# 将 _trigger_workflow_original 方法重命名为 _trigger_workflow
async def _trigger_workflow(self, trigger_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
    # 原始的 workflow_engine 调用逻辑...
```

### 2. 移除 NotificationService 依赖

从 `BaseTrigger.__init__` 中移除：
```python
# 删除这行
self._notification_service = NotificationService()
```

### 3. 更新配置

确保 `workflow_engine_url` 正确配置：
```bash
WORKFLOW_ENGINE_URL=http://workflow-engine:8002
```

## 日志监控

无论是否发送邮件，所有触发事件都会在日志中记录：

```bash
# 查看日志
tail -f logs/workflow_scheduler.log

# 或者运行时查看
python -m workflow_scheduler.app.main
```

## 触发器状态

可以通过 API 检查触发器状态：

```bash
# 健康检查
curl http://localhost:8003/health

# 触发器状态
curl http://localhost:8003/api/v1/triggers/workflows/test-workflow/status

# 所有触发器健康状态
curl http://localhost:8003/api/v1/triggers/health
```

## 部署记录

查看部署状态：

```bash
# 所有部署
curl http://localhost:8003/api/v1/deployment/workflows

# 特定部署状态
curl http://localhost:8003/api/v1/deployment/workflows/test-workflow/status
```
