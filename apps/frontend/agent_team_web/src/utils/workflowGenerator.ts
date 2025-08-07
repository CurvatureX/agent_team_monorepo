import { Workflow, WorkflowNode, WorkflowEdge } from '@/types/workflow';
import { WorkflowType, WorkflowStatus, ErrorPolicy, CallerPolicy, NodeType } from '@/types/workflow-enums';

interface WorkflowStep {
  type: string;
  subtype: string;
  name: string;
  description?: string;
}

// Mapping keywords to node types (using new API format)
const keywordToNodeType: Record<string, WorkflowStep> = {
  // Trigger related
  'start': { type: 'trigger', subtype: 'calendar', name: 'Start' },
  'trigger': { type: 'trigger', subtype: 'webhook', name: 'Trigger' },
  'schedule': { type: 'trigger', subtype: 'schedule', name: 'Schedule' },
  'calendar': { type: 'trigger', subtype: 'calendar', name: 'Calendar Event' },
  'webhook': { type: 'trigger', subtype: 'webhook', name: 'Webhook Trigger' },
  
  // AI related
  'ai': { type: 'ai_agent', subtype: 'agent', name: 'AI Processing' },
  'intelligence': { type: 'ai_agent', subtype: 'agent', name: 'Intelligent Processing' },
  'analysis': { type: 'ai_agent', subtype: 'agent', name: 'AI Analysis' },
  'generate': { type: 'ai_agent', subtype: 'agent', name: 'AI Generation' },
  'analyze': { type: 'ai_agent', subtype: 'agent', name: 'AI Analysis' },
  
  // Action related
  'process': { type: 'action', subtype: 'data_transform', name: 'Data Processing' },
  'transform': { type: 'action', subtype: 'data_transform', name: 'Data Transformation' },
  'request': { type: 'action', subtype: 'http_request', name: 'HTTP Request' },
  'send': { type: 'action', subtype: 'http_request', name: 'Send Request' },
  'fetch': { type: 'action', subtype: 'http_request', name: 'Fetch Data' },
  'data': { type: 'action', subtype: 'data_transform', name: 'Data Processing' },
  
  // External services
  'github': { type: 'external_action', subtype: 'github', name: 'GitHub Action' },
  'slack': { type: 'external_action', subtype: 'slack', name: 'Slack Notification' },
  'notification': { type: 'external_action', subtype: 'slack', name: 'Send Notification' },
  'notify': { type: 'external_action', subtype: 'slack', name: 'Send Notification' },
  
  // Flow control
  'condition': { type: 'flow', subtype: 'filter', name: 'Condition Check' },
  'filter': { type: 'flow', subtype: 'filter', name: 'Data Filter' },
  'branch': { type: 'flow', subtype: 'switch', name: 'Branch Selection' },
  'check': { type: 'flow', subtype: 'filter', name: 'Check Condition' },
  'switch': { type: 'flow', subtype: 'switch', name: 'Switch Flow' },
  
  // Human intervention
  'review': { type: 'human_in_the_loop', subtype: 'discord', name: 'Human Review' },
  'confirm': { type: 'human_in_the_loop', subtype: 'gmail', name: 'Human Confirmation' },
  'human': { type: 'human_in_the_loop', subtype: 'discord', name: 'Human Processing' },
  'approval': { type: 'human_in_the_loop', subtype: 'gmail', name: 'Human Approval' },
  
  // Tools and memory
  'store': { type: 'memory', subtype: 'store', name: 'Store Data' },
  'save': { type: 'memory', subtype: 'store', name: 'Save Results' },
  'tool': { type: 'tool', subtype: 'function', name: 'Tool Invocation' },
  'function': { type: 'tool', subtype: 'function', name: 'Function Call' },
  'memory': { type: 'memory', subtype: 'store', name: 'Memory Storage' },
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
  if (steps.length === 0 || steps[0].type !== 'trigger') {
    steps.unshift({ type: 'trigger', subtype: 'webhook', name: 'Start Trigger' });
  }
  
  // If only trigger exists, add some default nodes
  if (steps.length === 1) {
    steps.push({ type: 'ai_agent', subtype: 'agent', name: 'AI Processing' });
    steps.push({ type: 'action', subtype: 'data_transform', name: 'Process Results' });
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
    const nodeId = `${step.type}_${index}`;
    
    nodes.push({
      id: nodeId,
      name: step.name,
      type: step.type,
      subtype: step.subtype,
      type_version: 1,
      position: {
        x: 200 + (index * 300),
        y: 200 + (index % 2 === 0 ? -50 : 50), // Staggered layout
      },
      disabled: false,
      parameters: {},
      credentials: {},
      on_error: ErrorPolicy.Stop,
      retry_policy: {
        max_tries: 1,
        wait_between_tries: 0,
      },
      notes: {},
      webhooks: [],
    });
    
    // Create edges (linear connections)
    if (index > 0) {
      const prevNodeId = `${steps[index - 1].type}_${index - 1}`;
      edges.push({
        id: `e-${prevNodeId}-${nodeId}`,
        source: prevNodeId,
        target: nodeId,
        type: 'default',
      });
    }
  });
  
  return {
    id: workflowId,
    user_id: 'auto_generated',
    name: 'Auto-generated Workflow',
    description: `Generated from: ${description}`,
    type: WorkflowType.Sequential,
    status: WorkflowStatus.Draft,
    version: 1,
    nodes,
    edges,
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
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}