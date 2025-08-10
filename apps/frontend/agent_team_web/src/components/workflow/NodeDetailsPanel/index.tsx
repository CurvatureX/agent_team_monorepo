"use client";

import React, { useCallback, useState } from 'react';
import { X, Save, Trash2, Copy, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useWorkflow, useEditorUI } from '@/store/hooks';
import { FormRenderer } from './FormRenderer';
import { getNodeIcon, getCategoryColor } from '@/utils/nodeHelpers';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from '@/components/ui/dialog';

interface NodeDetailsPanelProps {
  className?: string;
}

export const NodeDetailsPanel: React.FC<NodeDetailsPanelProps> = ({ className }) => {
  const { selectedNode, updateNodeParameters, updateNodeData, deleteNode } = useWorkflow();
  const { detailsPanelOpen, setDetailsPanelOpen } = useEditorUI();
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleClose = useCallback(() => {
    setDetailsPanelOpen(false);
    setFormErrors({});
    setHasChanges(false);
  }, [setDetailsPanelOpen]);

  const handleParameterChange = useCallback((newParameters: Record<string, unknown>) => {
    if (selectedNode) {
      updateNodeParameters({
        nodeId: selectedNode.id,
        parameters: newParameters,
      });
      setHasChanges(true);
    }
  }, [selectedNode, updateNodeParameters]);

  const handleLabelChange = useCallback((newLabel: string) => {
    if (selectedNode) {
      updateNodeData({
        nodeId: selectedNode.id,
        data: { label: newLabel },
      });
      setHasChanges(true);
    }
  }, [selectedNode, updateNodeData]);

  const handleDelete = useCallback(() => {
    if (selectedNode) {
      deleteNode(selectedNode.id);
      setDeleteDialogOpen(false);
      handleClose();
    }
  }, [selectedNode, deleteNode, handleClose]);

  const handleDuplicate = useCallback(() => {
    // TODO: Implement node duplication
    console.log('Duplicate node:', selectedNode?.id);
  }, [selectedNode]);

  if (!selectedNode) return null;

  const Icon = getNodeIcon(
    selectedNode.data.template.node_type,
    selectedNode.data.template.node_subtype
  );
  const colorScheme = getCategoryColor(selectedNode.data.template.category);

  return (
    <AnimatePresence mode="wait">
      {detailsPanelOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 350, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'h-full bg-card border-l border-border overflow-hidden',
            'flex flex-col',
            className
          )}
        >
          {/* Header */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className={cn('p-1.5 rounded', colorScheme.bg)}>
                  <Icon className={cn('w-4 h-4', colorScheme.icon)} />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Node Details</h3>
                  <p className="text-xs text-muted-foreground">
                    {selectedNode.data.template.node_type.replace(/_/g, ' ')}
                  </p>
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

            {/* Node name */}
            <div className="space-y-2">
              <Label>Node Name</Label>
              <Input
                type="text"
                value={selectedNode.data.label}
                onChange={(e) => handleLabelChange(e.target.value)}
              />
            </div>
          </div>

          <Separator />
          
          {/* Node info */}
          <div className="p-4 bg-muted/30">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-muted-foreground mt-0.5" />
              <div className="flex-1 text-xs text-muted-foreground">
                <p>{selectedNode.data.template.description}</p>
                <p className="mt-1">
                  Version: {selectedNode.data.template.version} • 
                  ID: {selectedNode.data.template.id}
                </p>
              </div>
            </div>
          </div>
          
          <Separator />

          {/* Parameters form */}
          <ScrollArea className="flex-1 p-4">
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
          </ScrollArea>

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
              <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogTrigger asChild>
                  <Button
                    variant="destructive"
                    className="flex-1"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Delete Node</DialogTitle>
                    <DialogDescription>
                      Are you sure you want to delete &quot;{selectedNode.data.label}&quot;? This action cannot be undone.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setDeleteDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleDelete}
                    >
                      Delete
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
            {hasChanges && (
              <div className="text-xs text-muted-foreground text-center">
                <Save className="w-3 h-3 inline mr-1" />
                Changes saved automatically
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};