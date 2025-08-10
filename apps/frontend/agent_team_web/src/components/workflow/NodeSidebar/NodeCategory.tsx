"use client";

import React, { useState, DragEvent } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { NodeTemplate, NodeCategory as NodeCategoryType } from '@/types/node-template';
import { NodeTemplateCard } from './NodeTemplateCard';
import { getCategoryColor } from '@/utils/nodeHelpers';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface NodeCategoryProps {
  category: NodeCategoryType;
  templates: NodeTemplate[];
  count: number;
  defaultExpanded?: boolean;
  onNodeSelect: (template: NodeTemplate) => void;
  onNodeDragStart: (e: DragEvent<HTMLDivElement>, template: NodeTemplate) => void;
}

export const NodeCategory: React.FC<NodeCategoryProps> = ({
  category,
  templates,
  count,
  defaultExpanded = true,
  onNodeSelect,
  onNodeDragStart,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const colorScheme = getCategoryColor(category);

  return (
    <div className="mb-4">
      <Button
        variant="ghost"
        onClick={() => setExpanded(!expanded)}
        className="w-full justify-between p-2 h-auto font-medium"
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <span className="text-sm">{category}</span>
        </div>
        <Badge 
          variant="secondary" 
          className={cn('text-xs h-5', colorScheme.bg, colorScheme.icon)}
        >
          {count}
        </Badge>
      </Button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-2 px-2">
              {templates.map((template) => (
                <NodeTemplateCard
                  key={template.id}
                  template={template}
                  onDragStart={onNodeDragStart}
                  onClick={() => onNodeSelect(template)}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};