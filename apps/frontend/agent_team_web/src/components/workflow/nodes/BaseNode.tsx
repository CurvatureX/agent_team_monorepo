import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface BaseNodeProps extends NodeProps {
  icon: LucideIcon;
  title: string;
  color: string;
  children?: React.ReactNode;
}

// Define color mapping
const colorMap: Record<string, { bg: string, text: string, border: string }> = {
  green: { bg: 'bg-green-500/10', text: 'text-green-500', border: 'border-green-500/20' },
  indigo: { bg: 'bg-indigo-500/10', text: 'text-indigo-500', border: 'border-indigo-500/20' },
  amber: { bg: 'bg-amber-500/10', text: 'text-amber-500', border: 'border-amber-500/20' },
  blue: { bg: 'bg-blue-500/10', text: 'text-blue-500', border: 'border-blue-500/20' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-500', border: 'border-purple-500/20' },
  pink: { bg: 'bg-pink-500/10', text: 'text-pink-500', border: 'border-pink-500/20' },
  cyan: { bg: 'bg-cyan-500/10', text: 'text-cyan-500', border: 'border-cyan-500/20' },
  orange: { bg: 'bg-orange-500/10', text: 'text-orange-500', border: 'border-orange-500/20' },
};

const BaseNode: React.FC<BaseNodeProps> = ({
  data,
  icon: Icon,
  title,
  color,
  children,
  selected,
}) => {
  const isDisabled = data?.disabled || false;
  const colorClasses = colorMap[color] || { bg: 'bg-gray-500/10', text: 'text-gray-500', border: 'border-gray-500/20' };

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={{ scale: 1.02 }}
      className={cn(
        "relative min-w-[200px] rounded-lg border-2 bg-background shadow-lg transition-all",
        selected ? "border-primary shadow-xl" : "border-border",
        isDisabled && "opacity-50"
      )}
    >
      {/* Input connection point */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-muted-foreground !border-2 !border-background"
      />

      {/* Node header */}
      <div
        className={cn(
          "flex items-center gap-2 px-4 py-2 rounded-t-md border-b",
          colorClasses.bg,
          colorClasses.border
        )}
      >
        <Icon className={cn("w-4 h-4", colorClasses.text)} />
        <span className="font-medium text-sm">{data?.label || title}</span>
      </div>

      {/* Node content */}
      {children && (
        <div className="px-4 py-3">
          {children}
        </div>
      )}

      {/* Node info */}
      <div className="px-4 pb-2">
        <p className="text-xs text-muted-foreground">{data?.subtype || 'Default'}</p>
      </div>

      {/* Output connection point */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-muted-foreground !border-2 !border-background"
      />

      {/* Disabled marker */}
      {isDisabled && (
        <div className="absolute inset-0 bg-background/50 rounded-lg flex items-center justify-center">
          <span className="text-xs text-muted-foreground">Disabled</span>
        </div>
      )}
    </motion.div>
  );
};

export default BaseNode; 