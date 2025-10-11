import { atom } from 'jotai';
import { atomWithImmer } from 'jotai-immer';
import type { WorkflowNode, WorkflowEdge } from '@/types/workflow-editor';
import type { NodeTemplate } from '@/types/node-template';
import type { XYPosition } from 'reactflow';
import { getUserTimezone } from '@/utils/timezone';

// Workflow nodes atom with immer for easy updates
export const workflowNodesAtom = atomWithImmer<WorkflowNode[]>([]);

// Workflow edges atom with immer for easy updates
export const workflowEdgesAtom = atomWithImmer<WorkflowEdge[]>([]);

// Workflow metadata
export const workflowMetadataAtom = atom({
  id: '',
  name: 'Untitled Workflow',
  description: '',
  version: '1.0.0',
  created_at: Date.now(),
  updated_at: Date.now(),
  tags: [] as string[],
});

// Add node action atom
export const addNodeAtom = atom(
  null,
  (get, set, { template, position }: { template: NodeTemplate; position: XYPosition }) => {
    // Auto-detect timezone for CRON trigger nodes
    const parameters = { ...template.default_parameters };
    if (template.node_type === 'TRIGGER' && template.node_subtype === 'CRON') {
      parameters.timezone = getUserTimezone();
    }

    const newNode: WorkflowNode = {
      id: `${template.node_type.toLowerCase()}_${Date.now()}`,
      type: 'custom',
      position,
      data: {
        label: template.name,
        template,
        parameters,
        status: 'idle',
      },
    };

    console.log('Adding node to store:', newNode);
    const currentNodes = get(workflowNodesAtom);
    console.log('Current nodes before add:', currentNodes);

    set(workflowNodesAtom, (draft) => {
      draft.push(newNode);
      console.log('Nodes after add (draft):', draft);
      console.log('Draft length:', draft.length);
    });

    // Select the new node and show details panel
    set(selectedNodeIdAtom, newNode.id);
    set(detailsPanelOpenAtom, true);
    set(sidebarCollapsedAtom, true); // Hide Node Library when showing Node Details

    console.log('Node added successfully:', newNode.id);
    return newNode.id;
  }
);

// Helper function to check if a node is Slack-related
const isSlackNode = (node: WorkflowNode): boolean => {
  const subtype = node.data.template.node_subtype;
  return (
    subtype === 'SLACK' ||
    subtype === 'SLACK_INTERACTION' ||
    subtype === 'SLACK_MCP_TOOL' ||
    subtype.includes('SLACK')
  );
};

// Helper function to check if a node is Notion-related
const isNotionNode = (node: WorkflowNode): boolean => {
  const subtype = node.data.template.node_subtype;
  return (
    subtype === 'NOTION' ||
    subtype === 'NOTION_MCP_TOOL' ||
    subtype.includes('NOTION')
  );
};

// Helper function to check if a value is empty
const isEmptyValue = (value: unknown): boolean => {
  return (
    value === null ||
    value === undefined ||
    value === '' ||
    (typeof value === 'string' && value.trim() === '') ||
    (typeof value === 'string' && /^\{\{.*\}\}$|^\$placeholder.*$|^<.*>$/.test(value.trim()))
  );
};

