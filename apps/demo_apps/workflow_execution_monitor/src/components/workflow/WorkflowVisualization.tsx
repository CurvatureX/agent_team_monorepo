import React, { useMemo, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  MarkerType,
  ReactFlowProvider,
  Handle,
  Position,
  NodeProps,
  OnNodesChange
} from 'reactflow';
import 'reactflow/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Clock,
  CheckCircle,
  AlertCircle,
  Activity,
  Terminal,
  Calendar,
  Bot,
  Zap,
  Wrench,
  X,
  Code2
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import { AIWorker, ExecutionRecord } from '@/types/workflow';
import { TriggerInvocationForm } from '@/components/ui/TriggerInvocationForm';

const nodeTypeIcons = {
  TRIGGER: Calendar,
  AI_AGENT: Bot,
  ACTION: Zap,
  EXTERNAL_ACTION: Zap,
  TOOL: Wrench,
  MEMORY: Clock,
  FLOW: Activity,
  HUMAN_IN_THE_LOOP: CheckCircle
};

const nodeTypeColors = {
  TRIGGER: '#10b981',
  AI_AGENT: '#6366f1',
  ACTION: '#f59e0b',
  EXTERNAL_ACTION: '#f59e0b',
  TOOL: '#8b5cf6',
  MEMORY: '#06b6d4',
  FLOW: '#ec4899',
  HUMAN_IN_THE_LOOP: '#ef4444'
};

const statusConfig = {
  PENDING: { color: 'text-gray-500', bg: 'bg-gray-100' },
  RUNNING: { color: 'text-orange-500', bg: 'bg-orange-100' },
  SUCCESS: { color: 'text-green-500', bg: 'bg-green-100' },
  ERROR: { color: 'text-red-500', bg: 'bg-red-100' },
  SKIPPED: { color: 'text-gray-400', bg: 'bg-gray-100' }
};

interface WorkflowVisualizationProps {
  workflow: AIWorker;
  currentExecution?: ExecutionRecord;
  className?: string;
}

interface NodeDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodeData: any;
  nodeName: string;
  workflowId?: string;
}

