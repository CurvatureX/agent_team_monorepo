"use client";

import React from "react";
import { motion } from "framer-motion";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { AssistantCard } from "@/components/ui/assistant-card";
import { HandWrittenTitle } from "@/components/ui/hand-writing-text";
import { useRouter } from "next/navigation";

// Import assistant data
import { assistants } from "@/lib/assistant-data";

export default function Home() {
  const router = useRouter();

  const handleSendMessage = (message: string, files?: File[]) => {
    // Store message in sessionStorage for new workflow page
    sessionStorage.setItem('initialMessage', message);

    // Handle file uploads if any
    if (files && files.length > 0) {
      console.log('Uploaded files:', files);
    }

    // Navigate to new workflow page
    router.push('/workflow/new');
  };

  return (
    <div className="min-h-screen bg-background transition-colors duration-300">
      {/* Background Gradient Overlay */}
      <div className="fixed inset-0 bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,0.1)_10.5%,rgba(245,120,2,0.08)_16%,rgba(245,140,2,0.06)_17.5%,rgba(245,170,100,0.04)_25%,rgba(238,174,202,0.02)_40%,rgba(202,179,214,0.01)_65%,rgba(148,201,233,0.005)_100%)] dark:bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,0.05)_10.5%,rgba(245,120,2,0.04)_16%,rgba(245,140,2,0.03)_17.5%,rgba(245,170,100,0.02)_25%,rgba(238,174,202,0.01)_40%,rgba(202,179,214,0.005)_65%,rgba(148,201,233,0.002)_100%)] pointer-events-none" />

      <div className="relative z-1 max-w-6xl mx-auto px-4 py-4 pt-20">
        {/* Header Section */}
        <motion.div
          className="text-center mb-16 mt-8"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <div className="flex items-center justify-center gap-3 mb-6">
            <HandWrittenTitle title="Agent Team" />
          </div>
          <motion.p
            className="text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 1.2 }}
          >
            Every idea, answered by your AI team
          </motion.p>
        </motion.div>

        {/* Input Section */}
        <motion.div
          className="mb-20"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.8, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <div className="max-w-3xl mx-auto">
            <PromptInputBox
              onSend={handleSendMessage}
              placeholder="Describe your dream job—your next agent is waiting for an interview!"
            />
          </div>
        </motion.div>


      </div>

      {/* Divider */}
      <motion.div
        className="flex items-center gap-6 mb-12 px-[120px]"
        initial={{ opacity: 0, scaleX: 0 }}
        animate={{ opacity: 1, scaleX: 1 }}
        transition={{ duration: 0.8, delay: 1.0, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-border to-border"></div>
        <motion.span
          className="text-muted-foreground text-base font-medium px-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.2 }}
        >
          Agent Roster
        </motion.span>
        <div className="flex-1 h-px bg-gradient-to-l from-transparent via-border to-border"></div>
      </motion.div>

      {/* Assistant Cards Grid */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 px-[120px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 1.3 }}
      >
        {assistants.map((assistant, index) => (
          <div
            key={assistant.id}
            style={{
              animationDelay: `${index * 100}ms`,
            }}
          >
            <AssistantCard
              name={assistant.name}
              title={assistant.title}
              description={assistant.description}
              skills={assistant.skills}
              imagePath={assistant.imagePath}
            />
          </div>
        ))}
      </motion.div>
    </div>
  );
}
