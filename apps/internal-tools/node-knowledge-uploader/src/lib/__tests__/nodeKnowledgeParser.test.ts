import { parseNodeKnowledge, parseNodeKnowledgePreview } from '../nodeKnowledgeParser';

// Mock OpenAI
jest.mock('openai', () => {
  return jest.fn().mockImplementation(() => ({
    chat: {
      completions: {
        create: jest.fn()
      }
    }
  }));
});

// Mock environment variables
const originalEnv = process.env;
beforeEach(() => {
  process.env = { ...originalEnv };
  process.env.OPENAI_API_KEY = 'mock-api-key';
});

afterEach(() => {
  process.env = originalEnv;
  jest.clearAllMocks();
});

const OpenAI = require('openai');
const mockCreate = jest.fn();

beforeEach(() => {
  OpenAI.mockImplementation(() => ({
    chat: {
      completions: {
        create: mockCreate
      }
    }
  }));
});

describe('NodeKnowledge Parser', () => {
  describe('parseNodeKnowledge', () => {
    it('should parse simple node types with dash format correctly', async () => {
      const mockResponse = [
        {
          nodeType: 'TRIGGER_NODE',
          nodeSubtype: 'TRIGGER_CHAT',
          title: 'TRIGGER_NODE: TRIGGER_CHAT',
          description: 'A node that initiates a workflow based on an event or schedule.',
          content: 'Triggered by chat input from users.'
        }
      ];

      mockCreate.mockResolvedValue({
        choices: [
          {
            message: {
              content: JSON.stringify(mockResponse)
            }
          }
        ]
      });

      const content = `
Node Type: TRIGGER_NODE
Description: A node that initiates a workflow based on an event or schedule.
Subtypes:
- TRIGGER_CHAT: Triggered by chat input from users.
      `;

      const result = await parseNodeKnowledge(content);

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({
        nodeType: 'TRIGGER_NODE',
        nodeSubtype: 'TRIGGER_CHAT',
        title: 'TRIGGER_NODE: TRIGGER_CHAT',
        description: 'A node that initiates a workflow based on an event or schedule.',
        content: 'Triggered by chat input from users.'
      });
    });

    it('should parse nodes with capabilities correctly', async () => {
      const mockResponse = [
        {
          nodeType: 'EXTERNAL_ACTION_NODE',
          nodeSubtype: 'EXTERNAL_GITHUB',
          title: 'EXTERNAL_ACTION_NODE: EXTERNAL_GITHUB',
          description: 'A node that interacts with external systems and platforms.',
          content: 'Description: Performs actions using the GitHub API.\nCapabilities:\n  * Create, update, delete repositories, branches, tags, and files.\n  * Manage issues, pull requests, comments, labels, and milestones.'
        }
      ];

      mockCreate.mockResolvedValue({
        choices: [
          {
            message: {
              content: JSON.stringify(mockResponse)
            }
          }
        ]
      });

      const content = `
Node Type: EXTERNAL_ACTION_NODE
Description: A node that interacts with external systems and platforms.
Subtypes:
1. EXTERNAL_GITHUB
- Description: Performs actions using the GitHub API.
- Capabilities:
  * Create, update, delete repositories, branches, tags, and files.
  * Manage issues, pull requests, comments, labels, and milestones.
      `;

      const result = await parseNodeKnowledge(content);

      expect(result).toHaveLength(1);
      expect(result[0].nodeType).toBe('EXTERNAL_ACTION_NODE');
      expect(result[0].nodeSubtype).toBe('EXTERNAL_GITHUB');
      expect(result[0].content).toContain('Capabilities:');
      expect(result[0].content).toContain('Create, update, delete repositories');
    });

    it('should handle multiple node types', async () => {
      const mockResponse = [
        {
          nodeType: 'TRIGGER_NODE',
          nodeSubtype: 'TRIGGER_CHAT',
          title: 'TRIGGER_NODE: TRIGGER_CHAT',
          description: 'A node that initiates a workflow based on an event or schedule.',
          content: 'Triggered by chat input from users.'
        },
        {
          nodeType: 'AI_AGENT_NODE',
          nodeSubtype: 'AI_ROUTER_AGENT',
          title: 'AI_AGENT_NODE: AI_ROUTER_AGENT',
          description: 'A node that runs an intelligent AI-driven task.',
          content: 'Routes tasks to the most suitable agent.'
        }
      ];

      mockCreate.mockResolvedValue({
        choices: [
          {
            message: {
              content: JSON.stringify(mockResponse)
            }
          }
        ]
      });

      const content = `
Node Type: TRIGGER_NODE
Description: A node that initiates a workflow based on an event or schedule.
Subtypes:
- TRIGGER_CHAT: Triggered by chat input from users.

Node Type: AI_AGENT_NODE
Description: A node that runs an intelligent AI-driven task.
Subtypes:
- AI_ROUTER_AGENT: Routes tasks to the most suitable agent.
      `;

      const result = await parseNodeKnowledge(content);

      expect(result).toHaveLength(2);
      expect(result[0].nodeType).toBe('TRIGGER_NODE');
      expect(result[1].nodeType).toBe('AI_AGENT_NODE');
    });

    it('should throw error when OpenAI API key is missing', async () => {
      delete process.env.OPENAI_API_KEY;

      await expect(parseNodeKnowledge('test content')).rejects.toThrow();
    });

    it('should handle OpenAI API errors', async () => {
      mockCreate.mockRejectedValue(new Error('API Error'));

      await expect(parseNodeKnowledge('test content')).rejects.toThrow('Failed to parse node knowledge');
    });

    it('should sanitize undefined values in OpenAI response', async () => {
      const responseWithUndefined = `[
        {
          "nodeType": "TRIGGER_NODE",
          "nodeSubtype": "TRIGGER_CHAT",
          "title": "TRIGGER_NODE: TRIGGER_CHAT",
          "description": "A node that initiates a workflow based on an event or schedule.",
          "content": undefined
        }
      ]`;

      mockCreate.mockResolvedValue({
        choices: [
          {
            message: {
              content: responseWithUndefined
            }
          }
        ]
      });

      const result = await parseNodeKnowledge('test content');

      expect(result).toHaveLength(1);
      expect(result[0].content).toBeNull();
    });
  });

  describe('parseNodeKnowledgePreview', () => {
    it('should parse basic preview without OpenAI', () => {
      const content = `
Node Type: TRIGGER_NODE
Description: A node that initiates a workflow based on an event or schedule.
Subtypes:
- TRIGGER_CHAT: Triggered by chat input from users.
- TRIGGER_WEBHOOK: Triggered by an incoming HTTP webhook.
      `;

      const result = parseNodeKnowledgePreview(content);

      expect(result).toHaveLength(2);
      expect(result[0].nodeType).toBe('TRIGGER_NODE');
      expect(result[0].nodeSubtype).toBe('TRIGGER_CHAT');
      expect(result[0].content).toBe('Preview parsing - content will be parsed accurately by OpenAI during upload');
    });

    it('should parse numbered format in preview', () => {
      const content = `
Node Type: EXTERNAL_ACTION_NODE
Description: A node that interacts with external systems and platforms.
Subtypes:
1. EXTERNAL_GITHUB
2. EXTERNAL_SLACK
      `;

      const result = parseNodeKnowledgePreview(content);

      expect(result).toHaveLength(2);
      expect(result[0].nodeSubtype).toBe('EXTERNAL_GITHUB');
      expect(result[1].nodeSubtype).toBe('EXTERNAL_SLACK');
    });

    it('should handle multiple node types in preview', () => {
      const content = `
Node Type: TRIGGER_NODE
Description: A node that initiates a workflow based on an event or schedule.
Subtypes:
- TRIGGER_CHAT: Triggered by chat input from users.

Node Type: AI_AGENT_NODE
Description: A node that runs an intelligent AI-driven task.
Subtypes:
- AI_ROUTER_AGENT: Routes tasks to the most suitable agent.
      `;

      const result = parseNodeKnowledgePreview(content);

      expect(result).toHaveLength(2);
      expect(result[0].nodeType).toBe('TRIGGER_NODE');
      expect(result[1].nodeType).toBe('AI_AGENT_NODE');
    });
  });
});
