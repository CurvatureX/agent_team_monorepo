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

// 工作流状态枚举 (Aligned with backend WorkflowStatusEnum)
export enum WorkflowStatus {
  Idle = 'IDLE',
  Running = 'RUNNING',
  Success = 'SUCCESS',
  Error = 'ERROR',
  Canceled = 'CANCELED',
  WaitingForHuman = 'WAITING_FOR_HUMAN'
}

// 工作流部署状态枚举 (Aligned with backend WorkflowDeploymentStatus)
export enum WorkflowDeploymentStatus {
  Undeployed = 'UNDEPLOYED',            // 未部署 (默认状态)
  Deploying = 'DEPLOYING',              // 正在部署
  Deployed = 'DEPLOYED',                // 已部署
  DeploymentFailed = 'DEPLOYMENT_FAILED' // 部署失败
}

// 执行状态枚举 (Aligned with backend ExecutionStatus)
export enum ExecutionStatusEnum {
  Idle = 'IDLE',                 // 闲置状态 (从未执行，默认状态)
  New = 'NEW',
  Pending = 'PENDING',
  Running = 'RUNNING',
  Paused = 'PAUSED',
  Success = 'SUCCESS',
  Error = 'ERROR',
  Canceled = 'CANCELED',
  Waiting = 'WAITING',
  Timeout = 'TIMEOUT',
  WaitingForHuman = 'WAITING_FOR_HUMAN',
  Skipped = 'SKIPPED',
  Completed = 'COMPLETED',
  Cancelled = 'CANCELLED', // Alternative spelling
}

// 节点类型枚举 (Aligned with backend NodeType)
export enum NodeType {
  TRIGGER = 'TRIGGER',
  AI_AGENT = 'AI_AGENT',
  EXTERNAL_ACTION = 'EXTERNAL_ACTION',
  ACTION = 'ACTION',
  FLOW = 'FLOW',
  HUMAN_IN_THE_LOOP = 'HUMAN_IN_THE_LOOP',
  TOOL = 'TOOL',
  MEMORY = 'MEMORY'
}

// ===== Subtype Enums (Aligned with backend) =====

export enum TriggerSubtype {
  MANUAL = 'MANUAL',
  WEBHOOK = 'WEBHOOK',
  CRON = 'CRON',
  EMAIL = 'EMAIL',
  GITHUB = 'GITHUB',
  SLACK = 'SLACK',
}

export enum AIAgentSubtype {
  OPENAI_CHATGPT = 'OPENAI_CHATGPT',
  ANTHROPIC_CLAUDE = 'ANTHROPIC_CLAUDE',
  GOOGLE_GEMINI = 'GOOGLE_GEMINI',
}

export enum ExternalActionSubtype {
  API_CALL = 'API_CALL',
  WEBHOOK = 'WEBHOOK',
  NOTIFICATION = 'NOTIFICATION',
  SLACK = 'SLACK',
  DISCORD_ACTION = 'DISCORD_ACTION',
  TELEGRAM_ACTION = 'TELEGRAM_ACTION',
  EMAIL = 'EMAIL',
  GITHUB = 'GITHUB',
  GITLAB_ACTION = 'GITLAB_ACTION',
  JIRA_ACTION = 'JIRA_ACTION',
  GOOGLE_CALENDAR = 'GOOGLE_CALENDAR',
  TRELLO = 'TRELLO',
  NOTION = 'NOTION',
  FIRECRAWL = 'FIRECRAWL',
  AWS_ACTION = 'AWS_ACTION',
  GCP_ACTION = 'GCP_ACTION',
  AZURE_ACTION = 'AZURE_ACTION',
  POSTGRES_ACTION = 'POSTGRES_ACTION',
  MYSQL_ACTION = 'MYSQL_ACTION',
  MONGODB_ACTION = 'MONGODB_ACTION',
}

