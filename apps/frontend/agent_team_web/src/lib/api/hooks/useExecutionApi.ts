import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { API_PATHS } from '../config';
import { ExecutionStatusEnum } from '@/types/workflow-enums';
import { apiRequest } from '../fetcher';

export interface NodeExecution {
  node_id: string;
  status: string;
  start_time?: string;
  end_time?: string;
  error?: string;
  result?: unknown;
}

export interface ExecutionStatus {
  execution_id: string;
  workflow_id: string;
  // Use centralized enum, allow string for backward-compat (e.g. 'FAILED')
  status: ExecutionStatusEnum | string;
  start_time?: string | number;
  end_time?: string | number;
  error?: string;
  error_message?: string;
  result?: unknown;
  node_executions?: NodeExecution[];
  run_data?: {
    node_results?: Record<string, {
      status: string;
      [key: string]: unknown;
    }>;
  };
}

export interface ExecutionRequest {
  inputs?: Record<string, unknown>;
  start_from_node?: string;
  skip_trigger_validation?: boolean;
}

// Hook for executing workflow
export function useWorkflowExecution() {
  const { session } = useAuth();
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const executeWorkflow = useCallback(async (
    workflowId: string,
    request: ExecutionRequest = {}
  ) => {
    if (!session?.access_token) {
      throw new Error('Not authenticated');
    }

    setIsExecuting(true);
    setError(null);

    try {
      const result = await apiRequest(
        API_PATHS.WORKFLOW_EXECUTE(workflowId),
        session.access_token,
        'POST',
        request
      );

      if (result.execution_id) {
        setExecutionId(result.execution_id);
        return result.execution_id;
      } else {
        throw new Error('No execution ID returned');
      }
    } catch (err) {
      const error = err as Error;
      setError(error.message || 'Failed to execute workflow');
      throw err;
    } finally {
      setIsExecuting(false);
    }
  }, [session]);

  return {
    executeWorkflow,
    isExecuting,
    executionId,
    error,
  };
}

