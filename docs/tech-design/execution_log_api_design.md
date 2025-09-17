# Workflow执行日志API设计

## 概述

为了支持前端实时显示用户友好的workflow运行日志,我们需要设计两套API接口:

1. **流式接口** - 用于返回运行中的workflow的实时日志
2. **普通接口** - 用于返回历史运行记录的日志

## 技术架构

### 核心组件

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │───▶│  FastAPI Routes  │───▶│ ExecutionLog    │
│   (Vue/React)   │    │  (WebSocket/HTTP)│    │ Service         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                      │
        │                        │                      │
        ▼                        ▼                      ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  WebSocket/SSE  │    │   HTTP REST      │    │     Redis       │
│  实时推送      │    │   历史查询      │    │   (实时缓存)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   PostgreSQL    │
                                               │   (历史存储)    │
                                               └─────────────────┘
```

### 数据流设计

1. **执行时数据流**:
   ```
   Workflow Execution → Business Logger → ExecutionLogService
         ↓
   Redis Cache (实时) + Database (持久化) + WebSocket推送
   ```

2. **查询时数据流**:
   ```
   前端请求 → API路由 → ExecutionLogService
         ↓
   Redis (优先) → Memory Cache (备选) → Database (历史)
   ```

## API接口设计

### 1. 流式接口 (实时日志推送)

#### 1.1 WebSocket接口

**接口地址**: `ws://localhost:8002/v1/workflows/executions/{execution_id}/logs/stream`

**连接参数**:
- `execution_id`: 执行ID
- `auth_token`: 认证token (查询参数)

**消息格式**:
```typescript
interface LogStreamMessage {
  execution_id: string;
  event_type: "workflow_started" | "step_started" | "step_input" |
             "step_output" | "step_completed" | "step_error" |
             "workflow_progress" | "workflow_completed" | "separator";
  timestamp: string;
  message: string;
  level: "INFO" | "ERROR" | "DEBUG";
  data?: {
    step_name?: string;
    step_number?: number;
    total_steps?: number;
    progress_percentage?: number;
    key_inputs?: Record<string, any>;
    key_outputs?: Record<string, any>;
    error_details?: string;
    performance_stats?: Record<string, any>;
  };
}
```

**连接示例**:
```javascript
const ws = new WebSocket('ws://localhost:8002/v1/workflows/executions/exec-123/logs/stream?auth_token=xxx');

ws.onmessage = function(event) {
  const logEntry = JSON.parse(event.data);
  console.log('实时日志:', logEntry.message);

  // 根据事件类型更新UI
  switch(logEntry.event_type) {
    case 'workflow_started':
      updateWorkflowStatus('running');
      break;
    case 'step_started':
      updateStepStatus(logEntry.data.step_number, 'running');
      break;
    case 'step_completed':
      updateStepStatus(logEntry.data.step_number, 'completed');
      break;
    case 'workflow_progress':
      updateProgressBar(logEntry.data.progress_percentage);
      break;
  }
};
```

#### 1.2 Server-Sent Events (SSE) 接口

**接口地址**: `GET /v1/workflows/executions/{execution_id}/logs/stream`

**请求头**:
```
Accept: text/event-stream
Cache-Control: no-cache
Authorization: Bearer <token>
```

**响应格式**:
```
Content-Type: text/event-stream

event: log_entry
data: {"execution_id":"exec-123","event_type":"step_started",...}

event: log_entry
data: {"execution_id":"exec-123","event_type":"step_completed",...}

event: close
data: {"reason":"workflow_completed"}
```

### 2. 普通接口 (历史日志查询)

#### 2.1 获取执行日志列表

**接口地址**: `GET /v1/workflows/executions/{execution_id}/logs`

**请求参数**:
```typescript
interface LogQueryParams {
  // 分页参数
  limit?: number;        // 每页条数，范围1-100，默认50
  page?: number;         // 页码，从1开始，默认1
  cursor?: string;       // 游标分页，用于大数据集

  // 排序参数
  sort_order?: 'asc' | 'desc';  // 时间排序，默认asc (最早到最新)

  // 过滤参数
  log_category?: 'business' | 'technical';  // 日志分类
  level?: 'INFO' | 'ERROR' | 'DEBUG';       // 日志级别过滤
  event_type?: string;                      // 事件类型过滤
  min_priority?: number;                    // 最小显示优先级 (1-10)
  milestones_only?: boolean;                // 只返回里程碑事件

  // 时间范围过滤
  start_time?: string;   // 开始时间 (ISO8601)
  end_time?: string;     // 结束时间 (ISO8601)
}
```

