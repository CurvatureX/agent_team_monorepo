# 前端集成示例 - Workflow执行日志API

本文档提供了完整的前端集成示例，展示如何在React、Vue和原生JavaScript中使用Workflow执行日志API。

## 目录

1. [React集成示例](#react集成示例)
2. [Vue.js集成示例](#vuejs集成示例)
3. [原生JavaScript示例](#原生javascript示例)
4. [API使用指南](#api使用指南)
5. [WebSocket连接管理](#websocket连接管理)
6. [错误处理最佳实践](#错误处理最佳实践)

---

## React集成示例

### 1. React Hook - useWorkflowLogs

```tsx
// hooks/useWorkflowLogs.ts
import { useState, useEffect, useRef, useCallback } from 'react';

export interface LogEntry {
  execution_id: string;
  event_type: string;
  timestamp: string;
  message: string;
  level: 'INFO' | 'ERROR' | 'DEBUG';
  data?: Record<string, any>;
}

export interface WorkflowLogsState {
  logs: LogEntry[];
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  error: string | null;
}

export const useWorkflowLogs = (executionId: string, autoConnect = true) => {
  const [state, setState] = useState<WorkflowLogsState>({
    logs: [],
    isConnected: false,
    connectionStatus: 'disconnected',
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setState(prev => ({
      ...prev,
      connectionStatus: 'connecting',
      error: null
    }));

    const wsUrl = `ws://localhost:8002/v1/workflows/executions/${executionId}/logs/stream`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setState(prev => ({
        ...prev,
        isConnected: true,
        connectionStatus: 'connected',
        error: null,
      }));
      reconnectAttempts.current = 0;
      console.log('WebSocket连接已建立');
    };

    ws.onmessage = (event) => {
      try {
        const logEntry: LogEntry = JSON.parse(event.data);
        setState(prev => ({
          ...prev,
          logs: [...prev.logs, logEntry],
        }));
      } catch (error) {
        console.error('解析日志消息失败:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      setState(prev => ({
        ...prev,
        connectionStatus: 'error',
        error: 'WebSocket连接错误',
      }));
    };

    ws.onclose = (event) => {
      setState(prev => ({
        ...prev,
        isConnected: false,
        connectionStatus: 'disconnected',
      }));

      // 自动重连逻辑
      if (autoConnect && reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.pow(2, reconnectAttempts.current) * 1000; // 指数退避
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, delay);
      }
    };

  }, [executionId, autoConnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const clearLogs = useCallback(() => {
    setState(prev => ({ ...prev, logs: [] }));
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, autoConnect]);

  return {
    ...state,
    connect,
    disconnect,
    clearLogs,
  };
};
```

### 2. React组件 - WorkflowLogViewer

```tsx
// components/WorkflowLogViewer.tsx
import React, { useState, useEffect, useRef } from 'react';
import { useWorkflowLogs, LogEntry } from '../hooks/useWorkflowLogs';

interface WorkflowLogViewerProps {
  executionId: string;
  height?: string;
  autoScroll?: boolean;
}

