import { ApiWorkflow, ApiExecution, ApiExecutionLog } from './api';
import { AIWorker, ExecutionRecord, NodeExecution, LogEntry, DeploymentStatus, LatestExecutionStatus, NodeType } from '@/types/workflow';

// Map API status to our types
const mapDeploymentStatus = (active: boolean, deploymentInfo?: any): DeploymentStatus => {
  if (deploymentInfo?.status) {
    switch (deploymentInfo.status.toLowerCase()) {
      case 'deployed': return 'DEPLOYED';
      case 'deploying':
      case 'pending': return 'PENDING';
      case 'failed': return 'FAILED';
      case 'draft': return 'DRAFT';
      case 'undeployed': return 'UNDEPLOYED';
      default: return active ? 'DEPLOYED' : 'UNDEPLOYED';
    }
  }
  return active ? 'DEPLOYED' : 'UNDEPLOYED';
};

const mapExecutionStatus = (status: string): LatestExecutionStatus => {
  switch (status.toUpperCase()) {
    case 'NEW':
    case 'DRAFT': return 'DRAFT';
    case 'RUNNING': return 'RUNNING';
    case 'SUCCESS': return 'SUCCESS';
    case 'ERROR': return 'ERROR';
    case 'CANCELED': return 'CANCELED';
    case 'WAITING':
    case 'PAUSED': return 'WAITING_FOR_HUMAN';
    default: return 'DRAFT';
  }
};

const mapNodeType = (nodeType: string): NodeType => {
  switch (nodeType?.toUpperCase()) {
    case 'TRIGGER': return 'TRIGGER';
    case 'AI_AGENT': return 'AI_AGENT';
    case 'ACTION': return 'ACTION';
    case 'EXTERNAL_ACTION': return 'EXTERNAL_ACTION';
    case 'FLOW': return 'FLOW';
    case 'HUMAN_IN_THE_LOOP': return 'HUMAN_IN_THE_LOOP';
    case 'TOOL': return 'TOOL';
    case 'MEMORY': return 'MEMORY';
    default: return 'ACTION';
  }
};