**响应格式**:
```typescript
interface LogQueryResponse {
  execution_id: string;
  total_count: number;
  filtered_count: number;    // 过滤后的总数
  logs: LogEntry[];
  pagination: PaginationInfo;
}

interface PaginationInfo {
  current_page: number;      // 当前页码
  total_pages: number;       // 总页数
  page_size: number;         // 每页大小
  has_next: boolean;         // 是否有下一页
  has_prev: boolean;         // 是否有上一页
  next_cursor?: string;      // 下一页游标 (游标分页)
  prev_cursor?: string;      // 上一页游标 (游标分页)
}

interface LogEntry {
  id: string;                // 日志记录唯一ID
  execution_id: string;
  log_category: 'business' | 'technical';
  event_type: string;
  timestamp: string;         // ISO8601格式，用于排序
  message: string;
  user_friendly_message?: string;  // 业务日志的友好消息
  level: string;
  display_priority?: number;
  is_milestone?: boolean;

  // 节点信息
  node_id?: string;
  node_name?: string;
  node_type?: string;

  // 进度信息
  step_number?: number;
  total_steps?: number;
  progress_percentage?: number;
  duration_seconds?: number;

  // 扩展数据
  data?: Record<string, any>;
  technical_details?: Record<string, any>;  // 技术日志详情
  performance_metrics?: Record<string, any>;
}
```

**请求示例**:
```bash
# 基本查询 - 第一页，默认50条，按时间升序
GET /v1/workflows/executions/exec-123/logs

# 指定页码和每页数量
GET /v1/workflows/executions/exec-123/logs?page=2&limit=20

# 查询业务日志，按时间降序（最新在前）
GET /v1/workflows/executions/exec-123/logs?log_category=business&sort_order=desc

# 查询错误日志，高优先级
GET /v1/workflows/executions/exec-123/logs?level=ERROR&min_priority=7

# 游标分页（推荐用于大数据集）
GET /v1/workflows/executions/exec-123/logs?cursor=eyJpZCI6InV1aWQtMTIzIiwidGltZXN0YW1wIjoiMjAyNS0wOS0wOFQxMDowMDowMFoifQ==

# 时间范围查询
GET /v1/workflows/executions/exec-123/logs?start_time=2025-09-08T10:00:00Z&end_time=2025-09-08T11:00:00Z

# 只查询里程碑事件
GET /v1/workflows/executions/exec-123/logs?milestones_only=true
```

## 分页机制详细设计

### 1. 双重分页策略

我们支持两种分页方式来适应不同的使用场景：

#### 1.1 传统页码分页 (Offset-based Pagination)
- **适用场景**: 少量数据（&lt;10,000条）、需要跳页、显示总页数
- **参数**: `page` + `limit`
- **优点**: 简单直观，支持跳页
- **缺点**: 大数据集性能差，可能出现数据重复/遗漏

```sql
-- 实现方式
SELECT * FROM workflow_execution_logs
WHERE execution_id = 'exec-123'
ORDER BY created_at ASC
LIMIT 50 OFFSET 100;  -- 第3页，每页50条
```

#### 1.2 游标分页 (Cursor-based Pagination)
- **适用场景**: 大量数据、实时数据流、追求一致性
- **参数**: `cursor` + `limit`
- **优点**: 性能稳定，数据一致性好
- **缺点**: 不支持跳页，不能显示总页数

```sql
-- 实现方式
SELECT * FROM workflow_execution_logs
WHERE execution_id = 'exec-123'
  AND (created_at, id) > ('2025-09-08T10:30:00Z', 'last-uuid')
ORDER BY created_at ASC, id ASC
LIMIT 50;
```

### 2. 游标编码设计

游标包含排序字段和唯一标识符，确保分页一致性：

```typescript
interface CursorData {
  timestamp: string;  // 排序字段：created_at
  id: string;         // 唯一标识：记录ID
  direction: 'next' | 'prev';  // 分页方向
}

// 游标编码示例
const cursor = btoa(JSON.stringify({
  timestamp: "2025-09-08T10:30:00.123Z",
  id: "550e8400-e29b-41d4-a716-446655440000",
  direction: "next"
}));
// 结果: eyJ0aW1lc3RhbXAiOiIyMDI1LTA5LTA4VDEwOjMwOjAwLjEyM1oiLCJpZCI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsImRpcmVjdGlvbiI6Im5leHQifQ==
```

