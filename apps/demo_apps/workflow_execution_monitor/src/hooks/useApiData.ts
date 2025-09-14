import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from '@/services/api';
import { transformAPIWorkflowToAIWorker, transformAPIExecutionToRecord, needsAuthentication } from '@/services/dataTransform';
import { AIWorker, ExecutionRecord } from '@/types/workflow';
import { useAuth } from '@/contexts/auth-context';

interface ApiDataState {
  workers: AIWorker[];
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

interface ExecutionDataState {
  executions: Map<string, ExecutionRecord>;
  isLoading: boolean;
  error: string | null;
}

export const useWorkflowData = () => {
  const [dataState, setDataState] = useState<ApiDataState>({
    workers: [],
    isLoading: false,
    error: null,
    lastUpdated: null
  });

  const { session, user, loading: authLoading } = useAuth();
  const refreshTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const hasFetchedRef = useRef(false);

  // Update API client token when session changes
  useEffect(() => {
    if (session?.access_token) {
      apiClient.setAccessToken(session.access_token);
    } else {
      apiClient.setAccessToken(null);
    }
  }, [session]);

  const fetchWorkflows = useCallback(async () => {
    if (!session?.access_token || authLoading) return;

    setDataState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // Fetch workflows with executions
      const workflowsResponse = await apiClient.getWorkflows({
        active_only: false,
        limit: 100
      });

      // Transform workflows to workers using the metadata already included in the workflows response
      // No need for individual API calls - the backend now includes deployment and execution metadata
      const workers = workflowsResponse.workflows.map(workflow => {
        // Create deployment info from the workflow metadata
        const deploymentInfo = workflow.deployment_status ? {
          status: workflow.deployment_status,
          deployed_at: workflow.deployed_at,
        } : undefined;

        // Transform workflow with the metadata already included in the response
        return transformAPIWorkflowToAIWorker(workflow, [], deploymentInfo);
      });

      setDataState({
        workers,
        isLoading: false,
        error: null,
        lastUpdated: new Date()
      });

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch workflows';
      setDataState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage
      }));
    }
  }, [session?.access_token, authLoading]);

  // Auto-refresh data every 1 minute
  const startAutoRefresh = useCallback(() => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }

    refreshTimeoutRef.current = setTimeout(async () => {
      await fetchWorkflows();
      startAutoRefresh(); // Schedule next refresh
    }, 60000); // 1 minute
  }, [fetchWorkflows]);

  // Main effect: Fetch data when authenticated and setup auto-refresh
  useEffect(() => {
    if (session?.access_token && !authLoading && !hasFetchedRef.current) {
      hasFetchedRef.current = true;
      fetchWorkflows().then(() => {
        startAutoRefresh();
      });
    } else if (!session?.access_token || authLoading) {
      // Clear data when not authenticated
      hasFetchedRef.current = false;
      setDataState({
        workers: [],
        isLoading: false,
        error: null,
        lastUpdated: null
      });
      // Clear any existing refresh timeout
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    }

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [session?.access_token, authLoading]); // Only trigger on auth state changes
  // Note: fetchWorkflows and startAutoRefresh intentionally omitted to prevent dependency loop

  return {
    ...dataState,
    refresh: fetchWorkflows
  };
};