// Hook for polling execution status
export function useExecutionStatus(
  executionId: string | null,
  options?: {
    interval?: number;
    maxDuration?: number; // Maximum polling duration in milliseconds
    onComplete?: (status: ExecutionStatus) => void;
    onError?: (error: string) => void;
    onTimeout?: () => void;
    enabled?: boolean;
  }
) {
  const { session } = useAuth();
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const startTimeRef = useRef<number | null>(null);
  const inFlightRef = useRef<boolean>(false);
  const timerRef = useRef<number | null>(null);
  const currentIntervalRef = useRef<number>(options?.interval ?? 2000);
  const prevStatusRef = useRef<string | null>(null);
  const errorCountRef = useRef<number>(0);
  const abortRef = useRef<AbortController | null>(null);
  const pausedRef = useRef<boolean>(false);

  // Keep latest callbacks in refs to avoid re-creating polling effect
  const onCompleteRef = useRef<typeof options.onComplete>();
  const onErrorRef = useRef<typeof options.onError>();
  const onTimeoutRef = useRef<typeof options.onTimeout>();

  const {
    interval = 2000,
    maxDuration = 300000, // 5 minutes default
    enabled = true,
  } = options || {};

  // Keep latest callbacks
  useEffect(() => {
    onCompleteRef.current = options?.onComplete;
    onErrorRef.current = options?.onError;
    onTimeoutRef.current = options?.onTimeout;
  }, [options?.onComplete, options?.onError, options?.onTimeout]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Main polling effect (stable, adaptive, cancellable)
  useEffect(() => {
    mountedRef.current = true;

    if (!enabled || !executionId || !session?.access_token) {
      return () => {
        mountedRef.current = false;
        stopPolling();
      };
    }

    setIsPolling(true);
    setError(null);
    startTimeRef.current = Date.now();

    const baseInterval = interval;
    const maxInterval = Math.min(15000, Math.max(baseInterval, baseInterval * 8));
    currentIntervalRef.current = baseInterval;
    prevStatusRef.current = null;
    errorCountRef.current = 0;

    const tick = async () => {
      if (!mountedRef.current || pausedRef.current) return;
      if (inFlightRef.current) {
        // Try again later to avoid overlap
        timerRef.current = window.setTimeout(tick, currentIntervalRef.current);
        return;
      }
      inFlightRef.current = true;
      abortRef.current = new AbortController();
      try {
        const res = await fetch(API_PATHS.EXECUTION(executionId), {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          signal: abortRef.current.signal,
        });
        if (!mountedRef.current) return;
        if (!res.ok) throw new Error(`API Error: ${res.status} ${res.statusText}`);
        const latestStatus = (await res.json()) as ExecutionStatus;
        setStatus(latestStatus);

        const terminal = new Set<string>([
          ExecutionStatusEnum.Completed,
          ExecutionStatusEnum.Success,
          ExecutionStatusEnum.Error,
          ExecutionStatusEnum.Cancelled,
          ExecutionStatusEnum.Canceled,
          'FAILED',
          'COMPLETE',
        ]);

        // Adaptive interval based on changes
        const same = prevStatusRef.current === latestStatus.status;
        prevStatusRef.current = latestStatus.status;
        if (!terminal.has(latestStatus.status)) {
          // Increase interval if unchanged to reduce load
          currentIntervalRef.current = same
            ? Math.min(maxInterval, Math.floor(currentIntervalRef.current * 1.5))
            : baseInterval;
          errorCountRef.current = 0;
          timerRef.current = window.setTimeout(tick, currentIntervalRef.current);
        } else {
          // Stop on terminal and fire callbacks
          stopPolling();
          if (
            latestStatus.status === ExecutionStatusEnum.Completed ||
            latestStatus.status === ExecutionStatusEnum.Success ||
            latestStatus.status === 'COMPLETE'
          ) {
            onCompleteRef.current?.(latestStatus);
          } else if (
            latestStatus.status === 'FAILED' ||
            latestStatus.status === ExecutionStatusEnum.Error
          ) {
            const errorMsg = latestStatus.error || latestStatus.error_message || 'Execution failed';
            setError(errorMsg);
            onErrorRef.current?.(errorMsg);
          }
        }
      } catch (err) {
        if (!mountedRef.current) return;
        errorCountRef.current += 1;
        const msg = (err as Error).message || 'Failed to fetch status';
        setError(msg);
        // Backoff a bit and retry up to 3 times, then stop
        if (errorCountRef.current <= 3) {
          currentIntervalRef.current = Math.min(maxInterval, Math.floor(currentIntervalRef.current * 2));
          timerRef.current = window.setTimeout(tick, currentIntervalRef.current);
        } else {
          stopPolling();
          onErrorRef.current?.(msg);
        }
      } finally {
        inFlightRef.current = false;
      }
    };

    // Page visibility pause/resume
    const handleVisibility = () => {
      const hidden = typeof document !== 'undefined' && document.hidden;
      pausedRef.current = !!hidden;
      if (!hidden && mountedRef.current && isPolling && !timerRef.current) {
        // schedule an immediate tick on resume
        currentIntervalRef.current = baseInterval;
        timerRef.current = window.setTimeout(tick, 0);
      }
    };
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', handleVisibility);
    }

    // Initial tick
    timerRef.current = window.setTimeout(tick, 0);

    // Hard stop after maxDuration
    if (maxDuration > 0) {
      timeoutRef.current = window.setTimeout(() => {
        if (mountedRef.current) {
          stopPolling();
          setError('Execution timeout - polling stopped after ' + maxDuration / 1000 + ' seconds');
          onTimeoutRef.current?.();
        }
      }, maxDuration);
    }

    return () => {
      mountedRef.current = false;
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', handleVisibility);
      }
      stopPolling();
    };
  }, [enabled, executionId, interval, maxDuration, session?.access_token, stopPolling]);

  return {
    status,
    isPolling,
    error,
    refresh: async () => {
      if (!session?.access_token || !executionId) return null;
      const result = await apiRequest(
        API_PATHS.EXECUTION(executionId),
        session.access_token,
        'GET'
      );
      return result as ExecutionStatus;
    },
    startPolling: () => {},
    stopPolling,
  };
}

