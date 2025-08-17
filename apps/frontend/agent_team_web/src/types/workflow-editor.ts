import type { Node as ReactFlowNode, Edge as ReactFlowEdge, XYPosition } from 'reactflow';
import type { NodeTemplate } from './node-template';

// Extended node data for our workflow nodes
export interface WorkflowNodeData {
  label: string;
  template: NodeTemplate;
  parameters: Record<string, unknown>;
  status?: 'idle' | 'running' | 'success' | 'error';
  originalData?: any; // Store original API node data for export
}

// Our custom node type
export type WorkflowNode = ReactFlowNode<WorkflowNodeData>;
export type WorkflowEdge = ReactFlowEdge;

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