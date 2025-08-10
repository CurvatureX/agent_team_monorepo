"use client";

import React from 'react';
import { WorkflowEditor } from '@/components/workflow/WorkflowEditor';
import type { WorkflowData } from '@/types/workflow';

export default function WorkflowEditorPage() {
  const handleWorkflowChange = (workflow: WorkflowData) => {
    console.log('Workflow changed:', workflow);
    // Here you would typically save the workflow to your backend
  };

  return (
    <div className="h-screen w-full">
      <WorkflowEditor
        onSave={handleWorkflowChange}
        readOnly={false}
      />
    </div>
  );
}