const WorkflowLogViewer: React.FC<WorkflowLogViewerProps> = ({
  executionId,
  height = '400px',
  autoScroll = true,
}) => {
  const { logs, isConnected, connectionStatus, error, connect, disconnect, clearLogs } =
    useWorkflowLogs(executionId);

  const logContainerRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'text-red-600';
      case 'INFO':
        return 'text-blue-600';
      case 'DEBUG':
        return 'text-gray-500';
      default:
        return 'text-gray-800';
    }
  };

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'workflow_started':
        return '🚀';
      case 'workflow_completed':
        return '✅';
      case 'step_started':
        return '📍';
      case 'step_completed':
        return '✅';
      case 'step_error':
        return '💥';
      default:
        return '📋';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="border rounded-lg p-4">
      {/* 控制栏 */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">工作流执行日志</h3>
        <div className="flex items-center space-x-2">
          <div className={`flex items-center space-x-1 ${
            isConnected ? 'text-green-600' : 'text-red-600'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="text-sm">{connectionStatus}</span>
          </div>

          <button
            onClick={isConnected ? disconnect : connect}
            className={`px-3 py-1 rounded text-sm ${
              isConnected
                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            }`}
          >
            {isConnected ? '断开' : '连接'}
          </button>

          <button
            onClick={clearLogs}
            className="px-3 py-1 rounded text-sm bg-gray-100 text-gray-700 hover:bg-gray-200"
          >
            清空日志
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-300 rounded text-red-700">
          {error}
        </div>
      )}

      {/* 日志容器 */}
      <div
        ref={logContainerRef}
        className="bg-gray-50 border rounded overflow-y-auto font-mono text-sm"
        style={{ height }}
      >
        {logs.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            暂无日志数据
          </div>
        ) : (
          <div className="space-y-1">
            {logs.map((log, index) => (
              <div
                key={index}
                className={`p-2 border-l-4 ${
                  log.level === 'ERROR' ? 'border-red-400 bg-red-50' :
                  log.level === 'INFO' ? 'border-blue-400 bg-blue-50' :
                  'border-gray-400 bg-gray-50'
                }`}
              >
                <div className="flex items-start space-x-2">
                  <span className="text-lg">{getEventIcon(log.event_type)}</span>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 text-xs text-gray-600">
                      <span>{formatTimestamp(log.timestamp)}</span>
                      <span className={`font-semibold ${getLogLevelColor(log.level)}`}>
                        {log.level}
                      </span>
                      <span className="bg-gray-200 px-1 rounded">
                        {log.event_type}
                      </span>
                    </div>
                    <div className="mt-1 text-gray-800">
                      {log.message}
                    </div>

                    {/* 显示附加数据 */}
                    {log.data && Object.keys(log.data).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer">
                          显示详细信息
                        </summary>
                        <pre className="mt-1 text-xs bg-white p-2 rounded border overflow-x-auto">
                          {JSON.stringify(log.data, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 日志统计 */}
      <div className="mt-2 text-xs text-gray-500">
        总计: {logs.length} 条日志
      </div>
    </div>
  );
};

export default WorkflowLogViewer;
```

### 3. 历史日志查询组件

```tsx
// components/HistoricalLogs.tsx
import React, { useState, useEffect } from 'react';

interface LogQueryParams {
  limit?: number;
  offset?: number;
  level?: string;
  event_type?: string;
  start_time?: string;
  end_time?: string;
}

interface HistoricalLogsProps {
  executionId: string;
}

const HistoricalLogs: React.FC<HistoricalLogsProps> = ({ executionId }) => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    limit: 50,
    offset: 0,
    hasMore: true,
  });
  const [filters, setFilters] = useState<LogQueryParams>({});

  const fetchLogs = async (params: LogQueryParams = {}) => {
    setLoading(true);
    try {
      const queryParams = new URLSearchParams();
      Object.entries({ ...params, limit: pagination.limit, offset: pagination.offset })
        .forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            queryParams.append(key, value.toString());
          }
        });

      const response = await fetch(
        `http://localhost:8002/v1/workflows/executions/${executionId}/logs?${queryParams}`
      );

      if (!response.ok) {
        throw new Error('获取日志失败');
      }

      const data = await response.json();

      if (pagination.offset === 0) {
        setLogs(data.logs);
      } else {
        setLogs(prev => [...prev, ...data.logs]);
      }

      setPagination(prev => ({
        ...prev,
        hasMore: data.pagination.has_more,
      }));

    } catch (error) {
      console.error('获取历史日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(filters);
  }, [executionId, filters]);

  const handleLoadMore = () => {
    setPagination(prev => ({
      ...prev,
      offset: prev.offset + prev.limit
    }));
    fetchLogs(filters);
  };

  const handleFilterChange = (newFilters: LogQueryParams) => {
    setFilters(newFilters);
    setPagination(prev => ({ ...prev, offset: 0 }));
  };

  return (
    <div className="space-y-4">
      {/* 过滤器 */}
      <div className="bg-white p-4 rounded border">
        <h4 className="font-medium mb-3">日志过滤</h4>
        <div className="grid grid-cols-2 gap-4">
          <select
            value={filters.level || ''}
            onChange={(e) => handleFilterChange({
              ...filters,
              level: e.target.value || undefined
            })}
            className="border rounded px-3 py-2"
          >
            <option value="">所有级别</option>
            <option value="INFO">INFO</option>
            <option value="ERROR">ERROR</option>
            <option value="DEBUG">DEBUG</option>
          </select>

          <select
            value={filters.event_type || ''}
            onChange={(e) => handleFilterChange({
              ...filters,
              event_type: e.target.value || undefined
            })}
            className="border rounded px-3 py-2"
          >
            <option value="">所有事件</option>
            <option value="workflow_started">工作流开始</option>
            <option value="step_started">步骤开始</option>
            <option value="step_completed">步骤完成</option>
            <option value="step_error">步骤错误</option>
            <option value="workflow_completed">工作流完成</option>
          </select>
        </div>
      </div>

      {/* 日志列表 */}
      <div className="bg-white rounded border">
        {loading && pagination.offset === 0 ? (
          <div className="p-8 text-center">加载中...</div>
        ) : (
          <>
            {logs.map((log, index) => (
              <div key={index} className="border-b p-4 last:border-b-0">
                <div className="flex justify-between items-start mb-2">
                  <span className={`font-semibold ${
                    log.level === 'ERROR' ? 'text-red-600' :
                    log.level === 'INFO' ? 'text-blue-600' : 'text-gray-600'
                  }`}>
                    {log.level}
                  </span>
                  <span className="text-sm text-gray-500">
                    {new Date(log.timestamp).toLocaleString('zh-CN')}
                  </span>
                </div>
                <div className="text-gray-800 mb-2">{log.message}</div>
                <div className="text-xs text-gray-500">
                  事件类型: {log.event_type}
                </div>
              </div>
            ))}

            {pagination.hasMore && (
              <div className="p-4 text-center">
                <button
                  onClick={handleLoadMore}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                >
                  {loading ? '加载中...' : '加载更多'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default HistoricalLogs;
```

---

## Vue.js集成示例

### 1. Vue Composition API Hook

```typescript
// composables/useWorkflowLogs.ts
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';

export interface LogEntry {
  execution_id: string;
  event_type: string;
  timestamp: string;
  message: string;
  level: 'INFO' | 'ERROR' | 'DEBUG';
  data?: Record<string, any>;
}

export const useWorkflowLogs = (executionId: string, autoConnect = true) => {
  const logs = ref<LogEntry[]>([]);
  const isConnected = ref(false);
  const connectionStatus = ref<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const error = ref<string | null>(null);

  let ws: WebSocket | null = null;
  let reconnectTimeout: NodeJS.Timeout | null = null;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;

  const connect = () => {
    if (ws?.readyState === WebSocket.OPEN) {
      return;
    }

    connectionStatus.value = 'connecting';
    error.value = null;

    const wsUrl = `ws://localhost:8002/v1/workflows/executions/${executionId}/logs/stream`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isConnected.value = true;
      connectionStatus.value = 'connected';
      error.value = null;
      reconnectAttempts = 0;
      console.log('WebSocket连接已建立');
    };

    ws.onmessage = (event) => {
      try {
        const logEntry: LogEntry = JSON.parse(event.data);
        logs.value.push(logEntry);
      } catch (err) {
        console.error('解析日志消息失败:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket错误:', err);
      connectionStatus.value = 'error';
      error.value = 'WebSocket连接错误';
    };

    ws.onclose = () => {
      isConnected.value = false;
      connectionStatus.value = 'disconnected';

      // 自动重连逻辑
      if (autoConnect && reconnectAttempts < maxReconnectAttempts) {
        const delay = Math.pow(2, reconnectAttempts) * 1000;
        reconnectTimeout = setTimeout(() => {
          reconnectAttempts++;
          connect();
        }, delay);
      }
    };
  };

  const disconnect = () => {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }

    if (ws) {
      ws.close();
      ws = null;
    }
  };

  const clearLogs = () => {
    logs.value = [];
  };

  onMounted(() => {
    if (autoConnect) {
      connect();
    }
  });

  onUnmounted(() => {
    disconnect();
  });

  return {
    logs: computed(() => logs.value),
    isConnected: computed(() => isConnected.value),
    connectionStatus: computed(() => connectionStatus.value),
    error: computed(() => error.value),
    connect,
    disconnect,
    clearLogs,
  };
};
```

### 2. Vue组件 - WorkflowLogViewer

```vue
<!-- components/WorkflowLogViewer.vue -->
<template>
  <div class="border rounded-lg p-4">
    <!-- 控制栏 -->
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold">工作流执行日志</h3>
      <div class="flex items-center space-x-2">
        <div :class="[
          'flex items-center space-x-1',
          isConnected ? 'text-green-600' : 'text-red-600'
        ]">
          <div :class="[
            'w-2 h-2 rounded-full',
            isConnected ? 'bg-green-500' : 'bg-red-500'
          ]"></div>
          <span class="text-sm">{{ connectionStatus }}</span>
        </div>

        <button
          @click="isConnected ? disconnect() : connect()"
          :class="[
            'px-3 py-1 rounded text-sm',
            isConnected
              ? 'bg-red-100 text-red-700 hover:bg-red-200'
              : 'bg-green-100 text-green-700 hover:bg-green-200'
          ]"
        >
          {{ isConnected ? '断开' : '连接' }}
        </button>

        <button
          @click="clearLogs"
          class="px-3 py-1 rounded text-sm bg-gray-100 text-gray-700 hover:bg-gray-200"
        >
          清空日志
        </button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="mb-4 p-3 bg-red-100 border border-red-300 rounded text-red-700">
      {{ error }}
    </div>

    <!-- 日志容器 -->
    <div
      ref="logContainer"
      class="bg-gray-50 border rounded overflow-y-auto font-mono text-sm"
      :style="{ height: height }"
    >
      <div v-if="logs.length === 0" class="p-4 text-center text-gray-500">
        暂无日志数据
      </div>
      <div v-else class="space-y-1">
        <div
          v-for="(log, index) in logs"
          :key="index"
          :class="[
            'p-2 border-l-4',
            log.level === 'ERROR' ? 'border-red-400 bg-red-50' :
            log.level === 'INFO' ? 'border-blue-400 bg-blue-50' :
            'border-gray-400 bg-gray-50'
          ]"
        >
          <div class="flex items-start space-x-2">
            <span class="text-lg">{{ getEventIcon(log.event_type) }}</span>
            <div class="flex-1">
              <div class="flex items-center space-x-2 text-xs text-gray-600">
                <span>{{ formatTimestamp(log.timestamp) }}</span>
                <span :class="[
                  'font-semibold',
                  getLogLevelColor(log.level)
                ]">
                  {{ log.level }}
                </span>
                <span class="bg-gray-200 px-1 rounded">
                  {{ log.event_type }}
                </span>
              </div>
              <div class="mt-1 text-gray-800">
                {{ log.message }}
              </div>

              <!-- 显示附加数据 -->
              <details v-if="log.data && Object.keys(log.data).length > 0" class="mt-2">
                <summary class="text-xs text-gray-500 cursor-pointer">
                  显示详细信息
                </summary>
                <pre class="mt-1 text-xs bg-white p-2 rounded border overflow-x-auto">{{
                  JSON.stringify(log.data, null, 2)
                }}</pre>
              </details>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 日志统计 -->
    <div class="mt-2 text-xs text-gray-500">
      总计: {{ logs.length }} 条日志
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
import { useWorkflowLogs } from '../composables/useWorkflowLogs';

