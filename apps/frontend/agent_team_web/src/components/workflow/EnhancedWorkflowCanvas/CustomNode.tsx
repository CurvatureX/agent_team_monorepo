"use client";

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { cn } from '@/lib/utils';
import type { WorkflowNodeData } from '@/types/workflow-editor';
import { getNodeIcon, getCategoryColor, getParameterPreview } from '@/utils/nodeHelpers';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

type CustomNodeProps = NodeProps<WorkflowNodeData>;

export const CustomNode = memo<CustomNodeProps>(({ data, selected }) => {
  const Icon = getNodeIcon(data.template.node_type, data.template.node_subtype);
  const colorScheme = getCategoryColor(data.template.category);
  const parameterPreview = getParameterPreview(data.parameters);

  return (
    <TooltipProvider>
      <Card
        className={cn(
          'min-w-[200px] max-w-[280px] border-2 transition-all duration-200',
          colorScheme.border,
          selected && 'ring-2 ring-primary ring-offset-2 ring-offset-background',
          data.status === 'running' && 'animate-pulse',
          data.status === 'error' && 'border-destructive bg-destructive/5',
          data.status === 'success' && 'border-green-500 bg-green-500/5'
        )}
      >
        <CardHeader className="p-3 pb-2">
          <div className="flex items-center gap-2">
            <div className={cn('p-1.5 rounded', colorScheme.bg)}>
              <Icon className={cn('w-4 h-4', colorScheme.icon)} />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm truncate">{data.label}</h4>
              <p className="text-xs text-muted-foreground truncate">
                {data.template.node_type.replace(/_/g, ' ')}
              </p>
            </div>
            {/* Status badge */}
            {data.status && data.status !== 'idle' && (
              <Tooltip>
                <TooltipTrigger>
                  <Badge
                    variant={data.status === 'error' ? 'destructive' : 
                            data.status === 'success' ? 'default' : 'secondary'}
                    className={cn(
                      'text-xs px-1.5 py-0.5 h-5',
                      data.status === 'running' && 'animate-pulse',
                      data.status === 'success' && 'bg-green-500 hover:bg-green-600'
                    )}
                  >
                    {data.status === 'running' && '●'}
                    {data.status === 'success' && '✓'}
                    {data.status === 'error' && '✕'}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  Status: {data.status}
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </CardHeader>

        {/* Parameters Preview */}
        {parameterPreview.length > 0 && (
          <CardContent className="p-3 pt-0">
            <div className="space-y-1 border-t border-border pt-2">
              {parameterPreview.map((param, index) => (
                <Tooltip key={index}>
                  <TooltipTrigger asChild>
                    <p className="text-xs text-muted-foreground truncate cursor-help">
                      {param}
                    </p>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">{param}</p>
                  </TooltipContent>
                </Tooltip>
              ))}
            </div>
          </CardContent>
        )}

        {/* Handles */}
        {data.template.node_type !== 'TRIGGER' && (
          <Handle
            type="target"
            position={Position.Left}
            className={cn(
              'w-3 h-3 border-2',
              '!bg-background !border-muted-foreground',
              'hover:!bg-primary hover:!border-primary'
            )}
          />
        )}
        
        <Handle
          type="source"
          position={Position.Right}
          className={cn(
            'w-3 h-3 border-2',
            '!bg-background !border-muted-foreground',
            'hover:!bg-primary hover:!border-primary'
          )}
        />
      </Card>
    </TooltipProvider>
  );
});

CustomNode.displayName = 'CustomNode';