// Update node parameters action atom
export const updateNodeParametersAtom = atom(
  null,
  (get, set, { nodeId, parameters }: { nodeId: string; parameters: Record<string, unknown> }) => {
    console.log('[updateNodeParametersAtom] Updating parameters for node:', nodeId, {
      newParameters: parameters,
    });

    set(workflowNodesAtom, (draft) => {
      const node = draft.find((n) => n.id === nodeId);
      if (node) {
        console.log('[updateNodeParametersAtom] Found node, old parameters:', node.data.parameters);

        // Store old parameters to detect what changed
        const oldParameters = node.data.parameters || {};
        // IMPORTANT: Merge parameters instead of replacing to preserve all configuration fields
        node.data.parameters = { ...oldParameters, ...parameters };
        console.log('[updateNodeParametersAtom] Updated node parameters (merged):', node.data.parameters);

        // Auto-fill feature: propagate Slack channel and Notion database_id/page_id to other nodes
        const autoFillUpdates: Array<{ nodeId: string; field: string; value: unknown }> = [];

        // Check for Slack channel updates
        if (isSlackNode(node) && parameters.channel && !isEmptyValue(parameters.channel)) {
          const oldChannel = oldParameters.channel;
          // Only propagate if the channel actually changed
          if (oldChannel !== parameters.channel) {
            draft.forEach((otherNode) => {
              if (otherNode.id !== nodeId && isSlackNode(otherNode)) {
                const otherParams = otherNode.data.parameters || {};
                // Only update if the other node has an empty channel
                if (isEmptyValue(otherParams.channel)) {
                  otherNode.data.parameters = {
                    ...otherParams,
                    channel: parameters.channel,
                  };
                  autoFillUpdates.push({
                    nodeId: otherNode.id,
                    field: 'channel',
                    value: parameters.channel,
                  });
                }
              }
            });
          }
        }

        // Check for Notion database_id updates
        if (isNotionNode(node) && parameters.database_id && !isEmptyValue(parameters.database_id)) {
          const oldDatabaseId = oldParameters.database_id;
          // Only propagate if the database_id actually changed
          if (oldDatabaseId !== parameters.database_id) {
            draft.forEach((otherNode) => {
              if (otherNode.id !== nodeId && isNotionNode(otherNode)) {
                const otherParams = otherNode.data.parameters || {};
                // Only update if the other node has an empty database_id
                if (isEmptyValue(otherParams.database_id)) {
                  otherNode.data.parameters = {
                    ...otherParams,
                    database_id: parameters.database_id,
                  };
                  autoFillUpdates.push({
                    nodeId: otherNode.id,
                    field: 'database_id',
                    value: parameters.database_id,
                  });
                }
              }
            });
          }
        }

        // Check for Notion page_id updates
        if (isNotionNode(node) && parameters.page_id && !isEmptyValue(parameters.page_id)) {
          const oldPageId = oldParameters.page_id;
          // Only propagate if the page_id actually changed
          if (oldPageId !== parameters.page_id) {
            draft.forEach((otherNode) => {
              if (otherNode.id !== nodeId && isNotionNode(otherNode)) {
                const otherParams = otherNode.data.parameters || {};
                // Only update if the other node has an empty page_id or database_id
                // (page_id can be used instead of database_id)
                if (isEmptyValue(otherParams.page_id) || isEmptyValue(otherParams.database_id)) {
                  const updates: Record<string, unknown> = {};
                  if (isEmptyValue(otherParams.page_id)) {
                    updates.page_id = parameters.page_id;
                  }
                  if (isEmptyValue(otherParams.database_id)) {
                    updates.database_id = parameters.page_id;
                  }
                  otherNode.data.parameters = {
                    ...otherParams,
                    ...updates,
                  };
                  Object.entries(updates).forEach(([field, value]) => {
                    autoFillUpdates.push({
                      nodeId: otherNode.id,
                      field,
                      value,
                    });
                  });
                }
              }
            });
          }
        }

        // Log auto-fill updates if any occurred
        if (autoFillUpdates.length > 0) {
          console.log('[updateNodeParametersAtom] Auto-filled parameters in other nodes:', autoFillUpdates);
        }
      } else {
        console.error('[updateNodeParametersAtom] Node not found:', nodeId);
      }
    });

    // Log the updated state
    const updatedNodes = get(workflowNodesAtom);
    const updatedNode = updatedNodes.find((n) => n.id === nodeId);
    console.log('[updateNodeParametersAtom] Node after update in store:', updatedNode?.data.parameters);
  }
);

