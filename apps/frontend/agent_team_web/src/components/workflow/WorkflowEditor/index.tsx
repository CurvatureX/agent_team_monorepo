"use client";

import React, { useCallback } from 'react';
import { cn } from '@/lib/utils';
import { NodeSidebar } from '../NodeSidebar';
import { EnhancedWorkflowCanvas } from '../EnhancedWorkflowCanvas';
import { NodeDetailsPanel } from '../NodeDetailsPanel';
import { useWorkflow, useEditorUI } from '@/store/hooks';
import type { NodeTemplate } from '@/types/node-template';
import type { Workflow } from '@/types/workflow';

interface WorkflowEditorProps {
  workflowId?: string;
  initialWorkflow?: Workflow;  // 直接使用API的Workflow格式
  onSave?: (workflow: Workflow) => void;
  onApiSave?: (workflow?: Workflow) => void;  // API保存回调，接受工作流参数
  isSaving?: boolean;      // 添加保存状态
  readOnly?: boolean;
  className?: string;
  onExecute?: (workflowId: string) => void;  // 执行回调
  onToggleFullscreen?: () => void;  // 全屏切换回调
}

const WorkflowEditorContent: React.FC<WorkflowEditorProps> = ({
  initialWorkflow,
  onSave,
  onApiSave,
  isSaving = false,
  readOnly = false,
  className,
  onExecute,
  onToggleFullscreen,
}) => {
  const { addNode, exportWorkflow } = useWorkflow();
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

  // Handle save - export current state and call both callbacks
  const handleSaveClick = useCallback(() => {
    if (onApiSave) {
      // First export the current workflow state
      const currentState = exportWorkflow();
      console.log('Exported workflow state:', currentState);

      // Convert timestamps to strings if they are numbers
      const metadata = {
        ...currentState.metadata,
        created_at: typeof currentState.metadata.created_at === 'number'
          ? new Date(currentState.metadata.created_at).toISOString()
          : currentState.metadata.created_at,
        updated_at: typeof currentState.metadata.updated_at === 'number'
          ? new Date(currentState.metadata.updated_at).toISOString()
          : currentState.metadata.updated_at,
        // Convert version to number if it's a string
        version: typeof currentState.metadata.version === 'string'
          ? parseInt(currentState.metadata.version, 10) || 1
          : currentState.metadata.version || 1,
      };

      // Merge with initial workflow to preserve all fields (ID, settings, etc.)
      const updatedWorkflow: Workflow = {
        ...initialWorkflow,
        ...metadata,
        nodes: currentState.nodes,
        edges: (currentState as any).edges || [],
        // Ensure edges is always an array
        ...((currentState as any).edges && (currentState as any).edges.length > 0 ? { edges: (currentState as any).edges } : {}),
      } as unknown as Workflow;

      console.log('Updated workflow with edges:', {
        id: updatedWorkflow.id,
        nodesCount: updatedWorkflow.nodes?.length,
        edgesCount: (updatedWorkflow as any).edges?.length,
        edges: (updatedWorkflow as any).edges,
      });

      // Update parent component's state
      if (onSave) {
        onSave(updatedWorkflow);
      }

      // Trigger API save with the updated workflow
      // Use setTimeout to ensure state is updated first
      setTimeout(() => {
        if (typeof onApiSave === 'function') {
          onApiSave(updatedWorkflow);
        }
      }, 100);
    }
  }, [onApiSave, onSave, exportWorkflow, initialWorkflow]);

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
          workflow={initialWorkflow}
          onWorkflowChange={onSave}
          onSave={handleSaveClick}
          isSaving={isSaving}
          readOnly={readOnly}
          onExecute={onExecute}
          onToggleFullscreen={onToggleFullscreen}
        />
      </div>

      {/* Right Panel - Node Details */}
      {detailsPanelOpen && <NodeDetailsPanel />}
    </div>
  );
};

export const WorkflowEditor: React.FC<WorkflowEditorProps> = WorkflowEditorContent;
