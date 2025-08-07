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
import type { WorkflowEdge } from '@/types/workflow-editor';
import type { Workflow, WorkflowNode } from '@/types/workflow';

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

      const newEdge: WorkflowEdge = {
        id: `${connection.source}-${connection.target}`,
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

      // Set metadata from workflow
      setMetadata({
        name: workflowData.name || 'Untitled Workflow',
        description: workflowData.description || '',
        version: workflowData.version?.toString() || '1',
        tags: workflowData.tags || [],
      });

      // Create template map for quick lookup
      const templateMap = new Map<string, NodeTemplate>();
      templates.forEach((template) => {
        const key = `${template.node_type}_${template.node_subtype}`;
        templateMap.set(key, template);
      });

      // Import nodes
      const newNodes = workflowData.nodes.map((node: WorkflowNode) => {
        const templateKey = `${node.type}_${node.subtype}`;
        const template = templateMap.get(templateKey);

        if (!template) {
          console.error(`Template not found for ${templateKey}`);
          return null;
        }

        return {
          id: node.id,
          type: 'custom',
          position: node.position,
          data: {
            label: template.name,
            template,
            parameters: { ...template.default_parameters, ...node.parameters },
            status: 'idle',
          },
        };
      }).filter(Boolean);

      setNodes(newNodes);

      // Import edges
      if (workflowData.edges) {
        setEdges(workflowData.edges);
      }
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