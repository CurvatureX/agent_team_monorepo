"use client";

import React, { useCallback, useRef, useEffect, useMemo, DragEvent, useState } from 'react';
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
import { ExecutionStatusPanel } from '../ExecutionStatusPanel';
import { RunWorkflowDialog } from '../RunWorkflowDialog';
import type { Workflow } from '@/types/workflow';
import type { WorkflowNode, WorkflowEdge } from '@/types/workflow-editor';
import type { NodeTemplate } from '@/types/node-template';
import { isValidConnection, humanizeKey } from '@/utils/nodeHelpers';
import { useWorkflowExecution, useExecutionStatus, useExecutionCancel, type ExecutionStatus, type ExecutionRequest } from '@/lib/api/hooks/useExecutionApi';
import { useWorkflowActions } from '@/lib/api/hooks/useWorkflowsApi';
import { useToast } from '@/hooks/use-toast';
import { useAtomValue } from 'jotai';
import { workflowValidationAtom } from '@/store/atoms/workflow';

interface EnhancedWorkflowCanvasProps {
  workflow?: Workflow;
  onWorkflowChange?: (workflow: Workflow) => void;
  onSave?: () => void;
  isSaving?: boolean;
  readOnly?: boolean;
  className?: string;
  onExecute?: (workflowId: string) => void;
  onToggleFullscreen?: () => void;
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
  onExecute,
  onToggleFullscreen,
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { project } = useReactFlow();
  const { toast } = useToast();

  // Workflow validation
  const workflowValidation = useAtomValue(workflowValidationAtom);