### 3. 时间排序策略

#### 3.1 主排序字段
- **主要**: `created_at` (时间戳)
- **次要**: `id` (UUID) - 确保相同时间记录的稳定排序

#### 3.2 排序选项
```typescript
type SortOrder = 'asc' | 'desc';

// asc: 最早到最新 (默认) - 适合查看执行过程
// desc: 最新到最早 - 适合查看最新状态
```

#### 3.3 索引优化
```sql
-- 复合索引优化排序和分页性能
CREATE INDEX idx_logs_execution_time_id
ON workflow_execution_logs (execution_id, created_at, id);

-- 分类查询优化索引
CREATE INDEX idx_logs_category_time
ON workflow_execution_logs (execution_id, log_category, created_at, id);
```

### 4. 响应格式详解

```typescript
interface PaginatedResponse {
  execution_id: string;
  total_count: number;        // 未过滤的总记录数
  filtered_count: number;     // 应用过滤条件后的总数
  logs: LogEntry[];          // 当前页的日志记录
  pagination: {
    // 页码分页信息
    current_page: number;     // 当前页码 (1-based)
    total_pages: number;      // 总页数 (仅页码分页)
    page_size: number;        // 每页大小
    has_next: boolean;        // 是否有下一页
    has_prev: boolean;        // 是否有上一页

    // 游标分页信息
    next_cursor?: string;     // 下一页游标
    prev_cursor?: string;     // 上一页游标

    // 元数据
    sort_order: 'asc' | 'desc';
    filters_applied: string[]; // 已应用的过滤器列表
  };
}
```

### 5. 分页性能优化

#### 5.1 查询优化策略
```sql
-- 1. 使用复合索引避免排序
CREATE INDEX idx_execution_logs_optimal
ON workflow_execution_logs (
  execution_id,      -- 过滤条件
  log_category,      -- 分类过滤
  created_at,        -- 排序字段
  id                 -- 稳定排序
) WHERE log_category = 'business';  -- 部分索引

-- 2. 分区表（大数据集）
-- 按执行ID或时间分区，提升查询性能
```

#### 5.2 缓存策略
```typescript
interface CacheStrategy {
  // Redis缓存热点数据
  recent_logs: string;        // "logs:recent:exec-123" -> 最近100条
  page_cache: string;         // "logs:page:exec-123:1" -> 第1页数据
  count_cache: string;        // "logs:count:exec-123" -> 总数缓存

  // 缓存过期策略
  recent_ttl: 300;           // 5分钟
  page_ttl: 60;              // 1分钟
  count_ttl: 180;            // 3分钟
}
```

### 6. 前端集成示例

#### 6.1 React Hook实现
```typescript
interface UsePaginatedLogsOptions {
  executionId: string;
  pageSize?: number;
  sortOrder?: 'asc' | 'desc';
  filters?: LogQueryParams;
  useCursor?: boolean;  // 是否使用游标分页
}

const usePaginatedLogs = (options: UsePaginatedLogsOptions) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [cursor, setCursor] = useState<string>();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [pagination, setPagination] = useState<PaginationInfo>();
  const [loading, setLoading] = useState(false);

  const fetchLogs = async (page?: number, nextCursor?: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();

      if (options.useCursor && nextCursor) {
        params.append('cursor', nextCursor);
      } else if (!options.useCursor && page) {
        params.append('page', page.toString());
      }

      params.append('limit', (options.pageSize || 50).toString());
      params.append('sort_order', options.sortOrder || 'asc');

      // 添加过滤参数
      if (options.filters) {
        Object.entries(options.filters).forEach(([key, value]) => {
          if (value !== undefined) params.append(key, value.toString());
        });
      }

      const response = await fetch(
        `/v1/workflows/executions/${options.executionId}/logs?${params}`
      );

      const data: LogQueryResponse = await response.json();

      setLogs(data.logs);
      setPagination(data.pagination);

      if (options.useCursor) {
        setCursor(data.pagination.next_cursor);
      } else {
        setCurrentPage(data.pagination.current_page);
      }

    } finally {
      setLoading(false);
    }
  };

  const nextPage = () => {
    if (options.useCursor && pagination?.next_cursor) {
      fetchLogs(undefined, pagination.next_cursor);
    } else if (!options.useCursor && pagination?.has_next) {
      fetchLogs(currentPage + 1);
    }
  };

  const prevPage = () => {
    if (options.useCursor && pagination?.prev_cursor) {
      fetchLogs(undefined, pagination.prev_cursor);
    } else if (!options.useCursor && pagination?.has_prev) {
      fetchLogs(currentPage - 1);
    }
  };

  const goToPage = (page: number) => {
    if (!options.useCursor) {
      fetchLogs(page);
    }
  };

  return {
    logs,
    pagination,
    loading,
    nextPage,
    prevPage,
    goToPage,
    refresh: () => fetchLogs(options.useCursor ? undefined : 1)
  };
};
```

