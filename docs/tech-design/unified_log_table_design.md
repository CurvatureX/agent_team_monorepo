# 统一日志表设计 - 同时支持技术调试和用户友好日志

## 现状分析

目前系统中存在两种日志需求：

### 1. 现有的技术调试日志 (`ExecutionLog`)
```python
class ExecutionLog(BaseModel):
    timestamp: int
    level: str  # DEBUG, INFO, ERROR
    message: str
    node_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
```

**用途**:
- 内部技术调试
- AI Agent分析
- 系统故障排查
- 详细的技术信息记录

### 2. 新增的用户友好日志需求
**用途**:
- 前端用户界面展示
- 用户友好的执行进度追踪
- 业务流程可视化
- 精简的关键信息展示

## 设计方案: 扩展现有表结构

### 方案选择：单表双用途设计

通过扩展现有的`workflow_execution_logs`表，添加`log_category`字段来区分日志类型，同时保持向后兼容性。

### 扩展后的表结构

```sql
CREATE TABLE workflow_execution_logs (
    -- 基础字段
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR(255) NOT NULL,

    -- 日志分类 (新增字段)
    log_category VARCHAR(20) NOT NULL DEFAULT 'technical', -- 'technical' | 'business'

    -- 日志内容
    event_type VARCHAR(50) NOT NULL,  -- workflow_started, step_completed等
    level VARCHAR(10) NOT NULL DEFAULT 'INFO',  -- DEBUG, INFO, ERROR
    message TEXT NOT NULL,

    -- 结构化数据
    data JSONB DEFAULT '{}',

    -- 节点信息
    node_id VARCHAR(255),
    node_name VARCHAR(255),
    node_type VARCHAR(100),

    -- 执行进度信息
    step_number INTEGER,
    total_steps INTEGER,
    progress_percentage DECIMAL(5,2),

    -- 性能信息
    duration_seconds INTEGER,

    -- 用户友好信息 (新增字段)
    user_friendly_message TEXT,  -- 用户友好的消息(中文)
    display_priority INTEGER DEFAULT 5,  -- 显示优先级 1-10 (10最重要)
    is_milestone BOOLEAN DEFAULT FALSE,  -- 是否为里程碑事件

    -- 技术调试信息 (新增字段)
    technical_details JSONB DEFAULT '{}',  -- 详细的技术信息
    stack_trace TEXT,  -- 错误堆栈
    performance_metrics JSONB DEFAULT '{}',  -- 性能指标

    -- 索引字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 索引
    INDEX idx_execution_logs_execution_id (execution_id),
    INDEX idx_execution_logs_category (log_category),
    INDEX idx_execution_logs_level (level),
    INDEX idx_execution_logs_event_type (event_type),
    INDEX idx_execution_logs_priority (display_priority),
    INDEX idx_execution_logs_created_at (created_at),
    INDEX idx_execution_logs_business_query (execution_id, log_category, display_priority) -- 复合索引
);
```

## 数据库模型更新

### 扩展的枚举类型

```python
class LogCategoryEnum(str, enum.Enum):
    """日志分类枚举"""
    TECHNICAL = "technical"    # 技术调试日志
    BUSINESS = "business"      # 用户友好业务日志

class DisplayPriorityEnum(int, enum.Enum):
    """显示优先级枚举"""
    LOWEST = 1      # 最低优先级 - 详细调试信息
    LOW = 3         # 低优先级 - 一般技术信息
    NORMAL = 5      # 普通优先级 - 常规业务信息
    HIGH = 7        # 高优先级 - 重要业务事件
    CRITICAL = 10   # 最高优先级 - 关键里程碑事件
```

### 更新后的数据库模型

```python
class WorkflowExecutionLog(Base, BaseModel):
    """统一的工作流执行日志表 - 支持技术和业务两种用途"""

    __tablename__ = "workflow_execution_logs"

    # 基础字段
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    execution_id = Column(String(255), nullable=False, index=True)

    # 日志分类 (新增)
    log_category = Column(
        Enum(LogCategoryEnum),
        nullable=False,
        default=LogCategoryEnum.TECHNICAL,
        index=True
    )

    # 日志内容
    event_type = Column(Enum(LogEventTypeEnum), nullable=False, index=True)
    level = Column(Enum(LogLevelEnum), nullable=False, default=LogLevelEnum.INFO, index=True)
    message = Column(Text, nullable=False)

    # 结构化数据
    data = Column(JSON, nullable=True, default=dict)

    # 节点信息
    node_id = Column(String(255), nullable=True, index=True)
    node_name = Column(String(255), nullable=True)
    node_type = Column(String(100), nullable=True)

    # 执行进度
    step_number = Column(Integer, nullable=True)
    total_steps = Column(Integer, nullable=True)
    progress_percentage = Column(Numeric(5, 2), nullable=True)

    # 性能信息
    duration_seconds = Column(Integer, nullable=True)

    # 用户友好信息 (新增)
    user_friendly_message = Column(Text, nullable=True)
    display_priority = Column(Integer, nullable=False, default=5, index=True)
    is_milestone = Column(Boolean, nullable=False, default=False)

    # 技术调试信息 (新增)
    technical_details = Column(JSON, nullable=True, default=dict)
    stack_trace = Column(Text, nullable=True)
    performance_metrics = Column(JSON, nullable=True, default=dict)

    # 时间戳
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<WorkflowExecutionLog(id='{self.id}', execution_id='{self.execution_id}', category='{self.log_category}', event_type='{self.event_type}')>"

    @property
    def is_business_log(self) -> bool:
        """检查是否为业务日志"""
        return self.log_category == LogCategoryEnum.BUSINESS

    @property
    def is_technical_log(self) -> bool:
        """检查是否为技术日志"""
        return self.log_category == LogCategoryEnum.TECHNICAL

    @property
    def display_message(self) -> str:
        """获取显示消息 - 优先使用用户友好消息"""
        return self.user_friendly_message or self.message

    @property
    def is_high_priority(self) -> bool:
        """检查是否为高优先级日志"""
        return self.display_priority >= DisplayPriorityEnum.HIGH
```