interface Props {
  executionId: string;
  height?: string;
  autoScroll?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  height: '400px',
  autoScroll: true,
});

const { logs, isConnected, connectionStatus, error, connect, disconnect, clearLogs } =
  useWorkflowLogs(props.executionId);

const logContainer = ref<HTMLDivElement>();

// 自动滚动到底部
watch(logs, async () => {
  if (props.autoScroll && logContainer.value) {
    await nextTick();
    logContainer.value.scrollTop = logContainer.value.scrollHeight;
  }
});

const getLogLevelColor = (level: string) => {
  switch (level) {
    case 'ERROR':
      return 'text-red-600';
    case 'INFO':
      return 'text-blue-600';
    case 'DEBUG':
      return 'text-gray-500';
    default:
      return 'text-gray-800';
  }
};

const getEventIcon = (eventType: string) => {
  switch (eventType) {
    case 'workflow_started':
      return '🚀';
    case 'workflow_completed':
      return '✅';
    case 'step_started':
      return '📍';
    case 'step_completed':
      return '✅';
    case 'step_error':
      return '💥';
    default:
      return '📋';
  }
};

const formatTimestamp = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};
</script>
```

---

## 原生JavaScript示例

### 1. WebSocket连接类

```javascript
// WorkflowLogger.js
class WorkflowLogger {
  constructor(executionId, options = {}) {
    this.executionId = executionId;
    this.options = {
      autoConnect: true,
      autoReconnect: true,
      maxReconnectAttempts: 5,
      ...options
    };

    this.ws = null;
    this.logs = [];
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.reconnectTimeout = null;

    if (this.options.autoConnect) {
      this.connect();
    }
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.emit('connecting');

    const wsUrl = `ws://localhost:8002/v1/workflows/executions/${this.executionId}/logs/stream`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const logEntry = JSON.parse(event.data);
        this.logs.push(logEntry);
        this.emit('log', logEntry);
      } catch (error) {
        console.error('Failed to parse log message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };

    this.ws.onclose = (event) => {
      this.emit('disconnected', event);

      // 自动重连
      if (this.options.autoReconnect &&
          this.reconnectAttempts < this.options.maxReconnectAttempts) {
        const delay = Math.pow(2, this.reconnectAttempts) * 1000;
        this.reconnectTimeout = setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, delay);
      }
    };
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  // 事件监听器
  on(event, listener) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(listener);
  }

