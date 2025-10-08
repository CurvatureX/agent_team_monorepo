/**
 * API 配置和路径定义
 */

// API 基础配置
export const API_BASE = '/api/proxy/v1';

// API 路径定义
export const API_PATHS = {
  // Workflows
  NODE_TEMPLATES: `${API_BASE}/app/workflows/node-templates`,
  WORKFLOWS: `${API_BASE}/app/workflows/`,
  WORKFLOW: (id: string) => `${API_BASE}/app/workflows/${id}`,
  WORKFLOW_EXECUTE: (id: string) => `${API_BASE}/app/workflows/${id}/execute`,
  WORKFLOW_DEPLOY: (id: string) => `${API_BASE}/app/workflows/${id}/deploy`,
  WORKFLOW_EXECUTIONS: (id: string) => `${API_BASE}/app/workflows/${id}/executions`,

  // Sessions
  SESSIONS: `${API_BASE}/app/sessions`,
  SESSION: (id: string) => `${API_BASE}/app/sessions/${id}`,

  // Executions
  EXECUTION: (id: string) => `${API_BASE}/app/executions/${id}`,
  EXECUTION_LOGS: (id: string) => `${API_BASE}/app/executions/${id}/logs`,
  RECENT_LOGS: `${API_BASE}/app/executions/recent_logs`,
} as const;
