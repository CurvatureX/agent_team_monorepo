/**
 * Workflow Converter Utilities
 * 
 * This module handles conversions between API workflow format and editor workflow format.
 * API format: Based on backend API definition (WorkflowEntity, WorkflowNode from api.json)
 * Editor format: Used by React Flow for visual editing (WorkflowNode from workflow-editor.ts)
 */

import type { 
  Workflow as ApiWorkflow, 
  WorkflowNode as ApiWorkflowNode,
  WorkflowEdge as ApiWorkflowEdge,
  CreateWorkflowRequest,
  UpdateWorkflowRequest,
} from '@/types/workflow';
import type { 
  WorkflowNode as EditorWorkflowNode, 
  WorkflowEdge as EditorWorkflowEdge 
} from '@/types/workflow-editor';
import type { NodeTemplate } from '@/types/node-template';

/**
 * Convert API workflow node to editor workflow node
 */
export function apiNodeToEditorNode(
  apiNode: ApiWorkflowNode,
  template: NodeTemplate | undefined
): EditorWorkflowNode | null {
  if (!template) {
    console.warn(`Template not found for node ${apiNode.id} (type: ${apiNode.type}, subtype: ${apiNode.subtype})`);
    return null;
  }

  return {
    id: apiNode.id,
    type: 'custom', // React Flow custom node type
    position: apiNode.position || { x: 0, y: 0 },
    data: {
      label: apiNode.name || template.name,
      template,
      parameters: {
        ...template.default_parameters,
        ...apiNode.config,
        ...apiNode.parameters,
        ...apiNode.inputs,
      },
      status: apiNode.disabled ? 'error' : 'idle',
    },
  };
}

/**
 * Convert editor workflow node to API workflow node
 */
export function editorNodeToApiNode(editorNode: EditorWorkflowNode): ApiWorkflowNode {
  const { data } = editorNode;
  const template = data.template;

  return {
    id: editorNode.id,
    type: template.node_type,
    subtype: template.node_subtype,
    name: data.label,
    description: template.description,
    position: editorNode.position,
    config: data.parameters,
    parameters: data.parameters,
    inputs: {},
    outputs: {},
    metadata: {},
    disabled: data.status === 'error',
  };
}

/**
 * Convert API workflow edge to editor workflow edge
 */
export function apiEdgeToEditorEdge(apiEdge: ApiWorkflowEdge): EditorWorkflowEdge {
  return {
    id: apiEdge.id,
    source: apiEdge.source,
    target: apiEdge.target,
    type: apiEdge.type || 'default',
    sourceHandle: apiEdge.sourceHandle || null,
    targetHandle: apiEdge.targetHandle || null,
    label: (apiEdge.label || apiEdge.condition || undefined) as string | undefined,
    data: apiEdge.data,
  };
}

/**
 * Convert editor workflow edge to API workflow edge
 */
export function editorEdgeToApiEdge(editorEdge: EditorWorkflowEdge): ApiWorkflowEdge {
  return {
    id: editorEdge.id,
    source: editorEdge.source,
    target: editorEdge.target,
    condition: (typeof editorEdge.label === 'string' ? editorEdge.label : null),
    label: (typeof editorEdge.label === 'string' ? editorEdge.label : null),
    type: editorEdge.type,
    sourceHandle: editorEdge.sourceHandle,
    targetHandle: editorEdge.targetHandle,
    data: editorEdge.data,
  };
}

/**
 * Convert API workflow to editor format
 */