  off(event, listener) {
    if (!this.listeners[event]) return;

    const index = this.listeners[event].indexOf(listener);
    if (index !== -1) {
      this.listeners[event].splice(index, 1);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(listener => listener(data));
    }
  }

  // 获取历史日志
  async getHistoricalLogs(options = {}) {
    const params = new URLSearchParams();
    Object.entries(options).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });

    try {
      const response = await fetch(
        `http://localhost:8002/v1/workflows/executions/${this.executionId}/logs?${params}`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to fetch historical logs:', error);
      throw error;
    }
  }

  // 清空日志
  clearLogs() {
    this.logs = [];
    this.emit('logsCleared');
  }

  // 获取连接状态
  getConnectionState() {
    if (!this.ws) return 'disconnected';

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'disconnecting';
      case WebSocket.CLOSED:
      default:
        return 'disconnected';
    }
  }
}
```

### 2. HTML页面示例

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工作流执行日志查看器</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .header {
            padding: 20px;
            border-bottom: 1px solid #e5e5e5;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .status-indicator.connected {
            background-color: #10b981;
        }

        .status-indicator.disconnected {
            background-color: #ef4444;
        }

        .controls {
            display: flex;
            gap: 10px;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }

        .btn-primary {
            background-color: #3b82f6;
            color: white;
        }

        .btn-secondary {
            background-color: #6b7280;
            color: white;
        }

        .btn-danger {
            background-color: #ef4444;
            color: white;
        }

        .logs-container {
            height: 500px;
            overflow-y: auto;
            padding: 20px;
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        .log-entry {
            margin-bottom: 8px;
            padding: 12px;
            border-left: 4px solid #d1d5db;
            background-color: #f9fafb;
            border-radius: 0 4px 4px 0;
        }

        .log-entry.info {
            border-left-color: #3b82f6;
            background-color: #eff6ff;
        }

        .log-entry.error {
            border-left-color: #ef4444;
            background-color: #fef2f2;
        }

        .log-meta {
            display: flex;
            gap: 10px;
            margin-bottom: 4px;
            font-size: 11px;
            color: #6b7280;
        }

        .log-level {
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 2px;
            background-color: #e5e7eb;
        }

        .log-level.info {
            background-color: #dbeafe;
            color: #1d4ed8;
        }

        .log-level.error {
            background-color: #fee2e2;
            color: #dc2626;
        }

        .log-message {
            color: #374151;
            margin-bottom: 4px;
        }

        .log-details {
            font-size: 11px;
            color: #6b7280;
        }

        .filters {
            padding: 20px;
            border-bottom: 1px solid #e5e5e5;
            background-color: #f9fafb;
        }

        .filter-row {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .filter-group label {
            font-size: 12px;
            font-weight: 500;
            color: #374151;
        }

        .filter-group select {
            padding: 6px 10px;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>工作流执行日志查看器</h1>
            <div class="status">
                <div id="statusIndicator" class="status-indicator disconnected"></div>
                <span id="statusText">断开连接</span>
            </div>
            <div class="controls">
                <button id="connectBtn" class="btn btn-primary">连接</button>
                <button id="clearBtn" class="btn btn-secondary">清空日志</button>
                <button id="exportBtn" class="btn btn-secondary">导出日志</button>
            </div>
        </div>

        <div class="filters">
            <div class="filter-row">
                <div class="filter-group">
                    <label for="executionIdInput">执行ID:</label>
                    <input id="executionIdInput" type="text" placeholder="输入执行ID"
                           style="padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 4px;">
                </div>
                <div class="filter-group">
                    <label for="levelFilter">日志级别:</label>
                    <select id="levelFilter">
                        <option value="">全部</option>
                        <option value="INFO">INFO</option>
                        <option value="ERROR">ERROR</option>
                        <option value="DEBUG">DEBUG</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="eventFilter">事件类型:</label>
                    <select id="eventFilter">
                        <option value="">全部</option>
                        <option value="workflow_started">工作流开始</option>
                        <option value="step_started">步骤开始</option>
                        <option value="step_completed">步骤完成</option>
                        <option value="step_error">步骤错误</option>
                        <option value="workflow_completed">工作流完成</option>
                    </select>
                </div>
                <button id="loadHistoricalBtn" class="btn btn-primary">加载历史日志</button>
            </div>
        </div>

        <div id="logsContainer" class="logs-container">
            <div class="log-entry">
                <div class="log-message">输入执行ID并点击连接按钮开始查看实时日志</div>
            </div>
        </div>
    </div>

    <script src="WorkflowLogger.js"></script>
    <script>
        let logger = null;
        let filteredLogs = [];

        const elements = {
            executionIdInput: document.getElementById('executionIdInput'),
            statusIndicator: document.getElementById('statusIndicator'),
            statusText: document.getElementById('statusText'),
            connectBtn: document.getElementById('connectBtn'),
            clearBtn: document.getElementById('clearBtn'),
            exportBtn: document.getElementById('exportBtn'),
            loadHistoricalBtn: document.getElementById('loadHistoricalBtn'),
            logsContainer: document.getElementById('logsContainer'),
            levelFilter: document.getElementById('levelFilter'),
            eventFilter: document.getElementById('eventFilter'),
        };

        // 事件监听器
        elements.connectBtn.addEventListener('click', () => {
            const executionId = elements.executionIdInput.value.trim();
            if (!executionId) {
                alert('请输入执行ID');
                return;
            }

            if (logger && logger.getConnectionState() === 'connected') {
                logger.disconnect();
            } else {
                connectToLogger(executionId);
            }
        });

        elements.clearBtn.addEventListener('click', () => {
            if (logger) {
                logger.clearLogs();
            }
            clearLogDisplay();
        });

        elements.exportBtn.addEventListener('click', exportLogs);

        elements.loadHistoricalBtn.addEventListener('click', loadHistoricalLogs);

        elements.levelFilter.addEventListener('change', applyFilters);
        elements.eventFilter.addEventListener('change', applyFilters);

        // 连接到WebSocket
        function connectToLogger(executionId) {
            if (logger) {
                logger.disconnect();
            }

            logger = new WorkflowLogger(executionId);

            logger.on('connecting', () => {
                updateConnectionStatus('connecting', '连接中...');
            });

            logger.on('connected', () => {
                updateConnectionStatus('connected', '已连接');
                elements.connectBtn.textContent = '断开连接';
                elements.connectBtn.className = 'btn btn-danger';
            });

            logger.on('disconnected', () => {
                updateConnectionStatus('disconnected', '断开连接');
                elements.connectBtn.textContent = '连接';
                elements.connectBtn.className = 'btn btn-primary';
            });

            logger.on('error', (error) => {
                updateConnectionStatus('disconnected', '连接错误');
                console.error('WebSocket error:', error);
            });

            logger.on('log', (logEntry) => {
                displayLogEntry(logEntry);
                applyFilters();
            });

            logger.on('logsCleared', () => {
                clearLogDisplay();
            });
        }

        // 更新连接状态
        function updateConnectionStatus(status, text) {
            elements.statusIndicator.className = `status-indicator ${status}`;
            elements.statusText.textContent = text;
        }

        // 显示日志条目
        function displayLogEntry(logEntry) {
            const logElement = createLogElement(logEntry);
            elements.logsContainer.appendChild(logElement);

            // 自动滚动到底部
            elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
        }

        // 创建日志元素
        function createLogElement(logEntry) {
            const div = document.createElement('div');
            div.className = `log-entry ${logEntry.level.toLowerCase()}`;

            const timestamp = new Date(logEntry.timestamp).toLocaleTimeString('zh-CN');
            const eventIcon = getEventIcon(logEntry.event_type);

            div.innerHTML = `
                <div class="log-meta">
                    <span>${eventIcon} ${timestamp}</span>
                    <span class="log-level ${logEntry.level.toLowerCase()}">${logEntry.level}</span>
                    <span>${logEntry.event_type}</span>
                </div>
                <div class="log-message">${logEntry.message}</div>
                ${logEntry.data && Object.keys(logEntry.data).length > 0 ?
                  `<details class="log-details">
                     <summary>显示详细信息</summary>
                     <pre>${JSON.stringify(logEntry.data, null, 2)}</pre>
                   </details>` : ''}
            `;

            return div;
        }

        // 获取事件图标
        function getEventIcon(eventType) {
            switch (eventType) {
                case 'workflow_started': return '🚀';
                case 'workflow_completed': return '✅';
                case 'step_started': return '📍';
                case 'step_completed': return '✅';
                case 'step_error': return '💥';
                default: return '📋';
            }
        }

        // 应用过滤器
        function applyFilters() {
            if (!logger) return;

            const levelFilter = elements.levelFilter.value;
            const eventFilter = elements.eventFilter.value;

            filteredLogs = logger.logs.filter(log => {
                return (!levelFilter || log.level === levelFilter) &&
                       (!eventFilter || log.event_type === eventFilter);
            });

            // 重新显示过滤后的日志
            elements.logsContainer.innerHTML = '';
            filteredLogs.forEach(log => displayLogEntry(log));
        }

        // 加载历史日志
        async function loadHistoricalLogs() {
            const executionId = elements.executionIdInput.value.trim();
            if (!executionId) {
                alert('请输入执行ID');
                return;
            }

            const levelFilter = elements.levelFilter.value;
            const eventFilter = elements.eventFilter.value;

            const params = {};
            if (levelFilter) params.level = levelFilter;
            if (eventFilter) params.event_type = eventFilter;

            try {
                if (!logger) {
                    logger = new WorkflowLogger(executionId, { autoConnect: false });
                }

                const response = await logger.getHistoricalLogs(params);

                // 清空现有日志并显示历史日志
                clearLogDisplay();
                response.logs.forEach(log => displayLogEntry(log));

            } catch (error) {
                alert('加载历史日志失败: ' + error.message);
            }
        }

        // 清空日志显示
        function clearLogDisplay() {
            elements.logsContainer.innerHTML = '';
        }

        // 导出日志
        function exportLogs() {
            if (!logger || logger.logs.length === 0) {
                alert('没有日志可导出');
                return;
            }

            const logs = filteredLogs.length > 0 ? filteredLogs : logger.logs;
            const content = logs.map(log =>
                `[${log.timestamp}] ${log.level} ${log.event_type}: ${log.message}`
            ).join('\\n');

            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `workflow-logs-${new Date().toISOString().slice(0, 10)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
```

---

## API使用指南

### 1. 基础URL配置

```javascript
// 开发环境
const API_BASE_URL = 'http://localhost:8002';

// 生产环境
const API_BASE_URL = 'https://api.yourdomain.com';

// WebSocket URL
const WS_BASE_URL = API_BASE_URL.replace(/^https?/, 'ws');
```

### 2. API端点汇总

```typescript
const API_ENDPOINTS = {
  // WebSocket实时日志流
  WEBSOCKET_LOGS: (executionId: string) =>
    `${WS_BASE_URL}/v1/workflows/executions/${executionId}/logs/stream`,

  // SSE实时日志流
  SSE_LOGS: (executionId: string) =>
    `${API_BASE_URL}/v1/workflows/executions/${executionId}/logs/stream`,

  // 获取执行日志
  GET_LOGS: (executionId: string) =>
    `${API_BASE_URL}/v1/workflows/executions/${executionId}/logs`,

  // 获取活跃执行
  ACTIVE_EXECUTIONS: `${API_BASE_URL}/v1/workflows/executions/active`,

  // 获取执行统计
  EXECUTION_STATS: (executionId: string) =>
    `${API_BASE_URL}/v1/workflows/executions/${executionId}/stats`,

  // 清理历史日志
  CLEANUP_LOGS: `${API_BASE_URL}/v1/workflows/executions/logs/cleanup`,

  // 获取日志统计
  LOG_STATS: `${API_BASE_URL}/v1/workflows/logs/stats`,
};
```

### 3. 错误处理工具函数

```javascript
// API错误处理
async function handleApiError(response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const error = new Error(errorData?.detail?.message || `HTTP ${response.status}`);
    error.code = errorData?.detail?.code;
    error.details = errorData?.detail?.details;
    throw error;
  }
  return response;
}

