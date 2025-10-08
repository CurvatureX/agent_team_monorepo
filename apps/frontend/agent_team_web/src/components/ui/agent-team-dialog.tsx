"use client";

import React from "react";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";

interface AgentTeamDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AgentTeamDialog({ open, onOpenChange }: AgentTeamDialogProps) {
  const router = useRouter();

  const handleSendMessage = (message: string, files?: File[]) => {
    // Store message in sessionStorage for new workflow page
    sessionStorage.setItem('initialMessage', message);

    // Handle file uploads if any
    if (files && files.length > 0) {
      console.log('Uploaded files:', files);
    }

    // Close dialog and navigate to new workflow page
    onOpenChange(false);
    router.push('/workflow/new');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!w-[600px] !max-w-[600px] min-h-[600px] !top-[50%] !left-[50%] !translate-x-[-50%] !translate-y-[-50%] !p-8 border-none bg-transparent shadow-none [&>button]:hidden flex items-center justify-center">
        <DialogTitle className="sr-only">Create Workflow</DialogTitle>
        <div className="w-full">
          <PromptInputBox
            onSend={handleSendMessage}
            placeholder="Describe your workflow or agent..."
            textareaClassName="min-h-[220px]"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
