import React, { useState, useCallback, useEffect, useRef } from "react";
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  OnConnect,
  OnConnectStart,
  OnConnectEnd,
  NodeTypes,
  Panel,
  ReactFlowProvider,
  useReactFlow,
  Connection,
} from "reactflow";
import "reactflow/dist/style.css";

import TriggerNode from "./components/nodes/TriggerNode";
import AIAgentNode from "./components/nodes/AIAgentNode";
import ActionNode from "./components/nodes/ActionNode";
import ToolNode from "./components/nodes/ToolNode";
import MemoryNode from "./components/nodes/MemoryNode";
import FlowNode from "./components/nodes/FlowNode";
import HumanInTheLoopNode from "./components/nodes/HumanInTheLoopNode";
import SubtypeDropdown from "./components/SubtypeDropdown";
import { Workflow, Download } from "lucide-react";

// Define node types
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

// Define subtypes for each node type
const nodeSubtypes = {
  trigger: [
    {
      id: "TRIGGER_CHAT",
      label: "Chat Message",
      description: "Triggered by chat messages",
    },
    {
      id: "TRIGGER_WEBHOOK",
      label: "Webhook",
      description: "HTTP webhook trigger",
    },
    {
      id: "TRIGGER_CRON",
      label: "Schedule",
      description: "Time-based schedule trigger",
    },
    {
      id: "TRIGGER_MANUAL",
      label: "Manual",
      description: "Manually triggered",
    },
    { id: "TRIGGER_EMAIL", label: "Email", description: "Email-based trigger" },
    {
      id: "TRIGGER_FORM",
      label: "Form Submit",
      description: "Form submission trigger",
    },
    {
      id: "TRIGGER_CALENDAR",
      label: "Calendar",
      description: "Calendar event trigger",
    },
  ],
  ai_agent: [
    {
      id: "AI_AGENT",
      label: "AI Agent",
      description: "General AI agent for various tasks",
    },
    {
      id: "AI_CLASSIFIER",
      label: "AI Classifier",
      description: "Classifies and categorizes input data",
    },
  ],
  external_action: [
    {
      id: "EXTERNAL_GITHUB",
      label: "GitHub",
      description: "GitHub integration actions",
    },
    {
      id: "EXTERNAL_GOOGLE_CALENDAR",
      label: "Google Calendar",
      description: "Google Calendar operations",
    },
    {
      id: "EXTERNAL_TRELLO",
      label: "Trello",
      description: "Trello board management",
    },
    {
      id: "EXTERNAL_EMAIL",
      label: "Email",
      description: "Email sending/receiving",
    },
    { id: "EXTERNAL_SLACK", label: "Slack", description: "Slack messaging" },
    {
      id: "EXTERNAL_API_CALL",
      label: "API Call",
      description: "Generic API call",
    },
    {
      id: "EXTERNAL_WEBHOOK",
      label: "Webhook",
      description: "Send webhook requests",
    },
    {
      id: "EXTERNAL_NOTIFICATION",
      label: "Notification",
      description: "Send notifications",
    },
  ],
  action: [
    {
      id: "ACTION_RUN_CODE",
      label: "Run Code",
      description: "Execute code snippets",
    },
    {
      id: "ACTION_SEND_HTTP_REQUEST",
      label: "HTTP Request",
      description: "Send HTTP requests",
    },
    {
      id: "ACTION_PARSE_IMAGE",
      label: "Parse Image",
      description: "Extract data from images",
    },
    {
      id: "ACTION_WEB_SEARCH",
      label: "Web Search",
      description: "Search the web",
    },
    {
      id: "ACTION_DATABASE_OPERATION",
      label: "Database Op",
      description: "Database operations",
    },
    {
      id: "ACTION_FILE_OPERATION",
      label: "File Operation",
      description: "File system operations",
    },
    {
      id: "ACTION_DATA_TRANSFORMATION",
      label: "Data Transform",
      description: "Transform data formats",
    },
  ],
  flow: [
    {
      id: "FLOW_IF",
      label: "If Condition",
      description: "Conditional branching",
    },
    {
      id: "FLOW_FILTER",
      label: "Filter",
      description: "Filter data based on criteria",
    },
    { id: "FLOW_LOOP", label: "Loop", description: "Iterate over data" },
    {
      id: "FLOW_MERGE",
      label: "Merge",
      description: "Merge multiple data streams",
    },
    {
      id: "FLOW_SWITCH",
      label: "Switch",
      description: "Switch between multiple paths",
    },
    { id: "FLOW_WAIT", label: "Wait", description: "Pause execution" },
  ],
  human_in_the_loop: [
    {
      id: "HUMAN_GMAIL",
      label: "Gmail",
      description: "Gmail-based human interaction",
    },
    {
      id: "HUMAN_SLACK",
      label: "Slack",
      description: "Slack-based human interaction",
    },
    {
      id: "HUMAN_DISCORD",
      label: "Discord",
      description: "Discord-based human interaction",
    },
    {
      id: "HUMAN_TELEGRAM",
      label: "Telegram",
      description: "Telegram-based human interaction",
    },
    { id: "HUMAN_APP", label: "App", description: "In-app human interaction" },
  ],
  tool: [
    {
      id: "TOOL_GOOGLE_CALENDAR_MCP",
      label: "Google Calendar MCP",
      description: "Google Calendar via MCP",
    },
    {
      id: "TOOL_NOTION_MCP",
      label: "Notion MCP",
      description: "Notion integration via MCP",
    },
    {
      id: "TOOL_CALENDAR",
      label: "Calendar",
      description: "Generic calendar tool",
    },
    { id: "TOOL_EMAIL", label: "Email", description: "Email handling tool" },
    { id: "TOOL_HTTP", label: "HTTP", description: "HTTP client tool" },
    {
      id: "TOOL_CODE_EXECUTION",
      label: "Code Execution",
      description: "Code execution environment",
    },
  ],
  memory: [
    {
      id: "MEMORY_SIMPLE",
      label: "Simple",
      description: "Simple memory storage",
    },
    {
      id: "MEMORY_BUFFER",
      label: "Buffer",
      description: "Buffer-based memory",
    },
    {
      id: "MEMORY_KNOWLEDGE",
      label: "Knowledge",
      description: "Knowledge base memory",
    },
    {
      id: "MEMORY_VECTOR_STORE",
      label: "Vector Store",
      description: "Vector-based memory",
    },
    {
      id: "MEMORY_DOCUMENT",
      label: "Document",
      description: "Document-based memory",
    },
    {
      id: "MEMORY_EMBEDDING",
      label: "Embedding",
      description: "Embedding-based memory",
    },
  ],
};

