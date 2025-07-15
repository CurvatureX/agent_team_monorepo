import OpenAI from 'openai';

export interface NodeKnowledge {
  nodeType: string;
  nodeSubtype: string | null;
  title: string;
  description: string;
  content: string;
}

// Client-safe parser for preview (basic parsing without OpenAI)
export function parseNodeKnowledgePreview(content: string): NodeKnowledge[] {
  console.log('📄 Using basic preview parser (client-side) - upload for accurate OpenAI parsing');
  const nodes: NodeKnowledge[] = [];
  const sections = content.split(/Node Type: /).filter(Boolean);

  for (const section of sections) {
    const lines = section.trim().split('\n');
    const nodeType = lines[0].trim();

    let mainDescription = '';
    let i = 1;

    // Find the main description
    while (i < lines.length && !lines[i].includes('Subtypes:')) {
      if (lines[i].startsWith('Description:')) {
        mainDescription = lines[i].replace('Description:', '').trim();
      }
      i++;
    }

    // Skip "Subtypes:" line
    if (i < lines.length && lines[i].includes('Subtypes:')) {
      i++;
    }

    // Simple parsing for preview
    while (i < lines.length) {
      const line = lines[i].trim();

      if (line.startsWith('- ') && !line.startsWith('- Description:') && !line.startsWith('- Capabilities:')) {
        // Simple dash format (e.g., "- TRIGGER_CHAT: Description...")
        const subtype = line.replace(/^-\s*/, '').split(':')[0].trim();

        if (subtype) {
          nodes.push({
            nodeType,
            nodeSubtype: subtype,
            title: `${nodeType}: ${subtype}`,
            description: mainDescription,
            content: 'Preview parsing - content will be parsed accurately by OpenAI during upload'
          });
        }
      } else if (line.match(/^\d+\.\s+\w+/)) {
        // Numbered format (e.g., "1. EXTERNAL_GITHUB")
        const subtype = line.replace(/^\d+\.\s*/, '').trim();

        if (subtype) {
          nodes.push({
            nodeType,
            nodeSubtype: subtype,
            title: `${nodeType}: ${subtype}`,
            description: mainDescription,
            content: 'Preview parsing - content will be parsed accurately by OpenAI during upload'
          });
        }
      }
      i++;
    }
  }

  return nodes;
}

