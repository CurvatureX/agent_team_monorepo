"use client";

import React, { useCallback, useRef, useEffect, useMemo, DragEvent } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  MiniMap,
  Background,
  BackgroundVariant,
  useReactFlow,
  Node,
  Connection,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { cn } from '@/lib/utils';
import { useWorkflow, useEditorUI, useNodeTemplates } from '@/store/hooks';
import { CustomNode } from './CustomNode';
import { CanvasControls } from './CanvasControls';
import type { Workflow } from '@/types/workflow';
import type { WorkflowNode, WorkflowEdge } from '@/types/workflow-editor';
import type { NodeTemplate } from '@/types/node-template';
import { isValidConnection } from '@/utils/nodeHelpers';

interface EnhancedWorkflowCanvasProps {
  workflow?: Workflow;
  onWorkflowChange?: (workflow: Workflow) => void;
  onSave?: () => void;
  isSaving?: boolean;
  readOnly?: boolean;
  className?: string;
}

// Define node types
const nodeTypes: NodeTypes = {
  custom: CustomNode,
};

const EnhancedWorkflowCanvasContent: React.FC<EnhancedWorkflowCanvasProps> = ({
  workflow,
  onSave,
  isSaving = false,
  readOnly = false,
  className,
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { project } = useReactFlow();
  
  const {
    nodes,
    edges,
    setNodes,
    setEdges,
    addNode,
    addEdge,
    deleteNode,
    importWorkflow,
    // exportWorkflow,
  } = useWorkflow();
  
  const {
    showGrid,
    showMinimap,
    selectNode,
    clearSelection,
    isDraggingNode,
    setIsDraggingNode,
  } = useEditorUI();
  
  const { templates } = useNodeTemplates();

  // Import workflow data on mount if provided
  useEffect(() => {
    if (workflow && templates.length > 0) {
      importWorkflow(workflow, templates);
    }
  }, [workflow, templates, importWorkflow]);

  // Handle save with current editor state
  const handleSaveWithCurrentState = useCallback(() => {
    if (onSave) {
      onSave();
    }
  }, [onSave]);

  // Handle node changes
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (readOnly) return;
      
      setNodes((nds) => applyNodeChanges(changes, nds) as WorkflowNode[]);
    },
    [setNodes, readOnly]
  );

  // Handle edge changes
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (readOnly) return;
      
      setEdges((eds) => applyEdgeChanges(changes, eds) as WorkflowEdge[]);
    },
    [setEdges, readOnly]
  );

  // Handle connections
  const onConnect = useCallback(
    (connection: Connection) => {
      if (readOnly) return;
      
      // Validate connection
      const sourceNode = nodes.find((n) => n.id === connection.source);
      const targetNode = nodes.find((n) => n.id === connection.target);
      
      if (!sourceNode || !targetNode) return;
      
      const isValid = isValidConnection(
        sourceNode.data.template.node_type,
        targetNode.data.template.node_type
      );
      
      if (isValid) {
        addEdge(connection);
      }
    },
    [nodes, addEdge, readOnly]
  );

  // Handle node click
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  // Handle pane click
  const onPaneClick = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  // Handle drag over
  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  // Handle drop
  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      if (!reactFlowWrapper.current || readOnly) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const data = event.dataTransfer.getData('application/reactflow');

      if (!data) return;

      try {
        const { type, template } = JSON.parse(data) as { 
          type: string; 
          template: NodeTemplate;
        };

        if (type !== 'nodeTemplate') return;

        const position = project({
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top,
        });

        console.log('Adding node:', { template, position });
        const nodeId = addNode({ template, position });
        console.log('Node added with ID:', nodeId);
      } catch (error) {
        console.error('Error handling drop:', error);
      } finally {
        setIsDraggingNode(false);
      }
    },
    [project, addNode, readOnly, setIsDraggingNode]
  );

  // Handle node context menu (right-click)
  const onNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      event.preventDefault();
      if (readOnly) return;
      
      // Could show a context menu here
      const shouldDelete = window.confirm(`Delete node "${node.data.label}"?`);
      if (shouldDelete) {
        deleteNode(node.id);
      }
    },
    [deleteNode, readOnly]
  );

  // Edge styles
  const defaultEdgeOptions = useMemo(
    () => ({
      type: 'default',
      animated: true,
      style: { 
        strokeWidth: 2, 
        stroke: '#6b7280',
      },
    }),
    []
  );

  return (
    <div 
      ref={reactFlowWrapper}
      className={cn('w-full h-full', className)}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onNodeContextMenu={onNodeContextMenu}
        onPaneClick={onPaneClick}
        onDragOver={onDragOver}
        onDrop={onDrop}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        deleteKeyCode={readOnly ? null : 'Delete'}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={!readOnly}
        className={cn(
          isDraggingNode && 'ring-2 ring-primary ring-offset-2',
          'transition-all duration-200'
        )}
      >
        {showGrid && (
          <Background 
            variant={BackgroundVariant.Dots} 
            gap={12} 
            size={1}
            color="#333"
          />
        )}
        
        <CanvasControls 
          readOnly={readOnly} 
          onSave={handleSaveWithCurrentState}
          isSaving={isSaving}
        />
        
        {showMinimap && (
          <MiniMap
            nodeStrokeColor={(n: Node) => {
              const node = n as WorkflowNode;
              const colorMap: Record<string, string> = {
                TRIGGER: 'rgb(16, 185, 129)',
                AI_AGENT: 'rgb(99, 102, 241)',
                ACTION: 'rgb(245, 158, 11)',
                FLOW: 'rgb(139, 92, 246)',
                HUMAN_IN_THE_LOOP: 'rgb(236, 72, 153)',
                MEMORY: 'rgb(249, 115, 22)',
                TOOL: 'rgb(6, 182, 212)',
              };
              return colorMap[node.data.template.node_type] || 'rgb(107, 114, 128)';
            }}
            nodeColor={(n: Node) => {
              const node = n as WorkflowNode;
              const colorMap: Record<string, string> = {
                TRIGGER: 'rgba(16, 185, 129, 0.1)',
                AI_AGENT: 'rgba(99, 102, 241, 0.1)',
                ACTION: 'rgba(245, 158, 11, 0.1)',
                FLOW: 'rgba(139, 92, 246, 0.1)',
                HUMAN_IN_THE_LOOP: 'rgba(236, 72, 153, 0.1)',
                MEMORY: 'rgba(249, 115, 22, 0.1)',
                TOOL: 'rgba(6, 182, 212, 0.1)',
              };
              return colorMap[node.data.template.node_type] || 'rgba(107, 114, 128, 0.1)';
            }}
            pannable
            zoomable
            className="bg-background border border-border rounded-lg shadow-lg"
          />
        )}
      </ReactFlow>
    </div>
  );
};

export const EnhancedWorkflowCanvas: React.FC<EnhancedWorkflowCanvasProps> = (props) => {
  return (
    <ReactFlowProvider>
      <EnhancedWorkflowCanvasContent {...props} />
    </ReactFlowProvider>
  );
};