// Update node data action atom
export const updateNodeDataAtom = atom(
  null,
  (get, set, { nodeId, data }: { nodeId: string; data: Partial<WorkflowNode['data']> }) => {
    set(workflowNodesAtom, (draft) => {
      const node = draft.find((n) => n.id === nodeId);
      if (node) {
        node.data = { ...node.data, ...data };
      }
    });
  }
);

// Delete node action atom
export const deleteNodeAtom = atom(
  null,
  (get, set, nodeId: string) => {
    // Remove the node
    set(workflowNodesAtom, (draft) => {
      return draft.filter((n) => n.id !== nodeId);
    });

    // Remove connected edges
    set(workflowEdgesAtom, (draft) => {
      return draft.filter((e) => e.source !== nodeId && e.target !== nodeId);
    });

    // Clear selection if this node was selected
    if (get(selectedNodeIdAtom) === nodeId) {
      set(selectedNodeIdAtom, null);
      set(detailsPanelOpenAtom, false);
      set(sidebarCollapsedAtom, false); // Show Node Library when node is deleted
    }
  }
);

// Import these atoms from ui.ts to avoid circular dependency
import { selectedNodeIdAtom, detailsPanelOpenAtom, sidebarCollapsedAtom } from './ui';

// Derived atom - get selected node
export const selectedNodeAtom = atom((get) => {
  const nodeId = get(selectedNodeIdAtom);
  const nodes = get(workflowNodesAtom);
  return nodes.find((n) => n.id === nodeId);
});

// Derived atom - count nodes by type
export const nodeCountByTypeAtom = atom((get) => {
  const nodes = get(workflowNodesAtom);
  return nodes.reduce((acc, node) => {
    const type = node.data.template.node_type;
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
});

// Derived atom - validate workflow
export const workflowValidationAtom = atom((get) => {
  const nodes = get(workflowNodesAtom);
  const edges = get(workflowEdgesAtom);

  const errors: string[] = [];
  const invalidNodes: Array<{ id: string; name: string; missingFields: string[] }> = [];

  // Check if workflow has at least one trigger
  const hasTrigger = nodes.some((n) => n.data.template.node_type === 'TRIGGER');
  if (!hasTrigger) {
    errors.push('Workflow must have at least one trigger node');
  }

  // Check for disconnected nodes
  const connectedNodeIds = new Set<string>();
  edges.forEach((edge) => {
    connectedNodeIds.add(edge.source);
    connectedNodeIds.add(edge.target);
  });

  const disconnectedNodes = nodes.filter((n) =>
    n.data.template.node_type !== 'TRIGGER' && !connectedNodeIds.has(n.id)
  );

  if (disconnectedNodes.length > 0) {
    errors.push(`${disconnectedNodes.length} node(s) are not connected`);
  }

  // Check for missing required fields (import validateNodeParameters inline to avoid circular deps)
  nodes.forEach((node) => {
    const requiredFields = node.data.template?.parameter_schema?.required || [];
    const parameters = node.data.parameters || {};

    if (requiredFields.length > 0) {
      const missingFields: string[] = [];

      for (const field of requiredFields) {
        const value = parameters[field];
        // Check if value is incomplete (same logic as isValueIncomplete)
        const isIncomplete =
          value === null ||
          value === undefined ||
          value === '' ||
          (typeof value === 'string' && /^\{\{.*\}\}$|^\$[a-zA-Z_][a-zA-Z0-9_]*$|^<.*>$/.test(value.trim())) ||
          (Array.isArray(value) && value.length === 0) ||
          (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0);

        if (isIncomplete) {
          missingFields.push(field);
        }
      }

      if (missingFields.length > 0) {
        invalidNodes.push({
          id: node.id,
          name: node.data.label,
          missingFields,
        });
      }
    }
  });

  return {
    valid: errors.length === 0 && invalidNodes.length === 0,
    errors,
    invalidNodes,
  };
});
