import { Workflow, WorkflowNode, WorkflowEdge } from '@/types/workflow';
import {
  WorkflowType,
  WorkflowStatus,
  ErrorPolicy,
  CallerPolicy,
  NodeType,
  TriggerSubtype,
  AIAgentSubtype,
  ActionSubtype,
  HumanLoopSubtype,
  FlowSubtype,
  ToolSubtype,
  ExternalActionSubtype,
  MemorySubtype,
} from '@/types/workflow-enums';

interface WorkflowStep {
  type: NodeType | string;
  subtype: string;
  name: string;
  description?: string;
}

// Mapping keywords to node types (using new API format)
const keywordToNodeType: Record<string, WorkflowStep> = {
  // Trigger related
  'start': { type: NodeType.TRIGGER, subtype: TriggerSubtype.MANUAL, name: 'Start' },
  'trigger': { type: NodeType.TRIGGER, subtype: TriggerSubtype.WEBHOOK, name: 'Trigger' },
  'schedule': { type: NodeType.TRIGGER, subtype: TriggerSubtype.CRON, name: 'Schedule' },
  'calendar': { type: NodeType.TRIGGER, subtype: TriggerSubtype.CRON, name: 'Calendar Event' },
  'webhook': { type: NodeType.TRIGGER, subtype: TriggerSubtype.WEBHOOK, name: 'Webhook Trigger' },

  // AI related (provider-specific names)
  // Defaults to OpenAI ChatGPT when generic terms are used
  'ai': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' },
  'intelligence': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' },
  'analysis': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' },
  'generate': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' },
  'analyze': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' },
  // Explicit providers
  'openai': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' },
  'gpt': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' },
  'chatgpt': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' },
  'claude': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.ANTHROPIC_CLAUDE, name: 'Claude Agent' },
  'anthropic': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.ANTHROPIC_CLAUDE, name: 'Claude Agent' },
  'gemini': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.GOOGLE_GEMINI, name: 'Gemini Agent' },
  'google': { type: NodeType.AI_AGENT, subtype: AIAgentSubtype.GOOGLE_GEMINI, name: 'Gemini Agent' },

  // Action related
  'process': { type: NodeType.ACTION, subtype: ActionSubtype.DATA_TRANSFORMATION, name: 'Data Processing' },
  'transform': { type: NodeType.ACTION, subtype: ActionSubtype.DATA_TRANSFORMATION, name: 'Data Transformation' },
  'request': { type: NodeType.ACTION, subtype: ActionSubtype.HTTP_REQUEST, name: 'HTTP Request' },
  'send': { type: NodeType.ACTION, subtype: ActionSubtype.HTTP_REQUEST, name: 'Send Request' },
  'fetch': { type: NodeType.ACTION, subtype: ActionSubtype.HTTP_REQUEST, name: 'Fetch Data' },
  'data': { type: NodeType.ACTION, subtype: ActionSubtype.DATA_TRANSFORMATION, name: 'Data Processing' },

  // External services
  'github': { type: NodeType.EXTERNAL_ACTION, subtype: ExternalActionSubtype.GITHUB, name: 'GitHub Action' },
  'slack': { type: NodeType.EXTERNAL_ACTION, subtype: ExternalActionSubtype.SLACK, name: 'Slack Notification' },

  // Flow control
  'condition': { type: NodeType.FLOW, subtype: FlowSubtype.IF, name: 'Condition Check' },
  'filter': { type: NodeType.FLOW, subtype: FlowSubtype.FILTER, name: 'Data Filter' },
  'branch': { type: NodeType.FLOW, subtype: FlowSubtype.IF, name: 'Branch Selection' },
  'check': { type: NodeType.FLOW, subtype: FlowSubtype.IF, name: 'Check Condition' },
  'switch': { type: NodeType.FLOW, subtype: FlowSubtype.MERGE, name: 'Switch Flow' },

  // Human intervention
  'review': { type: NodeType.HUMAN_IN_THE_LOOP, subtype: HumanLoopSubtype.DISCORD_INTERACTION, name: 'Human Review' },
  'confirm': { type: NodeType.HUMAN_IN_THE_LOOP, subtype: HumanLoopSubtype.GMAIL_INTERACTION, name: 'Human Confirmation' },
  'human': { type: NodeType.HUMAN_IN_THE_LOOP, subtype: HumanLoopSubtype.DISCORD_INTERACTION, name: 'Human Processing' },
  'approval': { type: NodeType.HUMAN_IN_THE_LOOP, subtype: HumanLoopSubtype.GMAIL_INTERACTION, name: 'Human Approval' },

  // Tools and memory
  'store': { type: NodeType.MEMORY, subtype: MemorySubtype.KEY_VALUE_STORE, name: 'Store Data' },
  'save': { type: NodeType.MEMORY, subtype: MemorySubtype.KEY_VALUE_STORE, name: 'Save Results' },
  'tool': { type: NodeType.TOOL, subtype: ToolSubtype.CODE_TOOL, name: 'Tool Invocation' },
  'function': { type: NodeType.TOOL, subtype: ToolSubtype.CODE_TOOL, name: 'Function Call' },
  'memory': { type: NodeType.MEMORY, subtype: MemorySubtype.KEY_VALUE_STORE, name: 'Memory Storage' },
};