const generateNodePositions = (nodes: any[], connections?: any): { x: number; y: number }[] => {
  if (!connections || nodes.length === 0) {
    // Fallback to horizontal layout if no connections
    return nodes.map((_, index) => ({
      x: 100 + (index * 200),
      y: 100
    }));
  }

  // Create a graph structure from connections
  const nodeMap = new Map<string, number>();
  nodes.forEach((node, index) => {
    nodeMap.set(node.id || `node-${index}`, index);
  });

  // Build adjacency list and track incoming edges
  const adjacencyList = new Map<string, string[]>();
  const incomingEdges = new Map<string, number>();
  const outgoingEdges = new Map<string, number>();

  // Initialize all nodes
  nodes.forEach(node => {
    const nodeId = node.id || `node-${nodeMap.get(node.id) || 0}`;
    adjacencyList.set(nodeId, []);
    incomingEdges.set(nodeId, 0);
    outgoingEdges.set(nodeId, 0);
  });

  // Parse connections to build graph structure
  Object.entries(connections).forEach(([sourceNodeId, nodeConnections]) => {
    if (nodeConnections && typeof nodeConnections === 'object') {
      const parseConnections = (connectionsList: any[]) => {
        connectionsList.forEach(connection => {
          if (connection.node) {
            adjacencyList.get(sourceNodeId)?.push(connection.node);
            incomingEdges.set(connection.node, (incomingEdges.get(connection.node) || 0) + 1);
            outgoingEdges.set(sourceNodeId, (outgoingEdges.get(sourceNodeId) || 0) + 1);
          }
        });
      };

      // Handle new format: connection_types.main.connections
      const connectionTypes = (nodeConnections as any).connection_types;
      if (connectionTypes && connectionTypes.main && connectionTypes.main.connections) {
        parseConnections(connectionTypes.main.connections);
      }
      // Handle legacy format: main array directly
      else if ((nodeConnections as any).main && Array.isArray((nodeConnections as any).main)) {
        parseConnections((nodeConnections as any).main);
      }
    }
  });

  // Topological sort to determine layers
  const layers: string[][] = [];
  const visited = new Set<string>();
  const tempVisited = new Set<string>();
  const nodeToLayer = new Map<string, number>();

  // Find root nodes (nodes with no incoming edges)
  const rootNodes = nodes.filter(node => {
    const nodeId = node.id || `node-${nodeMap.get(node.id) || 0}`;
    return (incomingEdges.get(nodeId) || 0) === 0;
  }).map(node => node.id || `node-${nodeMap.get(node.id) || 0}`);

  // If no root nodes found, use first node
  if (rootNodes.length === 0 && nodes.length > 0) {
    rootNodes.push(nodes[0].id || `node-0`);
  }

  // BFS to assign layers
  const queue = rootNodes.map(nodeId => ({ nodeId, layer: 0 }));

  while (queue.length > 0) {
    const { nodeId, layer } = queue.shift()!;

    if (visited.has(nodeId)) continue;
    visited.add(nodeId);

    // Ensure layer array exists
    while (layers.length <= layer) {
      layers.push([]);
    }

    layers[layer].push(nodeId);
    nodeToLayer.set(nodeId, layer);

    // Add children to next layer
    const children = adjacencyList.get(nodeId) || [];
    children.forEach(childId => {
      if (!visited.has(childId)) {
        queue.push({ nodeId: childId, layer: layer + 1 });
      }
    });
  }

  // Add any unvisited nodes to appropriate layers
  nodes.forEach(node => {
    const nodeId = node.id || `node-${nodeMap.get(node.id) || 0}`;
    if (!visited.has(nodeId)) {
      layers[0].push(nodeId);
      nodeToLayer.set(nodeId, 0);
    }
  });

  // Generate positions based on layers with better spacing to prevent overlap
  const positions: { x: number; y: number }[] = new Array(nodes.length);
  const layerWidth = 280; // Increased horizontal spacing between layers
  const nodeHeight = 120; // Increased vertical spacing between nodes in same layer
  const nodeWidth = 160;  // Approximate node width for overlap detection
  const minY = 80;        // Minimum Y position
  const centerY = 200;    // Center point for graph

  layers.forEach((layer, layerIndex) => {
    const x = 120 + (layerIndex * layerWidth);

    // Calculate optimal vertical positioning for this layer
    const layerNodeCount = layer.length;

    if (layerNodeCount === 1) {
      // Single node: center it
      const nodeIndex = nodeMap.get(layer[0]);
      if (nodeIndex !== undefined) {
        positions[nodeIndex] = { x, y: centerY };
      }
    } else if (layerNodeCount === 2) {
      // Two nodes: spread them evenly around center
      layer.forEach((nodeId, nodeIndexInLayer) => {
        const nodeIndex = nodeMap.get(nodeId);
        if (nodeIndex !== undefined) {
          const y = centerY + (nodeIndexInLayer === 0 ? -nodeHeight/2 : nodeHeight/2);
          positions[nodeIndex] = { x, y: Math.max(minY, y) };
        }
      });
    } else {
      // Multiple nodes: distribute evenly with extra spacing
      const totalSpacing = (layerNodeCount - 1) * nodeHeight;
      const startY = centerY - (totalSpacing / 2);

      layer.forEach((nodeId, nodeIndexInLayer) => {
        const nodeIndex = nodeMap.get(nodeId);
        if (nodeIndex !== undefined) {
          const y = startY + (nodeIndexInLayer * nodeHeight);
          positions[nodeIndex] = { x, y: Math.max(minY, y) };
        }
      });
    }
  });

  // Post-process to fix any remaining overlaps
  const fixOverlaps = () => {
    let hasOverlap = true;
    let iterations = 0;
    const maxIterations = 10;

    while (hasOverlap && iterations < maxIterations) {
      hasOverlap = false;
      iterations++;

      for (let i = 0; i < positions.length; i++) {
        for (let j = i + 1; j < positions.length; j++) {
          if (!positions[i] || !positions[j]) continue;

          const dx = Math.abs(positions[i].x - positions[j].x);
          const dy = Math.abs(positions[i].y - positions[j].y);

          // Check if nodes are too close (potential overlap)
          if (dx < nodeWidth && dy < 60) { // 60px minimum vertical clearance
            hasOverlap = true;

            // Move the lower node down
            if (positions[i].y < positions[j].y) {
              positions[j].y = positions[i].y + nodeHeight;
            } else {
              positions[i].y = positions[j].y + nodeHeight;
            }
          }
        }
      }
    }
  };

  fixOverlaps();

  // Fill in any missing positions (fallback)
  positions.forEach((pos, index) => {
    if (!pos) {
      positions[index] = { x: 100 + (index * 200), y: 100 };
    }
  });

  return positions;
};