#### 6.2 分页组件示例
```typescript
const PaginationControls: React.FC<{
  pagination: PaginationInfo;
  onPageChange: (page: number) => void;
  onNext: () => void;
  onPrev: () => void;
}> = ({ pagination, onPageChange, onNext, onPrev }) => {
  return (
    <div className="flex items-center justify-between mt-4">
      <div className="text-sm text-gray-600">
        显示 {((pagination.current_page - 1) * pagination.page_size) + 1} - {' '}
        {Math.min(pagination.current_page * pagination.page_size, pagination.filtered_count)}
        {' '} 条，共 {pagination.filtered_count} 条记录
      </div>

      <div className="flex items-center space-x-2">
        {/* 上一页按钮 */}
        <button
          onClick={onPrev}
          disabled={!pagination.has_prev}
          className="px-3 py-1 border rounded disabled:opacity-50"
        >
          上一页
        </button>

        {/* 页码选择（仅页码分页） */}
        {pagination.total_pages && (
          <div className="flex space-x-1">
            {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
              const page = i + Math.max(1, pagination.current_page - 2);
              return (
                <button
                  key={page}
                  onClick={() => onPageChange(page)}
                  className={`px-3 py-1 border rounded ${
                    page === pagination.current_page ? 'bg-blue-500 text-white' : ''
                  }`}
                >
                  {page}
                </button>
              );
            })}
          </div>
        )}

        {/* 下一页按钮 */}
        <button
          onClick={onNext}
          disabled={!pagination.has_next}
          className="px-3 py-1 border rounded disabled:opacity-50"
        >
          下一页
        </button>
      </div>
    </div>
  );
};
```

### 7. 错误处理和边界情况

```typescript
interface PaginationErrors {
  INVALID_PAGE: "页码必须大于0";
  INVALID_LIMIT: "每页条数必须在1-100之间";
  INVALID_CURSOR: "游标格式无效或已过期";
  EXECUTION_NOT_FOUND: "执行记录不存在";
  NO_MORE_DATA: "已到达数据末尾";
}

// 边界情况处理
const handlePaginationEdgeCases = {
  // 1. 空结果集
  emptyResult: {
    logs: [],
    pagination: {
      current_page: 1,
      total_pages: 0,
      page_size: 50,
      has_next: false,
      has_prev: false
    }
  },

  // 2. 单页结果
  singlePage: {
    has_next: false,
    has_prev: false,
    total_pages: 1
  },

  // 3. 超出范围的页码
  outOfRange: "自动重定向到最后一页或第一页",

  // 4. 过期的游标
  expiredCursor: "返回错误，要求重新从第一页开始"
};
```

这个设计支持了你要求的所有功能：
- ✅ 每页最多100条记录
- ✅ 支持页码和游标两种分页方式
- ✅ 按时间顺序排序（升序/降序）
- ✅ 完整的分页元数据
- ✅ 性能优化和缓存策略
- ✅ 前端集成友好

#### 2.2 获取活跃执行列表

**接口地址**: `GET /v1/workflows/executions/active`

**响应格式**:
```typescript
interface ActiveExecutionsResponse {
  executions: ActiveExecution[];
  total_count: number;
}

interface ActiveExecution {
  execution_id: string;
  workflow_name: string;
  status: "RUNNING" | "PAUSED" | "SUCCESS" | "ERROR";
  started_at: string;
  last_activity: string;
  current_step?: string;
  progress_percentage?: number;
}
```

#### 2.3 获取执行统计信息

**接口地址**: `GET /v1/workflows/executions/{execution_id}/stats`

**响应格式**:
```typescript
interface ExecutionStats {
  execution_id: string;
  workflow_name: string;
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  total_duration: number;
  average_step_time: number;
  slowest_step: {
    name: string;
    duration: number;
  };
  performance_metrics: Record<string, any>;
}
```

### 3. 管理接口

#### 3.1 清理历史日志

**接口地址**: `DELETE /v1/workflows/executions/logs/cleanup`

