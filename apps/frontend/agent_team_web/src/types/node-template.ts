// Node template types based on node-template.json

export type NodeCategory =
  | 'Trigger'
  | 'AI Agents'
  | 'Actions'
  | 'Flow Control'
  | 'Human Interaction'
  | 'Memory'
  | 'Tools';

export type NodeTypeEnum =
  | 'TRIGGER'
  | 'AI_AGENT'
  | 'ACTION'
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
  enum?: string[];
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
}

export interface NodeTemplatesData {
  node_templates: NodeTemplate[];
}
