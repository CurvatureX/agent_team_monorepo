"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { PanelResizer } from "@/components/ui/panel-resizer";
import AssistantList from "@/components/ui/assistant-list";
import WorkflowCanvas from "@/components/workflow/WorkflowCanvas";
import { User, Bot, Workflow, Maximize2, ArrowLeft } from "lucide-react";
import { useResizablePanel } from "@/hooks";
import { assistants } from "@/lib/assistant-data";
import { WorkflowData } from "@/types/workflow";
import { generateWorkflowFromDescription } from "@/utils/workflowGenerator";

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

const CanvasPage = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowData | null>(null);
  const [isWorkflowExpanded, setIsWorkflowExpanded] = useState(false);
  
  // Use the custom hook for resizable panels
  const { width: rightPanelWidth, isResizing, resizerProps, overlayProps } = useResizablePanel({
    initialWidth: 384,
    minWidth: 300,
    maxWidthRatio: 0.6
  });

  // Get initial message from ai-prompt page
  useEffect(() => {
    const initialMessage = sessionStorage.getItem('initialMessage');
    if (initialMessage) {
      const userMessage: Message = {
        id: Date.now().toString(),
        content: initialMessage,
        sender: 'user',
        timestamp: new Date()
      };
      setMessages([userMessage]);
      sessionStorage.removeItem('initialMessage');
      
      // Simulate AI response
      setTimeout(() => {
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: "I understand your requirements. Let me create a solution for you.",
          sender: 'assistant',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
      }, 1000);
    }
  }, []);

  // Handle worker selection from AssistantList
  useEffect(() => {
    const handleAssistantSelect = (event: Event) => {
      const customEvent = event as CustomEvent<{ assistantId: string }>;
      const assistantId = customEvent.detail.assistantId;
      
      // Find the worker's workflow
      const assistant = assistants.find(a => a.id === assistantId);
      console.log('Selected worker:', assistant);
      
      if (assistant?.workflow) {
        console.log('Setting workflow:', assistant.workflow);
        setCurrentWorkflow(assistant.workflow);
      } else {
        setCurrentWorkflow(null);
      }
    };

    window.addEventListener('assistant-selected', handleAssistantSelect);
    return () => {
      window.removeEventListener('assistant-selected', handleAssistantSelect);
    };
  }, []);

  const handleSendMessage = useCallback((message: string, files?: File[]) => {
    if (!message.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: message,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Handle file uploads if any
    if (files && files.length > 0) {
      console.log('Processing uploaded files:', files);
    }

    // Check if this is a workflow generation request
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('create workflow') || lowerMessage.includes('generate workflow') || lowerMessage.includes('make flow')) {
      // Generate workflow
      const newWorkflow = generateWorkflowFromDescription(message);
      setCurrentWorkflow(newWorkflow);
      
      setTimeout(() => {
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `I've created a workflow based on your description. You can view and edit it on the left. The workflow contains ${newWorkflow.nodes.length} nodes. You can drag to adjust node positions or add new nodes from the panel.`,
          sender: 'assistant',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
        setIsLoading(false);
      }, 1000);
    } else {
      // Regular conversation response
      setTimeout(() => {
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `I received your message: "${message}". I can help you create a workflow. Just tell me what kind of flow you need. For example: "Create a workflow that starts with AI analysis, then processes data, and finally sends notifications."`,
          sender: 'assistant',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
        setIsLoading(false);
      }, 1500);
    }
  }, []);

  const handleWorkflowChange = useCallback((updatedWorkflow: WorkflowData) => {
    setCurrentWorkflow(updatedWorkflow);
    console.log('Workflow updated:', updatedWorkflow);
  }, []);

  const leftPanelWidth = `calc(100% - ${rightPanelWidth}px)`;

  return (
    <div className="bg-background transition-colors duration-300">
      {/* Background Gradient Overlay */}
      {/* <div className="fixed inset-0 bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,0.1)_10.5%,rgba(245,120,2,0.08)_16%,rgba(245,140,2,0.06)_17.5%,rgba(245,170,100,0.04)_25%,rgba(238,174,202,0.02)_40%,rgba(202,179,214,0.01)_65%,rgba(148,201,233,0.005)_100%)] dark:bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,0.05)_10.5%,rgba(245,120,2,0.04)_16%,rgba(245,140,2,0.03)_17.5%,rgba(245,170,100,0.02)_25%,rgba(238,174,202,0.01)_40%,rgba(202,179,214,0.005)_65%,rgba(148,201,233,0.002)_100%)] pointer-events-none" /> */}

      {/* Main Content */}
      <motion.div 
        className="flex fixed inset-0 pt-[80px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        {/* Left Side - Canvas Area */}
        <motion.div
          className="pb-6 px-6 h-full"
          style={{ width: leftPanelWidth }}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {currentWorkflow ? (
            <div className="h-full flex flex-col gap-4">
              {/* Workflow Header */}
              <motion.div 
                className="flex items-center justify-between"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="flex items-center gap-2">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setCurrentWorkflow(null)}
                    className="p-2 hover:bg-accent rounded-lg transition-colors mr-2"
                    title="Back to Workers"
                  >
                    <ArrowLeft className="w-4 h-4" />
                  </motion.button>
                  <Workflow className="w-5 h-5 text-primary" />
                  <h3 className="text-lg font-semibold">
                    {assistants.find(a => a.workflow === currentWorkflow)?.name || ''}&apos;s Workflow
                  </h3>
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setIsWorkflowExpanded(!isWorkflowExpanded)}
                  className="p-2 hover:bg-accent rounded-lg transition-colors"
                >
                  <Maximize2 className="w-4 h-4" />
                </motion.button>
              </motion.div>

              {/* Workflow Canvas */}
              <div className="flex-1 bg-muted/20 rounded-lg border border-border overflow-hidden">
                <WorkflowCanvas
                  workflowData={currentWorkflow}
                  onWorkflowChange={handleWorkflowChange}
                  isExpanded={isWorkflowExpanded}
                  onToggleExpand={() => setIsWorkflowExpanded(!isWorkflowExpanded)}
                  isSimpleView={false}
                />
              </div>
            </div>
          ) : (
            <AssistantList assistants={assistants} />
          )}
        </motion.div>

        {/* Resize Handle */}
        <PanelResizer isResizing={isResizing} resizerProps={resizerProps} overlayProps={overlayProps} />

        {/* Right Side - Chat Area */}
        <motion.div
          className="flex flex-col bg-background/95 backdrop-blur-sm h-full border-l border-t border-border/30 rounded-tl-lg"
          style={{ width: `${rightPanelWidth}px` }}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          {/* Chat Header */}
          <div className="p-4 border-b border-border/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold">Worker Manager</h3>
              </div>
              
              {/* <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  // Generate a new workflow
                  const newWorkflow = generateWorkflowFromDescription('Start with AI analysis, then process data, and finally store results');
                  setCurrentWorkflow(newWorkflow);
                }}
                className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-primary/10 text-primary text-sm hover:bg-primary/20 transition-colors"
              >
                <Workflow className="w-4 h-4" />
                <span>Create Workflow</span>
              </motion.button> */}
            </div>
          </div>
          
          {/* Chat Messages */}
          <div className="flex-1 p-4 overflow-y-auto pt-2">
            <div className="space-y-4">
              <AnimatePresence>
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                    className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] p-3 rounded-2xl ${
                        message.sender === 'user'
                          ? 'bg-primary text-primary-foreground ml-4'
                          : 'bg-muted text-muted-foreground mr-4'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {message.sender === 'assistant' && (
                          <Bot className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        )}
                        {message.sender === 'user' && (
                          <User className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        )}
                        <div>
                          <p className="text-sm">{message.content}</p>
                          <p className="text-xs opacity-70 mt-1">
                            {message.timestamp.toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start"
                >
                  <div className="bg-muted text-muted-foreground p-3 rounded-2xl mr-4">
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4" />
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>
          </div>

          {/* Input Area */}
          <motion.div
            className="p-4 bg-background/95 backdrop-blur-sm flex-shrink-0"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <PromptInputBox
              onSend={handleSendMessage}
              isLoading={isLoading}
              placeholder="Continue conversation..."
              className="shadow-sm"
            />
          </motion.div>
        </motion.div>
      </motion.div>

      {/* Expanded Workflow View */}
      <AnimatePresence>
        {isWorkflowExpanded && currentWorkflow && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-background z-50"
          >
            <div className="w-full h-full p-8">
              <WorkflowCanvas
                workflowData={currentWorkflow}
                onWorkflowChange={handleWorkflowChange}
                isExpanded={true}
                onToggleExpand={() => setIsWorkflowExpanded(false)}
                isSimpleView={false}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CanvasPage;
