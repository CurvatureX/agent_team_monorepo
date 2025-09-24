import { AIWorker, ExecutionRecord } from '../types/workflow';

export const mockAIWorkers: AIWorker[] = [
  {
    id: 'worker-1',
    name: 'Customer Support Agent',
    description: 'Automated customer support workflow that processes tickets, generates responses, and escalates complex issues to human agents.',
    deploymentStatus: 'DEPLOYED',
    latestExecutionStatus: 'SUCCESS',
    lastRunTime: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    nextRunTime: new Date(Date.now() + 30 * 60 * 1000), // 30 minutes from now
    trigger: {
      type: 'WEBHOOK',
      config: { eventType: 'ticket_created', source: 'zendesk' },
      description: 'Triggered when new support ticket is created'
    },
    graph: [
      {
        id: 'trigger-1',
        type: 'TRIGGER',
        position: { x: 100, y: 100 },
        data: { name: 'Ticket Created', subtype: 'WEBHOOK', description: 'New support ticket webhook trigger' }
      },
      {
        id: 'ai-1',
        type: 'AI_AGENT',
        position: { x: 300, y: 100 },
        data: { name: 'Analyze Ticket', subtype: 'ANTHROPIC_CLAUDE', description: 'Classify ticket priority and category' }
      },
      {
        id: 'action-1',
        type: 'EXTERNAL_ACTION',
        position: { x: 500, y: 100 },
        data: { name: 'Generate Response', subtype: 'EMAIL', description: 'Generate automated response' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-1',
        startTime: new Date(Date.now() - 2 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 2 * 60 * 60 * 1000 + 45000),
        status: 'SUCCESS',
        duration: 45,
        triggerType: 'WEBHOOK'
      }
    ]
  },
  {
    id: 'worker-2',
    name: 'Social Media Monitor',
    description: 'Monitors social media mentions, analyzes sentiment, and generates automated responses for brand management.',
    deploymentStatus: 'DEPLOYED',
    latestExecutionStatus: 'RUNNING',
    lastRunTime: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
    trigger: {
      type: 'CRON',
      config: { cron: '0 */15 * * * *' },
      description: 'Runs every 15 minutes'
    },
    graph: [
      {
        id: 'trigger-2',
        type: 'TRIGGER',
        position: { x: 100, y: 100 },
        data: { name: 'Schedule Trigger', subtype: 'CRON', description: 'Periodic social media scan' }
      },
      {
        id: 'tool-1',
        type: 'TOOL',
        position: { x: 300, y: 100 },
        data: { name: 'Twitter API', subtype: 'HTTP_CLIENT', description: 'Fetch recent mentions' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-2',
        startTime: new Date(Date.now() - 5 * 60 * 1000),
        status: 'RUNNING',
        triggerType: 'CRON'
      }
    ]
  },
  {
    id: 'worker-3',
    name: 'Lead Qualification Bot',
    description: 'Automatically qualifies inbound leads, scores them, and routes to appropriate sales representatives.',
    deploymentStatus: 'DEPLOYED',
    latestExecutionStatus: 'SUCCESS',
    lastRunTime: new Date(Date.now() - 6 * 60 * 60 * 1000), // 6 hours ago
    nextRunTime: new Date(Date.now() + 60 * 60 * 1000), // 1 hour from now
    trigger: {
      type: 'WEBHOOK',
      config: { endpoint: '/webhook/lead-capture' },
      description: 'Triggered when new lead form is submitted'
    },
    graph: [
      {
        id: 'trigger-3',
        type: 'TRIGGER',
        position: { x: 100, y: 100 },
        data: { name: 'Lead Form Submitted', subtype: 'WEBHOOK', description: 'New lead form webhook' }
      },
      {
        id: 'ai-3',
        type: 'AI_AGENT',
        position: { x: 300, y: 100 },
        data: { name: 'Lead Scorer', subtype: 'OPENAI_CHATGPT', description: 'Score lead quality' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-3',
        startTime: new Date(Date.now() - 6 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 6 * 60 * 60 * 1000 + 32000),
        status: 'SUCCESS',
        duration: 32,
        triggerType: 'WEBHOOK'
      }
    ]
  },
  {
    id: 'worker-4',
    name: 'Content Generator',
    description: 'Generates blog posts, social media content, and newsletters based on trending topics and company updates.',
    deploymentStatus: 'DEPLOYED',
    latestExecutionStatus: 'ERROR',
    lastRunTime: new Date(Date.now() - 12 * 60 * 60 * 1000), // 12 hours ago
    trigger: {
      type: 'CRON',
      config: { cron: '0 9 * * 1,3,5' },
      description: 'Runs Mon/Wed/Fri at 9 AM'
    },
    graph: [
      {
        id: 'trigger-4',
        type: 'TRIGGER',
        position: { x: 100, y: 100 },
        data: { name: 'Weekly Schedule', subtype: 'CRON', description: 'Content generation schedule' }
      },
      {
        id: 'ai-4',
        type: 'AI_AGENT',
        position: { x: 300, y: 100 },
        data: { name: 'Content Writer', subtype: 'GOOGLE_GEMINI', description: 'Generate content drafts' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-4',
        startTime: new Date(Date.now() - 12 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 12 * 60 * 60 * 1000 + 15000),
        status: 'ERROR',
        duration: 15,
        triggerType: 'CRON',
        error: 'API rate limit exceeded for content generation service'
      }
    ]
  },
  {
    id: 'worker-5',
    name: 'Invoice Processor',
    description: 'Processes incoming invoices, extracts data using OCR, validates against purchase orders, and routes for approval.',
    deploymentStatus: 'UNDEPLOYED',
    latestExecutionStatus: 'SUCCESS',
    lastRunTime: new Date(Date.now() - 24 * 60 * 60 * 1000), // 24 hours ago
    trigger: {
      type: 'WEBHOOK',
      config: { eventType: 'file_uploaded', folder: '/invoices' },
      description: 'Triggered when invoice document is uploaded'
    },
    graph: [
      {
        id: 'trigger-5',
        type: 'TRIGGER',
        position: { x: 100, y: 100 },
        data: { name: 'File Upload', subtype: 'WEBHOOK', description: 'Watch for invoice uploads' }
      },
      {
        id: 'tool-3',
        type: 'TOOL',
        position: { x: 300, y: 100 },
        data: { name: 'OCR Extract', subtype: 'FILE_PROCESSOR', description: 'Extract text from invoice' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-5',
        startTime: new Date(Date.now() - 24 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 24 * 60 * 60 * 1000 + 67000),
        status: 'SUCCESS',
        duration: 67,
        triggerType: 'WEBHOOK'
      }
    ]
  },
  {
    id: 'worker-6',
    name: 'DevOps Alert Manager',
    description: 'Monitors system alerts, categorizes incidents, creates tickets, and notifies relevant teams based on severity.',
    deploymentStatus: 'DEPLOYED',
    latestExecutionStatus: 'SUCCESS',
    lastRunTime: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
    nextRunTime: new Date(Date.now() + 5 * 60 * 1000), // 5 minutes from now
    trigger: {
      type: 'WEBHOOK',
      config: { endpoint: '/webhook/monitoring-alert' },
      description: 'Triggered by monitoring system alerts'
    },
    graph: [
      {
        id: 'trigger-6',
        type: 'TRIGGER',
        position: { x: 100, y: 100 },
        data: { name: 'Alert Webhook', subtype: 'WEBHOOK', description: 'System alert webhook' }
      },
      {
        id: 'ai-6',
        type: 'AI_AGENT',
        position: { x: 300, y: 100 },
        data: { name: 'Alert Classifier', subtype: 'ANTHROPIC_CLAUDE', description: 'Classify alert severity' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-6',
        startTime: new Date(Date.now() - 15 * 60 * 1000),
        endTime: new Date(Date.now() - 15 * 60 * 1000 + 12000),
        status: 'SUCCESS',
        duration: 12,
        triggerType: 'WEBHOOK'
      }
    ]
  }
];

// Mock real-time execution (currently running)
export const mockCurrentExecution: ExecutionRecord = {
  id: 'exec-current',
  startTime: new Date(Date.now() - 3 * 60 * 1000), // 3 minutes ago
  status: 'RUNNING',
  triggerType: 'CRON',
  nodeExecutions: [
    {
      nodeId: 'trigger-2',
      nodeName: 'Schedule Trigger',
      startTime: new Date(Date.now() - 3 * 60 * 1000),
      endTime: new Date(Date.now() - 3 * 60 * 1000 + 2000),
      status: 'SUCCESS',
      logs: [
        {
          timestamp: new Date(Date.now() - 3 * 60 * 1000),
          level: 'info',
          message: 'Scheduled trigger activated - scanning social media mentions',
          nodeId: 'trigger-2'
        }
      ]
    },
    {
      nodeId: 'tool-1',
      nodeName: 'Twitter API',
      startTime: new Date(Date.now() - 3 * 60 * 1000 + 2000),
      status: 'RUNNING',
      logs: [
        {
          timestamp: new Date(Date.now() - 3 * 60 * 1000 + 2000),
          level: 'info',
          message: 'Fetching recent Twitter mentions...',
          nodeId: 'tool-1'
        },
        {
          timestamp: new Date(Date.now() - 2 * 60 * 1000),
          level: 'debug',
          message: 'API request sent to Twitter endpoint',
          nodeId: 'tool-1'
        },
        {
          timestamp: new Date(Date.now() - 1 * 60 * 1000),
          level: 'info',
          message: 'Processing 47 new mentions found',
          nodeId: 'tool-1'
        }
      ]
    }
  ]
};
