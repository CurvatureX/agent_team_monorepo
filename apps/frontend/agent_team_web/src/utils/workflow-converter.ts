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
import { NodeSubtypeAliasToCanonical, NodeSubtypeCanonicalToAlias } from '@/types/workflow-enums';

/**
 * Helper function to check if a value is empty/placeholder
 */
function isEmptyOrPlaceholder(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (value === '') return true;
  if (value === '{{$placeholder}}') return true;
  if (Array.isArray(value) && value.length === 0) return true;
  if (typeof value === 'object' && Object.keys(value as object).length === 0) return true;
  return false;
}

/**
 * Smart merge parameters with priority: configurations > input_params > defaults
 * Filters out empty/placeholder values to prevent overwriting real data
 */
function mergeNodeParameters(
  templateDefaults: Record<string, unknown> = {},
  configurations: Record<string, unknown> = {},
  inputParams: Record<string, unknown> = {}
): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  // Collect all unique keys from all sources
  const allKeys = new Set([
    ...Object.keys(templateDefaults),
    ...Object.keys(configurations),
    ...Object.keys(inputParams),
  ]);

  // For each key, use the first non-empty value in priority order
  allKeys.forEach((key) => {
    const configValue = configurations[key];
    const inputValue = inputParams[key];
    const defaultValue = templateDefaults[key];

    // Priority: configurations (if non-empty) > input_params (if non-empty) > defaults
    if (!isEmptyOrPlaceholder(configValue)) {
      result[key] = configValue;
    } else if (!isEmptyOrPlaceholder(inputValue)) {
      result[key] = inputValue;
    } else if (defaultValue !== undefined) {
      result[key] = defaultValue;
    }
  });

  return result;
}

/**
 * Convert API workflow node to editor workflow node
 * Maps backend Node format to React Flow node format
 */
export function apiNodeToEditorNode(
  apiNode: ApiWorkflowNode,
  template: NodeTemplate | undefined
): EditorWorkflowNode | null {
  if (!template) {
    console.warn(`Template not found for node ${apiNode.id} (type: ${apiNode.type}, subtype: ${apiNode.subtype})`);
    return null;
  }

  // Smart merge: configurations take priority over input_params, empty values are filtered
  const mergedParameters = mergeNodeParameters(
    template.default_parameters || {},
    apiNode.configurations || {},
    apiNode.input_params || {}
  );

  return {
    id: apiNode.id,
    type: 'custom', // React Flow custom node type
    position: apiNode.position || { x: 0, y: 0 },
    data: {
      label: apiNode.name || template.name,
      description: apiNode.description || '',
      template,
      // CRITICAL: Use smart merge that filters empty values and prioritizes configurations
      // Priority: configurations (real values) > input_params (runtime) > template defaults
      // Empty strings, null, undefined, and placeholders are filtered out
      parameters: mergedParameters,
      status: 'idle',
      // Store the original API node data for later export
      originalData: apiNode,
    },
  };
}

/**
 * Convert editor workflow node to API workflow node
 * Maps React Flow node format to backend Node format
 */
export function editorNodeToApiNode(editorNode: EditorWorkflowNode): ApiWorkflowNode {
  const { data } = editorNode;
  const template = data.template;

  // Map alias (template subtype) to canonical backend subtype if mapping exists
  const typeKey = template.node_type as keyof typeof NodeSubtypeAliasToCanonical;
  const canonicalSubtype = NodeSubtypeAliasToCanonical[typeKey]?.[template.node_subtype] || template.node_subtype;

  return {
    id: editorNode.id,
    type: template.node_type,
    subtype: canonicalSubtype,
    name: data.label,
    description: template.description,
    position: editorNode.position,
    // Backend format (clean - no legacy fields)
    configurations: data.parameters,
    input_params: {},
    output_params: {},
  };
}

/**
 * Convert API workflow edge to editor workflow edge
 * Maps backend Connection format to React Flow Edge format
 */
export function apiEdgeToEditorEdge(apiEdge: ApiWorkflowEdge): EditorWorkflowEdge {
  // Type assertion for flexible edge format (handles both snake_case and camelCase)
  const edge = apiEdge as ApiWorkflowEdge & {
    fromNode?: string;
    toNode?: string;
    source?: string;
    target?: string;
    outputKey?: string;
    conversionFunction?: string | null;
  };

  console.log('🔄 Converting edge:', {
    input: apiEdge,
    type: typeof apiEdge,
    keys: Object.keys(apiEdge),
    from_node: edge.from_node,
    to_node: edge.to_node,
  });

  // Extract fields with fallbacks for different possible field names
  const fromNode = edge.from_node || edge.fromNode || edge.source;
  const toNode = edge.to_node || edge.toNode || edge.target;
  const outputKey = edge.output_key || edge.outputKey || 'result';
  const conversionFunction = edge.conversion_function || edge.conversionFunction || null;

  if (!fromNode || !toNode) {
    console.error('❌ Missing from_node or to_node in edge:', apiEdge);
  }

  const edgeResult: EditorWorkflowEdge = {
    id: edge.id || `${fromNode}-${toNode}`,
    // React Flow format (REQUIRED for rendering)
    source: fromNode || '',
    target: toNode || '',
    type: 'default',
    sourceHandle: null,
    targetHandle: null,
    // Store backend Connection fields in data for round-trip conversion
    data: {
      from_node: fromNode || '',
      to_node: toNode || '',
      output_key: outputKey,
      conversion_function: conversionFunction,
    },
  };

  console.log('✅ Converted edge result:', {
    id: edgeResult.id,
    source: edgeResult.source,
    target: edgeResult.target,
    hasSource: !!edgeResult.source,
    hasTarget: !!edgeResult.target,
  });

  return edgeResult;
}