const extractTriggerInfo = (workflow: ApiWorkflow) => {
  // Look for trigger node in the workflow nodes
  const triggerNode = workflow.nodes?.find(node =>
    node.type?.toLowerCase() === 'trigger' || node.node_type?.toLowerCase() === 'trigger'
  );

  if (triggerNode) {
    return {
      type: (triggerNode.subtype || triggerNode.trigger_type || 'MANUAL') as any,
      config: triggerNode.config || triggerNode.settings || {},
      description: triggerNode.description || triggerNode.name || 'Workflow trigger'
    };
  }

  // Default trigger
  return {
    type: 'MANUAL' as any,
    config: {},
    description: 'Manual trigger'
  };
};

export const transformAPIWorkflowToAIWorker = (
  apiWorkflow: ApiWorkflow,
  executions: ApiExecution[] = [],
  deploymentInfo?: any
): AIWorker => {
  // Get latest execution
  const latestExecution = executions.length > 0 ? executions[0] : null;

  // Calculate next run time (simplified - would need actual trigger logic)
  const nextRunTime = apiWorkflow.active && latestExecution?.status === 'SUCCESS'
    ? new Date(Date.now() + 30 * 60 * 1000) // 30 minutes from now
    : undefined;

  // Transform nodes with positions
  const positions = generateNodePositions(apiWorkflow.nodes || [], apiWorkflow.connections);
  const workflowNodes = (apiWorkflow.nodes || []).map((node, index) => ({
    id: node.id || `node-${index}`,
    type: mapNodeType(node.type || node.node_type),
    position: positions[index],
    data: {
      name: node.name || node.title || `Node ${index + 1}`,
      description: node.description || '',
      subtype: node.subtype || node.sub_type,
      parameters: node.config || node.settings || {},
      ...node
    }
  }));

  // Transform execution history with logs extraction
  const executionHistory: ExecutionRecord[] = executions.map(execution => {
    // Extract node executions and logs from run_data
    const nodeExecutionsMap = new Map<string, any>();
    const logs: any[] = [];

    if (execution.run_data && typeof execution.run_data === 'object') {
      const runData = execution.run_data as any;

      // Extract node results if available
      if (runData.node_results) {
        Object.entries(runData.node_results).forEach(([nodeId, nodeResult]: [string, any]) => {
          if (nodeResult && nodeResult.logs && Array.isArray(nodeResult.logs)) {
            // Convert node logs to our format
            const nodeLogs = nodeResult.logs.map((logMessage: string) => ({
              timestamp: new Date(execution.start_time * 1000), // Use execution time as fallback
              level: nodeResult.status === 'ERROR' ? 'error' : 'info',
              message: logMessage,
              nodeId: nodeId
            }));
            logs.push(...nodeLogs);
          }

          nodeExecutionsMap.set(nodeId, {
            nodeId: nodeId,
            nodeName: nodeId,
            startTime: new Date(execution.start_time * 1000),
            endTime: execution.end_time ? new Date(execution.end_time * 1000) : undefined,
            status: nodeResult.status || 'SUCCESS',
            logs: nodeResult.logs ? nodeResult.logs.map((logMessage: string) => ({
              timestamp: new Date(execution.start_time * 1000),
              level: nodeResult.status === 'ERROR' ? 'error' : 'info',
              message: logMessage,
              nodeId: nodeId
            })) : []
          });
        });
      }

      // Also add any general execution logs or error messages
      if (execution.error_message) {
        logs.push({
          timestamp: new Date(execution.start_time * 1000),
          level: 'error',
          message: execution.error_message,
          nodeId: 'system'
        });
      }
    }

    return {
      id: execution.id,
      startTime: new Date(execution.start_time * 1000),
      endTime: execution.end_time ? new Date(execution.end_time * 1000) : undefined,
      status: mapExecutionStatus(execution.status),
      duration: execution.end_time ?
        Math.round((execution.end_time - execution.start_time) / 1000) : undefined,
      triggerType: extractTriggerInfo(apiWorkflow).type,
      error: execution.error_message,
      nodeExecutions: Array.from(nodeExecutionsMap.values())
    };
  });

  return {
    id: apiWorkflow.id,
    name: apiWorkflow.name,
    description: apiWorkflow.description || '',
    deploymentStatus: mapDeploymentStatus(apiWorkflow.active, deploymentInfo),
    // Use the latest execution metadata from the workflow response instead of individual API calls
    latestExecutionStatus: apiWorkflow.latest_execution_status ?
      mapExecutionStatus(apiWorkflow.latest_execution_status) :
      (latestExecution ? mapExecutionStatus(latestExecution.status) : 'DRAFT'),
    // Use the latest execution time from the workflow metadata
    lastRunTime: apiWorkflow.latest_execution_time ?
      new Date(apiWorkflow.latest_execution_time) :
      (latestExecution ? new Date(latestExecution.start_time * 1000) : undefined),
    nextRunTime,
    trigger: extractTriggerInfo(apiWorkflow),
    graph: workflowNodes,
    connections: apiWorkflow.connections, // Pass through the connections data
    executionHistory
  };
};

