import type { NodeCategory, NodeTypeEnum } from '@/types/node-template';
import type { NodeColorScheme } from '@/types/workflow-editor';
import {
  Play,
  Bot,
  Zap,
  GitBranch,
  Users,
  Database,
  Wrench,
  Circle,
  Calendar,
  Webhook,
  Clock,
  MessageSquare,
  Mail,
  FileText,
  Filter,
  Repeat,
  Merge,
  ToggleLeft,
  PauseCircle,
  type LucideIcon,
} from 'lucide-react';

// Node type to icon mapping
const NODE_TYPE_ICONS: Record<NodeTypeEnum, LucideIcon> = {
  TRIGGER: Play,
  AI_AGENT: Bot,
  ACTION: Zap,
  FLOW: GitBranch,
  HUMAN_IN_THE_LOOP: Users,
  MEMORY: Database,
  TOOL: Wrench,
};

// Node subtype to icon mapping
const NODE_SUBTYPE_ICONS: Record<string, LucideIcon> = {
  // Triggers
  TRIGGER_MANUAL: Play,
  TRIGGER_WEBHOOK: Webhook,
  TRIGGER_SCHEDULE: Clock,
  TRIGGER_CALENDAR: Calendar,
  TRIGGER_CHAT: MessageSquare,
  TRIGGER_EMAIL: Mail,
  TRIGGER_FORM: FileText,
  TRIGGER_CRON: Clock,
  
  // Flow Control
  FLOW_IF: ToggleLeft,
  FLOW_FILTER: Filter,
  FLOW_LOOP: Repeat,
  FLOW_MERGE: Merge,
  FLOW_SWITCH: GitBranch,
  FLOW_WAIT: PauseCircle,
  
  // Default fallback to parent type
};

// Category color schemes
export const CATEGORY_COLORS: Record<NodeCategory, NodeColorScheme> = {
  'Trigger': {
    border: 'border-green-500',
    bg: 'bg-green-50 dark:bg-green-950',
    icon: 'text-green-600 dark:text-green-400',
  },
  'AI Agents': {
    border: 'border-indigo-500',
    bg: 'bg-indigo-50 dark:bg-indigo-950',
    icon: 'text-indigo-600 dark:text-indigo-400',
  },
  'Actions': {
    border: 'border-amber-500',
    bg: 'bg-amber-50 dark:bg-amber-950',
    icon: 'text-amber-600 dark:text-amber-400',
  },
  'Flow Control': {
    border: 'border-purple-500',
    bg: 'bg-purple-50 dark:bg-purple-950',
    icon: 'text-purple-600 dark:text-purple-400',
  },
  'Human Interaction': {
    border: 'border-pink-500',
    bg: 'bg-pink-50 dark:bg-pink-950',
    icon: 'text-pink-600 dark:text-pink-400',
  },
  'Memory': {
    border: 'border-orange-500',
    bg: 'bg-orange-50 dark:bg-orange-950',
    icon: 'text-orange-600 dark:text-orange-400',
  },
  'Tools': {
    border: 'border-cyan-500',
    bg: 'bg-cyan-50 dark:bg-cyan-950',
    icon: 'text-cyan-600 dark:text-cyan-400',
  },
};

// Get icon for node type
export const getNodeIcon = (nodeType: NodeTypeEnum, nodeSubtype?: string): LucideIcon => {
  if (nodeSubtype && NODE_SUBTYPE_ICONS[nodeSubtype]) {
    return NODE_SUBTYPE_ICONS[nodeSubtype];
  }
  return NODE_TYPE_ICONS[nodeType] || Circle;
};

// Get color scheme for category
export const getCategoryColor = (category: NodeCategory): NodeColorScheme => {
  return CATEGORY_COLORS[category] || {
    border: 'border-gray-500',
    bg: 'bg-gray-50 dark:bg-gray-950',
    icon: 'text-gray-600 dark:text-gray-400',
  };
};

// Format parameter value for display
export const formatParameterValue = (value: unknown): string => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'object') {
    if (Array.isArray(value)) return `[${value.length} items]`;
    return Object.keys(value).length > 0 ? `{${Object.keys(value).length} props}` : '{}';
  }
  return String(value);
};

// Get parameter preview (first few important parameters)
export const getParameterPreview = (parameters: Record<string, unknown>, maxItems = 2): string[] => {
  const entries = Object.entries(parameters);
  const preview = entries
    .slice(0, maxItems)
    .map(([key, value]) => `${key}: ${formatParameterValue(value)}`);
  
  if (entries.length > maxItems) {
    preview.push(`+${entries.length - maxItems} more`);
  }
  
  return preview;
};

// Humanize a key name (snake_case or camelCase to Title Case)
export const humanizeKey = (key: string): string => {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

// Validate node connection
export const isValidConnection = (
  sourceType: NodeTypeEnum,
  targetType: NodeTypeEnum
): boolean => {
  // Triggers can only be sources, not targets
  if (targetType === 'TRIGGER') return false;
  
  // All other connections are valid for now
  // Add more specific rules as needed
  return true;
};

// Check if node type can have multiple inputs
export const canHaveMultipleInputs = (nodeType: NodeTypeEnum): boolean => {
  const multiInputTypes: NodeTypeEnum[] = ['FLOW', 'ACTION', 'AI_AGENT'];
  return multiInputTypes.includes(nodeType);
};

// Check if node type can have multiple outputs
export const canHaveMultipleOutputs = (nodeType: NodeTypeEnum): boolean => {
  const multiOutputTypes: NodeTypeEnum[] = ['FLOW', 'TRIGGER'];
  return multiOutputTypes.includes(nodeType);
};

// Generate unique node ID
export const generateNodeId = (nodeType: NodeTypeEnum): string => {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 1000);
  return `${nodeType.toLowerCase()}_${timestamp}_${random}`;
};