// Hook for fetching individual workflow details with executions
export const useWorkflowDetail = (workflowId: string | null) => {
  const [detailState, setDetailState] = useState<{
    workflow: AIWorker | null;
    isLoading: boolean;
    error: string | null;
  }>({
    workflow: null,
    isLoading: false,
    error: null
  });

  const { session, loading: authLoading } = useAuth();

  const fetchWorkflowDetail = useCallback(async (id: string) => {
    if (!session?.access_token || authLoading) return;

    setDetailState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // Fetch workflow details and executions in parallel
      const [workflow, executionsResponse] = await Promise.all([
        apiClient.getWorkflow(id),
        apiClient.getWorkflowExecutions(id, 20) // Get latest 20 executions
      ]);

      // Transform the detailed workflow data with raw executions from API
      const detailedWorker = transformAPIWorkflowToAIWorker(workflow, executionsResponse.executions, {
        status: workflow.deployment_status,
        deployed_at: workflow.deployed_at,
      });

      setDetailState({
        workflow: detailedWorker,
        isLoading: false,
        error: null
      });

      return detailedWorker;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch workflow details';
      setDetailState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage
      }));
    }
  }, [session, authLoading]);

  // Fetch workflow details when workflowId changes
  useEffect(() => {
    if (workflowId && session?.access_token && !authLoading) {
      fetchWorkflowDetail(workflowId);
    } else {
      setDetailState({
        workflow: null,
        isLoading: false,
        error: null
      });
    }
  }, [workflowId, session, authLoading, fetchWorkflowDetail]);

  return {
    ...detailState,
    fetchWorkflowDetail
  };
};

export const useExecutionData = (executionId?: string) => {
  const [executionState, setExecutionState] = useState<ExecutionDataState>({
    executions: new Map(),
    isLoading: false,
    error: null
  });

  const { session, loading: authLoading } = useAuth();

  const fetchExecution = useCallback(async (id: string) => {
    if (!session?.access_token || authLoading) return;

    setExecutionState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const execution = await apiClient.getExecution(id);
      const logs = await apiClient.getExecutionLogs(id, { limit: 500 });

      const executionRecord = transformAPIExecutionToRecord(execution, logs.logs);

      setExecutionState(prev => ({
        ...prev,
        executions: new Map(prev.executions).set(id, executionRecord),
        isLoading: false,
        error: null
      }));

      return executionRecord;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch execution';
      setExecutionState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage
      }));
    }
  }, [session, authLoading]);

  // Fetch execution when executionId changes
  useEffect(() => {
    if (executionId && session?.access_token && !authLoading) {
      fetchExecution(executionId);
    }
  }, [executionId, session, authLoading, fetchExecution]);

  return {
    ...executionState,
    fetchExecution,
    getExecution: (id: string) => executionState.executions.get(id)
  };
};