// WebSocket错误处理
function getWebSocketErrorMessage(event) {
  switch (event.code) {
    case 1000:
      return '连接正常关闭';
    case 1001:
      return '端点已离开';
    case 1002:
      return '协议错误';
    case 1003:
      return '不支持的数据类型';
    case 1006:
      return '连接异常关闭';
    case 1011:
      return '服务器遇到意外情况';
    default:
      return `连接关闭 (代码: ${event.code})`;
  }
}
```

---

## WebSocket连接管理

### 1. 连接池管理

```javascript
class WebSocketManager {
  constructor() {
    this.connections = new Map();
    this.reconnectAttempts = new Map();
  }

  connect(executionId, options = {}) {
    // 如果已存在连接，先关闭
    this.disconnect(executionId);

    const connection = new WorkflowLogger(executionId, options);
    this.connections.set(executionId, connection);
    this.reconnectAttempts.set(executionId, 0);

    return connection;
  }

  disconnect(executionId) {
    const connection = this.connections.get(executionId);
    if (connection) {
      connection.disconnect();
      this.connections.delete(executionId);
      this.reconnectAttempts.delete(executionId);
    }
  }

  disconnectAll() {
    for (const executionId of this.connections.keys()) {
      this.disconnect(executionId);
    }
  }

  getConnection(executionId) {
    return this.connections.get(executionId);
  }

