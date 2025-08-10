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
        type: 'smoothstep',
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
      created_at: Date.now(),
      updated_at: Date.now(),
      tags: [],
    });
  }, [setNodes, setEdges, setMetadata]);

  // Export workflow
  const exportWorkflow = useCallback(() => {
    return {
      metadata,
      nodes: nodes.map((node) => ({
        id: node.id,
        type: node.data.template.node_type,
        subtype: node.data.template.node_subtype,
        position: node.position,
        parameters: node.data.parameters,
      })),
      edges: edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
      })),
    };
  }, [nodes, edges, metadata]);

  // Import workflow
  const importWorkflow = useCallback(
    (workflowData: Workflow, templates: NodeTemplate[]) => {
      // Clear existing workflow
      clearWorkflow();

      // Use the converter to transform API format to editor format
      const { nodes: editorNodes, edges: editorEdges, metadata } = apiWorkflowToEditor(workflowData, templates);

      // Set metadata
      setMetadata(metadata);

      // Set nodes and edges
      setNodes(editorNodes);
      setEdges(editorEdges);
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