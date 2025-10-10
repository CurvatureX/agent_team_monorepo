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
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);
  const startTimeRef = useRef<number | null>(null);

  const {
    interval = 2000,
    maxDuration = 300000, // 5 minutes default
    onComplete,
    onError,
    onTimeout,
    enabled = true,
  } = options || {};

  const fetchStatus = useCallback(async () => {
    if (!session?.access_token || !executionId) {
      return null;
    }

    try {
      const result = await apiRequest(
        API_PATHS.EXECUTION(executionId),
        session.access_token,
        'GET'
      );

      return result as ExecutionStatus;
    } catch (err) {
      const error = err as Error;
      throw new Error(error.message || 'Failed to fetch execution status');
    }
  }, [session, executionId]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const startPolling = useCallback(() => {
    if (!enabled || !executionId || intervalRef.current) {
      return;
    }

    setIsPolling(true);
    setError(null);
    startTimeRef.current = Date.now();

    // Set up timeout
    if (maxDuration > 0) {
      timeoutRef.current = setTimeout(() => {
        if (mountedRef.current) {
          stopPolling();
          setError('Execution timeout - polling stopped after ' + (maxDuration / 1000) + ' seconds');
          onTimeout?.();
        }
      }, maxDuration);
    }

    const poll = async () => {
      try {
        const latestStatus = await fetchStatus();

        if (!mountedRef.current) return;

        if (latestStatus) {
          setStatus(latestStatus);

          // Check if execution is complete
          const stopStatuses = new Set<string>([
            ExecutionStatusEnum.Completed,
            ExecutionStatusEnum.Success,
            ExecutionStatusEnum.Error,
            ExecutionStatusEnum.Cancelled,
            ExecutionStatusEnum.Canceled,
            // Backward compatibility
            'FAILED',
          ]);
          if (stopStatuses.has(latestStatus.status)) {
            stopPolling();

            if (
              latestStatus.status === ExecutionStatusEnum.Completed ||
              latestStatus.status === ExecutionStatusEnum.Success
            ) {
              onComplete?.(latestStatus);
            } else if (
              latestStatus.status === 'FAILED' ||
              latestStatus.status === ExecutionStatusEnum.Error
            ) {
              const errorMsg = latestStatus.error || latestStatus.error_message || 'Execution failed';
              setError(errorMsg);
              onError?.(errorMsg);
            }
          }
        }
      } catch (err) {
        if (!mountedRef.current) return;

        const error = err as Error;
        const errorMsg = error.message || 'Failed to fetch status';
        setError(errorMsg);
        stopPolling();
        onError?.(errorMsg);
      }
    };

    // Initial fetch
    poll();

    // Set up interval
    intervalRef.current = setInterval(poll, interval);
  }, [enabled, executionId, fetchStatus, interval, maxDuration, onComplete, onError, onTimeout, stopPolling]);

  // Start/stop polling based on conditions
  useEffect(() => {
    if (enabled && executionId && !intervalRef.current) {
      startPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, executionId, startPolling, stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, [stopPolling]);

  return {
    status,
    isPolling,
    error,
    refresh: fetchStatus,
    startPolling,
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
  timestamp: string;
  level: string;
  message: string;
  node_id?: string;
  execution_id?: string;
  [key: string]: unknown;
}

export function useExecutionLogsStream(executionId: string | null) {
  const { session } = useAuth();
  const [logs, setLogs] = useState<ExecutionLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    if (!session?.access_token || !executionId) {
      setLogs([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await apiRequest(
        API_PATHS.EXECUTION_LOGS_STREAM(executionId),
        session.access_token,
        'GET'
      );

      // The API should return an array of log entries
      setLogs(result.logs || result || []);
    } catch (err) {
      const error = err as Error;
      const errorMsg = error.message || 'Failed to fetch execution logs';
      setError(errorMsg);
      console.error('Error fetching execution logs:', err);
      setLogs([]);
    } finally {
      setIsLoading(false);
    }
  }, [session, executionId]);

  useEffect(() => {
    if (executionId) {
      fetchLogs();
    } else {
      setLogs([]);
    }
  }, [executionId, fetchLogs]);

  return {
    logs,
    isLoading,
    error,
    refresh: fetchLogs,
  };
}
