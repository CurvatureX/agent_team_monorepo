"use client";

import React, { useCallback } from 'react';
import { Provider } from 'jotai';
import { cn } from '@/lib/utils';
import { NodeSidebar } from '../NodeSidebar';
import { EnhancedWorkflowCanvas } from '../EnhancedWorkflowCanvas';
import { NodeDetailsPanel } from '../NodeDetailsPanel';
import { useWorkflow, useEditorUI } from '@/store/hooks';
import type { NodeTemplate } from '@/types/node-template';
import type { WorkflowData } from '@/types/workflow';

interface WorkflowEditorProps {
  workflowId?: string;
  initialData?: WorkflowData;
  onSave?: (workflow: WorkflowData) => void;
  readOnly?: boolean;
  className?: string;
}

const WorkflowEditorContent: React.FC<WorkflowEditorProps> = ({
  initialData,
  onSave,
  readOnly = false,
  className,
}) => {
  const { addNode } = useWorkflow();
  const { detailsPanelOpen } = useEditorUI();

  // Handle node selection from sidebar
  const handleNodeSelect = useCallback((template: NodeTemplate) => {
    // Add node at center of viewport
    const centerPosition = {
      x: window.innerWidth / 2 - 100,
      y: window.innerHeight / 2 - 50,
    };
    
    addNode({ template, position: centerPosition });
  }, [addNode]);

  return (
    <div className={cn(
      'flex h-screen bg-background',
      className
    )}>
      {/* Left Sidebar - Node Library */}
      <NodeSidebar onNodeSelect={handleNodeSelect} />

      {/* Center - Canvas */}
      <div className="flex-1 relative">
        <EnhancedWorkflowCanvas
          workflowData={initialData}
          onWorkflowChange={onSave}
          readOnly={readOnly}
        />
      </div>

      {/* Right Panel - Node Details */}
      {detailsPanelOpen && <NodeDetailsPanel />}
    </div>
  );
};

export const WorkflowEditor: React.FC<WorkflowEditorProps> = (props) => {
  return (
    <Provider>
      <WorkflowEditorContent {...props} />
    </Provider>
  );
};