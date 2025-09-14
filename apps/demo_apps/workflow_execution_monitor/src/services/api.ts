interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
}

// Removed LoginResponse interface since we'll use Supabase auth

interface ApiWorkflow {
  id: string;
  name: string;
  description: string;
  nodes: any[];
  connections: object;
  settings: object;
  tags: string[];
  active: boolean;
  created_at: string;
  updated_at: string;
  // Enhanced metadata from backend optimization
  deployment_status?: string;
  deployed_at?: string;
  latest_execution_status?: string;
  latest_execution_time?: string;
  latest_execution_id?: string;
}

interface ApiExecution {
  id: string;
  execution_id: string;
  workflow_id: string;
  status: 'NEW' | 'RUNNING' | 'SUCCESS' | 'ERROR' | 'CANCELED' | 'WAITING' | 'PAUSED';
  mode: string;
  triggered_by: string;
  start_time: number;
  end_time?: number;
  run_data: object;
  metadata: object;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

interface ApiExecutionLog {
  id: string;
  execution_id: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  message: string;
  timestamp: string;
  event_type?: string;
  node_id?: string;
  data?: any;
}

class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;
  private refreshCallback: (() => Promise<void>) | null = null;

  constructor() {
    // Use the proxy route to avoid CORS issues in development
    this.baseUrl = '/api/proxy';
  }

  // Set refresh callback from auth context
  setRefreshCallback(callback: (() => Promise<void>) | null): void {
    this.refreshCallback = callback;
  }

  // Set JWT token from Supabase
  setAccessToken(token: string | null): void {
    this.accessToken = token;
  }

  // Get current access token
  getAccessToken(): string | null {
    return this.accessToken;
  }

