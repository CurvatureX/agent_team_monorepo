"use client";

import React, { useCallback, useMemo, useState, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  Connection,
  Edge,
  BackgroundVariant,
  Panel,
  useReactFlow,
  ReactFlowInstance,
  Node,
  NodeChange,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { motion } from 'framer-motion';
import { Maximize2, Minimize2, Move } from 'lucide-react';

// Import custom node components
import {
  TriggerNode,
  AIAgentNode,
  ActionNode,
  ExternalActionNode,
  FlowNode,
  HumanInTheLoopNode,
  ToolNode,
  MemoryNode,
} from './nodes';
import NodePanel from './NodePanel';

// Import types and utility functions
import { WorkflowData, NodeType, NodeSubtype } from '@/types/workflow';
import { convertWorkflowToReactFlow, convertReactFlowToWorkflow } from '@/utils/workflowConverter';
import { cn } from '@/lib/utils';

interface WorkflowCanvasProps {
  workflowData?: WorkflowData;
  onWorkflowChange?: (workflow: WorkflowData) => void;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  isSimpleView?: boolean; // Add simplified view mode
}

// Define node type mapping
const nodeTypes = {
  TRIGGER_NODE: TriggerNode,
  AI_AGENT_NODE: AIAgentNode,
  ACTION_NODE: ActionNode,
  EXTERNAL_ACTION_NODE: ExternalActionNode,
  FLOW_NODE: FlowNode,
  HUMAN_IN_THE_LOOP_NODE: HumanInTheLoopNode,
  TOOL_NODE: ToolNode,
  MEMORY_NODE: MemoryNode,
};

const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  workflowData,
  onWorkflowChange,
  isExpanded = false,
  onToggleExpand,
  isSimpleView = false,
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const { fitView } = useReactFlow();

  // Convert workflow data to ReactFlow format
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (workflowData) {
      return convertWorkflowToReactFlow(workflowData);
    }
    return { nodes: [], edges: [] };
  }, [workflowData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Handle connection creation
  const onConnect = useCallback(
    (params: Edge | Connection) => {
      setEdges((eds) => addEdge({
        ...params,
        type: 'smoothstep',
        animated: true,
        style: { strokeWidth: 2, stroke: '#6b7280' }
      }, eds));
      
      // Notify workflow changes
      if (onWorkflowChange && workflowData) {
        const updatedWorkflow = convertReactFlowToWorkflow(
          nodes,
          addEdge(params, edges),
          workflowData
        );
        onWorkflowChange(updatedWorkflow);
      }
    },
    [setEdges, nodes, edges, workflowData, onWorkflowChange]
  );

  // Handle node click
  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    console.log('Node clicked:', node.id);
  }, []);

  // Handle node changes
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);
      
      // Notify workflow changes
      if (onWorkflowChange && workflowData) {
        setTimeout(() => {
          const updatedWorkflow = convertReactFlowToWorkflow(nodes, edges, workflowData);
          onWorkflowChange(updatedWorkflow);
        }, 100);
      }
    },
    [onNodesChange, nodes, edges, workflowData, onWorkflowChange]
  );

  // Handle drag and drop
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow');

      if (typeof type === 'undefined' || !type || !reactFlowBounds || !reactFlowInstance) {
        return;
      }

      const nodeData = JSON.parse(type);
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNode = {
        id: `${nodeData.type.toLowerCase()}_${Date.now()}`,
        type: nodeData.type,
        position,
        data: { 
          label: `New ${nodeData.type.replace(/_/g, ' ').toLowerCase()}`,
          subtype: nodeData.subtype,
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  // Handle adding nodes from panel
  const handleNodeAdd = useCallback((type: NodeType, subtype: NodeSubtype) => {
    const position = {
      x: Math.random() * 500,
      y: Math.random() * 300,
    };

    const newNode = {
      id: `${type.toLowerCase()}_${Date.now()}`,
      type,
      position,
      data: { 
        label: `New ${type.replace(/_/g, ' ').toLowerCase()}`,
        subtype,
      },
    };

    setNodes((nds) => nds.concat(newNode));
  }, [setNodes]);

  return (
    <div className="relative w-full h-full bg-background rounded-lg overflow-hidden">
      <div 
        ref={reactFlowWrapper}
        className="w-full h-full"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
          className={cn(
            "w-full h-full",
            "react-flow-dark",
            "[&_.react-flow__node]:text-xs [&_.react-flow__node]:border-none [&_.react-flow__node]:shadow-none",
            "[&_.react-flow__handle]:w-3 [&_.react-flow__handle]:h-3 [&_.react-flow__handle]:border-2 [&_.react-flow__handle]:border-background [&_.react-flow__handle]:bg-muted-foreground",
            "[&_.react-flow__handle:hover]:bg-primary",
            "[&_.react-flow__edge-path]:stroke-2",
            "[&_.react-flow__edge.selected_.react-flow__edge-path]:stroke-primary",
            "[&_.react-flow__controls]:bg-background [&_.react-flow__controls]:border [&_.react-flow__controls]:border-border [&_.react-flow__controls]:rounded-lg [&_.react-flow__controls]:shadow-md",
            "[&_.react-flow__controls-button]:bg-transparent [&_.react-flow__controls-button]:border-b [&_.react-flow__controls-button]:border-border",
            "[&_.react-flow__controls-button:hover]:bg-accent",
            "[&_.react-flow__controls-button:last-child]:border-b-0",
            "[&_.react-flow__minimap]:bg-background [&_.react-flow__minimap]:border [&_.react-flow__minimap]:border-border [&_.react-flow__minimap]:rounded-lg [&_.react-flow__minimap]:shadow-md"
          )}
        >
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
          
          {!isSimpleView && (
            <>
              <MiniMap 
                nodeStrokeColor={(n) => {
                  switch (n.type) {
                    case 'TRIGGER_NODE': return 'rgb(16, 185, 129)';
                    case 'AI_AGENT_NODE': return 'rgb(99, 102, 241)';
                    case 'ACTION_NODE': return 'rgb(245, 158, 11)';
                    case 'EXTERNAL_ACTION_NODE': return 'rgb(59, 130, 246)';
                    case 'FLOW_NODE': return 'rgb(139, 92, 246)';
                    case 'HUMAN_IN_THE_LOOP_NODE': return 'rgb(236, 72, 153)';
                    case 'TOOL_NODE': return 'rgb(6, 182, 212)';
                    case 'MEMORY_NODE': return 'rgb(249, 115, 22)';
                    default: return 'rgb(107, 114, 128)';
                  }
                }}
                nodeColor={(n) => {
                  switch (n.type) {
                    case 'TRIGGER_NODE': return 'rgba(16, 185, 129, 0.2)';
                    case 'AI_AGENT_NODE': return 'rgba(99, 102, 241, 0.2)';
                    case 'ACTION_NODE': return 'rgba(245, 158, 11, 0.2)';
                    case 'EXTERNAL_ACTION_NODE': return 'rgba(59, 130, 246, 0.2)';
                    case 'FLOW_NODE': return 'rgba(139, 92, 246, 0.2)';
                    case 'HUMAN_IN_THE_LOOP_NODE': return 'rgba(236, 72, 153, 0.2)';
                    case 'TOOL_NODE': return 'rgba(6, 182, 212, 0.2)';
                    case 'MEMORY_NODE': return 'rgba(249, 115, 22, 0.2)';
                    default: return 'rgba(107, 114, 128, 0.2)';
                  }
                }}
                pannable
                zoomable
              />
              <Controls showInteractive={false} />
              
              {/* Custom control panel */}
              <Panel position="top-right" className="bg-background/80 backdrop-blur-sm rounded-lg p-2 space-x-2 flex items-center">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => fitView({ padding: 0.1, duration: 300 })}
                  className="p-2 hover:bg-accent rounded-lg transition-colors"
                  title="Fit View"
                >
                  <Move className="w-4 h-4" />
                </motion.button>
                
                {onToggleExpand && (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onToggleExpand}
                    className="p-2 hover:bg-accent rounded-lg transition-colors"
                    title={isExpanded ? "Exit Fullscreen" : "Fullscreen"}
                  >
                    {isExpanded ? (
                      <Minimize2 className="w-4 h-4" />
                    ) : (
                      <Maximize2 className="w-4 h-4" />
                    )}
                  </motion.button>
                )}
              </Panel>

              {/* Node panel */}
              <Panel position="top-left" className="ml-4 mt-4">
                <NodePanel onNodeAdd={handleNodeAdd} />
              </Panel>
            </>
          )}
        </ReactFlow>
      </div>
    </div>
  );
};

// Wrapper component to provide ReactFlowProvider
const WorkflowCanvasWrapper: React.FC<WorkflowCanvasProps> = (props) => {
  return (
    <ReactFlowProvider>
      <WorkflowCanvas {...props} />
    </ReactFlowProvider>
  );
};

export default WorkflowCanvasWrapper; 