export const transformAPIExecutionToRecord = (
  apiExecution: ApiExecution,
  logs: ApiExecutionLog[] = []
): ExecutionRecord => {
  // Group logs by node_id to create node executions
  const nodeExecutionsMap = new Map<string, NodeExecution>();

  logs.forEach(log => {
    if (log.node_id) {
      const existing = nodeExecutionsMap.get(log.node_id);
      if (!existing) {
        nodeExecutionsMap.set(log.node_id, {
          nodeId: log.node_id,
          nodeName: log.data?.node_name || log.node_id,
          startTime: new Date(log.timestamp),
          status: 'RUNNING', // Will be updated based on log content
          logs: []
        });
      }

      const nodeExecution = nodeExecutionsMap.get(log.node_id)!;
      nodeExecution.logs.push({
        timestamp: new Date(log.timestamp),
        level: log.level.toLowerCase() as any,
        message: log.message,
        nodeId: log.node_id,
        data: log.data
      });

      // Update status based on log content
      if (log.message.includes('completed') || log.message.includes('success')) {
        nodeExecution.status = 'SUCCESS';
        nodeExecution.endTime = new Date(log.timestamp);
      } else if (log.message.includes('error') || log.message.includes('failed')) {
        nodeExecution.status = 'ERROR';
        nodeExecution.endTime = new Date(log.timestamp);
      }
    }
  });

  return {
    id: apiExecution.id,
    startTime: new Date(apiExecution.start_time * 1000),
    endTime: apiExecution.end_time ? new Date(apiExecution.end_time * 1000) : undefined,
    status: mapExecutionStatus(apiExecution.status),
    duration: apiExecution.end_time ?
      Math.round((apiExecution.end_time - apiExecution.start_time) / 1000) : undefined,
    triggerType: 'MANUAL' as any, // Would need to get from workflow trigger info
    nodeExecutions: Array.from(nodeExecutionsMap.values()),
    error: apiExecution.error_message
  };
};

export const transformAPILogsToLogEntries = (apiLogs: ApiExecutionLog[]): LogEntry[] => {
  return apiLogs.map(log => ({
    timestamp: new Date(log.timestamp),
    level: log.level.toLowerCase() as any,
    message: log.message,
    nodeId: log.node_id,
    data: log.data
  }));
};

// Utility to check if authentication is required
export const needsAuthentication = (error: any): boolean => {
  return error?.message === 'Authentication required' ||
         error?.status === 401 ||
         (typeof error === 'string' && error.includes('Authentication required'));
};
