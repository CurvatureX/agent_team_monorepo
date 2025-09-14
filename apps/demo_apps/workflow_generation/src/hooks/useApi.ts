import { useState, useEffect, useCallback } from 'react';
import { AIWorker, ExecutionRecord } from '../types';
import apiService from '../services/api';

// Hook for fetching workflows
export const useWorkflows = () => {
  const [workflows, setWorkflows] = useState<AIWorker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkflows = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getWorkflows();
      setWorkflows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch workflows');
      console.error('Error fetching workflows:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  return { workflows, loading, error, refetch: fetchWorkflows };
};

// Hook for fetching a single workflow
export const useWorkflow = (workflowId: string | undefined) => {
  const [workflow, setWorkflow] = useState<AIWorker | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkflow = useCallback(async () => {
    if (!workflowId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getWorkflow(workflowId);
      setWorkflow(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch workflow');
      console.error('Error fetching workflow:', err);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    fetchWorkflow();
  }, [fetchWorkflow]);

  return { workflow, loading, error, refetch: fetchWorkflow };
};

// Hook for fetching execution history
export const useExecutionHistory = (workflowId: string | undefined) => {
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExecutions = useCallback(async () => {
    if (!workflowId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getExecutionHistory(workflowId);
      setExecutions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch execution history');
      console.error('Error fetching execution history:', err);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  return { executions, loading, error, refetch: fetchExecutions };
};

// Hook for real-time workflow updates
export const useWorkflowUpdates = (workflowId: string | undefined) => {
  const [updates, setUpdates] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!workflowId) return;

    const eventSource = apiService.subscribeToWorkflowUpdates(workflowId, (data) => {
      setUpdates(prev => [...prev, data]);
    });

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onerror = () => {
      setIsConnected(false);
    };

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [workflowId]);

  const clearUpdates = useCallback(() => {
    setUpdates([]);
  }, []);

  return { updates, isConnected, clearUpdates };
};

// Hook for real-time execution updates
export const useExecutionUpdates = (executionId: string | undefined) => {
  const [updates, setUpdates] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!executionId) return;

    const eventSource = apiService.subscribeToExecutionUpdates(executionId, (data) => {
      setUpdates(prev => [...prev, data]);
    });

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onerror = () => {
      setIsConnected(false);
    };

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [executionId]);

  const clearUpdates = useCallback(() => {
    setUpdates([]);
  }, []);

  return { updates, isConnected, clearUpdates };
};

// Hook for workflow actions
export const useWorkflowActions = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const executeWorkflow = useCallback(async (workflowId: string, data?: any): Promise<ExecutionRecord | null> => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiService.executeWorkflow(workflowId, data);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute workflow');
      console.error('Error executing workflow:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelExecution = useCallback(async (executionId: string): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      await apiService.cancelExecution(executionId);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel execution');
      console.error('Error cancelling execution:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return { executeWorkflow, cancelExecution, loading, error };
};
