import { AIWorker, ExecutionRecord } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  // Add authentication token if available
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${token}`,
    };
  }

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      throw new APIError(response.status, `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(0, `Network error: ${error}`);
  }
}

export const apiService = {
  // Workflow management
  async getWorkflows(): Promise<AIWorker[]> {
    return request<AIWorker[]>('/app/workflows');
  },

  async getWorkflow(id: string): Promise<AIWorker> {
    return request<AIWorker>(`/app/workflows/${id}`);
  },

  async createWorkflow(workflow: Omit<AIWorker, 'id' | 'executionHistory'>): Promise<AIWorker> {
    return request<AIWorker>('/app/workflows', {
      method: 'POST',
      body: JSON.stringify(workflow),
    });
  },

  async updateWorkflow(id: string, updates: Partial<AIWorker>): Promise<AIWorker> {
    return request<AIWorker>(`/app/workflows/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  async deleteWorkflow(id: string): Promise<void> {
    return request<void>(`/app/workflows/${id}`, {
      method: 'DELETE',
    });
  },

  // Workflow execution
  async executeWorkflow(id: string, data?: any): Promise<ExecutionRecord> {
    return request<ExecutionRecord>(`/app/workflows/${id}/execute`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
  },

  async cancelExecution(executionId: string): Promise<void> {
    return request<void>(`/app/executions/${executionId}/cancel`, {
      method: 'POST',
    });
  },

  // Execution monitoring
  async getExecution(executionId: string): Promise<ExecutionRecord> {
    return request<ExecutionRecord>(`/app/executions/${executionId}`);
  },

  async getExecutionHistory(workflowId: string): Promise<ExecutionRecord[]> {
    return request<ExecutionRecord[]>(`/app/workflows/${workflowId}/executions`);
  },

  async getExecutionLogs(executionId: string): Promise<ExecutionRecord> {
    return request<ExecutionRecord>(`/app/executions/${executionId}/logs`);
  },

  // Real-time updates using Server-Sent Events
  subscribeToWorkflowUpdates(workflowId: string, callback: (data: any) => void): EventSource {
    const eventSource = new EventSource(`${API_BASE_URL}/app/workflows/${workflowId}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        callback(data);
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
    };

    return eventSource;
  },

  subscribeToExecutionUpdates(executionId: string, callback: (data: any) => void): EventSource {
    const eventSource = new EventSource(`${API_BASE_URL}/app/executions/${executionId}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        callback(data);
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
    };

    return eventSource;
  },

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return request<{ status: string; timestamp: string }>('/public/health');
  },
};

export default apiService;