export function apiWorkflowToEditor(
  apiWorkflow: ApiWorkflow,
  templates: NodeTemplate[]
): {
  nodes: EditorWorkflowNode[];
  edges: EditorWorkflowEdge[];
  metadata: {
    id: string;
    name: string;
    description: string;
    version: string;
    created_at: number;
    updated_at: number;
    tags: string[];
  };
} {
  // Create template lookup map
  const templateMap = new Map<string, NodeTemplate>();
  templates.forEach((template) => {
    // Try multiple key formats for flexibility
    templateMap.set(`${template.node_type}_${template.node_subtype}`, template);
    templateMap.set(`${template.node_type}:${template.node_subtype}`, template);
    templateMap.set(template.id, template);
  });

  // Convert nodes
  const nodes: EditorWorkflowNode[] = [];
  apiWorkflow.nodes.forEach((apiNode) => {
    // Try to find template with different key formats
    const template = 
      templateMap.get(`${apiNode.type}_${apiNode.subtype}`) ||
      templateMap.get(`${apiNode.type}:${apiNode.subtype}`) ||
      templateMap.get(apiNode.type as string) ||
      templateMap.get(apiNode.id);

    const editorNode = apiNodeToEditorNode(apiNode, template);
    if (editorNode) {
      nodes.push(editorNode);
    }
  });

  // Convert edges
  const edges = (apiWorkflow.edges || []).map(apiEdgeToEditorEdge);

  // Extract metadata
  const metadata = {
    id: apiWorkflow.id || '',
    name: apiWorkflow.name || 'Untitled Workflow',
    description: apiWorkflow.description || '',
    version: String(apiWorkflow.version || '1'),
    created_at: apiWorkflow.created_at ? new Date(apiWorkflow.created_at).getTime() : Date.now(),
    updated_at: apiWorkflow.updated_at ? new Date(apiWorkflow.updated_at).getTime() : Date.now(),
    tags: apiWorkflow.tags || [],
  };

  return { nodes, edges, metadata };
}

/**
 * Convert editor workflow to API create request
 */
export function editorWorkflowToCreateRequest(
  nodes: EditorWorkflowNode[],
  edges: EditorWorkflowEdge[],
  metadata: {
    name: string;
    description: string;
    tags?: string[];
  },
  userId: string
): CreateWorkflowRequest {
  // Convert nodes to API format
  const apiNodes = nodes.map(editorNodeToApiNode);

  // Build connections object (n8n style)
  interface ConnectionNode {
    node: string;
    type: string;
    index: number;
  }
  
  interface ConnectionStructure {
    main: ConnectionNode[][];
  }
  
  const connections: Record<string, ConnectionStructure> = {};
  edges.forEach((edge) => {
    if (!connections[edge.source]) {
      connections[edge.source] = {
        main: [[]]
      };
    }
    connections[edge.source].main[0].push({
      node: edge.target,
      type: 'main',
      index: 0,
    });
  });

  return {
    name: metadata.name,
    description: metadata.description,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    nodes: apiNodes as unknown as any[], // API expects NodeData format
    connections: connections as Record<string, unknown>,
    tags: metadata.tags || [],
    user_id: userId,
  };
}

/**
 * Convert editor workflow to API update request
 */
export function editorWorkflowToUpdateRequest(
  workflowId: string,
  nodes: EditorWorkflowNode[],
  edges: EditorWorkflowEdge[],
  metadata: {
    name?: string;
    description?: string;
    tags?: string[];
  },
  userId: string
): UpdateWorkflowRequest {
  // Convert nodes to API format
  const apiNodes = nodes.map(editorNodeToApiNode);

  // Build connections object
  interface ConnectionNode {
    node: string;
    type: string;
    index: number;
  }
  
  interface ConnectionStructure {
    main: ConnectionNode[][];
  }
  
  const connections: Record<string, ConnectionStructure> = {};
  edges.forEach((edge) => {
    if (!connections[edge.source]) {
      connections[edge.source] = {
        main: [[]]
      };
    }
    connections[edge.source].main[0].push({
      node: edge.target,
      type: 'main',
      index: 0,
    });
  });

  return {
    workflow_id: workflowId,
    name: metadata.name,
    description: metadata.description,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    nodes: apiNodes as unknown as any[],
    connections: connections as Record<string, unknown>,
    tags: metadata.tags,
    user_id: userId,
  };
}

/**
 * Generate a unique node ID
 */
export function generateNodeId(nodeType: string): string {
  return `${nodeType.toLowerCase()}_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Generate a unique edge ID
 */
export function generateEdgeId(source: string, target: string): string {
  return `edge_${source}_${target}_${Date.now()}`;
}