export function parseWorkflowDescription(description: string): WorkflowStep[] {
  const steps: WorkflowStep[] = [];
  const lowerDescription = description.toLowerCase();

  // Split description by common separators
  const phrases = lowerDescription.split(/[,;.]/);

  // Process each phrase to find relevant nodes
  phrases.forEach(phrase => {
    for (const [keyword, nodeInfo] of Object.entries(keywordToNodeType)) {
      if (phrase.includes(keyword)) {
        // Avoid duplicates of the same type+subtype combination
        const exists = steps.some(s =>
          s.type === nodeInfo.type && s.subtype === nodeInfo.subtype
        );
        if (!exists) {
          steps.push({ ...nodeInfo });
        }
      }
    }
  });

  // Ensure we have a trigger node at the start
  if (steps.length === 0 || steps[0].type !== NodeType.TRIGGER) {
    steps.unshift({ type: NodeType.TRIGGER, subtype: TriggerSubtype.WEBHOOK, name: 'Start Trigger' });
  }

  // If only trigger exists, add some default nodes
  if (steps.length === 1) {
    steps.push({ type: NodeType.AI_AGENT, subtype: AIAgentSubtype.OPENAI_CHATGPT, name: 'ChatGPT Agent' });
    steps.push({ type: NodeType.ACTION, subtype: ActionSubtype.DATA_TRANSFORMATION, name: 'Process Results' });
  }

  return steps;
}

export function generateWorkflowFromDescription(
  description: string,
  workflowId: string = `workflow_${Date.now()}`
): Workflow {
  const steps = parseWorkflowDescription(description);
  const nodes: WorkflowNode[] = [];
  const edges: WorkflowEdge[] = [];

  // Generate nodes
  steps.forEach((step, index) => {
    const nodeId = `${typeof step.type === 'string' ? step.type.toString().toLowerCase() : 'node'}_${index}`;

    nodes.push({
      id: nodeId,
      name: step.name,
      description: step.description || '',
      type: (step.type as NodeType),
      subtype: step.subtype,
      position: {
        x: 200 + (index * 300),
        y: 200 + (index % 2 === 0 ? -50 : 50), // Staggered layout
      },
      configurations: {},
      input_params: {},
      output_params: {},
    });

    // Create edges (linear connections)
    if (index > 0) {
      const prevNodeId = `${steps[index - 1].type}_${index - 1}`;
      edges.push({
        id: `e-${prevNodeId}-${nodeId}`,
        from_node: prevNodeId,
        to_node: nodeId,
        output_key: 'result',
      });
    }
  });

  return {
    id: workflowId,
    user_id: 'auto_generated',
    name: 'Auto-generated Workflow',
    description: `Generated from: ${description}`,
    type: WorkflowType.Sequential,
    status: WorkflowStatus.Idle,
    version: 1,
    nodes,
    connections: edges,  // WorkflowEntity uses 'connections' not 'edges'
    variables: {},
    settings: {
      timezone: { default: 'UTC' },
      save_execution_progress: true,
      save_manual_executions: true,
      timeout: 300,
      error_policy: ErrorPolicy.Stop,
      caller_policy: CallerPolicy.Workflow,
    },
    tags: ['auto-generated'],
    execution_count: 0,
    created_at: Date.now(),
    updated_at: Date.now(),
  };
}
