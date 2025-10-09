// Node template types based on node-template.json

export type NodeCategory =
  | 'Trigger'
  | 'AI Agents'
  | 'Actions'
  | 'External Integrations'
  | 'Flow Control'
  | 'Human Interaction'
  | 'Memory'
  | 'Tools';

export type NodeTypeEnum =
  | 'TRIGGER'
  | 'AI_AGENT'
  | 'ACTION'
  | 'EXTERNAL_ACTION'
  | 'FLOW'
  | 'HUMAN_IN_THE_LOOP'
  | 'MEMORY'
  | 'TOOL';

export interface ParameterSchema {
  type: 'object';
  properties?: Record<string, SchemaProperty>;
  required?: string[];
}

export interface SchemaProperty {
  type: 'string' | 'boolean' | 'integer' | 'number' | 'array' | 'object';
  description?: string;
  enum?: string[];  // Dropdown options (from backend "options" field, converted to JSON Schema "enum")
  default?: unknown;

  // UI/Behavior properties
  sensitive?: boolean;      // Password field with masking
  multiline?: boolean;      // Textarea instead of input
  readonly?: boolean;       // Non-editable display field

  // Validation properties
  min?: number;             // Min value for numbers, min length for strings
  max?: number;             // Max value for numbers, max length for strings
  validation_pattern?: string; // Regex pattern for validation

  // Dynamic dropdown properties
  api_endpoint?: string;    // API URL to fetch dropdown options
  search_endpoint?: string; // API URL to search and fetch options (for searchable fields)
  multiple?: boolean;       // Multi-select for arrays

  // UI enhancement properties
  placeholder?: string;     // Input placeholder text
  help_text?: string;       // Help text/tooltip content

  // Nested schemas
  items?: SchemaProperty;
  properties?: Record<string, SchemaProperty>;
}

export interface NodeTemplate {
  id: string;
  name: string;
  description: string;
  node_type: NodeTypeEnum;
  node_subtype: string;
  version: string;
  is_system_template: boolean;
  default_parameters: Record<string, unknown>;
  required_parameters: string[] | null;
  parameter_schema: ParameterSchema;
  input_params: ParameterSchema | Record<string, unknown>;  // Input parameters schema
  output_params: ParameterSchema | Record<string, unknown>; // Output parameters schema
}

export interface NodeTemplatesData {
  node_templates: NodeTemplate[];
}