/**
 * Convert editor workflow edge to API workflow edge
 * Maps React Flow Edge format to backend Connection format
 */
export function editorEdgeToApiEdge(editorEdge: EditorWorkflowEdge): ApiWorkflowEdge {
  // Extract backend fields from data object (where we store them)
  const edgeData = editorEdge.data || {
    from_node: editorEdge.source,
    to_node: editorEdge.target,
    output_key: 'result',
    conversion_function: null,
  };

  return {
    id: editorEdge.id,
    from_node: edgeData.from_node,
    to_node: edgeData.to_node,
    output_key: edgeData.output_key,
    conversion_function: edgeData.conversion_function || null,
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
    created_at: number; // epoch ms
    updated_at: number; // epoch ms
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
    let template =
      templateMap.get(`${apiNode.type}_${apiNode.subtype}`) ||
      templateMap.get(`${apiNode.type}:${apiNode.subtype}`) ||
      templateMap.get(apiNode.type as string) ||
      templateMap.get(apiNode.id);

    // If not found, try canonical->alias mapping for subtype
    if (!template && apiNode.type && apiNode.subtype) {
      const typeKey = String(apiNode.type) as keyof typeof NodeSubtypeCanonicalToAlias;
      const aliasSubtype = NodeSubtypeCanonicalToAlias[typeKey]?.[String(apiNode.subtype)];
      if (aliasSubtype) {
        template =
          templateMap.get(`${apiNode.type}_${aliasSubtype}`) ||
          templateMap.get(`${apiNode.type}:${aliasSubtype}`);
      }
    }

    const editorNode = apiNodeToEditorNode(apiNode, template);
    if (editorNode) {
      nodes.push(editorNode);
    }
  });

  // Convert connections to edges
  const edges: EditorWorkflowEdge[] = [];

  console.log('🔗 Processing connections:', {
    hasConnections: !!apiWorkflow.connections,
    isArray: Array.isArray(apiWorkflow.connections),
    connectionsCount: Array.isArray(apiWorkflow.connections) ? apiWorkflow.connections.length : 0,
    connections: apiWorkflow.connections,
  });

  // Backend sends connections as an array of Connection objects
  if (apiWorkflow.connections && Array.isArray(apiWorkflow.connections)) {
    console.log('🔗 Converting', apiWorkflow.connections.length, 'connections to edges...');
    console.log('🔗 First connection raw data:', apiWorkflow.connections[0]);

    const convertedEdges = apiWorkflow.connections.map((conn, index) => {
      console.log(`🔗 Converting connection ${index}:`, {
        id: conn.id,
        from_node: conn.from_node,
        to_node: conn.to_node,
        hasFromNode: 'from_node' in conn,
        hasToNode: 'to_node' in conn,
        keys: Object.keys(conn),
      });
      return apiEdgeToEditorEdge(conn);
    });

    edges.push(...convertedEdges);
    console.log('✅ Converted connections to edges:', edges.length, 'edges created');
    console.log('✅ First converted edge:', edges[0]);
  } else {
    console.warn('⚠️ No connections array found in API workflow data');
  }

  // Add edges for attached nodes (AI_AGENT -> TOOL/MEMORY relationships)
  console.log('🔗 Processing attached nodes...');
  apiWorkflow.nodes.forEach((apiNode) => {
    if (apiNode.attached_nodes && Array.isArray(apiNode.attached_nodes)) {
      console.log(`🔗 Node ${apiNode.id} has ${apiNode.attached_nodes.length} attached nodes:`, apiNode.attached_nodes);

      // Get AI_AGENT node position
      const aiAgentPosition = apiNode.position || { x: 0, y: 0 };

      apiNode.attached_nodes.forEach((attachedNodeId) => {
        // Find the attached node to determine its position
        const attachedNode = apiWorkflow.nodes.find(node => node.id === attachedNodeId);
        const attachedPosition = attachedNode?.position || { x: 0, y: 0 };

        // Determine which handles to use based on vertical position
        // If attached node is ABOVE AI_AGENT: use attached node's BOTTOM -> AI_AGENT's TOP
        // If attached node is BELOW AI_AGENT: use attached node's TOP -> AI_AGENT's BOTTOM
        const isAbove = attachedPosition.y < aiAgentPosition.y;
        const sourceHandle = isAbove ? 'attachment-bottom' : 'attachment-top';
        const targetHandle = isAbove ? 'attachment-top' : 'attachment-bottom';

        console.log(`🔗 Attached node ${attachedNodeId} position:`, attachedPosition, 'AI_AGENT position:', aiAgentPosition, `${isAbove ? 'ABOVE' : 'BELOW'}`, 'Using handles:', sourceHandle, '->', targetHandle);

        // Create edge from attached node to AI_AGENT node
        const attachmentEdge: EditorWorkflowEdge = {
          id: `attachment_${attachedNodeId}_${apiNode.id}`,
          source: attachedNodeId,
          target: apiNode.id,
          type: 'default',
          sourceHandle: sourceHandle,
          targetHandle: targetHandle,
          // Mark this as an attachment edge with special styling
          style: {
            strokeWidth: 2,
            stroke: '#8b5cf6', // Purple color for attachment edges
            strokeDasharray: '5,5' // Dashed line to distinguish from regular connections
          },
          animated: true,
          data: {
            from_node: attachedNodeId,
            to_node: apiNode.id,
            output_key: 'attachment',
            conversion_function: null,
            isAttachment: true, // Flag to identify attachment edges
          },
        };
        edges.push(attachmentEdge);
        console.log(`✅ Created attachment edge: ${attachedNodeId} -> ${apiNode.id} (${sourceHandle} -> ${targetHandle})`);
      });
    }
  });

  // If no edges were found, try to infer connections from node positions (workflow sequence)
  if (edges.length === 0 && nodes.length > 1) {
    // Sort nodes by x position to infer flow
    const sortedNodes = [...nodes].sort((a, b) => a.position.x - b.position.x);

    // Create sequential connections for nodes at similar y-positions
    for (let i = 0; i < sortedNodes.length - 1; i++) {
      const currentNode = sortedNodes[i];
      const nextNode = sortedNodes[i + 1];

      // Only connect if nodes are roughly at the same vertical level (within 100px)
      if (Math.abs(currentNode.position.y - nextNode.position.y) < 100) {
        edges.push({
          id: `${currentNode.id}-${nextNode.id}`,
          source: currentNode.id,
          target: nextNode.id,
          sourceHandle: 'output_0',
          targetHandle: 'input_0',
          type: 'default',
        });
      }
    }
  }

  // Debug: Log the conversion results
  console.log('Workflow conversion:', {
    inputConnections: apiWorkflow.connections,
    outputEdges: edges,
    edgeCount: edges.length,
    nodeCount: nodes.length,
    edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target })),
  });

  // Extract metadata - check both root level and nested metadata object
  const workflowWithMetadata = apiWorkflow as typeof apiWorkflow & { metadata?: { id?: string; name?: string; description?: string; version?: number | string; created_at?: string | number; updated_at?: string | number; tags?: string[] } };
  const workflowMetadata = workflowWithMetadata.metadata || {};
  const toMs = (v: unknown): number => {
    if (v === null || v === undefined) return Date.now();
    if (typeof v === 'number') return v < 1_000_000_000_000 ? v * 1000 : v;
    if (typeof v === 'string') {
      const s = v.trim();
      if (/^\d+$/.test(s)) {
        const iv = parseInt(s, 10);
        return iv < 1_000_000_000_000 ? iv * 1000 : iv;
      }
      const t = new Date(s).getTime();
      return isNaN(t) ? Date.now() : t;
    }
    return Date.now();
  };
  const metadata = {
    id: apiWorkflow.id || workflowMetadata.id || '',
    name: apiWorkflow.name || workflowMetadata.name || 'Untitled Workflow',
    description: apiWorkflow.description || workflowMetadata.description || '',
    version: String(apiWorkflow.version || workflowMetadata.version || '1'),
    created_at: toMs(apiWorkflow.created_at || workflowMetadata.created_at || Date.now()),
    updated_at: toMs(apiWorkflow.updated_at || workflowMetadata.updated_at || Date.now()),
    tags: apiWorkflow.tags || workflowMetadata.tags || [],
  };

  console.log('[Workflow Converter] Extracted metadata:', {
    id: metadata.id,
    name: metadata.name,
    hasId: !!metadata.id,
    apiWorkflowId: apiWorkflow.id,
    nestedMetadataId: workflowMetadata.id,
    structure: apiWorkflow.id ? 'flat' : (workflowMetadata.id ? 'nested' : 'missing'),
  });

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

  // Build connections object (n8n style) from edges
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

  // Build connections object (n8n style) from edges for update
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
