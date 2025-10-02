// Backend-aligned Node Types (from NodeType enum)
export type NodeType =
  | 'TRIGGER'
  | 'AI_AGENT'
  | 'ACTION'
  | 'EXTERNAL_ACTION'
  | 'FLOW'
  | 'HUMAN_IN_THE_LOOP'
  | 'TOOL'
  | 'MEMORY';

// Backend-aligned Subtypes (from respective subtype enums)
export type TriggerSubtype = 'MANUAL' | 'WEBHOOK' | 'CRON' | 'EMAIL' | 'GITHUB' | 'SLACK';
export type AIAgentSubtype = 'OPENAI_CHATGPT' | 'ANTHROPIC_CLAUDE' | 'GOOGLE_GEMINI';
export type ActionSubtype = 'RUN_CODE' | 'DATA_TRANSFORMATION' | 'FILE_OPERATION' | 'HTTP_REQUEST' | 'DATABASE_QUERY';
export type ExternalActionSubtype = 'API_CALL' | 'SLACK' | 'EMAIL' | 'GITHUB' | 'WEBHOOK' | 'NOTIFICATION';
export type ToolSubtype = 'MCP_TOOL' | 'HTTP_CLIENT' | 'FILE_PROCESSOR' | 'EMAIL_TOOL' | 'CODE_TOOL';
export type FlowSubtype = 'IF' | 'LOOP' | 'MERGE' | 'FILTER' | 'WAIT';
export type HumanLoopSubtype = 'GMAIL_INTERACTION' | 'SLACK_INTERACTION' | 'IN_APP_APPROVAL' | 'MANUAL_REVIEW';
export type MemorySubtype = 'CONVERSATION_BUFFER' | 'VECTOR_DATABASE' | 'KEY_VALUE_STORE' | 'DOCUMENT_STORE';

export type NodeSubtype =
  | TriggerSubtype
  | AIAgentSubtype
  | ActionSubtype
  | ExternalActionSubtype
  | ToolSubtype
  | FlowSubtype
  | HumanLoopSubtype
  | MemorySubtype;

// Backend-aligned status types
export type DeploymentStatus = 'DRAFT' | 'PENDING' | 'DEPLOYED' | 'FAILED' | 'UNDEPLOYED';
export type LatestExecutionStatus = 'DRAFT' | 'RUNNING' | 'SUCCESS' | 'ERROR' | 'CANCELED' | 'WAITING_FOR_HUMAN';
export type ExecutionStatus = 'RUNNING' | 'SUCCESS' | 'ERROR' | 'CANCELED';
export type NodeExecutionStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'ERROR' | 'SKIPPED';

export interface AIWorker {
  id: string;
  name: string;
  description: string;
  deploymentStatus: DeploymentStatus;
  latestExecutionStatus: LatestExecutionStatus;
  lastRunTime?: Date;
  nextRunTime?: Date;
  trigger: TriggerInfo;
  graph: WorkflowNode[];
  connections?: Record<string, any>; // Workflow connections data
  executionHistory: ExecutionRecord[];
}

export interface TriggerInfo {
  type: TriggerSubtype;
  config: Record<string, any>;
  description: string;
}

export interface WorkflowNode {
  id: string;
  type: NodeType;
  position: { x: number; y: number };
  data: {
    name?: string;
    description?: string;
    subtype?: NodeSubtype;
    parameters?: Record<string, any>;
    icon_url?: string;
    [key: string]: any;
  };
}

export interface ExecutionRecord {
  id: string;
  startTime: Date;
  endTime?: Date;
  status: LatestExecutionStatus;
  duration?: number;
  triggerType: TriggerSubtype;
  nodeExecutions?: NodeExecution[];
  error?: string;
}

export interface NodeExecution {
  nodeId: string;
  nodeName: string;
  startTime: Date;
  endTime?: Date;
  status: NodeExecutionStatus;
  input?: any;
  output?: any;
  error?: string;
  logs: LogEntry[];
}

export interface LogEntry {
  timestamp: Date;
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  nodeId?: string;
  data?: any;
}
