export interface AIWorker {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'idle' | 'error' | 'paused';
  lastRunTime?: Date;
  nextRunTime?: Date;
  trigger: TriggerInfo;
  graph: WorkflowNode[];
  executionHistory: ExecutionRecord[];
}

export interface TriggerInfo {
  type: 'schedule' | 'webhook' | 'manual' | 'event';
  config: Record<string, any>;
  description: string;
}

export interface WorkflowNode {
  id: string;
  type: 'trigger' | 'ai_agent' | 'action' | 'tool' | 'memory' | 'flow' | 'human_in_the_loop' | 'external_action';
  position: { x: number; y: number };
  data: {
    name?: string;
    description?: string;
    subtype?: string;
    parameters?: Record<string, any>;
    [key: string]: any;
  };
}

export interface ExecutionRecord {
  id: string;
  startTime: Date;
  endTime?: Date;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  duration?: number;
  triggerType: string;
  nodeExecutions?: NodeExecution[];
  error?: string;
}

export interface NodeExecution {
  nodeId: string;
  nodeName: string;
  startTime: Date;
  endTime?: Date;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
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

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
}
