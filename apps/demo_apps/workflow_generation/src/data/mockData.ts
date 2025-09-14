import { AIWorker, ExecutionRecord, LogEntry, NodeExecution } from '../types';

export const mockAIWorkers: AIWorker[] = [
  {
    id: 'worker-1',
    name: 'Customer Support Agent',
    description: 'Automated customer support workflow that processes tickets, generates responses, and escalates complex issues',
    status: 'active',
    lastRunTime: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    nextRunTime: new Date(Date.now() + 30 * 60 * 1000), // 30 minutes from now
    trigger: {
      type: 'event',
      config: { eventType: 'ticket_created', source: 'zendesk' },
      description: 'Triggered when new support ticket is created'
    },
    graph: [
      {
        id: 'trigger-1',
        type: 'trigger',
        position: { x: 100, y: 100 },
        data: { name: 'Ticket Created', subtype: 'webhook', description: 'New support ticket webhook trigger' }
      },
      {
        id: 'ai-1',
        type: 'ai_agent',
        position: { x: 300, y: 100 },
        data: { name: 'Analyze Ticket', subtype: 'classifier', description: 'Classify ticket priority and category' }
      },
      {
        id: 'action-1',
        type: 'action',
        position: { x: 500, y: 100 },
        data: { name: 'Generate Response', subtype: 'email', description: 'Generate automated response' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-1',
        startTime: new Date(Date.now() - 2 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 2 * 60 * 60 * 1000 + 45000),
        status: 'completed',
        duration: 45,
        triggerType: 'event'
      },
      {
        id: 'exec-2',
        startTime: new Date(Date.now() - 4 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 4 * 60 * 60 * 1000 + 52000),
        status: 'completed',
        duration: 52,
        triggerType: 'event'
      }
    ]
  },
  {
    id: 'worker-2',
    name: 'Social Media Monitor',
    description: 'Monitors social media mentions, analyzes sentiment, and generates automated responses for brand management',
    status: 'idle',
    lastRunTime: new Date(Date.now() - 6 * 60 * 60 * 1000), // 6 hours ago
    nextRunTime: new Date(Date.now() + 60 * 60 * 1000), // 1 hour from now
    trigger: {
      type: 'schedule',
      config: { cron: '0 */15 * * * *' },
      description: 'Runs every 15 minutes'
    },
    graph: [
      {
        id: 'trigger-2',
        type: 'trigger',
        position: { x: 100, y: 100 },
        data: { name: 'Schedule Trigger', subtype: 'cron', description: 'Periodic social media scan' }
      },
      {
        id: 'tool-1',
        type: 'tool',
        position: { x: 300, y: 100 },
        data: { name: 'Twitter API', subtype: 'api_call', description: 'Fetch recent mentions' }
      },
      {
        id: 'ai-2',
        type: 'ai_agent',
        position: { x: 500, y: 100 },
        data: { name: 'Sentiment Analysis', subtype: 'classifier', description: 'Analyze mention sentiment' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-3',
        startTime: new Date(Date.now() - 6 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 6 * 60 * 60 * 1000 + 23000),
        status: 'completed',
        duration: 23,
        triggerType: 'schedule'
      }
    ]
  },
  {
    id: 'worker-3',
    name: 'Lead Qualification Bot',
    description: 'Automatically qualifies inbound leads, scores them, and routes to appropriate sales representatives',
    status: 'running',
    lastRunTime: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
    trigger: {
      type: 'webhook',
      config: { endpoint: '/webhook/lead-capture' },
      description: 'Triggered when new lead form is submitted'
    },
    graph: [
      {
        id: 'trigger-3',
        type: 'trigger',
        position: { x: 100, y: 100 },
        data: { name: 'Lead Form Submitted', subtype: 'webhook', description: 'New lead form webhook' }
      },
      {
        id: 'ai-3',
        type: 'ai_agent',
        position: { x: 300, y: 100 },
        data: { name: 'Lead Scorer', subtype: 'classifier', description: 'Score lead quality' }
      },
      {
        id: 'flow-1',
        type: 'flow',
        position: { x: 500, y: 100 },
        data: { name: 'Route Decision', subtype: 'conditional', description: 'Route based on score' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-4',
        startTime: new Date(Date.now() - 5 * 60 * 1000),
        status: 'running',
        triggerType: 'webhook'
      }
    ]
  },
  {
    id: 'worker-4',
    name: 'Content Generator',
    description: 'Generates blog posts, social media content, and newsletters based on trending topics and company updates',
    status: 'error',
    lastRunTime: new Date(Date.now() - 12 * 60 * 60 * 1000), // 12 hours ago
    trigger: {
      type: 'schedule',
      config: { cron: '0 9 * * 1,3,5' },
      description: 'Runs Mon/Wed/Fri at 9 AM'
    },
    graph: [
      {
        id: 'trigger-4',
        type: 'trigger',
        position: { x: 100, y: 100 },
        data: { name: 'Weekly Schedule', subtype: 'cron', description: 'Content generation schedule' }
      },
      {
        id: 'tool-2',
        type: 'tool',
        position: { x: 300, y: 50 },
        data: { name: 'Trend Analysis', subtype: 'api_call', description: 'Analyze trending topics' }
      },
      {
        id: 'ai-4',
        type: 'ai_agent',
        position: { x: 500, y: 100 },
        data: { name: 'Content Writer', subtype: 'generator', description: 'Generate content drafts' }
      },
      {
        id: 'human-1',
        type: 'human_in_the_loop',
        position: { x: 700, y: 100 },
        data: { name: 'Content Review', description: 'Human review before publishing' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-5',
        startTime: new Date(Date.now() - 12 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 12 * 60 * 60 * 1000 + 15000),
        status: 'failed',
        duration: 15,
        triggerType: 'schedule',
        error: 'API rate limit exceeded for content generation service'
      }
    ]
  },
  {
    id: 'worker-5',
    name: 'Invoice Processor',
    description: 'Processes incoming invoices, extracts data using OCR, validates against purchase orders, and routes for approval',
    status: 'paused',
    lastRunTime: new Date(Date.now() - 24 * 60 * 60 * 1000), // 24 hours ago
    trigger: {
      type: 'event',
      config: { eventType: 'file_uploaded', folder: '/invoices' },
      description: 'Triggered when invoice document is uploaded'
    },
    graph: [
      {
        id: 'trigger-5',
        type: 'trigger',
        position: { x: 100, y: 100 },
        data: { name: 'File Upload', subtype: 'file_watcher', description: 'Watch for invoice uploads' }
      },
      {
        id: 'tool-3',
        type: 'tool',
        position: { x: 300, y: 100 },
        data: { name: 'OCR Extract', subtype: 'document_processing', description: 'Extract text from invoice' }
      },
      {
        id: 'ai-5',
        type: 'ai_agent',
        position: { x: 500, y: 100 },
        data: { name: 'Data Validator', subtype: 'validator', description: 'Validate extracted data' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-6',
        startTime: new Date(Date.now() - 24 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 24 * 60 * 60 * 1000 + 67000),
        status: 'completed',
        duration: 67,
        triggerType: 'event'
      }
    ]
  },
  {
    id: 'worker-6',
    name: 'DevOps Alert Manager',
    description: 'Monitors system alerts, categorizes incidents, creates tickets, and notifies relevant teams based on severity',
    status: 'active',
    lastRunTime: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
    nextRunTime: new Date(Date.now() + 5 * 60 * 1000), // 5 minutes from now
    trigger: {
      type: 'webhook',
      config: { endpoint: '/webhook/monitoring-alert' },
      description: 'Triggered by monitoring system alerts'
    },
    graph: [
      {
        id: 'trigger-6',
        type: 'trigger',
        position: { x: 100, y: 100 },
        data: { name: 'Alert Webhook', subtype: 'webhook', description: 'System alert webhook' }
      },
      {
        id: 'ai-6',
        type: 'ai_agent',
        position: { x: 300, y: 100 },
        data: { name: 'Alert Classifier', subtype: 'classifier', description: 'Classify alert severity' }
      },
      {
        id: 'action-2',
        type: 'external_action',
        position: { x: 500, y: 100 },
        data: { name: 'Create Ticket', subtype: 'jira', description: 'Create Jira ticket for incident' }
      }
    ],
    executionHistory: [
      {
        id: 'exec-7',
        startTime: new Date(Date.now() - 15 * 60 * 1000),
        endTime: new Date(Date.now() - 15 * 60 * 1000 + 12000),
        status: 'completed',
        duration: 12,
        triggerType: 'webhook'
      }
    ]
  }
];

// Mock execution details with logs
export const mockExecutionDetails: Record<string, ExecutionRecord> = {
  'exec-1': {
    id: 'exec-1',
    startTime: new Date(Date.now() - 2 * 60 * 60 * 1000),
    endTime: new Date(Date.now() - 2 * 60 * 60 * 1000 + 45000),
    status: 'completed',
    duration: 45,
    triggerType: 'event',
    nodeExecutions: [
      {
        nodeId: 'trigger-1',
        nodeName: 'Ticket Created',
        startTime: new Date(Date.now() - 2 * 60 * 60 * 1000),
        endTime: new Date(Date.now() - 2 * 60 * 60 * 1000 + 2000),
        status: 'completed',
        input: { ticketId: 'TKT-12345', priority: 'high', category: 'technical' },
        output: { processed: true, ticketData: { id: 'TKT-12345', customer: 'Acme Corp' } },
        logs: [
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
            level: 'info',
            message: 'Webhook trigger received',
            nodeId: 'trigger-1'
          },
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 1000),
            level: 'info',
            message: 'Ticket data validated and processed',
            nodeId: 'trigger-1'
          }
        ]
      },
      {
        nodeId: 'ai-1',
        nodeName: 'Analyze Ticket',
        startTime: new Date(Date.now() - 2 * 60 * 60 * 1000 + 2000),
        endTime: new Date(Date.now() - 2 * 60 * 60 * 1000 + 25000),
        status: 'completed',
        input: { ticketData: { id: 'TKT-12345', customer: 'Acme Corp' } },
        output: { priority: 'high', category: 'technical', sentiment: 'frustrated', confidence: 0.87 },
        logs: [
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 2000),
            level: 'info',
            message: 'Starting ticket analysis with AI classifier',
            nodeId: 'ai-1'
          },
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 15000),
            level: 'debug',
            message: 'AI model processing completed',
            nodeId: 'ai-1',
            data: { processingTime: '13s', tokens: 1250 }
          },
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 25000),
            level: 'info',
            message: 'Classification completed with high confidence',
            nodeId: 'ai-1'
          }
        ]
      },
      {
        nodeId: 'action-1',
        nodeName: 'Generate Response',
        startTime: new Date(Date.now() - 2 * 60 * 60 * 1000 + 25000),
        endTime: new Date(Date.now() - 2 * 60 * 60 * 1000 + 45000),
        status: 'completed',
        input: { priority: 'high', category: 'technical', sentiment: 'frustrated' },
        output: { emailSent: true, responseId: 'RESP-78901', escalated: true },
        logs: [
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 25000),
            level: 'info',
            message: 'Generating automated response based on classification',
            nodeId: 'action-1'
          },
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 35000),
            level: 'info',
            message: 'Response generated, escalating due to high priority',
            nodeId: 'action-1'
          },
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 45000),
            level: 'info',
            message: 'Email sent and ticket escalated to senior support',
            nodeId: 'action-1'
          }
        ]
      }
    ]
  }
};