export enum ActionSubtype {
  RUN_CODE = 'RUN_CODE',
  EXECUTE_SCRIPT = 'EXECUTE_SCRIPT',
  DATA_TRANSFORMATION = 'DATA_TRANSFORMATION',
  DATA_VALIDATION = 'DATA_VALIDATION',
  DATA_FORMATTING = 'DATA_FORMATTING',
  FILE_OPERATION = 'FILE_OPERATION',
  FILE_UPLOAD = 'FILE_UPLOAD',
  FILE_DOWNLOAD = 'FILE_DOWNLOAD',
  HTTP_REQUEST = 'HTTP_REQUEST',
  WEBHOOK_CALL = 'WEBHOOK_CALL',
  DATABASE_QUERY = 'DATABASE_QUERY',
  DATABASE_OPERATION = 'DATABASE_OPERATION',
  WEB_SEARCH = 'WEB_SEARCH',
}

export enum FlowSubtype {
  IF = 'IF',
  LOOP = 'LOOP',
  FOR_EACH = 'FOR_EACH',
  WHILE = 'WHILE',
  MERGE = 'MERGE',
  SPLIT = 'SPLIT',
  FILTER = 'FILTER',
  SORT = 'SORT',
  WAIT = 'WAIT',
  DELAY = 'DELAY',
  TIMEOUT = 'TIMEOUT',
}

export enum HumanLoopSubtype {
  GMAIL_INTERACTION = 'GMAIL_INTERACTION',
  OUTLOOK_INTERACTION = 'OUTLOOK_INTERACTION',
  SLACK_INTERACTION = 'SLACK_INTERACTION',
  DISCORD_INTERACTION = 'DISCORD_INTERACTION',
  TELEGRAM_INTERACTION = 'TELEGRAM_INTERACTION',
  TEAMS_INTERACTION = 'TEAMS_INTERACTION',
  IN_APP_APPROVAL = 'IN_APP_APPROVAL',
  FORM_SUBMISSION = 'FORM_SUBMISSION',
  MANUAL_REVIEW = 'MANUAL_REVIEW',
}

export enum ToolSubtype {
  NOTION_MCP_TOOL = 'NOTION_MCP_TOOL',
  SLACK_MCP_TOOL = 'SLACK_MCP_TOOL',
  DISCORD_MCP_TOOL = 'DISCORD_MCP_TOOL',
  GOOGLE_CALENDAR_MCP_TOOL = 'GOOGLE_CALENDAR_MCP_TOOL',
  FIRECRAWL_MCP_TOOL = 'FIRECRAWL_MCP_TOOL',
  GOOGLE_CALENDAR = 'GOOGLE_CALENDAR_TOOL',
  OUTLOOK_CALENDAR = 'OUTLOOK_CALENDAR_TOOL',
  CALENDAR_GENERIC = 'CALENDAR_GENERIC_TOOL',
  EMAIL_TOOL = 'EMAIL_TOOL',
  GMAIL_TOOL = 'GMAIL_TOOL',
  HTTP_CLIENT = 'HTTP_CLIENT',
  FILE_PROCESSOR = 'FILE_PROCESSOR',
  IMAGE_PROCESSOR = 'IMAGE_PROCESSOR',
  CODE_TOOL = 'CODE_TOOL',
}

export enum MemorySubtype {
  CONVERSATION_BUFFER = 'CONVERSATION_BUFFER',
  CONVERSATION_SUMMARY = 'CONVERSATION_SUMMARY',
  VECTOR_DATABASE = 'VECTOR_DATABASE',
  KEY_VALUE_STORE = 'KEY_VALUE_STORE',
  DOCUMENT_STORE = 'DOCUMENT_STORE',
  ENTITY_MEMORY = 'ENTITY_MEMORY',
  EPISODIC_MEMORY = 'EPISODIC_MEMORY',
  KNOWLEDGE_BASE = 'KNOWLEDGE_BASE',
  GRAPH_MEMORY = 'GRAPH_MEMORY',
}

// ===== Subtype Canonical <-> Alias mapping for template compatibility =====