// Initial nodes and edges
const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];

let nodeId = 0;
const getNodeId = () => `node_${nodeId++}`;

// MVP Workflow JSON structure interfaces
interface MVPWorkflow {
  id: string;
  name: string;
  active: boolean;
  nodes: MVPNode[];
  connections: {
    connections: Record<string, Record<string, { connections: MVPConnection[] }>>;
  };
  settings: {
    timezone: { default: string };
    save_execution_progress: boolean;
    save_manual_executions: boolean;
    timeout: number;
    error_policy: string;
    caller_policy: string;
  };
  static_data: Record<string, any>;
  pin_data: Record<string, any>;
  created_at: number;
  updated_at: number;
  version: string;
  tags: string[];
}

interface MVPNode {
  id: string;
  name: string;
  type: string;
  subtype?: string;
  type_version: number;
  position: { x: number; y: number };
  disabled: boolean;
  parameters: Record<string, any>;
  credentials: Record<string, any>;
  on_error: string;
  retry_policy: { max_tries: number; wait_between_tries: number };
  notes: Record<string, any>;
  webhooks: string[];
}

interface MVPConnection {
  node: string;
  type: string;
  index: number;
}

// Create a new component for the editor to use the useReactFlow hook
function WorkflowEditor() {
  // JSON as source of truth
  const [workflowJSON, setWorkflowJSON] = useState<MVPWorkflow>({
    id: "example_workflow",
    name: "Example Workflow",
    active: true,
    nodes: [],
    connections: { connections: {} },
    settings: {
      timezone: { default: "UTC" },
      save_execution_progress: true,
      save_manual_executions: true,
      timeout: 300,
      error_policy: "STOP_WORKFLOW",
      caller_policy: "WORKFLOW_MAIN"
    },
    static_data: {},
    pin_data: {},
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    version: "1.0.0",
    tags: ["example", "workflow"]
  });

  const [selectedNodeType, setSelectedNodeType] = useState<string>("trigger");
  const [showSubtypeDropdown, setShowSubtypeDropdown] = useState(false);
  const [pendingNodeCreation, setPendingNodeCreation] = useState<{
    position: { x: number; y: number };
    mousePosition: { x: number; y: number };
    nodeType: string;
    sourceNodeId?: string;
    sourceHandle?: string;
  } | null>(null);
  const { project, deleteElements } = useReactFlow();
  const connectingNodeId = useRef<{
    nodeId: string;
    handleId: string;
    handleType: string;
  } | null>(null);

  // Convert MVP JSON to React Flow format
  const convertJSONToReactFlow = useCallback(() => {
    const reactFlowNodes: Node[] = workflowJSON.nodes.map(mvpNode => ({
      id: mvpNode.id,
      type: convertMVPTypeToReactFlow(mvpNode.type),
      position: mvpNode.position,
      data: {
        label: mvpNode.name,
        nodeType: convertMVPTypeToReactFlow(mvpNode.type),
        ...(mvpNode.subtype && { subtype: mvpNode.subtype }),
        onAddNode: () => {}, // Will be updated by useEffect
        onStartConnection: () => {}, // Will be updated by useEffect
      },
      selected: false,
    }));

    const reactFlowEdges: Edge[] = [];
    Object.entries(workflowJSON.connections.connections).forEach(([sourceId, connectionTypes]) => {
      Object.entries(connectionTypes).forEach(([connectionType, connectionData]) => {
        connectionData.connections.forEach((connection, index) => {
          const sourceNode = workflowJSON.nodes.find(n => n.id === sourceId);
          const targetNode = workflowJSON.nodes.find(n => n.id === connection.node);
          
          if (sourceNode && targetNode) {
            reactFlowEdges.push({
              id: `edge_${sourceNode.id}_${targetNode.id}_${index}`,
              source: sourceNode.id,
              target: targetNode.id,
              sourceHandle: connectionType === "ai_memory" ? "memory" : 
                           connectionType === "ai_tool" ? "tool" : "output",
              targetHandle: "input",
            });
          }
        });
      });
    });

    return { nodes: reactFlowNodes, edges: reactFlowEdges };
  }, [workflowJSON]);

  // Convert MVP node type to React Flow node type
  const convertMVPTypeToReactFlow = (mvpType: string) => {
    switch (mvpType) {
      case "TRIGGER_NODE": return "trigger";
      case "AI_AGENT_NODE": return "ai_agent";
      case "EXTERNAL_ACTION_NODE": return "external_action";
      case "ACTION_NODE": return "action";
      case "FLOW_NODE": return "flow";
      case "HUMAN_IN_THE_LOOP_NODE": return "human_in_the_loop";
      case "TOOL_NODE": return "tool";
      case "MEMORY_NODE": return "memory";
      default: return "action";
    }
  };

  // Convert React Flow node type to MVP type
  const convertReactFlowTypeToMVP = (reactFlowType: string) => {
    switch (reactFlowType) {
      case "trigger": return "TRIGGER_NODE";
      case "ai_agent": return "AI_AGENT_NODE";
      case "external_action": return "EXTERNAL_ACTION_NODE";
      case "action": return "ACTION_NODE";
      case "flow": return "FLOW_NODE";
      case "human_in_the_loop": return "HUMAN_IN_THE_LOOP_NODE";
      case "tool": return "TOOL_NODE";
      case "memory": return "MEMORY_NODE";
      default: return "ACTION_NODE";
    }
  };

  // Derive React Flow state from JSON
  const { nodes: initialNodesFlow, edges: initialEdgesFlow } = convertJSONToReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodesFlow);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdgesFlow);

  // Update React Flow when JSON changes
  React.useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = convertJSONToReactFlow();
    setNodes(newNodes);
    setEdges(newEdges);
  }, [workflowJSON, convertJSONToReactFlow, setNodes, setEdges]);

  const onNodesChangeCallback = useCallback(
    (changes) => {
      onNodesChange(changes);
  
      const removedNodeIds = changes
        .filter((change) => change.type === 'remove')
        .map((change) => "id" in change && change.id);
  
      if (removedNodeIds.length > 0) {
        setWorkflowJSON((prev) => {
          const newNodes = prev.nodes.filter((node) => !removedNodeIds.includes(node.id));
  
          const newConnections = { ...prev.connections.connections };
          removedNodeIds.forEach(id => delete newConnections[id]);
  
          Object.keys(newConnections).forEach((sourceId) => {
            Object.keys(newConnections[sourceId]).forEach((connectionType) => {
              newConnections[sourceId][connectionType].connections = newConnections[sourceId][
                connectionType
              ].connections.filter((conn) => !removedNodeIds.includes(conn.node));
            });
          });
  
          return {
            ...prev,
            nodes: newNodes,
            connections: { connections: newConnections },
            updated_at: Math.floor(Date.now() / 1000),
          };
        });
      }
  
      const positionChanges = changes.filter(
        (change) => change.type === 'position' && "position" in change && change.position
      );
  
      if (positionChanges.length > 0) {
        setWorkflowJSON((prev) => ({
          ...prev,
          nodes: prev.nodes.map((node) => {
            const change = positionChanges.find((p) => "id" in p && p.id === node.id);
            if (change && "position" in change && change.position) {
              return { ...node, position: change.position };
            }
            return node;
          }),
          updated_at: Math.floor(Date.now() / 1000),
        }));
      }
    },
    [onNodesChange, setWorkflowJSON]
  );
  
  const onEdgesChangeCallback = useCallback(
    (changes) => {
      onEdgesChange(changes);
  
      const removedEdgeIds = changes
        .filter((change) => change.type === 'remove')
        .map((change) => "id" in change && change.id);
  
      if (removedEdgeIds.length > 0) {
        setWorkflowJSON((prev) => {
          const newConnections = { ...prev.connections.connections };
  
          removedEdgeIds.forEach((edgeId) => {
            const edge = edges.find((e) => e.id === edgeId);
            if (edge) {
              const sourceNode = prev.nodes.find((n) => n.id === edge.source);
              const targetNode = prev.nodes.find((n) => n.id === edge.target);
  
              if (sourceNode && targetNode) {
                const connectionType =
                  edge.sourceHandle === 'memory'
                    ? 'ai_memory'
                    : edge.sourceHandle === 'tool'
                    ? 'ai_tool'
                    : 'main';
  
                if (newConnections[sourceNode.id]?.[connectionType]) {
                  newConnections[sourceNode.id][connectionType].connections = newConnections[
                    sourceNode.id
                  ][connectionType].connections.filter(
                    (conn) => conn.node !== targetNode.id
                  );
                }
              }
            }
          });
  
          return {
            ...prev,
            connections: { connections: newConnections },
            updated_at: Math.floor(Date.now() / 1000),
          };
        });
      }
    },
    [onEdgesChange, edges, setWorkflowJSON]
  );

  const onConnect: OnConnect = useCallback(
    (params) => {
      const sourceNode = workflowJSON.nodes.find(n => n.id === params.source);
      const targetNode = workflowJSON.nodes.find(n => n.id === params.target);
      
      if (sourceNode && targetNode) {
        const connectionType = params.sourceHandle === "memory" ? "ai_memory" :
                             params.sourceHandle === "tool" ? "ai_tool" : "main";
        
        setWorkflowJSON(prev => {
          const newConnections = { ...prev.connections.connections };
          
          if (!newConnections[sourceNode.id]) {
            newConnections[sourceNode.id] = {};
          }
          
          if (!newConnections[sourceNode.id][connectionType]) {
            newConnections[sourceNode.id][connectionType] = { connections: [] };
          }
          
          newConnections[sourceNode.id][connectionType].connections.push({
            node: targetNode.id,
            type: "MAIN",
            index: 0
          });
          
          return {
            ...prev,
            connections: { connections: newConnections },
            updated_at: Math.floor(Date.now() / 1000)
          };
        });
      }
    },
    [workflowJSON.nodes]
  );

  const onConnectStart: OnConnectStart = useCallback(
    (_, { nodeId, handleId, handleType }) => {
      connectingNodeId.current = {
        nodeId: nodeId!,
        handleId: handleId!,
        handleType: handleType!,
      };
    },
    []
  );

  // Helper function to create a node with optional subtype - updates JSON
  const createNode = useCallback(
    (
      nodeType: string,
      position: { x: number; y: number },
      subtype?: string,
      sourceNodeId?: string,
      sourceHandle?: string
    ) => {
      const newNodeId = getNodeId();
      const newMVPNode: MVPNode = {
        id: newNodeId,
        name: getNodeLabel(nodeType, subtype),
        type: convertReactFlowTypeToMVP(nodeType),
        ...(subtype && { subtype }),
        type_version: 1,
        position: { x: Math.round(position.x), y: Math.round(position.y) },
        disabled: false,
        parameters: {},
        credentials: {},
        on_error: "STOP_WORKFLOW_ON_ERROR",
        retry_policy: { max_tries: 1, wait_between_tries: 0 },
        notes: {},
        webhooks: []
      };

      setWorkflowJSON(prev => {
        const newWorkflow = {
          ...prev,
          nodes: [...prev.nodes, newMVPNode],
          updated_at: Math.floor(Date.now() / 1000)
        };

        // Create connection if this is from a plus button
        if (sourceNodeId && nodeType !== "trigger") {
          const sourceNode = prev.nodes.find(n => n.id === sourceNodeId);
          if (sourceNode) {
            const connectionType = sourceHandle === "memory" ? "ai_memory" :
                                 sourceHandle === "tool" ? "ai_tool" : "main";
            
            const newConnections = { ...newWorkflow.connections.connections };
            
            if (!newConnections[sourceNode.id]) {
              newConnections[sourceNode.id] = {};
            }
            
            if (!newConnections[sourceNode.id][connectionType]) {
              newConnections[sourceNode.id][connectionType] = { connections: [] };
            }
            
            newConnections[sourceNode.id][connectionType].connections.push({
              node: newMVPNode.id,
              type: "MAIN",
              index: 0
            });

            // If this is a loop branch, also create a connection back from the new node to the loop node
            if (sourceHandle === "loop") {
              if (!newConnections[newMVPNode.id]) {
                newConnections[newMVPNode.id] = {};
              }
              if (!newConnections[newMVPNode.id]["main"]) {
                newConnections[newMVPNode.id]["main"] = { connections: [] };
              }
              newConnections[newMVPNode.id]["main"].connections.push({
                node: sourceNode.id,
                type: "MAIN",
                index: 0
              });
            }

            newWorkflow.connections = { connections: newConnections };
          }
        }

        return newWorkflow;
      });
    },
    [convertReactFlowTypeToMVP]
  );

  const handleAddConnectedNode = useCallback(
    (sourceNodeId: string, sourceHandle: string = "output") => {
      const sourceNode = workflowJSON.nodes.find((node) => node.id === sourceNodeId);
      if (!sourceNode) {
        return;
      }

      // Determine node type and position based on source handle
      let newNodeType = selectedNodeType; // Use the selected node type from UI
      let offsetX = 250;
      let offsetY = 0;

      if (sourceHandle === "memory") {
        newNodeType = "memory";
        offsetX = -50;
        offsetY = 150;
      } else if (sourceHandle === "tool") {
        newNodeType = "tool";
        offsetX = 50;
        offsetY = 150;
      } else if (sourceHandle === "loop") {
        // Loop handle - position node slightly up and to the right
        offsetX = 250;
        offsetY = -30;
      } else if (sourceHandle === "done") {
        // Done handle - position node slightly down and to the right
        offsetX = 250;
        offsetY = 30;
      } else if (sourceHandle === "true") {
        // True handle - position node slightly up and to the right
        offsetX = 250;
        offsetY = -30;
      } else if (sourceHandle === "false") {
        // False handle - position node slightly down and to the right
        offsetX = 250;
        offsetY = 30;
      }

      const position = {
        x: sourceNode.position.x + offsetX,
        y: sourceNode.position.y + offsetY,
      };

      // Check if the node type has subtypes
      const hasSubtypes =
        nodeSubtypes[newNodeType as keyof typeof nodeSubtypes]?.length > 0;

      if (hasSubtypes) {
        // Show subtype dropdown for plus button clicks too
        const bounds = document
          .querySelector(".react-flow")
          ?.getBoundingClientRect();
        const mousePosition = {
          x: (bounds?.left || 0) + position.x,
          y: (bounds?.top || 0) + position.y,
        };

        setPendingNodeCreation({
          position,
          mousePosition,
          nodeType: newNodeType,
          sourceNodeId,
          sourceHandle,
        });
        setShowSubtypeDropdown(true);
      } else {
        // Create node directly without subtype
        createNode(
          newNodeType,
          position,
          undefined,
          sourceNodeId,
          sourceHandle
        );
      }
    },
    [selectedNodeType, workflowJSON.nodes, createNode]
  );

  const onConnectEnd: OnConnectEnd = useCallback(
    (event) => {
      if (!connectingNodeId.current) return;

      const targetIsPane = (event.target as Element).classList.contains(
        "react-flow__pane"
      );

      if (targetIsPane) {
        // User dropped the connection on the pane - create a new node
        const {
          nodeId: sourceNodeId,
          handleId: sourceHandle,
          handleType,
        } = connectingNodeId.current;

        if (handleType === "source") {
          // Calculate position where the user dropped
          const reactFlowBounds = document
            .querySelector(".react-flow")
            ?.getBoundingClientRect();
          if (reactFlowBounds) {
            const position = project({
              x: (event as MouseEvent).clientX - reactFlowBounds.left,
              y: (event as MouseEvent).clientY - reactFlowBounds.top,
            });

            // Use the selected node type, but determine special cases
            let newNodeType = selectedNodeType;
            let actualSourceHandle = sourceHandle;
            
            // Map plus handles to their main handles
            if (sourceHandle === "loop-plus") {
              actualSourceHandle = "loop";
            } else if (sourceHandle === "done-plus") {
              actualSourceHandle = "done";
            } else if (sourceHandle === "true-plus") {
              actualSourceHandle = "true";
            } else if (sourceHandle === "false-plus") {
              actualSourceHandle = "false";
            } else if (sourceHandle === "output-plus") {
              actualSourceHandle = "output";
            } else if (sourceHandle === "memory") {
              newNodeType = "memory";
            } else if (sourceHandle === "tool") {
              newNodeType = "tool";
            }

            // Check if the node type has subtypes
            const hasSubtypes =
              nodeSubtypes[newNodeType as keyof typeof nodeSubtypes]?.length >
              0;

            if (hasSubtypes) {
              // Show subtype dropdown
              setPendingNodeCreation({
                position,
                mousePosition: {
                  x: (event as MouseEvent).clientX,
                  y: (event as MouseEvent).clientY,
                },
                nodeType: newNodeType,
                sourceNodeId,
                sourceHandle: actualSourceHandle,
              });
              setShowSubtypeDropdown(true);
            } else {
              // Create node directly
              createNode(
                newNodeType,
                position,
                undefined,
                sourceNodeId,
                actualSourceHandle
              );
            }
          }
        }
      }

      connectingNodeId.current = null;
    },
    [project, selectedNodeType, createNode]
  );

  // Function to start connection dragging from plus buttons
  const handleStartConnection = useCallback(
    (nodeId: string, handleId: string) => {
      // Create a synthetic connection start event
      connectingNodeId.current = { nodeId, handleId, handleType: "source" };

      // Enable connection mode by programmatically triggering a connection start
      // This will enable the connection line to follow the cursor
      const reactFlowWrapper = document.querySelector(".react-flow");
      if (reactFlowWrapper) {
        const connectionEvent = new CustomEvent("connectionstart", {
          detail: { nodeId, handleId, handleType: "source" },
        });
        reactFlowWrapper.dispatchEvent(connectionEvent);
      }
    },
    []
  );

  // Update all nodes with the latest callback when selectedNodeType changes
  useEffect(() => {
    setNodes((currentNodes) =>
      currentNodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          ...(node.type !== "memory" &&
            node.type !== "tool" && {
              onAddNode: handleAddConnectedNode,
              onStartConnection: handleStartConnection,
            }),
        },
      }))
    );
  }, [
    selectedNodeType,
    handleAddConnectedNode,
    handleStartConnection,
    setNodes,
  ]);

  // Handle subtype selection
  const handleSubtypeSelect = useCallback(
    (subtype: string) => {
      if (pendingNodeCreation) {
        createNode(
          pendingNodeCreation.nodeType,
          pendingNodeCreation.position,
          subtype,
          pendingNodeCreation.sourceNodeId,
          pendingNodeCreation.sourceHandle
        );
      }
      setShowSubtypeDropdown(false);
      setPendingNodeCreation(null);
    },
    [pendingNodeCreation, createNode]
  );

  // Handle subtype dropdown cancel
  const handleSubtypeCancel = useCallback(() => {
    setShowSubtypeDropdown(false);
    setPendingNodeCreation(null);
  }, []);

  // Node creation at mouse position
  const onPaneClick = useCallback(
    (event: React.MouseEvent) => {
      // Get the ReactFlow wrapper bounds to calculate correct position
      const reactFlowBounds = (
        event.currentTarget as HTMLElement
      ).getBoundingClientRect();
      const position = project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      // Check if the selected node type has subtypes
      const hasSubtypes =
        nodeSubtypes[selectedNodeType as keyof typeof nodeSubtypes]?.length > 0;

      if (hasSubtypes) {
        // Show subtype dropdown
        setPendingNodeCreation({
          position,
          mousePosition: { x: event.clientX, y: event.clientY },
          nodeType: selectedNodeType,
        });
        setShowSubtypeDropdown(true);
      } else {
        // Create node directly without subtype
        createNode(selectedNodeType, position);
      }
    },
    [project, selectedNodeType, createNode]
  );

  const getNodeLabel = (nodeType: string, subtype?: string): string => {
    // Handle trigger subtypes with specific labels
    if (nodeType === "trigger" && subtype) {
      switch (subtype) {
        case "TRIGGER_CHAT":
          return "When chat message received";
        case "TRIGGER_WEBHOOK":
          return "When webhook triggered";
        case "TRIGGER_CRON":
          return "When scheduled time reached";
        case "TRIGGER_MANUAL":
          return "When manually triggered";
        case "TRIGGER_EMAIL":
          return "When email received";
        case "TRIGGER_FORM":
          return "When form submitted";
        case "TRIGGER_CALENDAR":
          return "When calendar event occurs";
        default:
          return "When trigger activated";
      }
    }

    // Handle AI Agent subtypes
    if (nodeType === "ai_agent" && subtype) {
      switch (subtype) {
        case "AI_AGENT":
          return "AI Agent Processing";
        case "AI_CLASSIFIER":
          return "AI Classification";
        default:
          return "AI Agent";
      }
    }

    // Handle Human-in-the-Loop subtypes
    if (nodeType === "human_in_the_loop" && subtype) {
      switch (subtype) {
        case "HUMAN_GMAIL":
          return "Human Input via Gmail";
        case "HUMAN_SLACK":
          return "Human Input via Slack";
        case "HUMAN_DISCORD":
          return "Human Input via Discord";
        case "HUMAN_TELEGRAM":
          return "Human Input via Telegram";
        case "HUMAN_APP":
          return "Human Input via App";
        default:
          return "Human Input Required";
      }
    }

    // Default labels for other node types
    const labels: Record<string, string> = {
      trigger: "When trigger activated",
      ai_agent: "AI Agent",
      action: "Action Node",
      external_action: "External Action",
      tool: "Tool",
      memory: "Memory",
      flow: "Flow Control",
      human_in_the_loop: "Human Input Required",
    };
    return labels[nodeType] || "Unknown Node";
  };

  const nodeTypeOptions = [
    {
      type: "trigger",
      label: "Trigger Node",
      description: "Start workflow with triggers",
    },
    { type: "ai_agent", label: "AI Agent", description: "AI processing node" },
    { type: "action", label: "Action Node", description: "Execute actions" },
    {
      type: "external_action",
      label: "External Action",
      description: "External API calls",
    },
    {
      type: "flow",
      label: "Flow Control",
      description: "Control workflow flow",
    },
    {
      type: "human_in_the_loop",
      label: "Human Input",
      description: "Require human interaction",
    },
  ];

  const saveWorkflow = useCallback(() => {
    const dataStr = JSON.stringify(workflowJSON, null, 2);
    const dataUri =
      "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);

    const exportFileDefaultName = "workflow.json";
    const linkElement = document.createElement("a");
    linkElement.setAttribute("href", dataUri);
    linkElement.setAttribute("download", exportFileDefaultName);
    linkElement.click();
  }, [workflowJSON]);

  const clearCanvas = useCallback(() => {
    setWorkflowJSON({
      id: "example_workflow",
      name: "Example Workflow",
      active: true,
      nodes: [],
      connections: { connections: {} },
      settings: {
        timezone: { default: "UTC" },
        save_execution_progress: true,
        save_manual_executions: true,
        timeout: 300,
        error_policy: "STOP_WORKFLOW",
        caller_policy: "WORKFLOW_MAIN"
      },
      static_data: {},
      pin_data: {},
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      version: "1.0.0",
      tags: ["example", "workflow"]
    });
    nodeId = 0;
  }, []);

  return (
    <div className="min-h-screen w-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Workflow className="h-8 w-8 text-blue-600" />
            <h1 className="text-xl font-semibold text-gray-800">
              Workflow Canvas
            </h1>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <button
            onClick={clearCanvas}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            Clear All
          </button>
          <button
            onClick={saveWorkflow}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-col">
        {/* Canvas Section */}
        <div className="h-[70vh] relative">
          {/* Node Type Selector */}
          <div className="absolute top-4 left-6 z-10 bg-white rounded-lg shadow-lg border border-gray-200 p-4 w-64">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Select Node Type
            </h3>
            <div className="space-y-2">
              {nodeTypeOptions.map((option) => (
                <button
                  key={option.type}
                  onClick={() => setSelectedNodeType(option.type)}
                  className={`w-full text-left p-3 rounded-md transition-colors ${
                    selectedNodeType === option.type
                      ? "bg-blue-50 border-blue-200 border text-blue-700"
                      : "bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700"
                  }`}
                >
                  <div className="font-medium text-sm">{option.label}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {option.description}
                  </div>
                </button>
              ))}
            </div>
            <div className="mt-4 p-3 bg-blue-50 rounded-md">
              <p className="text-xs text-blue-700">
                💡 Click on the canvas to create a node.
              </p>
              <p className="text-xs text-blue-700 mt-1">
                💡 Press ESC to delete selected nodes.
              </p>
            </div>
          </div>

          {/* React Flow Canvas */}
          <div className="h-full">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChangeCallback}
              onEdgesChange={onEdgesChangeCallback}
              onConnect={onConnect}
              onConnectStart={onConnectStart}
              onConnectEnd={onConnectEnd}
              onPaneClick={onPaneClick} // Use onPaneClick
              nodeTypes={nodeTypes}
              fitView
              snapToGrid
              snapGrid={[20, 20]}
              defaultEdgeOptions={{
                style: { strokeWidth: 2, stroke: "#94a3b8" },
                type: "smoothstep",
              }}
            >
              <Background
                variant={BackgroundVariant.Dots}
                gap={20}
                size={1}
                color="#e2e8f0"
              />
              <Controls className="bg-white border border-gray-200 shadow-lg" />
              <MiniMap
                className="bg-white border border-gray-200 shadow-lg"
                nodeColor="#3b82f6"
                maskColor="rgba(0, 0, 0, 0.1)"
              />

              {nodes.length === 0 && (
                <Panel position="top-center">
                  <div className="bg-white p-8 rounded-lg shadow-lg border border-gray-200 text-center max-w-md mt-20">
                    <Workflow className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                    <h2 className="text-xl font-semibold text-gray-700 mb-2">
                      Welcome to Workflow Canvas
                    </h2>
                    <p className="text-gray-500 mb-4">
                      Create your first workflow by clicking anywhere on the canvas
                      to add a node.
                    </p>
                    <p className="text-sm text-gray-400">
                      You can also use the + buttons on nodes to quickly add
                      connected nodes.
                    </p>
                  </div>
                </Panel>
              )}
            </ReactFlow>
          </div>
        </div>

        {/* JSON Section */}
        <div className="min-h-[60vh] bg-gray-900 border-t border-gray-300 flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
            <h3 className="text-sm font-medium text-gray-200">
              Workflow JSON (MVP Data Structure)
            </h3>
            <button
              onClick={() => {
                const jsonString = JSON.stringify(workflowJSON, null, 2);
                navigator.clipboard.writeText(jsonString);
              }}
              className="px-3 py-1 text-xs font-medium text-gray-300 bg-gray-700 rounded hover:bg-gray-600 transition-colors"
            >
              Copy JSON
            </button>
          </div>
          <div className="flex-1 overflow-auto p-6">
            <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap leading-relaxed">
              {JSON.stringify(workflowJSON, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      {/* Subtype Dropdown */}
      {showSubtypeDropdown && pendingNodeCreation && (
        <SubtypeDropdown
          nodeType={pendingNodeCreation.nodeType}
          subtypes={
            nodeSubtypes[
              pendingNodeCreation.nodeType as keyof typeof nodeSubtypes
            ] || []
          }
          position={pendingNodeCreation.mousePosition}
          onSelect={handleSubtypeSelect}
          onCancel={handleSubtypeCancel}
        />
      )}
    </div>
  );
}

// Wrap with ReactFlowProvider
function App() {
  return (
    <ReactFlowProvider>
      <WorkflowEditor />
    </ReactFlowProvider>
  );
}

export default App;
