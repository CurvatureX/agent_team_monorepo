"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PlayIcon, XIcon } from "lucide-react";
import { FormRenderer } from "../NodeDetailsPanel/FormRenderer";
import type { ParameterSchema, SchemaProperty } from "@/types/node-template";
import type { Workflow } from "@/types/workflow";
import type { ExecutionRequest } from "@/lib/api/hooks/useExecutionApi";
import { useNodeTemplates } from "@/store/hooks/useNodeTemplates";

interface RunWorkflowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflow: Workflow | null | undefined;
  onRun: (request: ExecutionRequest) => void;
  isExecuting?: boolean;
}

export const RunWorkflowDialog: React.FC<RunWorkflowDialogProps> = ({
  open,
  onOpenChange,
  workflow,
  onRun,
  isExecuting = false,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string>("__from_beginning__");
  const [inputs, setInputs] = useState<Record<string, unknown>>({});
  const [skipTriggerValidation, setSkipTriggerValidation] = useState(false);

  const { templates: nodeTemplates } = useNodeTemplates();

  // Get available nodes from workflow
  const nodes = useMemo(() => {
    if (!workflow?.nodes) return [];
    return workflow.nodes;
  }, [workflow]);

  // Get selected node and its template
  const selectedNode = useMemo(() => {
    if (!selectedNodeId || selectedNodeId === "__from_beginning__" || !nodes) return null;
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [selectedNodeId, nodes]);

  const selectedNodeTemplate = useMemo(() => {
    if (!selectedNode || !nodeTemplates) return null;

    // Find template by matching type/subtype (API format) with node_type/node_subtype (template format)
    // API WorkflowNode uses: type, subtype
    // NodeTemplate uses: node_type, node_subtype
    return nodeTemplates.find(
      (t) =>
        t.node_type === selectedNode.type &&
        t.node_subtype === selectedNode.subtype
    ) || null;
  }, [selectedNode, nodeTemplates]);

  // Get input parameter schema from the selected node's template
  const inputParamsSchema = useMemo((): ParameterSchema | null => {
    if (!selectedNodeTemplate) return null;

    // input_params is at the top level of the template, not in parameter_schema
    const inputParams = selectedNodeTemplate.input_params;

    // Check if input_params exists and is a schema object
    if (!inputParams || typeof inputParams !== 'object') return null;

    // If input_params is already a schema with properties, use it directly
    if ('properties' in inputParams && inputParams.properties) {
      return inputParams as ParameterSchema;
    }

    // If input_params has type=object and properties, extract them
    const typedInputParams = inputParams as { type?: string; properties?: Record<string, unknown>; required?: string[] };
    if (typedInputParams.type === 'object' && typedInputParams.properties) {
      return {
        type: 'object',
        properties: typedInputParams.properties as Record<string, SchemaProperty>,
        required: typedInputParams.required || [],
      };
    }

    return null;
  }, [selectedNodeTemplate]);

  // Reset inputs when node selection changes
  useEffect(() => {
    if (!selectedNodeId || selectedNodeId === "__from_beginning__" || !inputParamsSchema) {
      setInputs({});
      return;
    }

    // Initialize inputs with default values
    const defaultInputs: Record<string, unknown> = {};
    if (inputParamsSchema.properties) {
      Object.entries(inputParamsSchema.properties).forEach(([key, prop]) => {
        if (prop.default !== undefined) {
          defaultInputs[key] = prop.default;
        }
      });
    }
    setInputs(defaultInputs);
  }, [selectedNodeId, inputParamsSchema]);

  // Reset dialog state when closed
  useEffect(() => {
    if (!open) {
      setSelectedNodeId("__from_beginning__");
      setInputs({});
      setSkipTriggerValidation(false);
    }
  }, [open]);

  const handleRun = () => {
    const request: ExecutionRequest = {
      inputs,
      skip_trigger_validation: skipTriggerValidation,
    };

    // Add start_from_node if a specific node is selected
    if (selectedNodeId && selectedNodeId !== "__from_beginning__") {
      request.start_from_node = selectedNodeId;
    }

    onRun(request);
    onOpenChange(false);
  };

  const canRun = useMemo(() => {
    // Can always run from the beginning
    if (!selectedNodeId || selectedNodeId === "__from_beginning__") return true;

    // If a node is selected, check if required inputs are filled
    if (!inputParamsSchema || !inputParamsSchema.required) return true;

    // Check if all required fields have values
    return inputParamsSchema.required.every((field) => {
      const value = inputs[field];
      return value !== undefined && value !== null && value !== "";
    });
  }, [selectedNodeId, inputParamsSchema, inputs]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Run Workflow</DialogTitle>
          <DialogDescription>
            Select a starting node and configure its inputs, or run from the beginning
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-6 py-4">
            {/* Node Selection */}
            <div className="space-y-2">
              <Label htmlFor="start-node">Starting Node (Optional)</Label>
              <Select
                value={selectedNodeId}
                onValueChange={setSelectedNodeId}
                disabled={isExecuting}
              >
                <SelectTrigger id="start-node">
                  <SelectValue placeholder="Run from the beginning" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__from_beginning__">
                    <span className="text-muted-foreground">From the beginning</span>
                  </SelectItem>
                  {nodes.map((node) => (
                    <SelectItem key={node.id} value={node.id}>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{node.name || node.id}</span>
                        <span className="text-xs text-muted-foreground">
                          ({node.subtype})
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedNode && (
                <p className="text-xs text-muted-foreground">
                  Starting from: <span className="font-medium">{selectedNode.name}</span>
                </p>
              )}
            </div>

            {/* Input Parameters Form */}
            {selectedNodeId && selectedNodeId !== "__from_beginning__" && inputParamsSchema && inputParamsSchema.properties && (
              <div className="space-y-4">
                <div className="border-t pt-4">
                  <h4 className="text-sm font-semibold mb-4">Input Parameters</h4>
                  <FormRenderer
                    schema={inputParamsSchema}
                    values={inputs}
                    onChange={setInputs}
                  />
                </div>
              </div>
            )}

            {selectedNodeId && selectedNodeId !== "__from_beginning__" && !inputParamsSchema?.properties && (
              <div className="text-sm text-muted-foreground border rounded-md p-4 bg-muted/30">
                This node has no input parameters to configure.
              </div>
            )}

            {/* Advanced Options */}
            <div className="space-y-3 border-t pt-4">
              <h4 className="text-sm font-semibold">Advanced Options</h4>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="skip-trigger"
                  checked={skipTriggerValidation}
                  onChange={(e) => setSkipTriggerValidation(e.target.checked)}
                  disabled={isExecuting}
                  className="rounded border-gray-300 text-primary focus:ring-primary"
                />
                <Label
                  htmlFor="skip-trigger"
                  className="text-sm font-normal cursor-pointer"
                >
                  Skip trigger validation
                </Label>
              </div>
            </div>
          </div>
        </ScrollArea>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isExecuting}
          >
            <XIcon className="w-4 h-4 mr-2" />
            Cancel
          </Button>
          <Button
            onClick={handleRun}
            disabled={!canRun || isExecuting}
          >
            <PlayIcon className="w-4 h-4 mr-2" />
            {isExecuting ? "Running..." : "Run"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