export const NodeSubtypeAliasToCanonical: Record<string, Record<string, string>> = {
  [NodeType.TRIGGER]: {
    CHAT: TriggerSubtype.MANUAL,
    FORM: TriggerSubtype.MANUAL,
    CALENDAR: TriggerSubtype.CRON,
  },
  [NodeType.AI_AGENT]: {
    ROUTER_AGENT: AIAgentSubtype.OPENAI_CHATGPT,
    TASK_ANALYZER: AIAgentSubtype.OPENAI_CHATGPT,
    DATA_INTEGRATOR: AIAgentSubtype.OPENAI_CHATGPT,
    REPORT_GENERATOR: AIAgentSubtype.OPENAI_CHATGPT,
  },
  [NodeType.HUMAN_IN_THE_LOOP]: {
    GMAIL: HumanLoopSubtype.GMAIL_INTERACTION,
    SLACK: HumanLoopSubtype.SLACK_INTERACTION,
    DISCORD: HumanLoopSubtype.DISCORD_INTERACTION,
    TELEGRAM: HumanLoopSubtype.TELEGRAM_INTERACTION,
    APP: HumanLoopSubtype.IN_APP_APPROVAL,
  },
  [NodeType.MEMORY]: {
    VECTOR_DB: MemorySubtype.VECTOR_DATABASE,
    KEY_VALUE: MemorySubtype.KEY_VALUE_STORE,
    DOCUMENT: MemorySubtype.DOCUMENT_STORE,
  },
  [NodeType.TOOL]: {
    CALENDAR: ToolSubtype.GOOGLE_CALENDAR,
    EMAIL: ToolSubtype.EMAIL_TOOL,
    HTTP: ToolSubtype.HTTP_CLIENT,
    MCP: ToolSubtype.CODE_TOOL,
  },
  [NodeType.ACTION]: {},
  [NodeType.FLOW]: {},
  [NodeType.EXTERNAL_ACTION]: {},
};

export const NodeSubtypeCanonicalToAlias: Record<string, Record<string, string>> = {
  [NodeType.TRIGGER]: {
    [TriggerSubtype.CRON]: 'CRON',
    [TriggerSubtype.WEBHOOK]: 'WEBHOOK',
    [TriggerSubtype.EMAIL]: 'EMAIL',
    [TriggerSubtype.MANUAL]: 'MANUAL',
  },
  [NodeType.AI_AGENT]: {
    [AIAgentSubtype.OPENAI_CHATGPT]: 'ROUTER_AGENT',
    [AIAgentSubtype.ANTHROPIC_CLAUDE]: 'ROUTER_AGENT',
    [AIAgentSubtype.GOOGLE_GEMINI]: 'ROUTER_AGENT',
  },
  [NodeType.HUMAN_IN_THE_LOOP]: {
    [HumanLoopSubtype.GMAIL_INTERACTION]: 'GMAIL',
    [HumanLoopSubtype.SLACK_INTERACTION]: 'SLACK',
    [HumanLoopSubtype.DISCORD_INTERACTION]: 'DISCORD',
    [HumanLoopSubtype.TELEGRAM_INTERACTION]: 'TELEGRAM',
    [HumanLoopSubtype.IN_APP_APPROVAL]: 'APP',
  },
  [NodeType.MEMORY]: {
    [MemorySubtype.VECTOR_DATABASE]: 'VECTOR_DB',
    [MemorySubtype.KEY_VALUE_STORE]: 'KEY_VALUE',
    [MemorySubtype.DOCUMENT_STORE]: 'DOCUMENT',
  },
  [NodeType.TOOL]: {
    [ToolSubtype.GOOGLE_CALENDAR]: 'CALENDAR',
    [ToolSubtype.EMAIL_TOOL]: 'EMAIL',
    [ToolSubtype.HTTP_CLIENT]: 'HTTP',
    [ToolSubtype.CODE_TOOL]: 'MCP',
  },
  [NodeType.ACTION]: {},
  [NodeType.FLOW]: {},
  [NodeType.EXTERNAL_ACTION]: {},
};

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
