import type { Node as ReactFlowNode, Edge as ReactFlowEdge, XYPosition } from 'reactflow';
import type { NodeTemplate } from './node-template';
import type { WorkflowNode as ApiWorkflowNode } from './workflow';

// Extended node data for our workflow nodes
export interface WorkflowNodeData {
  label: string;
  description?: string;
  template: NodeTemplate;
  parameters: Record<string, unknown>;
  status?: 'idle' | 'running' | 'success' | 'error';
  originalData?: ApiWorkflowNode; // Store original API node data for export
}

// Extended edge data for workflow connections (stores backend Connection model fields)
export interface WorkflowEdgeData {
  // Backend Connection model fields (for round-trip conversion)
  from_node: string;                    // Source node ID (backend format)
  to_node: string;                      // Target node ID (backend format)
  output_key: string;                   // Which output to use (default: "result")
  conversion_function?: string | null;  // Python code for data transformation
  // Allow additional properties for flexibility
  [key: string]: unknown;
}

// Our custom node and edge types
// Note: WorkflowEdge extends ReactFlowEdge which has source, target, type, sourceHandle, targetHandle
// The backend Connection fields are stored in the 'data' property
export type WorkflowNode = ReactFlowNode<WorkflowNodeData>;
export type WorkflowEdge = ReactFlowEdge<WorkflowEdgeData>;

// UI state types
export interface EditorUIState {
  selectedNodeId: string | null;
  sidebarCollapsed: boolean;
  detailsPanelOpen: boolean;
  searchQuery: string;
  selectedCategory: string | null;
  canvasZoom: number;
  canvasPosition: XYPosition;
}

// Form field types
export type FieldType = 'text' | 'number' | 'checkbox' | 'select' | 'array' | 'object';

export interface FormField {
  name: string;
  type: FieldType;
  label: string;
  value: unknown;
  required?: boolean;
  options?: string[];
  validation?: (value: unknown) => string | null;
}

// Node color scheme
export interface NodeColorScheme {
  border: string;
  bg: string;
  icon: string;
}

// Validation result
export interface ValidationResult {
  valid: boolean;
  error?: string;
}