// Hook for cancelling execution
export function useExecutionCancel() {
  const { session } = useAuth();
  const [isCancelling, setIsCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cancelExecution = useCallback(async (executionId: string) => {
    if (!session?.access_token) {
      throw new Error('Not authenticated');
    }

    setIsCancelling(true);
    setError(null);

    try {
      const result = await apiRequest(
        `${API_PATHS.EXECUTION(executionId)}/cancel`,
        session.access_token,
        'POST'
      );

      return result;
    } catch (err) {
      const error = err as Error;
      const errorMsg = error.message || 'Failed to cancel execution';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setIsCancelling(false);
    }
  }, [session]);

  return {
    cancelExecution,
    isCancelling,
    error,
  };
}

// Hook for fetching recent execution logs
export interface RecentExecutionLog {
  execution_id: string;
  status: string;
  timestamp: string;
  duration?: string;
  error_message?: string;
}

export function useRecentExecutionLogs(workflowId: string | null, limit: number = 10) {
  const { session } = useAuth();
  const [logs, setLogs] = useState<RecentExecutionLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    if (!session?.access_token || !workflowId) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        workflow_id: workflowId,
        limit: limit.toString(),
      });

      const result = await apiRequest(
        `${API_PATHS.RECENT_LOGS}?${params.toString()}`,
        session.access_token,
        'GET'
      );

      setLogs(result.logs || []);
    } catch (err) {
      const error = err as Error;
      const errorMsg = error.message || 'Failed to fetch recent logs';
      setError(errorMsg);
      console.error('Error fetching recent execution logs:', err);
    } finally {
      setIsLoading(false);
    }
  }, [session, workflowId, limit]);

  useEffect(() => {
    if (workflowId) {
      fetchLogs();
    }
  }, [workflowId, fetchLogs]);

  return {
    logs,
    isLoading,
    error,
    refresh: fetchLogs,
  };
}

// Hook for streaming execution logs from a specific execution
export interface ExecutionLogEntry {
  id?: string;
  timestamp?: string | number;
  level?: string;
  message?: string;
  node_id?: string;
  node_name?: string;
  event_type?: string;
  execution_id?: string;
  [key: string]: unknown;
}

export function useExecutionLogsStream(executionId: string | null) {
  const { session } = useAuth();
  const [logs, setLogs] = useState<ExecutionLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef<boolean>(true);
  const abortRef = useRef<AbortController | null>(null);
  const [restartId, setRestartId] = useState(0);

  const stop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    setLogs([]);
    setError(null);
    stop();

    if (!executionId || !session?.access_token) {
      setIsLoading(false);
      return () => {
        mountedRef.current = false;
        stop();
      };
    }

    const stream = async () => {
      setIsLoading(true);
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        const res = await fetch(API_PATHS.EXECUTION_LOGS_STREAM(executionId), {
          method: 'GET',
          headers: {
            Accept: 'text/event-stream',
            Authorization: `Bearer ${session.access_token}`,
          },
          signal: ctrl.signal,
        });
        if (!res.ok || !res.body) {
          throw new Error(`Stream error: ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        const pump = async (): Promise<void> => {
          const { done, value } = await reader.read();
          if (done) {
            setIsLoading(false);
            return;
          }
          buffer += decoder.decode(value, { stream: true });

          // Process SSE events line by line for immediate updates
          // Split by newline and process any complete lines
          const lines = buffer.split('\n');

          // Keep the last potentially incomplete line in the buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();

            // Skip empty lines and comments
            if (!trimmed || trimmed.startsWith(':')) {
              continue;
            }

            // Process data lines
            if (trimmed.startsWith('data: ')) {
              const jsonStr = trimmed.slice(6);
              try {
                const payload = JSON.parse(jsonStr) as {
                  type?: string;
                  data?: ExecutionLogEntry;
                  is_final?: boolean;
                };
                const type = (payload.type || '').toUpperCase();

                if (type === 'LOG') {
                  if (payload.data && mountedRef.current) {
                    setLogs((prev) => [...prev, payload.data!]);
                  }
                } else if (type === 'COMPLETE' || (payload.is_final && type === 'ERROR')) {
                  setIsLoading(false);
                  stop();
                  return;
                }
              } catch (e) {
                console.warn('Failed to parse SSE log entry:', jsonStr, e);
              }
            }
          }

          await pump();
        };
        await pump();
      } catch (err) {
        if (!mountedRef.current) return;
        // Do not call static logs; rely solely on stream
        const e = err as Error;
        setError(e.message || 'Failed to stream execution logs');
        setIsLoading(false);
      }
    };

    void stream();

    return () => {
      mountedRef.current = false;
      stop();
    };
  }, [executionId, session?.access_token, stop, restartId]);

  return {
    logs,
    isLoading,
    error,
    refresh: () => setRestartId((v) => v + 1),
  };
}
