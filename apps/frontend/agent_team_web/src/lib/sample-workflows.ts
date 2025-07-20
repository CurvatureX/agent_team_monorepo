import { WorkflowData } from '@/types/workflow';

export const exampleWorkflow: WorkflowData = {
  "id": "example_workflow",
  "name": "Example Workflow",
  "active": true,
  "nodes": [
    {
      "id": "trigger_0",
      "name": "When calendar event occurs",
      "type": "TRIGGER_NODE",
      "subtype": "TRIGGER_CALENDAR",
      "type_version": 1,
      "position": {
        "x": -200,
        "y": -140
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": "STOP_WORKFLOW_ON_ERROR",
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    },
    {
      "id": "ai_agent_0",
      "name": "AI Agent Processing",
      "type": "AI_AGENT_NODE",
      "subtype": "AI_AGENT",
      "type_version": 1,
      "position": {
        "x": 1020,
        "y": -220
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": "STOP_WORKFLOW_ON_ERROR",
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
      "type": "ACTION_NODE",
      "subtype": "ACTION_DATA_TRANSFORMATION",
      "type_version": 1,
      "position": {
        "x": 460,
        "y": -280
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": "STOP_WORKFLOW_ON_ERROR",
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
      "type": "EXTERNAL_ACTION_NODE",
      "subtype": "EXTERNAL_GITHUB",
      "type_version": 1,
      "position": {
        "x": 160,
        "y": -160
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": "STOP_WORKFLOW_ON_ERROR",
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
      "type": "FLOW_NODE",
      "subtype": "FLOW_FILTER",
      "type_version": 1,
      "position": {
        "x": 740,
        "y": -300
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": "STOP_WORKFLOW_ON_ERROR",
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
      "type": "HUMAN_IN_THE_LOOP_NODE",
      "subtype": "HUMAN_DISCORD",
      "type_version": 1,
      "position": {
        "x": 1380,
        "y": -100
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": "STOP_WORKFLOW_ON_ERROR",
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
      "type": "HUMAN_IN_THE_LOOP_NODE",
      "subtype": "HUMAN_GMAIL",
      "type_version": 1,
      "position": {
        "x": 400,
        "y": 20
      },
      "disabled": false,
      "parameters": {},
      "credentials": {},
      "on_error": "STOP_WORKFLOW_ON_ERROR",
      "retry_policy": {
        "max_tries": 1,
        "wait_between_tries": 0
      },
      "notes": {},
      "webhooks": []
    }
  ],
  "connections": {
    "connections": {
      "trigger_0": {
        "output": {
          "connections": [
            {
              "node": "external_action_0",
              "type": "MAIN",
              "index": 0
            }
          ]
        }
      },
      "external_action_0": {
        "output": {
          "connections": [
            {
              "node": "action_2",
              "type": "MAIN",
              "index": 0
            },
            {
              "node": "human_in_the_loop_1",
              "type": "MAIN",
              "index": 1
            }
          ]
        }
      },
      "action_2": {
        "output": {
          "connections": [
            {
              "node": "flow_0",
              "type": "MAIN",
              "index": 0
            }
          ]
        }
      },
      "flow_0": {
        "output": {
          "connections": [
            {
              "node": "ai_agent_0",
              "type": "MAIN",
              "index": 0
            }
          ]
        }
      },
      "ai_agent_0": {
        "output": {
          "connections": [
            {
              "node": "human_in_the_loop_0",
              "type": "MAIN",
              "index": 0
            }
          ]
        }
      },
      "human_in_the_loop_1": {
        "output": {
          "connections": [
            {
              "node": "ai_agent_0",
              "type": "MAIN",
              "index": 0
            }
          ]
        }
      }
    }
  },
  "settings": {
    "timezone": {
      "default": "UTC"
    },
    "save_execution_progress": true,
    "save_manual_executions": true,
    "timeout": 300,
    "error_policy": "STOP_WORKFLOW",
    "caller_policy": "WORKFLOW_MAIN"
  },
  "static_data": {},
  "pin_data": {},
  "created_at": 1752851205,
  "updated_at": 1752851364,
  "version": "1.0.0",
  "tags": [
    "example",
    "workflow"
  ]
}; 