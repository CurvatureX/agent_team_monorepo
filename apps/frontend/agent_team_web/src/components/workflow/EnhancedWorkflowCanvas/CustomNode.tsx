"use client";

import React, { memo } from 'react';
import Image from 'next/image';
import { Handle, Position, NodeProps } from 'reactflow';
import { cn } from '@/lib/utils';
import type { WorkflowNodeData } from '@/types/workflow-editor';
import { getNodeIcon, getCategoryColor, getCategoryFromNodeType, getParameterPreview, formatSubtype, getProviderIcon } from '@/utils/nodeHelpers';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

type CustomNodeProps = NodeProps<WorkflowNodeData>;

export const CustomNode = memo<CustomNodeProps>(({ data, selected }) => {
  const Icon = getNodeIcon(data.template.node_type, data.template.node_subtype);
  const providerIcon = getProviderIcon(data.template.node_type, data.template.node_subtype);
  const category = getCategoryFromNodeType(data.template.node_type);
  const colorScheme = getCategoryColor(category);
  const parameterPreview = getParameterPreview(data.parameters);

  // Debug: Log status changes
  React.useEffect(() => {
    if (data.status && data.status !== 'idle') {
      console.log(`Node ${data.label} status:`, data.status);
    }
  }, [data.status, data.label]);

  return (
    <TooltipProvider>
      <Card
        className={cn(
          'min-w-[200px] max-w-[280px] border-2 transition-all duration-200 shadow-lg',
          selected ? 'border-primary shadow-xl' : colorScheme.border,
          data.status === 'running' && 'animate-pulse border-blue-500 bg-blue-500/10',
          data.status === 'error' && 'border-red-500 bg-red-500/10',
          data.status === 'success' && 'border-green-500 bg-green-500/10'
        )}
      >
        <CardHeader className="p-3 pb-2">
          <div className="flex items-center gap-2">
            <div className={cn('p-1.5 rounded', colorScheme.bg)}>
              {providerIcon ? (
                <Image
                  src={providerIcon}
                  alt={data.template.node_subtype}
                  width={16}
                  height={16}
                  className="w-4 h-4"
                />
              ) : (
                <Icon className={cn('w-4 h-4', colorScheme.icon)} />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm truncate">{data.label}</h4>
              <p className="text-xs text-muted-foreground truncate">
                {formatSubtype(data.template.node_subtype)}
              </p>
            </div>
            {/* Status badge - Always show for debugging */}
            {data.status && (
              <Tooltip>
                <TooltipTrigger>
                  <Badge
                    variant={data.status === 'error' ? 'destructive' :
                            data.status === 'success' ? 'default' :
                            data.status === 'idle' ? 'outline' : 'secondary'}
                    className={cn(
                      'text-sm px-2 py-1 h-6 min-w-[24px] font-bold',
                      data.status === 'running' && 'animate-pulse bg-blue-500 hover:bg-blue-600 text-white',
                      data.status === 'success' && 'bg-green-500 hover:bg-green-600 text-white',
                      data.status === 'error' && 'bg-red-500 hover:bg-red-600 text-white',
                      data.status === 'idle' && 'opacity-30'
                    )}
                  >
                    {data.status === 'running' && '●'}
                    {data.status === 'success' && '✓'}
                    {data.status === 'error' && '✕'}
                    {data.status === 'idle' && '○'}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  Status: {data.status || 'unknown'}
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