  // Make authenticated request with automatic token refresh
  private async makeRequest<T>(endpoint: string, options: RequestInit = {}, retryCount = 0): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    console.log(`[API Client] Making request to ${endpoint}, token available: ${!!this.accessToken}`);
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
      console.log(`[API Client] Added Bearer token: ${this.accessToken.substring(0, 20)}...`);
    } else {
      console.log(`[API Client] No access token available`);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401 && retryCount === 0 && this.refreshCallback) {
        console.log(`[API Client] 401 Unauthorized - attempting token refresh`);
        try {
          // Attempt to refresh the token
          await this.refreshCallback();
          console.log(`[API Client] Token refreshed, retrying request`);
          // Retry the request with the new token
          return this.makeRequest<T>(endpoint, options, retryCount + 1);
        } catch (refreshError) {
          console.error(`[API Client] Token refresh failed:`, refreshError);
          throw new Error('Authentication required - token refresh failed');
        }
      } else if (response.status === 401) {
        console.log(`[API Client] 401 Unauthorized - no refresh available or already retried`);
        throw new Error('Authentication required');
      }
      throw new Error(`API request failed: ${response.status}`);
    }

    return response.json();
  }

  // Workflow APIs
  async getWorkflows(params: {
    active_only?: boolean;
    tags?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<{workflows: ApiWorkflow[], total: number}> {
    const searchParams = new URLSearchParams();
    if (params.active_only !== undefined) searchParams.set('active_only', params.active_only.toString());
    if (params.tags) searchParams.set('tags', params.tags);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    // Add trailing slash to match backend endpoint and avoid redirects
    const endpoint = query ? `/v1/app/workflows/?${query}` : `/v1/app/workflows/`;

    return this.makeRequest<{workflows: ApiWorkflow[], total: number}>(endpoint);
  }

  async getWorkflow(workflowId: string): Promise<ApiWorkflow> {
    const response = await this.makeRequest<{workflow: ApiWorkflow, found: boolean, message: string}>(`/v1/app/workflows/${workflowId}`);
    return response.workflow;
  }

  async getWorkflowExecutions(workflowId: string, limit: number = 50): Promise<{executions: ApiExecution[], total: number}> {
    return this.makeRequest<{executions: ApiExecution[], total: number}>(
      `/v1/app/workflows/${workflowId}/executions?limit=${limit}`
    );
  }

  // Execution APIs
  async getExecution(executionId: string): Promise<ApiExecution> {
    return this.makeRequest<ApiExecution>(`/v1/app/executions/${executionId}`);
  }

  async getExecutionLogs(executionId: string, params: {
    limit?: number;
    offset?: number;
    level?: string;
    start_time?: string;
    end_time?: string;
  } = {}): Promise<{logs: ApiExecutionLog[], total: number}> {
    const searchParams = new URLSearchParams();
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());
    if (params.level) searchParams.set('level', params.level);
    if (params.start_time) searchParams.set('start_time', params.start_time);
    if (params.end_time) searchParams.set('end_time', params.end_time);

    const query = searchParams.toString();
    const endpoint = `/v1/app/executions/${executionId}/logs${query ? `?${query}` : ''}`;

    return this.makeRequest<{logs: ApiExecutionLog[], total: number}>(endpoint);
  }

  async getActiveExecutions(): Promise<{executions: ApiExecution[]}> {
    return this.makeRequest<{executions: ApiExecution[]}>('/v1/workflows/executions/active');
  }

  // Real-time streaming - updated to match API gateway endpoint
  createLogStream(executionId: string, follow: boolean = false): EventSource {
    const params = new URLSearchParams();
    if (follow) params.set('follow', 'true');

    // Add authorization token to URL params since EventSource doesn't support custom headers
    if (this.accessToken) {
      params.set('access_token', this.accessToken);
    }

    const query = params.toString();
    const url = `${this.baseUrl}/v1/app/executions/${executionId}/logs/stream${query ? `?${query}` : ''}`;

    console.log(`[API Client] Creating SSE connection to: ${url.replace(/access_token=[^&]+/, 'access_token=***')}`);

    const eventSource = new EventSource(url);
    return eventSource;
  }

  // WebSocket connection for real-time logs
  createLogWebSocket(executionId: string): WebSocket {
    const wsUrl = this.baseUrl.replace('https://', 'wss://').replace('http://', 'ws://');
    return new WebSocket(`${wsUrl}/v1/workflows/executions/${executionId}/logs/stream`);
  }

  // Workflow actions
  async executeWorkflow(workflowId: string, data?: any): Promise<{execution_id: string}> {
    return this.makeRequest<{execution_id: string}>(`/v1/app/workflows/${workflowId}/execute`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
  }

  async triggerWorkflow(workflowId: string): Promise<{execution_id: string}> {
    return this.makeRequest<{execution_id: string}>(`/v1/app/workflows/${workflowId}/trigger/manual`, {
      method: 'POST',
    });
  }

  async deployWorkflow(workflowId: string, config?: any): Promise<{deployment_id: string}> {
    return this.makeRequest<{deployment_id: string}>(`/v1/app/workflows/${workflowId}/deploy`, {
      method: 'POST',
      body: JSON.stringify(config || {}),
    });
  }

  async getDeploymentStatus(workflowId: string): Promise<{status: string, details?: any}> {
    return this.makeRequest<{status: string, details?: any}>(`/v1/app/workflows/${workflowId}/deployment/status`);
  }

  // Note: User profile is now handled by Supabase auth context

  // Manual node invocation APIs
  async getNodeSchema(nodeType: string, nodeSubtype: string): Promise<{
    node_type: string;
    node_subtype: string;
    supported: boolean;
    schema: {
      type: string;
      properties: any;
      required: string[];
    };
    examples: any[];
    description: string;
    success: boolean;
  }> {
    return this.makeRequest(`/v1/public/node-schemas/${nodeType.toLowerCase()}/${nodeSubtype.toLowerCase()}`);
  }

  // Backward compatibility - getTriggerSchema now uses the new node-schemas endpoint
  async getTriggerSchema(triggerType: string): Promise<{
    trigger_type: string;
    schema: {
      type: string;
      properties: any;
      required: string[];
    };
    examples: any[];
    description: string;
    success: boolean;
  }> {
    const nodeSchema = await this.getNodeSchema('trigger', triggerType);
    // Transform the response to maintain backward compatibility
    return {
      trigger_type: triggerType,
      schema: nodeSchema.schema,
      examples: nodeSchema.examples,
      description: nodeSchema.description,
      success: nodeSchema.success
    };
  }

  // Get all available node types and their manual invocation support
  async getNodeTypes(): Promise<{
    node_types: Record<string, {
      subtypes: Array<{
        subtype: string;
        name: string;
        description: string;
        manual_invocation_supported: boolean;
      }>;
      manual_invocation_count: number;
      total_count: number;
    }>;
    summary: {
      total_node_types: number;
      total_specifications: number;
      manual_invocation_supported: number;
      manual_invocation_percentage: number;
    };
    success: boolean;
  }> {
    return this.makeRequest('/v1/public/node-types');
  }

  async manualInvokeTrigger(workflowId: string, triggerNodeId: string, data: {
    parameters: any;
    description?: string;
  }): Promise<{
    success: boolean;
    workflow_id: string;
    trigger_node_id: string;
    execution_id: string;
    message: string;
    trigger_data: any;
    execution_url: string;
  }> {
    return this.makeRequest(`/v1/app/workflows/${workflowId}/triggers/${triggerNodeId}/manual-invoke`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Health check
  async healthCheck(): Promise<{status: string}> {
    return this.makeRequest<{status: string}>('/v1/public/health');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export type { ApiWorkflow, ApiExecution, ApiExecutionLog };
