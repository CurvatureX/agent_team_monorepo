// import { Node as ReactFlowNode, Edge as ReactFlowEdge } from 'reactflow';
// import { WorkflowData, NodeType } from '@/types/workflow';

// // Convert workflow data to ReactFlow format
// export function convertWorkflowToReactFlow(workflow: WorkflowData) {
//   const nodes: ReactFlowNode[] = workflow.nodes.map((node) => ({
//     id: node.id,
//     type: node.type,
//     position: node.position,
//     data: {
//       label: node.name,
//       subtype: node.subtype,
//       disabled: node.disabled,
//       parameters: node.parameters,
//       nodeData: node, // Use a different property name to avoid overwriting
//     },
//   }));

//   const edges: ReactFlowEdge[] = [];
  
//   // Parse connection relationships
//   Object.entries(workflow.connections.connections).forEach(([sourceId, connection]) => {
//     if (connection.output?.connections) {
//       connection.output.connections.forEach((conn, index) => {
//         edges.push({
//           id: `${sourceId}-${conn.node}-${index}`,
//           source: sourceId,
//           target: conn.node,
//           type: 'smoothstep',
//           animated: true,
//           style: {
//             stroke: '#6b7280',
//             strokeWidth: 2,
//           },
//         });
//       });
//     }
//   });

//   return { nodes, edges };
// }

// // Convert ReactFlow format back to workflow data
// export function convertReactFlowToWorkflow(
//   nodes: ReactFlowNode[],
//   edges: ReactFlowEdge[],
//   originalWorkflow: WorkflowData
// ): WorkflowData {
//   // Update node positions and data
//   const updatedNodes = nodes.map((node) => {
//     const originalNode = originalWorkflow.nodes.find((n) => n.id === node.id);
//     if (originalNode) {
//       return {
//         ...originalNode,
//         position: node.position,
//         name: node.data.label || originalNode.name,
//         disabled: node.data.disabled ?? originalNode.disabled,
//         parameters: node.data.parameters || originalNode.parameters,
//       };
//     }
//     // New node
//     return {
//       id: node.id,
//       name: node.data.label || 'New Node',
//       type: node.type as NodeType,
//       subtype: node.data.subtype,
//       type_version: 1,
//       position: node.position,
//       disabled: false,
//       parameters: node.data.parameters || {},
//       credentials: {},
//       on_error: 'STOP_WORKFLOW_ON_ERROR' as const,
//       retry_policy: {
//         max_tries: 1,
//         wait_between_tries: 0,
//       },
//       notes: {},
//       webhooks: [],
//     };
//   });

//   // Rebuild connection relationships
//   const connections: { connections: Record<string, { output: { connections: Array<{ node: string; type: string; index: number }> } }> } = { connections: {} };
  
//   edges.forEach((edge) => {
//     if (!connections.connections[edge.source]) {
//       connections.connections[edge.source] = {
//         output: { connections: [] },
//       };
//     }
    
//     const existingIndex = connections.connections[edge.source].output.connections.findIndex(
//       (conn) => conn.node === edge.target
//     );
    
//     if (existingIndex === -1) {
//       connections.connections[edge.source].output.connections.push({
//         node: edge.target,
//         type: 'MAIN',
//         index: connections.connections[edge.source].output.connections.length,
//       });
//     }
//   });

//   return {
//     ...originalWorkflow,
//     nodes: updatedNodes,
//     connections,
//     updated_at: Date.now() / 1000,
//   };
// } 