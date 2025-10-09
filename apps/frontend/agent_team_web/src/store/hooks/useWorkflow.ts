import { useAtom, useSetAtom, useAtomValue } from 'jotai';
import { useCallback } from 'react';
import type { Connection } from 'reactflow';
import {
  workflowNodesAtom,
  workflowEdgesAtom,
  workflowMetadataAtom,
  addNodeAtom,
  updateNodeParametersAtom,
  updateNodeDataAtom,
  deleteNodeAtom,
  selectedNodeAtom,
  nodeCountByTypeAtom,
  workflowValidationAtom,
} from '../atoms/workflow';
import type { NodeTemplate } from '@/types/node-template';
import type {
  WorkflowEdge as EditorWorkflowEdge
} from '@/types/workflow-editor';
import type { Workflow } from '@/types/workflow';
import {
  apiWorkflowToEditor,
  generateEdgeId
} from '@/utils/workflow-converter';

export const useWorkflow = () => {
  const [nodes, setNodes] = useAtom(workflowNodesAtom);
  const [edges, setEdges] = useAtom(workflowEdgesAtom);
  const [metadata, setMetadata] = useAtom(workflowMetadataAtom);

  const addNode = useSetAtom(addNodeAtom);
  const updateNodeParameters = useSetAtom(updateNodeParametersAtom);
  const updateNodeData = useSetAtom(updateNodeDataAtom);
  const deleteNode = useSetAtom(deleteNodeAtom);

  const selectedNode = useAtomValue(selectedNodeAtom);
  const nodeCountByType = useAtomValue(nodeCountByTypeAtom);
  const validation = useAtomValue(workflowValidationAtom);

  // Add edge
  const addEdge = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;

      const newEdge: EditorWorkflowEdge = {
        id: generateEdgeId(connection.source, connection.target),
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        type: 'default',
        animated: true,
        style: { strokeWidth: 2, stroke: '#6b7280' },
      };

      setEdges((draft) => {
        // Check if edge already exists
        const exists = draft.some(
          (e) => e.source === newEdge.source && e.target === newEdge.target
        );
        if (!exists) {
          draft.push(newEdge);
        }
      });
    },
    [setEdges]
  );

  // Remove edge
  const removeEdge = useCallback(
    (edgeId: string) => {
      setEdges((draft) => {
        return draft.filter((e) => e.id !== edgeId);
      });
    },
    [setEdges]
  );

  // Clear workflow
  const clearWorkflow = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setMetadata({
      id: '',
      name: 'Untitled Workflow',
      description: '',
      version: '1.0.0',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      tags: [],
    });
  }, [setNodes, setEdges, setMetadata]);

  // Export workflow
  const exportWorkflow = useCallback(() => {
    console.log('[exportWorkflow] Starting export with nodes:', nodes.length);

    // Export nodes with all original data preserved
    const exportedNodes = nodes.map((node) => {
      console.log(`[exportWorkflow] Processing node ${node.id}:`, {
        type: node.data.template.node_type,
        subtype: node.data.template.node_subtype,
        hasOriginalData: !!node.data.originalData,
        currentParameters: node.data.parameters,
        originalConfigurations: node.data.originalData?.configurations,
      });

      // If we have original node data, use it as base and update position
      if (node.data.originalData) {
        const exportedNode = {
          ...node.data.originalData,
          name: node.data.label || node.data.originalData.name,
          description: node.data.description || node.data.originalData.description,
          position: node.position, // Update position from editor
          configurations: {
            ...(node.data.originalData?.configurations || {}),
            ...node.data.parameters, // Merge any updated parameters
          },
        };
        console.log(`[exportWorkflow] Exported node ${node.id} with merged configurations:`, exportedNode.configurations);
        return exportedNode;
      }

      // Fallback: construct node data from template (clean backend format)
      const exportedNode = {
        id: node.id,
        name: node.data.label || node.id,
        description: node.data.description || node.data.template.description,
        type: node.data.template.node_type,
        subtype: node.data.template.node_subtype,
        position: node.position,
        configurations: node.data.parameters || {},
        input_params: {},
        output_params: {},
      };
      console.log(`[exportWorkflow] Exported node ${node.id} (from template) with configurations:`, exportedNode.configurations);
      return exportedNode;
    });

    // Export edges in backend Connection format (exclude attachment edges)
    // Attachment edges are represented in the attached_nodes field of AI_AGENT nodes
    const exportedEdges = edges
      .filter((edge) => !edge.data?.isAttachment) // Filter out attachment edges
      .map((edge) => ({
        id: edge.id,
        from_node: edge.data?.from_node || edge.source,
        to_node: edge.data?.to_node || edge.target,
        output_key: edge.data?.output_key || 'result',
        conversion_function: edge.data?.conversion_function || null,
      }));

    console.log('Exporting workflow - nodes:', exportedNodes.length, 'edges:', exportedEdges.length, '(excluded attachment edges)');
    console.log('Exported edges:', exportedEdges);

    return {
      metadata,
      nodes: exportedNodes,
      connections: exportedEdges, // Backend uses 'connections' not 'edges'
    };
  }, [nodes, edges, metadata]);

  // Import workflow
  const importWorkflow = useCallback(
    (workflowData: Workflow, templates: NodeTemplate[]) => {
      console.log('[importWorkflow] Starting import with workflow:', {
        hasId: !!workflowData.id,
        id: workflowData.id,
        name: workflowData.name,
      });

      // Clear existing workflow
      clearWorkflow();

      // Use the converter to transform API format to editor format
      const { nodes: editorNodes, edges: editorEdges, metadata } = apiWorkflowToEditor(workflowData, templates);

      console.log('[importWorkflow] Converter returned metadata:', {
        id: metadata.id,
        name: metadata.name,
        hasId: !!metadata.id,
      });

      // Set metadata
      setMetadata(metadata);

      console.log('[importWorkflow] Metadata set in store:', metadata);

      // Set nodes and edges
      setNodes(editorNodes);
      setEdges(editorEdges);

      console.log('[importWorkflow] Import complete - Workflow ID:', metadata.id);
    },
    [clearWorkflow, setMetadata, setNodes, setEdges]
  );

  return {
    // State
    nodes,
    edges,
    metadata,
    selectedNode,
    nodeCountByType,
    validation,

    // Actions
    addNode,
    updateNodeParameters,
    updateNodeData,
    deleteNode,
    addEdge,
    removeEdge,
    clearWorkflow,
    exportWorkflow,
    importWorkflow,

    // Setters
    setNodes,
    setEdges,
    setMetadata,
  };
};