// Hook for fetching historical execution logs (static API call)
export const useExecutionLogs = (executionId: string | null) => {
  const [logs, setLogs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { session, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!executionId || !session?.access_token || authLoading) {
      setLogs([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    const fetchLogs = async () => {
      setIsLoading(true);
      setError(null);

      try {
        console.log(`[Static Logs] Fetching logs for execution ${executionId}`);
        const response = await apiClient.getExecutionLogs(executionId, { limit: 500 });

        // Transform logs to match the expected format
        const transformedLogs = response.logs.map((log, index) => ({
          id: log.id || `${executionId}-${index}`,
          execution_id: executionId,
          timestamp: log.timestamp,
          level: log.level.toLowerCase(),
          message: log.message,
          node_id: log.node_id,
          event_type: log.event_type || 'log',
          display_priority: 5, // Default priority for historical logs
          is_milestone: false,
          is_realtime: false,
          data: log.data
        }));

        setLogs(transformedLogs);
        setIsLoading(false);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch execution logs';
        console.error(`[Static Logs] Error fetching logs for ${executionId}:`, error);
        setError(errorMessage);
        setIsLoading(false);
      }
    };

    fetchLogs();
  }, [executionId, session, authLoading]);

  return {
    logs,
    isLoading,
    error,
    clearLogs: () => setLogs([])
  };
};

// Enhanced hook for real-time execution monitoring with proper SSE event handling
// Only used for currently running executions
export const useRealtimeExecution = (executionId: string | null, isRunning: boolean = false) => {
  const [logs, setLogs] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const { session, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!executionId || !session?.access_token || authLoading || !isRunning) {
      setLogs([]);
      setIsConnected(false);
      setError(null);
      setIsComplete(false);
      return;
    }

    setError(null);
    setIsComplete(false);

    // Create SSE connection for real-time logs
    try {
      const eventSource = apiClient.createLogStream(executionId, true);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log(`[SSE] Connected to execution logs stream for ${executionId}`);
        setIsConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const eventData = JSON.parse(event.data);
          console.log(`[SSE] Received event:`, eventData);

          // Handle different SSE event types from API gateway
          switch (eventData.type) {
            case 'log':
              // Extract log information from the SSE event
              const logEntry = {
                id: `${executionId}-${Date.now()}-${Math.random()}`,
                execution_id: executionId,
                timestamp: eventData.data.timestamp || new Date().toISOString(),
                level: eventData.data.level || 'info',
                message: eventData.data.message || '',
                node_id: eventData.data.node_id,
                event_type: eventData.data.event_type || 'log',
                display_priority: eventData.data.display_priority || 5,
                is_milestone: eventData.data.is_milestone || false,
                step_number: eventData.data.step_number,
                total_steps: eventData.data.total_steps,
                is_realtime: eventData.data.is_realtime || false
              };
              setLogs(prev => [...prev, logEntry]);
              break;

            case 'complete':
              console.log(`[SSE] Log stream completed:`, eventData.data);
              setIsComplete(true);
              // For following streams, keep connection open
              // For non-following streams, close after completion
              setTimeout(() => {
                if (eventSourceRef.current) {
                  eventSourceRef.current.close();
                }
              }, 100);
              break;

            case 'error':
              console.error(`[SSE] Log stream error:`, eventData.data);
              setError(eventData.data.error || 'Unknown error occurred');
              break;

            default:
              console.warn(`[SSE] Unknown event type: ${eventData.type}`, eventData);
              break;
          }
        } catch (error) {
          console.warn('Failed to parse SSE event:', error, event.data);
        }
      };

      eventSource.onerror = (event) => {
        console.error(`[SSE] Connection error:`, event);
        setIsConnected(false);
        setError('Connection to log stream failed');
      };

    } catch (error) {
      console.error('Failed to create log stream:', error);
      setIsConnected(false);
      setError('Failed to initialize log stream');
    }

    return () => {
      if (eventSourceRef.current) {
        console.log(`[SSE] Closing connection for execution ${executionId}`);
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setIsConnected(false);
    };
  }, [executionId, isRunning, session, authLoading]);

  const reconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsConnected(false);
    setError(null);
    // Trigger useEffect to reconnect by updating a dependency
  }, []);

  return {
    logs,
    isConnected,
    isComplete,
    error,
    clearLogs: () => setLogs([]),
    reconnect
  };
};

// Hook for fetching workflow executions
export const useWorkflowExecutions = (workflowId: string | null, limit: number = 20) => {
  const [executionsState, setExecutionsState] = useState<{
    executions: ExecutionRecord[];
    isLoading: boolean;
    error: string | null;
    lastUpdated: Date | null;
  }>({
    executions: [],
    isLoading: false,
    error: null,
    lastUpdated: null
  });

  const { session, loading: authLoading } = useAuth();

  const fetchExecutions = useCallback(async () => {
    if (!workflowId || !session?.access_token || authLoading) return;

    setExecutionsState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const executionsResponse = await apiClient.getWorkflowExecutions(workflowId, limit);

      // Transform executions to records
      const executionRecords = executionsResponse.executions.map(execution =>
        transformAPIExecutionToRecord(execution, [])
      );

      setExecutionsState({
        executions: executionRecords,
        isLoading: false,
        error: null,
        lastUpdated: new Date()
      });

      return executionRecords;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch workflow executions';
      setExecutionsState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage
      }));
    }
  }, [workflowId, limit, session, authLoading]);

  // Fetch executions when workflowId changes
  useEffect(() => {
    if (workflowId && session?.access_token && !authLoading) {
      fetchExecutions();
    } else {
      setExecutionsState({
        executions: [],
        isLoading: false,
        error: null,
        lastUpdated: null
      });
    }
  }, [workflowId, session, authLoading, fetchExecutions]);

  return {
    ...executionsState,
    refresh: fetchExecutions
  };
};
