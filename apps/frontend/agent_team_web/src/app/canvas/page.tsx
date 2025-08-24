"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { PanelResizer } from "@/components/ui/panel-resizer";
import AssistantList from "@/components/ui/assistant-list";
import { WorkflowEditor } from "@/components/workflow/WorkflowEditor";
import { User, Bot, Workflow, Maximize2, ArrowLeft, StopCircle, RefreshCw } from "lucide-react";
import { useResizablePanel } from "@/hooks";
import { assistants as mockAssistants, Assistant } from "@/lib/assistant-data";
import { WorkflowData } from "@/types/workflow";
import { useWorkflowsApi, useWorkflowActions } from "@/lib/api/hooks/useWorkflowsApi";
import { useToast } from "@/hooks/use-toast";
import { chatService, ChatSSEEvent } from "@/lib/api/chatService";

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
  const [isSavingWorkflow, setIsSavingWorkflow] = useState(false);
  const [streamCancelFn, setStreamCancelFn] = useState<(() => void) | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  
  const { toast } = useToast();
  const { updateWorkflow } = useWorkflowActions();
  
  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // Use the custom hook for resizable panels
  const { width: rightPanelWidth, isResizing, resizerProps, overlayProps } = useResizablePanel({
    initialWidth: 384,
    minWidth: 300,
    maxWidthRatio: 0.6
  });

  // Fetch workflows from API
  const { workflows: apiWorkflows, isLoading: isLoadingWorkflows, error } = useWorkflowsApi();
  
  // Debug logging
  useEffect(() => {
    if (apiWorkflows) {
      console.log('API Workflows loaded:', apiWorkflows);
    }
    if (error) {
      console.error('API Workflows error:', error);
    }
  }, [apiWorkflows, error]);

  // Map API workflows to Assistant format and merge with mock data
  const assistants = useMemo(() => {
    // Check if apiWorkflows has the expected structure
    let workflowsArray: any[] = [];
    
    if (apiWorkflows) {
      // If apiWorkflows is an object with a 'workflows' property (like the API response)
      if (apiWorkflows.workflows && Array.isArray(apiWorkflows.workflows)) {
        workflowsArray = apiWorkflows.workflows;
      } 
      // If apiWorkflows is already an array
      else if (Array.isArray(apiWorkflows)) {
        workflowsArray = apiWorkflows;
      }
      
      console.log('Workflows data structure:', apiWorkflows);
      console.log('Extracted workflows array:', workflowsArray);
    }
    
    const apiAssistants: Assistant[] = workflowsArray.map((workflow: any, index: number) => ({
      id: `api-workflow-${index}`,
      name: workflow.name || `Workflow ${index + 1}`,
      title: workflow.subtype || 'Custom Workflow',
      description: workflow.description || 'No description available',
      skills: workflow.tags ? (Array.isArray(workflow.tags) ? workflow.tags : workflow.tags.split(',').map((tag: string) => tag.trim())) : [],
      imagePath: '/assistant/AlfieKnowledgeBaseQueryAssistantIcon.png', // Default image
      workflow: workflow as WorkflowData
    }));

    // Merge API workflows with mock assistants
    return [...apiAssistants, ...mockAssistants];
  }, [apiWorkflows]);

  // Load chat history on mount and ensure session exists
  useEffect(() => {
    const initializeChat = async () => {
      try {
        // First ensure we have a session
        console.log('Initializing chat session...');
        const sessionId = await chatService.createNewSession();
        console.log('Chat session initialized:', sessionId);
        
        // Then try to load history
        const history = await chatService.getChatHistory();
        if (history.messages && history.messages.length > 0) {
          const formattedMessages: Message[] = history.messages.map((msg: any) => ({
            id: msg.id,
            content: msg.content,
            sender: msg.role === 'user' ? 'user' : 'assistant',
            timestamp: new Date(msg.created_at)
          }));
          setMessages(formattedMessages);
        }
      } catch (error) {
        console.log('Error initializing chat:', error);
      }
    };

    initializeChat();

    // Check for initial message from ai-prompt page
    const initialMessage = sessionStorage.getItem('initialMessage');
    if (initialMessage) {
      sessionStorage.removeItem('initialMessage');
      // Send initial message after component mounts
      setTimeout(() => {
        handleSendMessage(initialMessage);
      }, 100);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle worker selection from AssistantList
  useEffect(() => {
    const handleAssistantSelect = (event: Event) => {
      const customEvent = event as CustomEvent<{ assistantId: string }>;
      const assistantId = customEvent.detail.assistantId;
      
      // Find the worker's workflow
      const assistant = assistants.find((a: Assistant) => a.id === assistantId);
      console.log('Selected worker:', assistant);
      
      if (assistant?.workflow) {
        console.log('Setting workflow ---:', assistant.workflow);
        setCurrentWorkflow(assistant.workflow);
      } else {
        setCurrentWorkflow(null);
      }
    };

    window.addEventListener('assistant-selected', handleAssistantSelect);
    return () => {
      window.removeEventListener('assistant-selected', handleAssistantSelect);
    };
  }, [assistants]);

  const handleSendMessage = useCallback(async (message: string, files?: File[]) => {
    console.log('handleSendMessage called with:', message);
    if (!message.trim()) return;

    // Cancel any ongoing stream
    if (streamCancelFn) {
      console.log('Cancelling previous stream');
      streamCancelFn();
      setStreamCancelFn(null);
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      content: message,
      sender: 'user',
      timestamp: new Date()
    };

    console.log('Adding user message to UI');
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setIsStreaming(true);

    // Handle file uploads if any
    if (files && files.length > 0) {
      console.log('Processing uploaded files:', files);
    }

    // Prepare AI message placeholder
    const currentAiMessageId = (Date.now() + 1).toString();
    let accumulatedContent = '';
    let hasReceivedContent = false;

    console.log('About to call chatService.sendChatMessage');
    try {
      // Send message to chat API with streaming
      const cancelFn = await chatService.sendChatMessage(
        message,
        (event: ChatSSEEvent) => {
          console.log('Received SSE event:', event);
          hasReceivedContent = true;
          
          // Handle different message types from the SSE stream
          if (event.type === 'message') {
            // Check if it's a text message from assistant
            if (event.data?.text) {
              accumulatedContent += event.data.text;
              
              // Update or create AI message
              setMessages(prev => {
                const existingIndex = prev.findIndex(m => m.id === currentAiMessageId);
                const aiMessage: Message = {
                  id: currentAiMessageId,
                  content: accumulatedContent,
                  sender: 'assistant',
                  timestamp: new Date()
                };
                
                if (existingIndex !== -1) {
                  const updated = [...prev];
                  updated[existingIndex] = aiMessage;
                  return updated;
                } else {
                  return [...prev, aiMessage];
                }
              });
            } 
            // Handle status/processing messages (these are transient, we can optionally show them)
            else if (event.data?.message && event.data?.status === 'processing') {
              // Optionally show processing status as a temporary message
              console.log('Processing status:', event.data.message);
            }
            // Handle role-based messages (when data contains text and role)
            else if (event.data?.role === 'assistant') {
              // This is for messages that come with a role field
              const messageText = event.data.text || event.data.message || '';
              if (messageText) {
                accumulatedContent = messageText; // Replace accumulated content
                
                setMessages(prev => {
                  const existingIndex = prev.findIndex(m => m.id === currentAiMessageId);
                  const aiMessage: Message = {
                    id: currentAiMessageId,
                    content: accumulatedContent,
                    sender: 'assistant',
                    timestamp: new Date()
                  };
                  
                  if (existingIndex !== -1) {
                    const updated = [...prev];
                    updated[existingIndex] = aiMessage;
                    return updated;
                  } else {
                    return [...prev, aiMessage];
                  }
                });
              }
            }
          } else if (event.type === 'workflow' && event.data) {
            // Handle workflow generation if the AI creates one
            if (event.data.workflow) {
              console.log('Received workflow:', event.data.workflow);
              setCurrentWorkflow(event.data.workflow);
              
              // Also show a message about workflow creation if there's text
              if (event.data.text) {
                const workflowMessage = event.data.text;
                setMessages(prev => {
                  const existingIndex = prev.findIndex(m => m.id === currentAiMessageId);
                  const aiMessage: Message = {
                    id: currentAiMessageId,
                    content: workflowMessage,
                    sender: 'assistant',
                    timestamp: new Date()
                  };
                  
                  if (existingIndex !== -1) {
                    const updated = [...prev];
                    updated[existingIndex] = aiMessage;
                    return updated;
                  } else {
                    return [...prev, aiMessage];
                  }
                });
              }
            }
          } else if (event.type === 'status_change') {
            // Log status changes for debugging but don't show them as messages
            console.log('Workflow status change:', event.data);
          } else if (event.type === 'error') {
            toast({
              title: "Error",
              description: event.data?.message || "An error occurred while processing your message",
              variant: "destructive",
            });
          }
        },
        (error) => {
          console.error('Chat API error:', error);
          
          // If no content was received, show a fallback message
          if (!hasReceivedContent) {
            const fallbackMessage: Message = {
              id: currentAiMessageId,
              content: "I'm sorry, I couldn't connect to the AI service. Please check if the backend service is running.",
              sender: 'assistant',
              timestamp: new Date()
            };
            setMessages(prev => [...prev, fallbackMessage]);
          }
          
          toast({
            title: "Connection Error",
            description: "Failed to connect to AI service. Make sure the backend is running.",
            variant: "destructive",
          });
          setIsLoading(false);
          setIsStreaming(false);
        },
        () => {
          console.log('Stream completed, received content:', hasReceivedContent);
          setIsLoading(false);
          setIsStreaming(false);
          setStreamCancelFn(null);
        }
      );

      setStreamCancelFn(() => cancelFn);
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Show error message
      const errorMessage: Message = {
        id: currentAiMessageId,
        content: "I'm having trouble connecting to the AI service. Please make sure the backend server is running.",
        sender: 'assistant',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      
      setIsLoading(false);
      setIsStreaming(false);
    }
  }, [currentWorkflow, toast, streamCancelFn]);

  // Handle stop streaming
  const handleStopStreaming = useCallback(() => {
    if (streamCancelFn) {
      streamCancelFn();
      setStreamCancelFn(null);
      setIsStreaming(false);
      setIsLoading(false);
    }
  }, [streamCancelFn]);

  // Handle retry last message
  const handleRetryLastMessage = useCallback(() => {
    const lastUserMessage = [...messages].reverse().find(m => m.sender === 'user');
    if (lastUserMessage) {
      // Remove last AI message if it exists
      setMessages(prev => {
        const lastAiIndex = prev.map((m, i) => m.sender === 'assistant' ? i : -1)
          .filter(i => i !== -1)
          .pop();
        if (lastAiIndex !== undefined && lastAiIndex > -1) {
          return prev.slice(0, lastAiIndex);
        }
        return prev;
      });
      // Resend the message
      handleSendMessage(lastUserMessage.content);
    }
  }, [messages, handleSendMessage]);

  const handleWorkflowChange = useCallback((updatedWorkflow: WorkflowData) => {
    setCurrentWorkflow(updatedWorkflow);
    console.log('Workflow updated:', updatedWorkflow);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamCancelFn) {
        streamCancelFn();
      }
      // Don't clear session to preserve chat history
    };
  }, [streamCancelFn]);

  // Handle saving workflow to API
  const handleSaveWorkflow = useCallback(async (workflowToSave?: WorkflowData) => {
    // Use the provided workflow or fall back to currentWorkflow
    const workflow = workflowToSave || currentWorkflow;
    
    if (!workflow || !workflow.id) {
      toast({
        title: "Error",
        description: "No workflow to save",
        variant: "destructive",
      });
      return;
    }

    setIsSavingWorkflow(true);
    
    try {
      // Convert edges to connections format (n8n style)
      const connections: Record<string, any> = {};
      if (workflow.edges) {
        workflow.edges.forEach((edge: any) => {
          if (!connections[edge.source]) {
            connections[edge.source] = {
              main: [[]]
            };
          }
          connections[edge.source].main[0].push({
            node: edge.target,
            type: 'main',
            index: 0,
          });
        });
      }

      // Prepare the update data according to API spec
      const updateData = {
        name: workflow.name,
        description: workflow.description,
        nodes: workflow.nodes || [],
        connections: connections,
        settings: workflow.settings,
        tags: workflow.tags || [],
      };

      console.log('Saving workflow to API:', {
        id: workflow.id,
        nodesCount: updateData.nodes.length,
        connections: connections,
      });
      
      await updateWorkflow(workflow.id, updateData);
      
      // Update currentWorkflow with the saved data
      if (workflowToSave) {
        setCurrentWorkflow(workflowToSave);
      }
      
      toast({
        title: "Success",
        description: "Workflow saved successfully",
      });
    } catch (error) {
      console.error('Failed to save workflow:', error);
      toast({
        title: "Error",
        description: "Failed to save workflow. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSavingWorkflow(false);
    }
  }, [currentWorkflow, updateWorkflow, toast]);

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
                    {currentWorkflow.name || 'Untitled'}&apos;s Workflow
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

              {/* Workflow Editor */}
              <div className="flex-1 bg-muted/20 rounded-lg border border-border overflow-hidden">
                <WorkflowEditor
                  initialWorkflow={currentWorkflow}
                  onSave={handleWorkflowChange}
                  onApiSave={handleSaveWorkflow}
                  isSaving={isSavingWorkflow}
                  readOnly={false}
                  className="h-full"
                />
              </div>
            </div>
          ) : isLoadingWorkflows ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                <p className="text-muted-foreground">Loading workflows...</p>
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
          <div ref={chatContainerRef} className="flex-1 p-4 overflow-y-auto pt-2">
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
              
              <div ref={messagesEndRef} />
              
              {isLoading && !isStreaming && (
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

          {/* Action Buttons */}
          {(isStreaming || messages.length > 0) && (
            <div className="px-4 py-2 border-t border-border/30 flex items-center gap-2">
              {isStreaming && (
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleStopStreaming}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-destructive/10 text-destructive hover:bg-destructive/20 transition-colors text-sm"
                >
                  <StopCircle className="w-4 h-4" />
                  <span>Stop</span>
                </motion.button>
              )}
              {!isLoading && messages.length > 0 && (
                <>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleRetryLastMessage}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-muted hover:bg-accent transition-colors text-sm"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Retry</span>
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      setMessages([]);
                      chatService.clearSession();
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-muted hover:bg-accent transition-colors text-sm ml-auto"
                  >
                    <span>Clear Chat</span>
                  </motion.button>
                </>
              )}
            </div>
          )}

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
            className="fixed inset-0 bg-background z-50 flex flex-col"
          >
            {/* Fullscreen Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Workflow className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold">
                  {currentWorkflow.name || 'Untitled'}&apos;s Workflow
                </h3>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsWorkflowExpanded(false)}
                className="p-2 hover:bg-accent rounded-lg transition-colors"
                title="Exit Fullscreen"
              >
                <Maximize2 className="w-4 h-4" />
              </motion.button>
            </div>
            {/* Workflow Editor */}
            <div className="flex-1">
              <WorkflowEditor
                initialWorkflow={currentWorkflow}
                onSave={handleWorkflowChange}
                onApiSave={handleSaveWorkflow}
                isSaving={isSavingWorkflow}
                readOnly={false}
                className="h-full"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CanvasPage;