  // Execution state
  const { executeWorkflow, isExecuting, executionId } = useWorkflowExecution();
  const { cancelExecution } = useExecutionCancel();
  const { deployWorkflow } = useWorkflowActions();
  const [executionStatus, setExecutionStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [isRunDialogOpen, setIsRunDialogOpen] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);

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
      console.log('[WorkflowCanvas] Importing workflow:', {
        id: workflow.id,
        name: workflow.name,
        hasNodes: !!workflow.nodes,
        nodesCount: workflow.nodes?.length,
        hasConnections: !!workflow.connections,
      });
      importWorkflow(workflow, templates);
    }
  }, [workflow, templates, importWorkflow]);

  // Update node execution status based on execution results
  const updateNodeExecutionStatus = useCallback((executionStatus: ExecutionStatus) => {
    // Handle both node_executions array and run_data.node_results object
    const nodeResults = executionStatus?.run_data?.node_results || {};
    const nodeExecutions = executionStatus?.node_executions || [];

    // If we have run_data.node_results (backend format)
    if (Object.keys(nodeResults).length > 0) {
      setNodes((currentNodes) => {
        return currentNodes.map((node) => {
          // Check if this node has results
          const nodeResult = nodeResults[node.id];

          if (nodeResult) {
            console.log(`Updating node ${node.id} status to:`, nodeResult.status);
            return {
              ...node,
              data: {
                ...node.data,
                status: nodeResult.status === 'SUCCESS' ? 'success' :
                        nodeResult.status === 'FAILED' || nodeResult.status === 'ERROR' ? 'error' :
                        nodeResult.status === 'RUNNING' ? 'running' : 'idle'
              }
            };
          }

          return node;
        });
      });
    }
    // Fallback to node_executions array format
    else if (nodeExecutions.length > 0) {
      setNodes((currentNodes) => {
        return currentNodes.map((node) => {
          const nodeExecution = nodeExecutions.find(
            (ne) => ne.node_id === node.id
          );

          if (nodeExecution) {
            return {
              ...node,
              data: {
                ...node.data,
                status: nodeExecution.status === 'COMPLETED' || nodeExecution.status === 'SUCCESS' ? 'success' :
                        nodeExecution.status === 'FAILED' || nodeExecution.status === 'ERROR' ? 'error' :
                        nodeExecution.status === 'RUNNING' ? 'running' : 'idle'
              }
            };
          }

          return node;
        });
      });
    }
  }, [setNodes]);

  // Clear node execution status
  const clearNodeExecutionStatus = useCallback(() => {
    setNodes((currentNodes) => {
      return currentNodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          status: 'idle'
        }
      }));
    });
  }, [setNodes]);

  // Calculate duration helper
  const calculateDuration = (start?: string, end?: string) => {
    if (!start || !end) return 'N/A';
    const duration = new Date(end).getTime() - new Date(start).getTime();
    const seconds = Math.floor(duration / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  // Use execution status polling
  const { status, isPolling } = useExecutionStatus(executionId, {
    interval: 2000,
    maxDuration: 600000, // 10 minutes max
    enabled: !!executionId && executionStatus === 'running',
    onComplete: (status) => {
      console.log('Execution completed with status:', status);
      setExecutionStatus('completed');
      updateNodeExecutionStatus(status);

      // Calculate duration for display
      let duration = 'N/A';
      if (status.start_time && status.end_time) {
        // Handle both timestamp formats (unix timestamp or ISO string)
        const start = typeof status.start_time === 'number'
          ? status.start_time * 1000
          : new Date(status.start_time).getTime();
        const end = typeof status.end_time === 'number'
          ? status.end_time * 1000
          : new Date(status.end_time).getTime();
        duration = calculateDuration(new Date(start).toISOString(), new Date(end).toISOString());
      }

      toast({
        title: "Workflow Execution Completed",
        description: `Execution finished successfully in ${duration}`,
      });
    },
    onError: (error) => {
      console.error('Execution failed:', error);
      setExecutionStatus('failed');
      toast({
        title: "Workflow Execution Failed",
        description: error,
        variant: "destructive",
      });
    },
    onTimeout: () => {
      console.warn('Execution timeout');
      setExecutionStatus('failed');
      toast({
        title: "Execution Timeout",
        description: "The workflow execution took too long and was stopped",
        variant: "destructive",
      });
    },
  });

  // Update nodes whenever status changes during polling
  useEffect(() => {
    if (status) {
      console.log('Received execution status update:', {
        status: status.status,
        isPolling,
        hasNodeResults: !!(status.run_data?.node_results),
        nodeResultsCount: Object.keys(status.run_data?.node_results || {}).length
      });

      if (isPolling) {
        updateNodeExecutionStatus(status);
      }
    }
  }, [status, isPolling, updateNodeExecutionStatus]);

  // Handle save with current editor state
  const handleSaveWithCurrentState = useCallback(() => {
    if (onSave) {
      onSave();
    }
  }, [onSave]);

  // Handle workflow execution - opens the run dialog
  const handleExecute = useCallback(() => {
    if (!workflow?.id) {
      toast({
        title: "Cannot Execute",
        description: "Please save the workflow before executing",
        variant: "destructive",
      });
      return;
    }

    // Validate all nodes have required fields filled
    if (workflowValidation.invalidNodes.length > 0) {
      toast({
        title: "Missing Required Fields",
        description: (
          <div className="space-y-2">
            <p>Please fill in all required fields before running:</p>
            <ul className="list-disc list-inside space-y-1">
              {workflowValidation.invalidNodes.map(node => {
                const fields = node.missingFields.map(f => humanizeKey(f)).join(', ');
                return (
                  <li key={node.id}>
                    <span className="font-medium">{node.name}:</span> {fields}
                  </li>
                );
              })}
            </ul>
          </div>
        ),
        variant: "destructive",
      });
      return;
    }

    setIsRunDialogOpen(true);
  }, [workflow, workflowValidation, toast]);

  // Handle workflow deployment
  const handleDeploy = useCallback(async () => {
    if (!workflow?.id) {
      toast({
        title: "Cannot Deploy",
        description: "Please save the workflow before deploying",
        variant: "destructive",
      });
      return;
    }

    // Validate all nodes have required fields filled
    if (workflowValidation.invalidNodes.length > 0) {
      toast({
        title: "Missing Required Fields",
        description: (
          <div className="space-y-2">
            <p>Please fill in all required fields before deploying:</p>
            <ul className="list-disc list-inside space-y-1">
              {workflowValidation.invalidNodes.map(node => {
                const fields = node.missingFields.map(f => humanizeKey(f)).join(', ');
                return (
                  <li key={node.id}>
                    <span className="font-medium">{node.name}:</span> {fields}
                  </li>
                );
              })}
            </ul>
          </div>
        ),
        variant: "destructive",
      });
      return;
    }

    setIsDeploying(true);
    try {
      await deployWorkflow(workflow.id);
      toast({
        title: "Deployment Successful",
        description: "Workflow has been deployed successfully",
      });
    } catch (error) {
      console.error('Deploy error:', error);
      toast({
        title: "Deployment Failed",
        description: error instanceof Error ? error.message : "Failed to deploy workflow",
        variant: "destructive",
      });
    } finally {
      setIsDeploying(false);
    }
  }, [workflow, workflowValidation, deployWorkflow, toast]);

  // Handle actual workflow execution with parameters
  const handleRunWorkflow = useCallback(async (request: ExecutionRequest) => {
    if (!workflow?.id) return;

    try {
      // Clear previous execution status from nodes
      clearNodeExecutionStatus();
      setExecutionStatus('running');
      const execId = await executeWorkflow(workflow.id, request);

      toast({
        title: "Workflow Execution Started",
        description: `Execution ID: ${execId}`,
      });

      // Optional: Call parent callback
      if (onExecute) {
        onExecute(workflow.id);
      }
    } catch (error) {
      const err = error as Error;
      setExecutionStatus('failed');
      toast({
        title: "Failed to Execute",
        description: err.message || "An error occurred while starting the execution",
        variant: "destructive",
      });
    }
  }, [workflow, executeWorkflow, toast, onExecute, clearNodeExecutionStatus]);

  // Handle stop execution
  const handleStopExecution = useCallback(async () => {
    if (!executionId) return;

    try {
      await cancelExecution(executionId);
      setExecutionStatus('idle');
      clearNodeExecutionStatus(); // Clear node status when stopping
      toast({
        title: "Execution Cancelled",
        description: "The workflow execution has been stopped",
      });
    } catch (error) {
      const err = error as Error;
      toast({
        title: "Failed to Cancel",
        description: err.message || "Could not cancel the execution",
        variant: "destructive",
      });
    }
  }, [executionId, cancelExecution, toast, clearNodeExecutionStatus]);

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
          onDeploy={handleDeploy}
          isDeploying={isDeploying}
          onExecute={handleExecute}
          onStopExecution={handleStopExecution}
          isExecuting={isExecuting || isPolling}
          executionStatus={executionStatus}
          onToggleFullscreen={onToggleFullscreen}
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

      {/* Execution Status Panel */}
      {(executionId || isPolling) && (
        <ExecutionStatusPanel
          status={status}
          isPolling={isPolling}
          onClose={() => {
            // Only allow closing when not actively running
            if (executionStatus !== 'running') {
              setExecutionStatus('idle');
              clearNodeExecutionStatus();
            }
          }}
        />
      )}

      {/* Run Workflow Dialog */}
      <RunWorkflowDialog
        open={isRunDialogOpen}
        onOpenChange={setIsRunDialogOpen}
        workflow={workflow}
        onRun={handleRunWorkflow}
        isExecuting={isExecuting}
      />
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