**请求参数**:
```typescript
interface CleanupParams {
  before_date: string;    // 删除此日期前的日志
  keep_recent?: number;   // 保留最近N条执行的日志
}
```

#### 3.2 获取日志统计

**接口地址**: `GET /v1/workflows/logs/stats`

**响应格式**:
```typescript
interface LogStats {
  total_executions: number;
  active_executions: number;
  total_log_entries: number;
  log_size_mb: number;
  cache_hit_rate: number;
}
```

## 错误处理

### 标准错误响应

```typescript
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: any;
  };
  request_id: string;
  timestamp: string;
}
```

### 常见错误码

- `EXECUTION_NOT_FOUND`: 执行ID不存在
- `UNAUTHORIZED`: 认证失败
- `RATE_LIMITED`: 请求过于频繁
- `WEBSOCKET_CONNECTION_FAILED`: WebSocket连接失败
- `LOG_SERVICE_UNAVAILABLE`: 日志服务不可用

## 性能考虑

### 1. 缓存策略
- **Redis缓存**: 实时日志24小时过期
- **内存缓存**: 最近1000条日志备选
- **数据库**: 历史日志持久化存储

### 2. 并发控制
- **WebSocket连接限制**: 每个执行最多10个连接
- **请求频率限制**: 每秒最多20次查询请求
- **日志大小限制**: 单条日志最大10KB

### 3. 数据清理
- **自动清理**: 超过30天的日志自动删除
- **大小限制**: Redis缓存总大小限制1GB
- **压缩存储**: 历史日志采用压缩存储

## 安全考虑

### 1. 认证授权
- **JWT Token**: API访问需要有效token
- **权限控制**: 只能访问自己的执行日志
- **WebSocket认证**: 连接时验证token

### 2. 数据保护
- **敏感信息过滤**: 自动过滤密码、API密钥
- **日志脱敏**: PII数据自动脱敏
- **传输加密**: HTTPS/WSS强制加密

## 前端集成指南

### 1. React Hook示例

```typescript
// useWorkflowLogs.ts
import { useState, useEffect, useRef } from 'react';

export const useWorkflowLogs = (executionId: string) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'error'>('connecting');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8002/v1/workflows/executions/${executionId}/logs/stream`);
    wsRef.current = ws;

    ws.onopen = () => setStatus('connected');
    ws.onerror = () => setStatus('error');
    ws.onmessage = (event) => {
      const logEntry = JSON.parse(event.data);
      setLogs(prev => [...prev, logEntry]);
    };

    return () => ws.close();
  }, [executionId]);

  return { logs, status };
};
```

### 2. Vue Composition API示例

```typescript
// useWorkflowLogs.ts
import { ref, onMounted, onUnmounted } from 'vue';

export const useWorkflowLogs = (executionId: string) => {
  const logs = ref<LogEntry[]>([]);
  const status = ref<'connecting' | 'connected' | 'error'>('connecting');
  let ws: WebSocket | null = null;

  onMounted(() => {
    ws = new WebSocket(`ws://localhost:8002/v1/workflows/executions/${executionId}/logs/stream`);

    ws.onopen = () => status.value = 'connected';
    ws.onerror = () => status.value = 'error';
    ws.onmessage = (event) => {
      const logEntry = JSON.parse(event.data);
      logs.value.push(logEntry);
    };
  });

  onUnmounted(() => {
    ws?.close();
  });

  return { logs, status };
};
```

## 测试计划

### 1. 单元测试
- ExecutionLogService的各个方法
- Redis连接和缓存逻辑
- WebSocket连接管理
- 日志格式化和过滤

### 2. 集成测试
- 完整workflow执行的日志记录
- WebSocket实时推送准确性
- 历史日志查询性能
- 错误场景的处理

### 3. 性能测试
- 1000个并发WebSocket连接
- 大量历史日志查询
- Redis缓存命中率测试
- 内存使用量监控

## 实现优先级

### Phase 1 (高优先级)
- [ ] ExecutionLogService核心实现
- [ ] Redis缓存机制
- [ ] 基础WebSocket流式接口
- [ ] 历史日志查询接口

### Phase 2 (中优先级)
- [ ] SSE流式接口实现
- [ ] 完整的错误处理
- [ ] 性能优化和缓存策略
- [ ] 前端集成示例

### Phase 3 (低优先级)
- [ ] 高级查询和过滤
- [ ] 日志管理和清理
- [ ] 监控和统计接口
- [ ] 安全加固和审计

这个设计提供了完整的实时和历史日志API,支持高性能的前端实时显示需求。