  getAllConnections() {
    return Array.from(this.connections.values());
  }
}

// 全局WebSocket管理器
const wsManager = new WebSocketManager();

// 页面卸载时断开所有连接
window.addEventListener('beforeunload', () => {
  wsManager.disconnectAll();
});
```

### 2. 心跳检测

```javascript
class HeartbeatWebSocket extends WebSocket {
  constructor(url, protocols, options = {}) {
    super(url, protocols);

    this.heartbeatInterval = options.heartbeatInterval || 30000; // 30秒
    this.heartbeatTimer = null;
    this.pongTimer = null;

    this.addEventListener('open', this.startHeartbeat.bind(this));
    this.addEventListener('close', this.stopHeartbeat.bind(this));
    this.addEventListener('message', this.onHeartbeatMessage.bind(this));
  }

  startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.readyState === WebSocket.OPEN) {
        this.send(JSON.stringify({ type: 'ping' }));

        // 等待pong回应，超时则认为连接有问题
        this.pongTimer = setTimeout(() => {
          console.warn('心跳超时，重新连接...');
          this.close();
        }, 5000);
      }
    }, this.heartbeatInterval);
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }

  onHeartbeatMessage(event) {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'pong' && this.pongTimer) {
        clearTimeout(this.pongTimer);
        this.pongTimer = null;
      }
    } catch (error) {
      // 不是心跳消息，忽略
    }
  }
}
```

---

## 错误处理最佳实践

### 1. 统一错误处理

```javascript
// 错误类型定义
const ERROR_TYPES = {
  NETWORK_ERROR: 'network_error',
  WEBSOCKET_ERROR: 'websocket_error',
  PARSE_ERROR: 'parse_error',
  API_ERROR: 'api_error',
  TIMEOUT_ERROR: 'timeout_error',
};

