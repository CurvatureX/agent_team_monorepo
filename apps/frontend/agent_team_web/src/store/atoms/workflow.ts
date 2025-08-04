import { atom } from 'jotai';
import { atomWithImmer } from 'jotai-immer';
import type { WorkflowNode, WorkflowEdge } from '@/types/workflow-editor';
import type { NodeTemplate } from '@/types/node-template';
import type { XYPosition } from 'reactflow';

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
});

// Add node action atom
export const addNodeAtom = atom(
  null,
  (get, set, { template, position }: { template: NodeTemplate; position: XYPosition }) => {
    const newNode: WorkflowNode = {
      id: `${template.node_type.toLowerCase()}_${Date.now()}`,
      type: 'custom',
      position,
      data: {
        label: template.name,
        template,
        parameters: { ...template.default_parameters },
        status: 'idle',
      },
    };

    set(workflowNodesAtom, (draft) => {
      draft.push(newNode);
    });

    // Select the new node
    set(selectedNodeIdAtom, newNode.id);
    set(detailsPanelOpenAtom, true);

    return newNode.id;
  }
);

// Update node parameters action atom
export const updateNodeParametersAtom = atom(
  null,
  (get, set, { nodeId, parameters }: { nodeId: string; parameters: Record<string, unknown> }) => {
    set(workflowNodesAtom, (draft) => {
      const node = draft.find((n) => n.id === nodeId);
      if (node) {
        node.data.parameters = parameters;
      }
    });
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
    }
  }
);

// Import these atoms from ui.ts to avoid circular dependency
import { selectedNodeIdAtom, detailsPanelOpenAtom } from './ui';

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
  
  return {
    valid: errors.length === 0,
    errors,
  };
});