// Server-side OpenAI-powered parser
export async function parseNodeKnowledge(content: string): Promise<NodeKnowledge[]> {
  // Only instantiate OpenAI on server side
  if (typeof window !== 'undefined') {
    throw new Error('OpenAI parsing should only be used on the server side');
  }

  const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY!,
    timeout: 30000, // 30 second timeout
  });

  const prompt = `Parse this node knowledge text into a JSON array. For each subtype, create a specific, contextual description by combining the main type purpose with the specific subtype functionality.

Requirements:
- nodeType: main type (e.g., "TRIGGER_NODE", "AI_AGENT_NODE")
- nodeSubtype: specific subtype (e.g., "TRIGGER_CHAT", "AI_ROUTER_AGENT")
- title: format as "nodeType: nodeSubtype"
- description: Create a SPECIFIC description combining main type + subtype functionality (e.g., "A node that initiates a workflow when received chat input from users" NOT just "A node that initiates a workflow based on an event or schedule")
- content: Full detailed description including capabilities if listed

Examples:
For "TRIGGER_CHAT: Triggered by chat input from users" under TRIGGER_NODE:

return [
  {
    "nodeType": "TRIGGER_NODE",
    "nodeSubtype": "TRIGGER_CHAT",
    "title": "TRIGGER_NODE: TRIGGER_CHAT",
    "description": "A node that initiates a workflow when received chat input from users",
    "content": "A node that initiates a workflow when received chat input from users"
  }
]

For "4. EXTERNAL_EMAIL
- Description: Sends or receives emails.
- Capabilities:
  * Send emails via SMTP or email APIs (e.g., Gmail, Outlook).
  * Receive and parse emails via IMAP or webhook forwarding.
  * Trigger workflows based on email content.
  * Attach files or HTML content."

return [
  {
    "nodeType": "EXTERNAL_ACTION_NODE",
    "nodeSubtype": "EXTERNAL_EMAIL",
    "title": "EXTERNAL_ACTION_NODE: EXTERNAL_EMAIL",
    "description": "A node that interacts with external systems and platforms by sending or receiving emails",
    "content": "Sends or receives emails. Capabilities: Send emails via SMTP or email APIs (e.g., Gmail, Outlook). Receive and parse emails via IMAP or webhook forwarding. Trigger workflows based on email content. Attach files or HTML content."
  }
]
Return ONLY valid JSON array, no other text.

Content to parse:
${content}`;

  try {
    console.log('🤖 Using OpenAI GPT-4o-mini to parse node knowledge...');
    console.log(`📝 Prompt length: ${prompt.length} characters`);
    console.log(`📝 Content length: ${content.length} characters`);

    const startTime = Date.now();
    console.log('📡 Making OpenAI API call...');

    const response = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content: 'You are a precise data parser. Return only valid JSON arrays with no additional text or formatting.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.1,
      max_tokens: 4000
    });

    const duration = Date.now() - startTime;
    console.log(`⏱️ OpenAI API call completed in ${duration}ms`);

    const result = response.choices[0]?.message?.content?.trim();
    if (!result) {
      throw new Error('No response from OpenAI');
    }

    console.log('🔍 Raw OpenAI response:', result.substring(0, 200) + '...');

    // Sanitize the response to fix common JSON issues
    const sanitizedResult = result
      .replace(/:\s*undefined\s*,/g, ': null,')  // Replace undefined with null
      .replace(/:\s*undefined\s*}/g, ': null}')  // Replace undefined at end of objects
      .replace(/:\s*undefined\s*$/g, ': null');  // Replace undefined at end of string

    // Parse the JSON response
    const parsedNodes = JSON.parse(sanitizedResult) as NodeKnowledge[];
    console.log(`✅ OpenAI successfully parsed ${parsedNodes.length} nodes with structured content`);
    return parsedNodes;
  } catch (error) {
    console.error('Error parsing with OpenAI:', error);
    throw new Error(`Failed to parse node knowledge: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

export const NODE_KNOWLEDGE_TEXT = `Every node has a main_type and sub_type.
There are 8 Node types: TRIGGER_NODE, AI_AGENT_NODE, EXTERNAL_ACTION_NODE, ACTION_NODE, FLOW_NODE, HUMAN_IN_THE_LOOP_NODE, TOOL_NODE, MEMORY_NODE

Node Type: TRIGGER_NODE
Description: A node that initiates a workflow based on an event or schedule.
Subtypes:
- TRIGGER_CHAT: Triggered by chat input from users.
- TRIGGER_WEBHOOK: Triggered by an incoming HTTP webhook.
- TRIGGER_CRON: Triggered by a scheduled cron job.
- TRIGGER_MANUAL: Triggered manually by a user action.
- TRIGGER_EMAIL: Triggered when a specific email is received.
- TRIGGER_FORM: Triggered when a form is submitted.
- TRIGGER_CALENDAR: Triggered by a calendar event.

Node Type: AI_AGENT_NODE
Description: A node that runs an intelligent AI-driven task.
Subtypes:
- AI_ROUTER_AGENT: Routes tasks to the most suitable agent.
- AI_TASK_ANALYZER: Breaks down user requests into structured tasks.
- AI_DATA_INTEGRATOR: Integrates and summarizes information from multiple sources.
- AI_REPORT_GENERATOR: Automatically creates structured reports.

Node Type: EXTERNAL_ACTION_NODE
Description: A node that interacts with external systems and platforms.
Subtypes:
1. EXTERNAL_GITHUB
- Description: Performs actions using the GitHub API.
- Capabilities:
  * Create, update, delete repositories, branches, tags, and files.
  * Manage issues, pull requests, comments, labels, and milestones.
  * Trigger and manage GitHub Actions workflows.
  * Access organization/team settings and members.
  * Use GraphQL or REST APIs; subscribe to webhook events.

2. EXTERNAL_GOOGLE_CALENDAR
- Description: Interacts with Google Calendar.
- Capabilities:
  * Create, update, and delete calendars and events.
  * Manage attendees, reminders, timezones, and recurrence.
  * Access free/busy status and user settings like working location.
  * Use push notifications/webhooks for real-time sync.

3. EXTERNAL_TRELLO
- Description: Sends actions to or reads data from Trello.
- Capabilities:
  * Create, update, delete boards, lists, cards, and checklists.
  * Manage labels, attachments, comments, and due dates.
  * Search across boards and cards.
  * Extend with Power-Ups or webhooks.

4. EXTERNAL_EMAIL
- Description: Sends or receives emails.
- Capabilities:
  * Send emails via SMTP or email APIs (e.g., Gmail, Outlook).
  * Receive and parse emails via IMAP or webhook forwarding.
  * Trigger workflows based on email content.
  * Attach files or HTML content.

5. EXTERNAL_SLACK
- Description: Sends messages or reads data from Slack.
- Capabilities:
  * Send, update, and delete messages in channels or threads.
  * Upload and attach files.
  * Interact with users via bots, modals, and slash commands.
  * Subscribe to workspace events and channel activity.
  * Search messages and users.

6. EXTERNAL_API_CALL
- Description: Makes a generic HTTP API call.
- Capabilities:
  * Make HTTP requests (GET, POST, PUT, DELETE, etc.) to any REST API.
  * Set custom headers, body (JSON/XML), and query params.
  * Handle responses, errors, and authentication.
  * Chain API responses into subsequent workflow steps.

7. EXTERNAL_WEBHOOK
- Description: Sends a webhook to an external service.
- Capabilities:
  * Send HTTP POST (or other method) to external endpoint.
  * Customize payloads, headers, and retry logic.
  * Trigger integrations with third-party systems.
  * Log response or continue workflow conditionally.

8. EXTERNAL_NOTIFICATION
- Description: Sends a notification to a user or system.
- Capabilities:
  * Send push notifications (APNs, FCM), SMS, or in-app alerts.
  * Customize message content and target.
  * Integrate with services like OneSignal, Twilio, or Amazon SNS.
  * Track delivery status and user interaction.

Node Type: ACTION_NODE
Description: A node that performs a self-contained action within the workflow.
Subtypes:
- ACTION_RUN_CODE: Runs a script or code block.
- ACTION_SEND_HTTP_REQUEST: Sends a standard HTTP request.
- ACTION_PARSE_IMAGE: Processes and analyzes image data.
- ACTION_WEB_SEARCH: Performs a web search to find information.
- ACTION_DATABASE_OPERATION: Executes CRUD operations on a database.
- ACTION_FILE_OPERATION: Reads, writes, or moves files.
- ACTION_DATA_TRANSFORMATION: Transforms input data into a new format.

Node Type: FLOW_NODE
Description: A node used to control the flow of the workflow.
Subtypes:
- FLOW_IF: Evaluates an input condition and directs the workflow to either the "true" or "false" branch based on the result, determining which path is executed.
- FLOW_FILTER: Applies specified conditions to filter elements in a collection, passing only those that meet criteria to subsequent nodes.
- FLOW_LOOP: Repeatedly executes a connected node for each item in a collection or until a specified condition is met, processing data iteratively and passing results back to the workflow.
- FLOW_MERGE: Combines multiple incoming flows or data streams into a single unified path, synchronizing parallel branches.
- FLOW_SWITCH: Directs workflow execution down one of several paths based on a key or selector value, functioning like a multi-way branch or switch-case.
- FLOW_WAIT: Waits for a specified amount of time or event, can connect with a Trigger node.

Node Type: HUMAN_IN_THE_LOOP_NODE
Description: A node that waits for manual human interaction to continue.
Subtypes:
- HUMAN_GMAIL: Sends message through email and wait for a human's reply.
- HUMAN_SLACK: Invokes Slack interaction with a human.
- HUMAN_DISCORD: Requires human interaction via Discord.
- HUMAN_TELEGRAM: Engages a human via Telegram.
- HUMAN_APP: Interfaces with a human in our mobile app.

Node Type: TOOL_NODE
Description: A utility node that provides a MCP tool to AI Node.
Subtypes:
- TOOL_GOOGLE_CALENDAR_MCP: Manages calendar operations through MCP.
- TOOL_NOTION_MCP: Integrates Notion functionality via MCP.
- TOOL_CALENDAR: General calendar utilities.
- TOOL_EMAIL: Email utility tools.
- TOOL_HTTP: Sends or receives data over HTTP.
- TOOL_CODE_EXECUTION: Executes code as a utility function.

Node Type: MEMORY_NODE
Description: A node that stores or retrieves memory for AI Node.
Subtypes:
- MEMORY_SIMPLE: Stores simple key-value memory.
- MEMORY_BUFFER: Stores recent history or conversation buffer.
- MEMORY_KNOWLEDGE: Saves structured knowledge for later retrieval.
- MEMORY_VECTOR_STORE: Embeds and stores vectors for semantic search.
- MEMORY_DOCUMENT: Stores and retrieves full documents.
- MEMORY_EMBEDDING: Embeds content into vector space for AI tasks.`;
