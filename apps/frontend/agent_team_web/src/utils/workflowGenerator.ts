import { WorkflowData, NodeType, NodeSubtype } from '@/types/workflow';

interface WorkflowStep {
  type: NodeType;
  subtype: NodeSubtype;
  name: string;
  description?: string;
}

// Mapping keywords to node types
const keywordToNodeType: Record<string, WorkflowStep> = {
  // Trigger related
  'start': { type: 'TRIGGER_NODE', subtype: 'TRIGGER_CALENDAR', name: 'Start' },
  'trigger': { type: 'TRIGGER_NODE', subtype: 'TRIGGER_WEBHOOK', name: 'Trigger' },
  'schedule': { type: 'TRIGGER_NODE', subtype: 'TRIGGER_SCHEDULE', name: 'Schedule' },
  'calendar': { type: 'TRIGGER_NODE', subtype: 'TRIGGER_CALENDAR', name: 'Calendar Event' },
  
  // AI related
  'ai': { type: 'AI_AGENT_NODE', subtype: 'AI_AGENT', name: 'AI Processing' },
  'intelligence': { type: 'AI_AGENT_NODE', subtype: 'AI_AGENT', name: 'Intelligent Processing' },
  'analysis': { type: 'AI_AGENT_NODE', subtype: 'AI_AGENT', name: 'AI Analysis' },
  'generate': { type: 'AI_AGENT_NODE', subtype: 'AI_AGENT', name: 'AI Generation' },
  
  // Action related
  'process': { type: 'ACTION_NODE', subtype: 'ACTION_DATA_TRANSFORMATION', name: 'Data Processing' },
  'transform': { type: 'ACTION_NODE', subtype: 'ACTION_DATA_TRANSFORMATION', name: 'Data Transformation' },
  'request': { type: 'ACTION_NODE', subtype: 'ACTION_HTTP_REQUEST', name: 'HTTP Request' },
  'send': { type: 'ACTION_NODE', subtype: 'ACTION_HTTP_REQUEST', name: 'Send Request' },
  
  // External services
  'github': { type: 'EXTERNAL_ACTION_NODE', subtype: 'EXTERNAL_GITHUB', name: 'GitHub Action' },
  'slack': { type: 'EXTERNAL_ACTION_NODE', subtype: 'EXTERNAL_SLACK', name: 'Slack Notification' },
  'notification': { type: 'EXTERNAL_ACTION_NODE', subtype: 'EXTERNAL_SLACK', name: 'Send Notification' },
  
  // Flow control
  'condition': { type: 'FLOW_NODE', subtype: 'FLOW_FILTER', name: 'Condition Check' },
  'filter': { type: 'FLOW_NODE', subtype: 'FLOW_FILTER', name: 'Data Filter' },
  'branch': { type: 'FLOW_NODE', subtype: 'FLOW_SWITCH', name: 'Branch Selection' },
  
  // Human intervention
  'review': { type: 'HUMAN_IN_THE_LOOP_NODE', subtype: 'HUMAN_DISCORD', name: 'Human Review' },
  'confirm': { type: 'HUMAN_IN_THE_LOOP_NODE', subtype: 'HUMAN_GMAIL', name: 'Human Confirmation' },
  'human': { type: 'HUMAN_IN_THE_LOOP_NODE', subtype: 'HUMAN_DISCORD', name: 'Human Processing' },
  
  // Tools and memory
  'store': { type: 'MEMORY_NODE', subtype: 'MEMORY_STORE', name: 'Store Data' },
  'save': { type: 'MEMORY_NODE', subtype: 'MEMORY_STORE', name: 'Save Results' },
  'tool': { type: 'TOOL_NODE', subtype: 'TOOL_FUNCTION', name: 'Tool Invocation' },
};

export function parseWorkflowDescription(description: string): WorkflowStep[] {
  const steps: WorkflowStep[] = [];
  const lowerDescription = description.toLowerCase();
  
  // Always add a trigger node as the starting point
  steps.push({ type: 'TRIGGER_NODE', subtype: 'TRIGGER_CALENDAR', name: 'Start' });
  
  // Match nodes based on keywords
  for (const [keyword, nodeInfo] of Object.entries(keywordToNodeType)) {
    if (lowerDescription.includes(keyword) && !steps.some(s => s.type === nodeInfo.type)) {
      steps.push(nodeInfo);
    }
  }
  
  // If no nodes were found, add some default nodes
  if (steps.length === 1) {
    steps.push({ type: 'AI_AGENT_NODE', subtype: 'AI_AGENT', name: 'AI Processing' });
    steps.push({ type: 'ACTION_NODE', subtype: 'ACTION_DATA_TRANSFORMATION', name: 'Process Results' });
  }
  
  return steps;
}

export function generateWorkflowFromDescription(
  description: string,
  workflowId: string = `workflow_${Date.now()}`
): WorkflowData {
  const steps = parseWorkflowDescription(description);
  const nodes: WorkflowData['nodes'] = [];
  const connections: WorkflowData['connections'] = { connections: {} };
  
  // Generate nodes
  steps.forEach((step, index) => {
    const nodeId = `${step.type.toLowerCase()}_${index}`;
    
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
      on_error: 'STOP_WORKFLOW_ON_ERROR',
      retry_policy: {
        max_tries: 1,
        wait_between_tries: 0,
      },
      notes: {},
      webhooks: [],
    });
    
    // Create connections (linear connections)
    if (index > 0) {
      const prevNodeId = `${steps[index - 1].type.toLowerCase()}_${index - 1}`;
      connections.connections[prevNodeId] = {
        output: {
          connections: [{
            node: nodeId,
            type: 'MAIN',
            index: 0,
          }],
        },
      };
    }
  });
  
  return {
    id: workflowId,
    name: 'Auto-generated Workflow',
    active: true,
    nodes,
    connections,
    settings: {
      timezone: { default: 'UTC' },
      save_execution_progress: true,
      save_manual_executions: true,
      timeout: 300,
      error_policy: 'STOP_WORKFLOW',
      caller_policy: 'WORKFLOW_MAIN',
    },
    static_data: {},
    pin_data: {},
    created_at: Date.now() / 1000,
    updated_at: Date.now() / 1000,
    version: '1.0.0',
    tags: ['auto-generated'],
  };
} 