## 服务层设计更新

### 统一的日志服务接口

```python
class UnifiedExecutionLogService:
    """统一执行日志服务 - 支持技术和业务日志"""

    async def add_technical_log(
        self,
        execution_id: str,
        level: str,
        message: str,
        event_type: LogEventType,
        node_id: Optional[str] = None,
        technical_details: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        performance_metrics: Optional[Dict[str, Any]] = None
    ):
        """添加技术调试日志"""
        log_entry = UnifiedLogEntry(
            execution_id=execution_id,
            log_category=LogCategoryEnum.TECHNICAL,
            level=level,
            message=message,
            event_type=event_type,
            node_id=node_id,
            technical_details=technical_details,
            stack_trace=stack_trace,
            performance_metrics=performance_metrics,
            display_priority=DisplayPriorityEnum.LOW  # 技术日志通常优先级较低
        )
        await self._store_log_entry(log_entry)

    async def add_business_log(
        self,
        execution_id: str,
        event_type: LogEventType,
        technical_message: str,
        user_friendly_message: str,
        level: str = "INFO",
        display_priority: int = DisplayPriorityEnum.NORMAL,
        is_milestone: bool = False,
        step_info: Optional[Dict[str, Any]] = None
    ):
        """添加业务友好日志"""
        log_entry = UnifiedLogEntry(
            execution_id=execution_id,
            log_category=LogCategoryEnum.BUSINESS,
            level=level,
            message=technical_message,
            user_friendly_message=user_friendly_message,
            event_type=event_type,
            display_priority=display_priority,
            is_milestone=is_milestone,
            step_number=step_info.get("step_number") if step_info else None,
            total_steps=step_info.get("total_steps") if step_info else None,
            progress_percentage=step_info.get("progress_percentage") if step_info else None,
        )
        await self._store_log_entry(log_entry)

    async def get_business_logs(
        self,
        execution_id: str,
        min_priority: int = DisplayPriorityEnum.NORMAL,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取业务友好日志 - 前端用户界面"""
        return await self._get_logs_with_filter(
            execution_id=execution_id,
            log_category=LogCategoryEnum.BUSINESS,
            min_priority=min_priority,
            limit=limit,
            offset=offset
        )

    async def get_technical_logs(
        self,
        execution_id: str,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取技术调试日志 - AI Agent分析"""
        return await self._get_logs_with_filter(
            execution_id=execution_id,
            log_category=LogCategoryEnum.TECHNICAL,
            level=level,
            limit=limit,
            offset=offset
        )

    async def get_milestone_logs(
        self,
        execution_id: str
    ) -> List[Dict[str, Any]]:
        """获取里程碑日志 - 重要事件概览"""
        return await self._get_logs_with_filter(
            execution_id=execution_id,
            log_category=LogCategoryEnum.BUSINESS,
            is_milestone=True
        )
```

## API设计更新

### 分类查询端点

```python
# 业务日志端点 - 前端用户界面
@router.get("/executions/{execution_id}/logs/business")
async def get_business_logs(
    execution_id: str,
    min_priority: int = Query(default=5, description="最小显示优先级"),
    milestones_only: bool = Query(default=False, description="只返回里程碑事件"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    """获取用户友好的业务日志"""

# 技术日志端点 - 调试和AI分析
@router.get("/executions/{execution_id}/logs/technical")
async def get_technical_logs(
    execution_id: str,
    level: Optional[str] = Query(default=None),
    include_stack_trace: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """获取技术调试日志"""

# 里程碑事件端点 - 执行概览
@router.get("/executions/{execution_id}/logs/milestones")
async def get_milestone_logs(execution_id: str):
    """获取执行里程碑事件"""
```

## 数据迁移策略

### 1. 数据库迁移脚本

