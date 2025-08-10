/**
 * Workflow Enums - Based on API Definition
 * Auto-generated from api.json
 */

// 工作流类型枚举
export enum WorkflowType {
  Sequential = 'sequential',
  Parallel = 'parallel',
  Conditional = 'conditional',
  Loop = 'loop',
  Hybrid = 'hybrid'
}

// 工作流状态枚举
export enum WorkflowStatus {
  Draft = 'draft',
  Active = 'active',
  Paused = 'paused',
  Completed = 'completed',
  Failed = 'failed',
  Archived = 'archived'
}

// 节点类型枚举
export enum NodeType {
  Trigger = 'trigger',
  Action = 'action',
  Condition = 'condition',
  Loop = 'loop',
  Webhook = 'webhook',
  ApiCall = 'api_call',
  Email = 'email',
  Delay = 'delay'
}

// 消息类型枚举
export enum MessageType {
  User = 'user',
  Assistant = 'assistant'
}

// SSE事件类型枚举
export enum SSEEventType {
  Message = 'message',
  StatusChange = 'status_change',
  Workflow = 'workflow',
  Error = 'error',
  Debug = 'debug'
}

// 错误策略枚举
export enum ErrorPolicy {
  Continue = 'continue',
  Stop = 'stop',
  Retry = 'retry'
}

// 调用者策略枚举
export enum CallerPolicy {
  Workflow = 'workflow',
  User = 'user'
}