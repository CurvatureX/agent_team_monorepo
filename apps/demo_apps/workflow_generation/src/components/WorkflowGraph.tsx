import React, { useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  NodeTypes,
  MarkerType,
  ReactFlowProvider
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';

// Import existing node components
import TriggerNode from './nodes/TriggerNode';
import AIAgentNode from './nodes/AIAgentNode';
import ActionNode from './nodes/ActionNode';
import ToolNode from './nodes/ToolNode';
import MemoryNode from './nodes/MemoryNode';
import FlowNode from './nodes/FlowNode';
import HumanInTheLoopNode from './nodes/HumanInTheLoopNode';

import { AIWorker, WorkflowNode, WorkflowEdge } from '../types';

const nodeTypes: NodeTypes = {
  trigger: TriggerNode,
  ai_agent: AIAgentNode,
  action: ActionNode,
  external_action: ActionNode,
  tool: ToolNode,
  memory: MemoryNode,
  flow: FlowNode,
  human_in_the_loop: HumanInTheLoopNode,
};

const nodeWidth = 180;
const nodeHeight = 100;

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'LR', ranksep: 100, nodesep: 50 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = 'left' as const;
    node.sourcePosition = 'right' as const;
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
  });

  return { nodes, edges };
};

// Convert workflow nodes to ReactFlow format
const convertToReactFlowNodes = (workflowNodes: WorkflowNode[]): Node[] => {
  return workflowNodes.map((node, index) => ({
    id: node.id,
    type: node.type,
    position: node.position,
    data: {
      ...node.data,
      isConnectable: false, // Read-only view
    },
    draggable: false, // Read-only view
  }));
};

// Generate edges based on node sequence (for demo purposes)
const generateEdges = (nodes: WorkflowNode[]): Edge[] => {
  const edges: Edge[] = [];
  for (let i = 0; i < nodes.length - 1; i++) {
    edges.push({
      id: `edge-${i}`,
      source: nodes[i].id,
      target: nodes[i + 1].id,
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
  return edges;
};

interface WorkflowGraphProps {
  workflow: AIWorker;
}

export const WorkflowGraph: React.FC<WorkflowGraphProps> = ({ workflow }) => {
  const { nodes, edges } = useMemo(() => {
    const reactFlowNodes = convertToReactFlowNodes(workflow.graph);
    const workflowEdges = generateEdges(workflow.graph);
    return getLayoutedElements(reactFlowNodes, workflowEdges);
  }, [workflow.graph]);

  const nodeColor = (node: Node) => {
    switch (node.type) {
      case 'trigger':
        return '#10b981'; // green
      case 'ai_agent':
        return '#6366f1'; // indigo
      case 'action':
      case 'external_action':
        return '#f59e0b'; // amber
      case 'tool':
        return '#8b5cf6'; // violet
      case 'memory':
        return '#06b6d4'; // cyan
      case 'flow':
        return '#ec4899'; // pink
      case 'human_in_the_loop':
        return '#ef4444'; // red
      default:
        return '#6b7280'; // gray
    }
  };

  return (
    <div className="space-y-4">
      {/* Graph Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Workflow Visualization</h3>
          <p className="text-sm text-gray-600">
            Interactive view of your workflow nodes and connections
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>{nodes.length} nodes</span>
          <span>•</span>
          <span>{edges.length} connections</span>
        </div>
      </div>

      {/* Node Legend */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Node Types</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
          {[
            { type: 'trigger', label: 'Trigger' },
            { type: 'ai_agent', label: 'AI Agent' },
            { type: 'action', label: 'Action' },
            { type: 'tool', label: 'Tool' },
            { type: 'memory', label: 'Memory' },
            { type: 'flow', label: 'Flow' },
            { type: 'human_in_the_loop', label: 'Human' },
          ].map(({ type, label }) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: nodeColor({ type } as Node) }}
              />
              <span className="text-xs text-gray-600">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ReactFlow Graph */}
      <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
        <div style={{ height: '600px' }}>
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
              zoomOnScroll={true}
              zoomOnPinch={true}
              panOnScroll={false}
              panOnScrollSpeed={0.5}
              minZoom={0.1}
              maxZoom={2}
              defaultViewport={{ x: 0, y: 0, zoom: 1 }}
            >
              <Controls
                position="bottom-right"
                showInteractive={false}
              />
              <MiniMap
                nodeColor={nodeColor}
                nodeStrokeWidth={3}
                pannable
                zoomable
                position="bottom-left"
                style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                }}
              />
              <Background
                variant={BackgroundVariant.Dots}
                gap={20}
                size={1}
                color="#e2e8f0"
              />
            </ReactFlow>
          </ReactFlowProvider>
        </div>
      </div>

      {/* Node Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workflow.graph.map((node) => (
          <div key={node.id} className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: nodeColor({ type: node.type } as Node) }}
              />
              <h4 className="font-medium text-gray-900">
                {node.data.name || `${node.type.replace('_', ' ')} Node`}
              </h4>
            </div>
            <p className="text-sm text-gray-600 mb-2">
              {node.data.description || 'No description available'}
            </p>
            <div className="text-xs text-gray-500">
              <span className="capitalize">{node.type.replace('_', ' ')}</span>
              {node.data.subtype && (
                <>
                  <span className="mx-1">•</span>
                  <span className="capitalize">{node.data.subtype}</span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
