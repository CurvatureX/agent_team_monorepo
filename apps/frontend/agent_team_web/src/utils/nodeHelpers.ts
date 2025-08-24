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

// Category color schemes with inline styles
export interface NodeColorSchemeWithStyles extends NodeColorScheme {
  bgStyle?: React.CSSProperties;
  iconStyle?: React.CSSProperties;
  borderStyle?: React.CSSProperties;
}

export const CATEGORY_COLORS: Record<NodeCategory, NodeColorSchemeWithStyles> = {
  'Trigger': {
    border: 'border-green-500',
    bg: 'bg-green-50 dark:bg-green-950',
    icon: 'text-green-600 dark:text-green-400',
    bgStyle: { backgroundColor: 'rgb(240 253 244)' }, // green-50
    iconStyle: { color: 'rgb(22 163 74)' }, // green-600
    borderStyle: { borderColor: 'rgb(34 197 94)' }, // green-500
  },
  'AI Agents': {
    border: 'border-indigo-500',
    bg: 'bg-indigo-50 dark:bg-indigo-950',
    icon: 'text-indigo-600 dark:text-indigo-400',
    bgStyle: { backgroundColor: 'rgb(238 242 255)' }, // indigo-50
    iconStyle: { color: 'rgb(79 70 229)' }, // indigo-600
    borderStyle: { borderColor: 'rgb(99 102 241)' }, // indigo-500
  },
  'Actions': {
    border: 'border-amber-500',
    bg: 'bg-amber-50 dark:bg-amber-950',
    icon: 'text-amber-600 dark:text-amber-400',
    bgStyle: { backgroundColor: 'rgb(255 251 235)' }, // amber-50
    iconStyle: { color: 'rgb(217 119 6)' }, // amber-600
    borderStyle: { borderColor: 'rgb(245 158 11)' }, // amber-500
  },
  'Flow Control': {
    border: 'border-purple-500',
    bg: 'bg-purple-50 dark:bg-purple-950',
    icon: 'text-purple-600 dark:text-purple-400',
    bgStyle: { backgroundColor: 'rgb(250 245 255)' }, // purple-50
    iconStyle: { color: 'rgb(147 51 234)' }, // purple-600
    borderStyle: { borderColor: 'rgb(168 85 247)' }, // purple-500
  },
  'Human Interaction': {
    border: 'border-pink-500',
    bg: 'bg-pink-50 dark:bg-pink-950',
    icon: 'text-pink-600 dark:text-pink-400',
    bgStyle: { backgroundColor: 'rgb(253 242 248)' }, // pink-50
    iconStyle: { color: 'rgb(219 39 119)' }, // pink-600
    borderStyle: { borderColor: 'rgb(236 72 153)' }, // pink-500
  },
  'Memory': {
    border: 'border-orange-500',
    bg: 'bg-orange-50 dark:bg-orange-950',
    icon: 'text-orange-600 dark:text-orange-400',
    bgStyle: { backgroundColor: 'rgb(255 247 237)' }, // orange-50
    iconStyle: { color: 'rgb(234 88 12)' }, // orange-600
    borderStyle: { borderColor: 'rgb(249 115 22)' }, // orange-500
  },
  'Tools': {
    border: 'border-cyan-500',
    bg: 'bg-cyan-50 dark:bg-cyan-950',
    icon: 'text-cyan-600 dark:text-cyan-400',
    bgStyle: { backgroundColor: 'rgb(236 254 255)' }, // cyan-50
    iconStyle: { color: 'rgb(8 145 178)' }, // cyan-600
    borderStyle: { borderColor: 'rgb(6 182 212)' }, // cyan-500
  },
};

// Get color scheme for category
export const getCategoryColor = (category: NodeCategory): NodeColorSchemeWithStyles => {
  return CATEGORY_COLORS[category] || {
    // border: 'border-gray-500',
    // bg: 'bg-gray-50 dark:bg-gray-950',
    // icon: 'text-gray-600 dark:text-gray-400',
    border: 'border-gray-500',
    bg: 'bg-gray-50 dark:bg-gray-950',
    icon: 'text-gray-600 dark:text-gray-400',
    bgStyle: { backgroundColor: 'rgb(249 250 251)' },
    iconStyle: { color: 'rgb(75 85 99)' },
    borderStyle: { borderColor: 'rgb(107 114 128)' },
  };
};

// Get icon for node type
export const getNodeIcon = (nodeType: NodeTypeEnum, nodeSubtype?: string): LucideIcon => {
  if (nodeSubtype && NODE_SUBTYPE_ICONS[nodeSubtype]) {
    return NODE_SUBTYPE_ICONS[nodeSubtype];
  }
  return NODE_TYPE_ICONS[nodeType] || Circle;
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