// Workflow node types
export type NodeType = 
  | 'TRIGGER_NODE'
  | 'AI_AGENT_NODE'
  | 'ACTION_NODE'
  | 'EXTERNAL_ACTION_NODE'
  | 'FLOW_NODE'
  | 'HUMAN_IN_THE_LOOP_NODE'
  | 'TOOL_NODE'
  | 'MEMORY_NODE';

// Node subtypes
export type NodeSubtype =
  | 'TRIGGER_CALENDAR'
  | 'TRIGGER_WEBHOOK'
  | 'TRIGGER_SCHEDULE'
  | 'AI_AGENT'
  | 'ACTION_DATA_TRANSFORMATION'
  | 'ACTION_HTTP_REQUEST'
  | 'EXTERNAL_GITHUB'
  | 'EXTERNAL_SLACK'
  | 'FLOW_FILTER'
  | 'FLOW_SWITCH'
  | 'HUMAN_DISCORD'
  | 'HUMAN_GMAIL'
  | 'TOOL_FUNCTION'
  | 'MEMORY_STORE';

// Error handling policy
export type ErrorPolicy = 'STOP_WORKFLOW_ON_ERROR' | 'CONTINUE_ON_ERROR' | 'RETRY';

// Node position
export interface Position {
  x: number;
  y: number;
}

// Retry policy
export interface RetryPolicy {
  max_tries: number;
  wait_between_tries: number;
}

// Node definition
export interface Node {
  id: string;
  name: string;
  type: NodeType;
  subtype: NodeSubtype;
  type_version: number;
  position: Position;
  disabled: boolean;
  parameters: Record<string, unknown>;
  credentials: Record<string, unknown>;
  on_error: ErrorPolicy;
  retry_policy: RetryPolicy;
  notes: Record<string, unknown>;
  webhooks: unknown[];
}

// Connection definition
export interface ConnectionItem {
  node: string;
  type: string;
  index: number;
}

export interface NodeConnections {
  output?: {
    connections: ConnectionItem[];
  };
}

export interface Connections {
  connections: Record<string, NodeConnections>;
}

// Workflow settings
export interface WorkflowSettings {
  timezone: {
    default: string;
  };
  save_execution_progress: boolean;
  save_manual_executions: boolean;
  timeout: number;
  error_policy: string;
  caller_policy: string;
}

// Complete workflow data structure
export interface WorkflowData {
  id: string;
  name: string;
  active: boolean;
  nodes: Node[];
  connections: Connections;
  settings: WorkflowSettings;
  static_data: Record<string, unknown>;
  pin_data: Record<string, unknown>;
  created_at: number;
  updated_at: number;
  version: string;
  tags: string[];
} 