```sql
-- 添加新字段
ALTER TABLE workflow_execution_logs
ADD COLUMN log_category VARCHAR(20) NOT NULL DEFAULT 'technical',
ADD COLUMN user_friendly_message TEXT,
ADD COLUMN display_priority INTEGER NOT NULL DEFAULT 5,
ADD COLUMN is_milestone BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN technical_details JSONB DEFAULT '{}',
ADD COLUMN stack_trace TEXT,
ADD COLUMN performance_metrics JSONB DEFAULT '{}',
ADD COLUMN progress_percentage DECIMAL(5,2);

-- 创建新索引
CREATE INDEX idx_execution_logs_category ON workflow_execution_logs(log_category);
CREATE INDEX idx_execution_logs_priority ON workflow_execution_logs(display_priority);
CREATE INDEX idx_execution_logs_business_query ON workflow_execution_logs(execution_id, log_category, display_priority);

-- 迁移现有数据 (将现有记录标记为技术日志)
UPDATE workflow_execution_logs
SET log_category = 'technical',
    display_priority = CASE
        WHEN level = 'ERROR' THEN 7
        WHEN level = 'INFO' THEN 3
        ELSE 1
    END;
```

### 2. 代码兼容性

```python
# 向后兼容的工厂函数
def create_log_entry_from_legacy(
    legacy_log: ExecutionLog,
    execution_id: str,
    log_category: LogCategoryEnum = LogCategoryEnum.TECHNICAL
) -> UnifiedLogEntry:
    """从现有日志格式创建统一日志条目"""
    return UnifiedLogEntry(
        execution_id=execution_id,
        log_category=log_category,
        level=legacy_log.level,
        message=legacy_log.message,
        node_id=legacy_log.node_id,
        technical_details=legacy_log.extra_data or {},
        event_type=LogEventType.SEPARATOR,  # 默认事件类型
        created_at=datetime.fromtimestamp(legacy_log.timestamp)
    )
```

## 使用示例

### 1. 记录业务日志

```python
# 工作流开始
await log_service.add_business_log(
    execution_id="exec-123",
    event_type=LogEventType.WORKFLOW_STARTED,
    technical_message="Starting workflow execution with 4 nodes",
    user_friendly_message="🚀 开始执行客户服务工作流 (共4个步骤)",
    display_priority=DisplayPriorityEnum.HIGH,
    is_milestone=True,
    step_info={"total_steps": 4}
)

# 步骤完成
await log_service.add_business_log(
    execution_id="exec-123",
    event_type=LogEventType.STEP_COMPLETED,
    technical_message="AI analysis step completed successfully",
    user_friendly_message="✅ AI智能分析完成 - 识别为订单查询请求",
    display_priority=DisplayPriorityEnum.NORMAL,
    step_info={"step_number": 2, "total_steps": 4, "progress_percentage": 50.0}
)
```

### 2. 记录技术日志

```python
# 详细的技术信息
await log_service.add_technical_log(
    execution_id="exec-123",
    level="DEBUG",
    message="OpenAI API call completed",
    event_type=LogEventType.STEP_OUTPUT,
    node_id="ai_analysis_node",
    technical_details={
        "api_endpoint": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4",
        "token_usage": {"prompt_tokens": 150, "completion_tokens": 89},
        "response_time_ms": 1234
    },
    performance_metrics={
        "latency_ms": 1234,
        "tokens_per_second": 72.1
    }
)

# 错误日志
await log_service.add_technical_log(
    execution_id="exec-123",
    level="ERROR",
    message="Slack API rate limit exceeded",
    event_type=LogEventType.STEP_ERROR,
    node_id="slack_notification",
    technical_details={"status_code": 429, "retry_after": 60},
    stack_trace="Traceback (most recent call last):\n..."
)
```

## 前端查询示例

### 业务日志查询 (用户界面)

```typescript
// 获取用户友好的执行概览
const businessLogs = await fetch(
  `/v1/workflows/executions/${executionId}/logs/business?min_priority=5&limit=50`
);

// 只获取重要里程碑
const milestones = await fetch(
  `/v1/workflows/executions/${executionId}/logs/milestones`
);
```

### 技术日志查询 (调试界面)

```typescript
// 获取详细技术信息 (管理员/开发者)
const technicalLogs = await fetch(
  `/v1/workflows/executions/${executionId}/logs/technical?include_stack_trace=true`
);
```

## 优势总结

### ✅ **单表设计优势**
1. **数据一致性**: 所有日志在同一个事务中
2. **查询效率**: 避免JOIN操作，通过索引快速过滤
3. **存储优化**: 减少表数量，简化维护
4. **扩展性**: 新增字段灵活，向后兼容

### ✅ **业务价值**
1. **用户体验**: 前端显示友好的中文消息和进度
2. **开发效率**: 技术人员有详细的调试信息
3. **AI分析**: 结构化的技术数据便于AI处理
4. **运维监控**: 分优先级的日志便于告警和监控

### ✅ **性能优化**
1. **索引策略**: 针对不同查询模式优化索引
2. **分层查询**: 用户界面只查询必要信息
3. **缓存友好**: Redis缓存可以按类别分别缓存
4. **清理策略**: 可按类别和优先级制定不同的保留策略

这个设计方案既保持了现有系统的兼容性，又满足了新的用户友好日志需求，是一个平衡的解决方案。