// 错误处理类
class ErrorHandler {
  static handle(error, context = {}) {
    const errorInfo = {
      type: this.getErrorType(error),
      message: error.message,
      code: error.code,
      details: error.details,
      context,
      timestamp: new Date().toISOString(),
    };

    // 记录错误
    console.error('Application error:', errorInfo);

    // 发送错误事件
    this.emit('error', errorInfo);

    // 显示用户友好的错误消息
    this.showUserError(errorInfo);

    return errorInfo;
  }

  static getErrorType(error) {
    if (error instanceof TypeError) {
      return ERROR_TYPES.NETWORK_ERROR;
    }
    if (error.name === 'SyntaxError') {
      return ERROR_TYPES.PARSE_ERROR;
    }
    if (error.code) {
      return ERROR_TYPES.API_ERROR;
    }
    return 'unknown_error';
  }

  static showUserError(errorInfo) {
    const userMessage = this.getUserFriendlyMessage(errorInfo);

    // 这里可以集成你的通知系统
    alert(userMessage); // 简单示例，实际项目中应该使用更好的UI组件
  }

  static getUserFriendlyMessage(errorInfo) {
    switch (errorInfo.type) {
      case ERROR_TYPES.NETWORK_ERROR:
        return '网络连接失败，请检查网络设置';
      case ERROR_TYPES.WEBSOCKET_ERROR:
        return '实时连接中断，正在尝试重连...';
      case ERROR_TYPES.PARSE_ERROR:
        return '数据解析失败，请刷新页面重试';
      case ERROR_TYPES.API_ERROR:
        return errorInfo.message || '服务器请求失败';
      case ERROR_TYPES.TIMEOUT_ERROR:
        return '请求超时，请稍后重试';
      default:
        return '发生未知错误，请联系技术支持';
    }
  }