// Node Detail Modal Component
const NodeDetailModal: React.FC<NodeDetailModalProps> = ({ isOpen, onClose, nodeData, nodeName, workflowId }) => {
  const [currentTab, setCurrentTab] = useState<'details' | 'trigger'>('details');
  const isTriggerNode = nodeData?.type === 'TRIGGER';

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-card border border-border rounded-lg shadow-lg max-w-4xl max-h-[80vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Modal Header */}
          <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Code2 className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold text-foreground">
                Node Details: {nodeName}
              </h3>
              {isTriggerNode && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                  Trigger Node
                </span>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-accent rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Tab Navigation */}
          {isTriggerNode && workflowId && (
            <div className="flex border-b border-border">
              <button
                onClick={() => setCurrentTab('details')}
                className={clsx(
                  "px-4 py-2 text-sm font-medium transition-colors",
                  currentTab === 'details'
                    ? 'text-primary border-b-2 border-primary bg-primary/5'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                Node Details
              </button>
              <button
                onClick={() => setCurrentTab('trigger')}
                className={clsx(
                  "px-4 py-2 text-sm font-medium transition-colors",
                  currentTab === 'trigger'
                    ? 'text-primary border-b-2 border-primary bg-primary/5'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                Manual Trigger
              </button>
            </div>
          )}

          {/* Modal Content */}
          <div className="p-4 overflow-auto max-h-[calc(80vh-120px)]">
            {currentTab === 'details' ? (
              <pre className="bg-muted p-4 rounded-lg text-sm text-muted-foreground overflow-auto whitespace-pre-wrap">
                {JSON.stringify(nodeData, null, 2)}
              </pre>
            ) : (
              isTriggerNode && workflowId && (
                <TriggerInvocationForm
                  workflowId={workflowId}
                  triggerNodeId={nodeData.id}
                  triggerName={nodeName}
                  triggerType={nodeData.subtype || 'MANUAL'}
                  onSuccess={(result) => {
                    console.log('Trigger invocation successful:', result);
                    // You could add a toast notification here
                  }}
                  onError={(error) => {
                    console.error('Trigger invocation error:', error);
                    // You could add a toast notification here
                  }}
                />
              )
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

// Compact Node Component
const CustomNode = ({ data }: { data: any }) => {
  const IconComponent = nodeTypeIcons[data.type as keyof typeof nodeTypeIcons] || Bot;
  const nodeColor = nodeTypeColors[data.type as keyof typeof nodeTypeColors];
  const isRunning = data.executionStatus === 'RUNNING';
  const isCompleted = data.executionStatus === 'SUCCESS';
  const isFailed = data.executionStatus === 'ERROR';
  const isFirstNode = data.type === 'TRIGGER';
  const isLastNode = data.isLast;

  return (
    <>
      {/* Input handle - all nodes except the first one */}
      {!isFirstNode && (
        <Handle
          type="target"
          position={Position.Left}
          style={{ background: '#6366f1', width: '8px', height: '8px' }}
        />
      )}

      <div
        className={clsx(
          "px-3 py-2 shadow-sm rounded-md bg-card border border-border min-w-[120px] max-w-[160px] cursor-pointer hover:shadow-md transition-shadow",
          isRunning && "ring-1 ring-orange-300 animate-pulse",
          isCompleted && "border-green-300 bg-green-50/50",
          isFailed && "border-red-300 bg-red-50/50"
        )}
        style={{ borderLeftColor: nodeColor, borderLeftWidth: '3px' }}
      >
        <div className="flex items-center gap-2">
          <div
            className="p-1 rounded text-white flex-shrink-0"
            style={{ backgroundColor: nodeColor }}
          >
            <IconComponent className="w-3 h-3" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-xs text-foreground truncate">{data.name || data.type}</div>
          </div>
          {isRunning && <Activity className="w-3 h-3 text-orange-500 animate-spin flex-shrink-0" />}
          {isCompleted && <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />}
          {isFailed && <AlertCircle className="w-3 h-3 text-red-500 flex-shrink-0" />}
        </div>
      </div>

      {/* Output handle - all nodes except the last one */}
      {!isLastNode && (
        <Handle
          type="source"
          position={Position.Right}
          style={{ background: '#6366f1', width: '8px', height: '8px' }}
        />
      )}
    </>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

export const WorkflowVisualization: React.FC<WorkflowVisualizationProps> = ({
  workflow,
  currentExecution,
  className
}) => {
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleNodeClick = (event: React.MouseEvent, node: Node) => {
    event.stopPropagation();
    // Enhance node data with the node ID for trigger invocation
    setSelectedNode({
      ...node,
      data: {
        ...node.data,
        id: node.id
      }
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedNode(null);
  };

  const { nodes, edges } = useMemo(() => {
    // Convert workflow nodes to ReactFlow format
    const reactFlowNodes: Node[] = workflow.graph.map((node, index) => {
      // Check if this node is currently executing
      const nodeExecution = currentExecution?.nodeExecutions?.find(ne => ne.nodeId === node.id);

      return {
        id: node.id,
        type: 'custom',
        position: node.position,
        data: {
          ...node.data,
          type: node.type,
          executionStatus: nodeExecution?.status,
          isLast: false // We'll determine this based on connections
        },
        draggable: false,
      };
    });

    // Generate edges based on actual workflow connections
    const workflowEdges: Edge[] = [];
    const hasIncomingEdge = new Set<string>();

    // Parse connections from the workflow data (if available)
    if (workflow.connections) {
      Object.entries(workflow.connections).forEach(([sourceNodeId, nodeConnections]) => {
        if (nodeConnections && typeof nodeConnections === 'object') {
          // Handle new format: connection_types.main.connections
          const connectionTypes = (nodeConnections as any).connection_types;
          if (connectionTypes && connectionTypes.main && connectionTypes.main.connections) {
            connectionTypes.main.connections.forEach((connection: any, index: number) => {
              if (connection.node) {
                hasIncomingEdge.add(connection.node);
                workflowEdges.push({
                  id: `edge-${sourceNodeId}-${connection.node}-${index}`,
                  source: sourceNodeId,
                  target: connection.node,
                  type: 'smoothstep',
                  markerEnd: {
                    type: MarkerType.ArrowClosed,
                    width: 20,
                    height: 20,
                    color: '#6366f1',
                  },
                  style: {
                    stroke: '#6366f1',
                    strokeWidth: 2,
                  },
                });
              }
            });
          }
          // Handle legacy format: main array directly
          else if ((nodeConnections as any).main && Array.isArray((nodeConnections as any).main)) {
            (nodeConnections as any).main.forEach((connection: any, index: number) => {
              if (connection.node) {
                hasIncomingEdge.add(connection.node);
                workflowEdges.push({
                  id: `edge-${sourceNodeId}-${connection.node}-${index}`,
                  source: sourceNodeId,
                  target: connection.node,
                  type: 'smoothstep',
                  markerEnd: {
                    type: MarkerType.ArrowClosed,
                    width: 20,
                    height: 20,
                    color: '#6366f1',
                  },
                  style: {
                    stroke: '#6366f1',
                    strokeWidth: 2,
                  },
                });
              }
            });
          }
        }
      });
    }

    // If no connections found, fall back to sequential flow
    if (workflowEdges.length === 0) {
      for (let i = 0; i < workflow.graph.length - 1; i++) {
        const sourceNode = workflow.graph[i];
        const targetNode = workflow.graph[i + 1];

        if (sourceNode?.id && targetNode?.id) {
          hasIncomingEdge.add(targetNode.id);
          workflowEdges.push({
            id: `edge-${i}`,
            source: sourceNode.id,
            target: targetNode.id,
            type: 'smoothstep',
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 20,
              height: 20,
              color: '#6366f1',
            },
            style: {
              stroke: '#6366f1',
              strokeWidth: 2,
            },
          });
        }
      }
    }

    // Update nodes to mark last nodes (nodes with no outgoing connections)
    const updatedNodes = reactFlowNodes.map(node => ({
      ...node,
      data: {
        ...node.data,
        isLast: !workflowEdges.some(edge => edge.source === node.id)
      }
    }));

    return { nodes: updatedNodes, edges: workflowEdges };
  }, [workflow.graph, workflow.connections, currentExecution]);

  const nodeColor = (node: Node) => {
    return nodeTypeColors[node.data.type as keyof typeof nodeTypeColors] || '#6b7280';
  };

  return (
    <div className={clsx("flex flex-col", className)}>
      {/* Compact Workflow Graph */}
      <div className="h-96 bg-card border border-border rounded-lg overflow-hidden">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{
              padding: 0.2,
              includeHiddenNodes: false,
            }}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={true}
            onNodeClick={handleNodeClick}
            zoomOnScroll={false}
            zoomOnPinch={false}
            panOnScroll={false}
            attributionPosition="bottom-left"
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={16}
              size={0.8}
              color="rgba(0,0,0,0.1)"
            />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      {/* Current Execution Status */}
      {currentExecution && (
        <div className="mt-4 space-y-3">
          <h4 className="font-medium text-sm text-foreground">Execution Status</h4>
          <div className="space-y-2">
            {currentExecution.nodeExecutions?.map((nodeExec) => (
              <div key={nodeExec.nodeId} className="flex items-center justify-between text-sm bg-card border border-border rounded-md p-2">
                <div className="flex items-center gap-2">
                  <div className={clsx(
                    "w-2 h-2 rounded-full flex-shrink-0",
                    nodeExec.status === 'SUCCESS' ? 'bg-green-500' :
                    nodeExec.status === 'RUNNING' ? 'bg-orange-500 animate-pulse' :
                    nodeExec.status === 'ERROR' ? 'bg-red-500' :
                    'bg-gray-400'
                  )} />
                  <span className="font-medium text-foreground truncate">{nodeExec.nodeName}</span>
                </div>
                <span className={clsx(
                  "px-2 py-1 rounded text-xs font-medium flex-shrink-0",
                  statusConfig[nodeExec.status]?.bg,
                  statusConfig[nodeExec.status]?.color
                )}>
                  {nodeExec.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Node Detail Modal */}
      <NodeDetailModal
        isOpen={isModalOpen}
        onClose={closeModal}
        nodeData={selectedNode?.data}
        nodeName={selectedNode?.data?.name || selectedNode?.data?.type || 'Unknown Node'}
        workflowId={workflow.id}
      />
    </div>
  );
};
