import { Workflow } from '@/types/workflow';
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
} from '@/types/workflow-enums';

export const exampleWorkflow = {
  "created_at": new Date().toISOString(),
  "updated_at": new Date().toISOString(),
  "id": "example_workflow",
  "user_id": "user_123",
  "name": "Example Workflow",
  "description": "An example workflow demonstrating various node types",
  "type": WorkflowType.Sequential,
  "status": WorkflowStatus.Idle,
  "version": 1,
  "execution_count": 0,
  "nodes": [
    {
      "id": "trigger_0",
      "name": "When calendar event occurs",
      "type": NodeType.TRIGGER,
      "subtype": TriggerSubtype.WEBHOOK,
      "type_version": 1,
      "position": {
        "x": -200,
        "y": -140
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": ErrorPolicy.Stop,
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    },
    {
      "id": "ai_agent_0",
      "name": "ChatGPT Agent",
      "type": NodeType.AI_AGENT,
      "subtype": AIAgentSubtype.OPENAI_CHATGPT,
      "type_version": 1,
      "position": {
        "x": 1020,
        "y": -220
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": ErrorPolicy.Stop,
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    },
    {
      "id": "action_2",
      "name": "Action Node",
      "type": NodeType.ACTION,
      "subtype": ActionSubtype.DATA_TRANSFORMATION,
      "type_version": 1,
      "position": {
        "x": 460,
        "y": -280
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": ErrorPolicy.Stop,
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    },
    {
      "id": "external_action_0",
      "name": "External Action",
      "type": NodeType.TOOL,
      "subtype": ToolSubtype.HTTP_CLIENT,
      "type_version": 1,
      "position": {
        "x": 160,
        "y": -160
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": ErrorPolicy.Stop,
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    },
    {
      "id": "flow_0",
      "name": "Flow Control",
      "type": NodeType.FLOW,
      "subtype": FlowSubtype.FILTER,
      "type_version": 1,
      "position": {
        "x": 740,
        "y": -300
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": ErrorPolicy.Stop,
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    },
    {
      "id": "human_in_the_loop_0",
      "name": "Human Input via Discord",
      "type": NodeType.HUMAN_IN_THE_LOOP,
      "subtype": HumanLoopSubtype.DISCORD_INTERACTION,
      "type_version": 1,
      "position": {
        "x": 1380,
        "y": -100
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": ErrorPolicy.Stop,
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    },
    {
      "id": "human_in_the_loop_1",
      "name": "Human Input via Gmail",
      "type": NodeType.HUMAN_IN_THE_LOOP,
      "subtype": HumanLoopSubtype.GMAIL_INTERACTION,
      "type_version": 1,
      "position": {
        "x": 400,
        "y": 20
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": ErrorPolicy.Stop,
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    }
  ],
  "edges": [
    {
      "id": "e-trigger_0-external_action_0",
      "source": "trigger_0",
      "target": "external_action_0",
      "type": "default"
    },
    {
      "id": "e-external_action_0-action_2",
      "source": "external_action_0",
      "target": "action_2",
      "type": "default"
    },
    {
      "id": "e-external_action_0-human_in_the_loop_1",
      "source": "external_action_0",
      "target": "human_in_the_loop_1",
      "type": "default"
    },
    {
      "id": "e-action_2-flow_0",
      "source": "action_2",
      "target": "flow_0",
      "type": "default"
    },
    {
      "id": "e-flow_0-ai_agent_0",
      "source": "flow_0",
      "target": "ai_agent_0",
      "type": "default"
    },
    {
      "id": "e-ai_agent_0-human_in_the_loop_0",
      "source": "ai_agent_0",
      "target": "human_in_the_loop_0",
      "type": "default"
    },
    {
      "id": "e-human_in_the_loop_1-ai_agent_0",
      "source": "human_in_the_loop_1",
      "target": "ai_agent_0",
      "type": "default"
    }
  ],
  "variables": {},
  "settings": {
    "timezone": {
      "default": "UTC"
    },
    "save_execution_progress": true,
    "save_manual_executions": true,
    "timeout": 300,
    "error_policy": ErrorPolicy.Stop,
    "caller_policy": CallerPolicy.Workflow
  },
  "tags": [
    "example",
    "workflow"
  ]
} as any as Workflow;