  static emit(event, data) {
    // 这里可以集成事件总线系统
    window.dispatchEvent(new CustomEvent(event, { detail: data }));
  }
}

// 全局错误处理
window.addEventListener('error', (event) => {
  ErrorHandler.handle(event.error, { type: 'global_error' });
});

window.addEventListener('unhandledrejection', (event) => {
  ErrorHandler.handle(event.reason, { type: 'unhandled_promise_rejection' });
});
```

### 2. 重试机制

```javascript
// 指数退避重试
async function retryWithBackoff(fn, maxAttempts = 3, baseDelay = 1000) {
  let attempt = 0;

  while (attempt < maxAttempts) {
    try {
      return await fn();
    } catch (error) {
      attempt++;

      if (attempt >= maxAttempts) {
        throw error;
      }

      const delay = baseDelay * Math.pow(2, attempt - 1);
      console.log(`重试第 ${attempt} 次，延迟 ${delay}ms`);

      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// 使用示例
async function fetchLogsWithRetry(executionId, params) {
  return retryWithBackoff(async () => {
    const response = await fetch(`/v1/workflows/executions/${executionId}/logs?${new URLSearchParams(params)}`);
    await handleApiError(response);
    return response.json();
  }, 3, 1000);
}
```

---

以上示例提供了完整的前端集成方案，包括React、Vue和原生JavaScript的实现。每个示例都包含了错误处理、重连机制、状态管理等生产环境必需的功能。根据项目需求选择合适的技术栈进行集成即可。
