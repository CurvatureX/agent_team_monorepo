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
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
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
        node.data.parameters = parameters;
        console.log('[updateNodeParametersAtom] Updated node parameters:', node.data.parameters);
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
