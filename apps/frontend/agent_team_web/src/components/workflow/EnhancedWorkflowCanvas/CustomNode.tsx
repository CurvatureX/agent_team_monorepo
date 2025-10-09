"use client";

import React, { memo } from "react";
import Image from "next/image";
import { Handle, Position, NodeProps } from "reactflow";
import { cn } from "@/lib/utils";
import type { WorkflowNodeData } from "@/types/workflow-editor";
import {
  getNodeIcon,
  getCategoryColor,
  getCategoryFromNodeType,
  getParameterPreview,
  formatSubtype,
  getProviderIcon,
  validateNodeParameters,
} from "@/utils/nodeHelpers";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AlertTriangle } from "lucide-react";

type CustomNodeProps = NodeProps<WorkflowNodeData>;

export const CustomNode = memo<CustomNodeProps>(({ data, selected }) => {
  const Icon = getNodeIcon(data.template.node_type, data.template.node_subtype);
  const providerIcon = getProviderIcon(
    data.template.node_type,
    data.template.node_subtype
  );
  const category = getCategoryFromNodeType(data.template.node_type);
  const colorScheme = getCategoryColor(category);
  const parameterPreview = getParameterPreview(data.parameters);

  // Validate node parameters
  const requiredFields = data.template.parameter_schema?.required || [];
  const validation = validateNodeParameters(data.parameters, requiredFields);
  const hasValidationErrors = !validation.isValid;

  // Debug: Log status changes
  React.useEffect(() => {
    if (data.status && data.status !== "idle") {
      console.log(`Node ${data.label} status:`, data.status);
    }
  }, [data.status, data.label]);

  return (
    <TooltipProvider>
      <Card
        className={cn(
          "min-w-[200px] max-w-[280px] border-2 transition-all duration-200 shadow-lg",
          selected ? "border-primary shadow-xl" : colorScheme.border,
          data.status === "running" &&
            "animate-pulse border-blue-500 bg-blue-500/10",
          data.status === "error" && "border-red-500 bg-red-500/10",
          data.status === "success" && "border-green-500 bg-green-500/10",
          hasValidationErrors && data.status === "idle" && "border-red-500 border-2"
        )}
      >
        <CardHeader className="p-3 pb-2">
          <div className="flex items-center gap-2">
            <div className={cn("p-1.5 rounded", colorScheme.bg)}>
              {providerIcon ? (
                <Image
                  src={providerIcon}
                  alt={data.template.node_subtype}
                  width={16}
                  height={16}
                  className="w-4 h-4"
                />
              ) : (
                <Icon className={cn("w-4 h-4", colorScheme.icon)} />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm truncate">{data.label}</h4>
              <p className="text-xs text-muted-foreground truncate">
                {formatSubtype(data.template.node_subtype)}
              </p>
            </div>
            {/* Validation error badge */}
            {hasValidationErrors && data.status === "idle" && (
              <Tooltip>
                <TooltipTrigger>
                  <Badge
                    variant="destructive"
                    className="text-xs px-1.5 py-0.5 h-5 min-w-[20px]"
                  >
                    <AlertTriangle className="w-3 h-3" />
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">
                    Missing required fields:
                  </p>
                  <ul className="text-xs list-disc list-inside mt-1">
                    {validation.missingFields.map((field) => (
                      <li key={field}>{field}</li>
                    ))}
                  </ul>
                </TooltipContent>
              </Tooltip>
            )}
            {/* Status badge - Always show for debugging */}
            {data.status && (
              <Tooltip>
                <TooltipTrigger>
                  <Badge
                    variant={
                      data.status === "error"
                        ? "destructive"
                        : data.status === "success"
                        ? "default"
                        : data.status === "idle"
                        ? "outline"
                        : "secondary"
                    }
                    className={cn(
                      "text-sm px-2 py-1 h-6 min-w-[24px] font-bold",
                      data.status === "running" &&
                        "animate-pulse bg-blue-500 hover:bg-blue-600 text-white",
                      data.status === "success" &&
                        "bg-green-500 hover:bg-green-600 text-white",
                      data.status === "error" &&
                        "bg-red-500 hover:bg-red-600 text-white",
                      data.status === "idle" && "opacity-30"
                    )}
                  >
                    {data.status === "running" && "●"}
                    {data.status === "success" && "✓"}
                    {data.status === "error" && "✕"}
                    {data.status === "idle" && "○"}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  Status: {data.status || "unknown"}
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
        {data.template.node_type !== "TRIGGER" && (
          <Handle
            type="target"
            position={Position.Left}
            className={cn(
              "w-3 h-3 border-2",
              "!bg-background !border-muted-foreground",
              "hover:!bg-primary hover:!border-primary"
            )}
          />
        )}

        <Handle
          type="source"
          position={Position.Right}
          className={cn(
            "w-3 h-3 border-2",
            "!bg-background !border-muted-foreground",
            "hover:!bg-primary hover:!border-primary"
          )}
        />

        {/* AI_AGENT specific handles for attached nodes (top and bottom) */}
        {data.template.node_type === "AI_AGENT" && (
          <>
            <Handle
              type="target"
              position={Position.Top}
              id="attachment-top"
              className={cn(
                "w-3 h-3 border-2",
                "!bg-purple-500 !border-purple-600",
                "hover:!bg-purple-400 hover:!border-purple-500"
              )}
            />
            <Handle
              type="target"
              position={Position.Bottom}
              id="attachment-bottom"
              className={cn(
                "w-3 h-3 border-2",
                "!bg-purple-500 !border-purple-600",
                "hover:!bg-purple-400 hover:!border-purple-500"
              )}
            />
          </>
        )}

        {/* TOOL and MEMORY specific handles for attaching to AI_AGENT (top and bottom) */}
        {(data.template.node_type === "TOOL" || data.template.node_type === "MEMORY") && (
          <>
            <Handle
              type="source"
              position={Position.Top}
              id="attachment-top"
              className={cn(
                "w-3 h-3 border-2",
                "!bg-purple-500 !border-purple-600",
                "hover:!bg-purple-400 hover:!border-purple-500"
              )}
            />
            <Handle
              type="source"
              position={Position.Bottom}
              id="attachment-bottom"
              className={cn(
                "w-3 h-3 border-2",
                "!bg-purple-500 !border-purple-600",
                "hover:!bg-purple-400 hover:!border-purple-500"
              )}
            />
          </>
        )}
      </Card>
    </TooltipProvider>
  );
});

CustomNode.displayName = "CustomNode";
