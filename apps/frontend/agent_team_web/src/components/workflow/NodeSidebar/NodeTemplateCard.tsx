"use client";

import React, { DragEvent } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { NodeTemplate } from '@/types/node-template';
import { getNodeIcon, getCategoryColor, getCategoryFromNodeType } from '@/utils/nodeHelpers';
import { Card } from '@/components/ui/card';

interface NodeTemplateCardProps {
  template: NodeTemplate;
  onDragStart: (e: DragEvent<HTMLDivElement>, template: NodeTemplate) => void;
  onClick: () => void;
}

export const NodeTemplateCard: React.FC<NodeTemplateCardProps> = ({
  template,
  onDragStart,
  onClick,
}) => {
  const Icon = getNodeIcon(template.node_type, template.node_subtype);
  const category = getCategoryFromNodeType(template.node_type);
  const colorScheme = getCategoryColor(category);

  const handleDragStart = (e: DragEvent<HTMLDivElement>) => {
    onDragStart(e, template);
    // Add visual feedback
    e.currentTarget.style.opacity = '0.5';
  };

  const handleDragEnd = (e: DragEvent<HTMLDivElement>) => {
    // Remove visual feedback
    e.currentTarget.style.opacity = '1';
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <Card
        draggable
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onClick={onClick}
        className={cn(
          'p-3 transition-all cursor-move group',
          'hover:bg-accent/50',
          'hover:border-primary/50'
        )}>
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'p-2 rounded-md transition-colors',
              colorScheme.bg,
              'group-hover:bg-opacity-80'
            )}
            style={colorScheme.bgStyle}
          >
            <Icon className={cn('w-4 h-4', colorScheme.icon)} style={colorScheme.iconStyle} />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium truncate">{template.name}</h4>
            <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
              {template.description}
            </p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
};