// Mock real-time execution (currently running)
export const mockCurrentExecution: ExecutionRecord = {
  id: 'exec-current',
  startTime: new Date(Date.now() - 2 * 60 * 1000), // 2 minutes ago
  status: 'running',
  triggerType: 'webhook',
  nodeExecutions: [
    {
      nodeId: 'trigger-3',
      nodeName: 'Lead Form Submitted',
      startTime: new Date(Date.now() - 2 * 60 * 1000),
      endTime: new Date(Date.now() - 2 * 60 * 1000 + 5000),
      status: 'completed',
      input: { formData: { name: 'John Doe', email: 'john@example.com', company: 'TechCorp' } },
      output: { leadId: 'LEAD-54321', processed: true },
      logs: [
        {
          timestamp: new Date(Date.now() - 2 * 60 * 1000),
          level: 'info',
          message: 'New lead form submission received',
          nodeId: 'trigger-3'
        }
      ]
    },
    {
      nodeId: 'ai-3',
      nodeName: 'Lead Scorer',
      startTime: new Date(Date.now() - 2 * 60 * 1000 + 5000),
      status: 'running',
      input: { leadId: 'LEAD-54321', leadData: { name: 'John Doe', company: 'TechCorp' } },
      logs: [
        {
          timestamp: new Date(Date.now() - 2 * 60 * 1000 + 5000),
          level: 'info',
          message: 'Starting lead qualification scoring',
          nodeId: 'ai-3'
        },
        {
          timestamp: new Date(Date.now() - 1 * 60 * 1000),
          level: 'debug',
          message: 'Analyzing company data and lead attributes',
          nodeId: 'ai-3'
        }
      ]
    }
  ]
};
