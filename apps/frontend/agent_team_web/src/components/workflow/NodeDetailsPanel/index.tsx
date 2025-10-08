"use client";

import React, { useCallback, useState, useEffect, useRef } from "react";
import Image from "next/image";
import {
  X,
  Save,
  Trash2,
  Copy,
  Info,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useWorkflow, useEditorUI } from "@/store/hooks";
import { useAuth } from "@/contexts/auth-context";
import { apiRequest } from "@/lib/api/fetcher";
import { FormRenderer } from "./FormRenderer";
import {
  getNodeIcon,
  getCategoryColor,
  getCategoryFromNodeType,
  getProviderIcon,
} from "@/utils/nodeHelpers";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface NodeDetailsPanelProps {
  className?: string;
}

export const NodeDetailsPanel: React.FC<NodeDetailsPanelProps> = ({
  className,
}) => {
  const {
    selectedNode,
    updateNodeParameters,
    deleteNode,
    exportWorkflow,
    metadata,
  } = useWorkflow();
  const { detailsPanelOpen, setDetailsPanelOpen } = useEditorUI();
  const { session } = useAuth();
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [saveStatus, setSaveStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [countdown, setCountdown] = useState(5);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const autoSaveRef = useRef<(() => Promise<void>) | undefined>(undefined);

  // Auto-save function - always use the latest version
  autoSaveRef.current = async () => {
    console.log("[Auto-save] Function called");

    if (!metadata.id || !session?.access_token) {
      console.warn(
        "[Auto-save] Cannot auto-save: missing workflow ID or auth token",
        {
          hasWorkflowId: !!metadata.id,
          hasToken: !!session?.access_token,
        }
      );
      return;
    }

    try {
      console.log("[Auto-save] Starting save for workflow:", metadata.id);
      setSaveStatus("saving");
      const workflowData = exportWorkflow();

      console.log("[Auto-save] Workflow data exported:", {
        nodes: workflowData.nodes.length,
        connections: workflowData.connections.length,
      });

      await apiRequest(
        `/api/proxy/v1/app/workflows/${metadata.id}`,
        session.access_token,
        "PUT",
        {
          name: workflowData.metadata.name,
          description: workflowData.metadata.description,
          nodes: workflowData.nodes,
          connections: workflowData.connections,
          tags: workflowData.metadata.tags,
        }
      );

      console.log("[Auto-save] Save successful");
      setSaveStatus("saved");
      setHasChanges(false);

      // Reset status after 2 seconds
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch (error) {
      console.error("[Auto-save] Failed:", error);
      setSaveStatus("error");

      // Reset error status after 3 seconds
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  };

  // Debounced auto-save effect with countdown (5 seconds after last change)
  useEffect(() => {
    if (hasChanges && metadata.id) {
      console.log(
        "[Auto-save] Setting 5-second countdown for workflow:",
        metadata.id
      );

      // Clear existing intervals and timeouts
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }

      // Reset countdown to 5
      setCountdown(5);

      // Update countdown every second
      let currentCountdown = 5;
      countdownIntervalRef.current = setInterval(() => {
        currentCountdown -= 1;
        setCountdown(currentCountdown);

        if (currentCountdown <= 0) {
          if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current);
          }
        }
      }, 1000);

      // Trigger save after 5 seconds
      saveTimeoutRef.current = setTimeout(() => {
        console.log(
          "[Auto-save] Timeout triggered, calling autoSaveRef.current"
        );
        if (countdownIntervalRef.current) {
          clearInterval(countdownIntervalRef.current);
        }
        autoSaveRef.current?.();
      }, 5000);
    } else {
      console.log("[Auto-save] Conditions not met:", {
        hasChanges,
        workflowId: metadata.id,
      });
      // Clear countdown if conditions not met
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    }

    // Cleanup on unmount
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    };
  }, [hasChanges, metadata.id]);

  const handleClose = useCallback(() => {
    setDetailsPanelOpen(false);
    setFormErrors({});
    setHasChanges(false);
    setSaveStatus("idle");
    setCountdown(5);

    // Clear any active timers
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }
  }, [setDetailsPanelOpen]);

  const handleParameterChange = useCallback(
    (newParameters: Record<string, unknown>) => {
      if (selectedNode) {
        console.log("[Auto-save] Parameter changed for node:", selectedNode.id);
        updateNodeParameters({
          nodeId: selectedNode.id,
          parameters: newParameters,
        });
        setHasChanges(true);
        setSaveStatus("idle"); // Reset status when user makes changes
        setCountdown(5); // Reset countdown display
      }
    },
    [selectedNode, updateNodeParameters]
  );

  const handleDelete = useCallback(() => {
    if (selectedNode) {
      deleteNode(selectedNode.id);
      setDeleteDialogOpen(false);
      handleClose();
    }
  }, [selectedNode, deleteNode, handleClose]);

  const handleDuplicate = useCallback(() => {
    // TODO: Implement node duplication
    console.log("Duplicate node:", selectedNode?.id);
  }, [selectedNode]);

  if (!selectedNode) return null;

  const Icon = getNodeIcon(
    selectedNode.data.template.node_type,
    selectedNode.data.template.node_subtype
  );
  const providerIcon = getProviderIcon(
    selectedNode.data.template.node_type,
    selectedNode.data.template.node_subtype
  );
  const category = getCategoryFromNodeType(
    selectedNode.data.template.node_type
  );
  const colorScheme = getCategoryColor(category);

  return (
    <AnimatePresence mode="wait">
      {detailsPanelOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 350, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className={cn(
            "h-full bg-card border-l border-border overflow-hidden",
            "flex flex-col",
            className
          )}
        >
          {/* Header */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className={cn("p-1.5 rounded", colorScheme.bg)}>
                  {providerIcon ? (
                    <Image
                      src={providerIcon}
                      alt={selectedNode.data.template.node_subtype}
                      width={16}
                      height={16}
                      className="w-4 h-4"
                    />
                  ) : (
                    <Icon className={cn("w-4 h-4", colorScheme.icon)} />
                  )}
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Node Details</h3>
                  <div className="text-sm font-semibold text-foreground">
                    {selectedNode.data.label}
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClose}
                className="h-6 w-6 p-0"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Node info */}
          <div className="p-4 bg-muted/30">
            <div className="space-y-2">
              {/* Node description */}
              {selectedNode.data.description && (
                <div>
                  <p className="text-xs text-muted-foreground font-medium">
                    Description:
                  </p>
                  <p className="text-sm text-foreground mt-1">
                    {selectedNode.data.description}
                  </p>
                </div>
              )}

              {/* Template info */}
              <div
                className={cn(
                  "flex items-start gap-2",
                  selectedNode.data.description && "pt-2 border-t"
                )}
              >
                <Info className="w-3 h-3 text-muted-foreground mt-0.5 flex-shrink-0" />
                <div className="flex-1 text-xs text-muted-foreground">
                  <p className="mt-1 opacity-70">
                    Version: {selectedNode.data.template.version} • Type:{" "}
                    {selectedNode.data.template.node_type}
                    {"-"}
                    {selectedNode.data.template.node_subtype}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Separator />

          {/* Parameters form */}
          <div className="flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="p-4">
                <h4 className="text-sm font-medium mb-4">Parameters</h4>
                {selectedNode.data.template.parameter_schema ? (
                  <FormRenderer
                    schema={selectedNode.data.template.parameter_schema}
                    values={selectedNode.data.parameters}
                    onChange={handleParameterChange}
                    errors={formErrors}
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No parameters available for this node type.
                  </p>
                )}
              </div>
            </ScrollArea>
          </div>

          <Separator />

          {/* Actions */}
          <div className="p-4 space-y-2">
            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={handleDuplicate}
                className="flex-1"
              >
                <Copy className="w-4 h-4 mr-2" />
                Duplicate
              </Button>
              <Dialog
                open={deleteDialogOpen}
                onOpenChange={setDeleteDialogOpen}
              >
                <DialogTrigger asChild>
                  <Button variant="destructive" className="flex-1">
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Delete Node</DialogTitle>
                    <DialogDescription>
                      Are you sure you want to delete &quot;
                      {selectedNode.data.label}&quot;? This action cannot be
                      undone.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setDeleteDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button variant="destructive" onClick={handleDelete}>
                      Delete
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            {/* Save status indicator */}
            <div className="text-xs text-center min-h-[20px]">
              {saveStatus === "saving" && (
                <div className="text-muted-foreground flex items-center justify-center gap-1">
                  <Save className="w-3 h-3 animate-pulse" />
                  <span>Saving changes...</span>
                </div>
              )}
              {saveStatus === "saved" && (
                <div className="text-green-600 flex items-center justify-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Changes saved</span>
                </div>
              )}
              {saveStatus === "error" && (
                <div className="text-destructive flex items-center justify-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  <span>Failed to save</span>
                </div>
              )}
              {saveStatus === "idle" && hasChanges && (
                <div className="text-muted-foreground/60 flex items-center justify-center gap-1">
                  <Save className="w-3 h-3" />
                  <span>Auto-saving in {countdown}s...</span>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
