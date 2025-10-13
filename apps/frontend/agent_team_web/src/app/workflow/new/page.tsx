"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { PanelResizer } from "@/components/ui/panel-resizer";
import { WorkflowEditor } from "@/components/workflow/WorkflowEditor";
import {
  Maximize2,
  StopCircle,
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  History,
  Bot,
} from "lucide-react";
import Image from "next/image";
import { useResizablePanel } from "@/hooks";
import {
  WorkflowData,
} from "@/types/workflow";
import { useWorkflowActions } from "@/lib/api/hooks/useWorkflowsApi";
import { useToast } from "@/hooks/use-toast";
import { chatService, ChatSSEEvent } from "@/lib/api/chatService";
import { useLayout } from "@/components/ui/layout-wrapper";
import { usePageTitle } from "@/contexts/page-title-context";
// import { useAuth } from "@/contexts/auth-context";

interface Message {
  id: string;
  content: string;
  sender: "user" | "assistant";
  timestamp: Date;
}

// Helper function to get status badge variant and icon
// const getExecutionStatusInfo = (status: string | null) => {
//   if (!status)
//     return {
//       variant: "secondary" as const,
//       icon: AlertCircle,
//       label: "No runs yet",
//     };

//   const statusLower = status.toLowerCase();
//   if (statusLower === "success" || statusLower === "completed") {
//     return {
//       variant: "default" as const,
//       icon: CheckCircle,
//       label: "Success",
//       color: "text-green-600",
//     };
//   }
//   if (statusLower === "error" || statusLower === "failed") {
//     return {
//       variant: "destructive" as const,
//       icon: XCircle,
//       label: "Failed",
//       color: "text-red-600",
//     };
//   }
//   if (statusLower === "running" || statusLower === "in_progress") {
//     return {
//       variant: "outline" as const,
//       icon: RefreshCw,
//       label: "Running",
//       color: "text-blue-600",
//     };
//   }
//   return {
//     variant: "secondary" as const,
//     icon: AlertCircle,
//     label: status,
//     color: "text-gray-600",
//   };
// };

const NewWorkflowPage = () => {
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowData | null>(
    null
  );
  const [isWorkflowExpanded, setIsWorkflowExpanded] = useState(false);
  const [isSavingWorkflow, setIsSavingWorkflow] = useState(false);
  const [streamCancelFn, setStreamCancelFn] = useState<(() => void) | null>(
    null
  );
  const [isStreaming, setIsStreaming] = useState(false);
  const [workflowName, setWorkflowName] = useState<string>("New Workflow");
  const [workflowDescription, setWorkflowDescription] = useState<string>("");
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [isChatExpanded, setIsChatExpanded] = useState(true);
  const [isExecutionLogsExpanded, setIsExecutionLogsExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const hasAutoSentMessage = useRef(false);
  const hasInitializedSession = useRef(false);
  const [isSessionReady, setIsSessionReady] = useState(false);

  const { toast } = useToast();
  // const { session } = useAuth();
  const { createWorkflow } = useWorkflowActions();

  useLayout();
  const { setCustomTitle } = usePageTitle();

  // Use the custom hook for resizable panels
  const {
    width: rightPanelWidth,
    isResizing,
    resizerProps,
    overlayProps,
  } = useResizablePanel({
    initialWidth: 384,
    minWidth: 300,
    maxWidthRatio: 0.6,
  });

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Set custom breadcrumb title
  useEffect(() => {
    const breadcrumbTitle = (
      <div className="flex items-center gap-1 text-sm font-bold">
        <button
          onClick={() => router.push("/canvas")}
          className="text-black dark:text-white hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          Assistants
        </button>
        <span className="text-black/50 dark:text-white/50 px-1">/</span>
        <span className="text-black dark:text-white">
          {workflowName}
        </span>
      </div>
    );

    setCustomTitle(breadcrumbTitle);

    // Clear custom title when leaving
    return () => {
      setCustomTitle(null);
    };
  }, [setCustomTitle, workflowName, router]);

  // Initialize chat session (only once) - ALWAYS create a new session for new workflows
  useEffect(() => {
    // Prevent duplicate session creation in React StrictMode
    if (hasInitializedSession.current) {
      console.log("[NewWorkflow] Session already initialized, skipping...");
      return;
    }

    const initializeChat = async () => {
      try {
        hasInitializedSession.current = true;
        console.log("[NewWorkflow] Creating new chat session for new workflow...");
        // IMPORTANT: Always clear existing session and create a fresh one for new workflows
        // This ensures we don't reuse sessions from other workflows
        chatService.clearSession();

        // Create a brand new session
        const newSessionId = await chatService.createNewSession();
        console.log("[NewWorkflow] Created new session ID:", newSessionId);

        // New workflow should start with empty chat history
        setMessages([]);

        // Mark session as ready
        setIsSessionReady(true);
        console.log("[NewWorkflow] Session is now ready");
      } catch (error) {
        console.error("[NewWorkflow] Error initializing chat:", error);
        // Reset flags on error so user can retry
        hasInitializedSession.current = false;
        setIsSessionReady(false);

        toast({
          title: "Session Initialization Error",
          description: "Failed to initialize chat session. Please refresh the page.",
          variant: "destructive",
        });
      }
    };

    initializeChat();

    // Reset flag on unmount so a fresh session is created if user returns
    return () => {
      hasInitializedSession.current = false;
      setIsSessionReady(false);
    };
  }, []);

  const handleSendMessage = useCallback(
    async (message: string, files?: File[]) => {
      if (!message.trim()) return;

      // Cancel any ongoing stream
      if (streamCancelFn) {
        streamCancelFn();
        setStreamCancelFn(null);
      }

      const userMessage: Message = {
        id: Date.now().toString(),
        content: message,
        sender: "user",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setIsStreaming(true);

      // Handle file uploads if any
      if (files && files.length > 0) {
        console.log("Processing uploaded files:", files);
      }

      // Prepare AI message placeholder
      const currentAiMessageId = (Date.now() + 1).toString();
      let accumulatedContent = "";
      let hasReceivedContent = false;

      try {
        const cancelFn = await chatService.sendChatMessage(
          message,
          (event: ChatSSEEvent) => {
            hasReceivedContent = true;

            if (event.type === "message") {
              if (event.data?.text) {
                accumulatedContent += event.data.text;

                setMessages((prev) => {
                  const existingIndex = prev.findIndex(
                    (m) => m.id === currentAiMessageId
                  );
                  const aiMessage: Message = {
                    id: currentAiMessageId,
                    content: accumulatedContent,
                    sender: "assistant",
                    timestamp: new Date(),
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
            } else if (event.type === "workflow" && event.data) {
              if (event.data.workflow) {
                console.log("[NewWorkflow] Received workflow update from stream");
                console.log("[NewWorkflow] Stream event session_id:", event.session_id);
                console.log("[NewWorkflow] Workflow metadata session_id:", event.data.workflow?.metadata?.session_id);
                console.log("[NewWorkflow] Full workflow data:", event.data.workflow);
                const workflowData = event.data.workflow;
                setCurrentWorkflow(workflowData);

                // Update workflow name and description if available (consistent pattern)
                if (workflowData.name) {
                  setWorkflowName(workflowData.name);
                }
                if (workflowData.description) {
                  setWorkflowDescription(workflowData.description);
                }

                // Extract the actual database workflow ID from the response
                // The AI agent saves the workflow and returns workflow_id
                // Use type assertion to access workflow_id which may exist at runtime but isn't in the type definition
                const workflowDataAny = workflowData as unknown as Record<string, unknown>;
                const eventDataAny = event.data as unknown as Record<string, unknown>;
                const savedWorkflowId = (workflowDataAny.workflow_id as string | undefined) ||  // Root level workflow_id (actual DB ID)
                                       (eventDataAny.workflow_id as string | undefined) ||
                                       workflowData.id ||              // Fallback to structure ID
                                       (eventDataAny.id as string | undefined);

                console.log("[NewWorkflow] Workflow ID extraction:", {
                  'workflow.workflow_id': workflowDataAny.workflow_id,
                  'event.data.workflow_id': eventDataAny.workflow_id,
                  'workflow.id': workflowData.id,
                  'event.data.id': eventDataAny.id,
                  'selectedId': savedWorkflowId
                });

                if (savedWorkflowId) {
                  console.log("[NewWorkflow] Using workflow ID:", savedWorkflowId);
                  setWorkflowId(savedWorkflowId);
                } else {
                  console.warn("[NewWorkflow] No workflow ID found in response:", event.data);
                }
              }
            } else if (event.type === "error") {
              toast({
                title: "Error",
                description:
                  event.data?.message ||
                  "An error occurred while processing your message",
                variant: "destructive",
              });
            }
          },
          (error) => {
            console.error("Chat API error:", error);
            if (!hasReceivedContent) {
              const fallbackMessage: Message = {
                id: currentAiMessageId,
                content:
                  "I'm sorry, I couldn't connect to the AI service. Please check if the backend service is running.",
                sender: "assistant",
                timestamp: new Date(),
              };
              setMessages((prev) => [...prev, fallbackMessage]);
            }

            toast({
              title: "Connection Error",
              description: "Failed to connect to AI service.",
              variant: "destructive",
            });
            setIsLoading(false);
            setIsStreaming(false);
          },
          () => {
            setIsLoading(false);
            setIsStreaming(false);
            setStreamCancelFn(null);
          }
        );

        setStreamCancelFn(() => cancelFn);
      } catch (error) {
        console.error("Failed to send message:", error);
        setIsLoading(false);
        setIsStreaming(false);
      }
    },
    [toast, streamCancelFn]
  );

  // Auto-send initial message from sessionStorage once session is ready
  useEffect(() => {
    if (hasAutoSentMessage.current || !isSessionReady) return;

    const initialMessage = sessionStorage.getItem("initialMessage");
    if (initialMessage) {
      console.log("[NewWorkflow] Session ready, auto-sending initial message:", initialMessage);
      hasAutoSentMessage.current = true;
      sessionStorage.removeItem("initialMessage");

      // Send the message immediately since session is confirmed ready
      handleSendMessage(initialMessage);
    }
  }, [isSessionReady, handleSendMessage]);

  // Redirect to workflow detail page when workflow ID is received
  // The AI agent already saves the workflow to the database and returns the ID
  useEffect(() => {
    if (workflowId && currentWorkflow) {
      console.log("Workflow received from AI, redirecting to detail page:", workflowId);
      // Small delay to ensure any async operations complete
      const timer = setTimeout(() => {
        router.replace(`/workflow/${workflowId}`);
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [workflowId, currentWorkflow, router]);

  const handleStopStreaming = useCallback(() => {
    if (streamCancelFn) {
      streamCancelFn();
      setStreamCancelFn(null);
      setIsStreaming(false);
      setIsLoading(false);
    }
  }, [streamCancelFn]);

  const handleRetryLastMessage = useCallback(() => {
    const lastUserMessage = [...messages]
      .reverse()
      .find((m) => m.sender === "user");
    if (lastUserMessage) {
      setMessages((prev) => {
        const lastAiIndex = prev
          .map((m, i) => (m.sender === "assistant" ? i : -1))
          .filter((i) => i !== -1)
          .pop();
        if (lastAiIndex !== undefined && lastAiIndex > -1) {
          return prev.slice(0, lastAiIndex);
        }
        return prev;
      });
      handleSendMessage(lastUserMessage.content);
    }
  }, [messages, handleSendMessage]);

  const handleWorkflowChange = useCallback((updatedWorkflow: WorkflowData) => {
    setCurrentWorkflow(updatedWorkflow);
    console.log("Workflow updated:", updatedWorkflow);
  }, []);

  const handleSaveWorkflow = useCallback(
    async (workflowToSave?: WorkflowData) => {
      const workflow = workflowToSave || currentWorkflow;

      if (!workflow) {
        toast({
          title: "Error",
          description: "No workflow to save",
          variant: "destructive",
        });
        return;
      }

      setIsSavingWorkflow(true);

      try {
        // Convert connections to backend expected format (List of Connection objects)
        const connections: Array<{
          id: string;
          from_node: string;
          to_node: string;
          output_key: string;
        }> = [];

        if (workflow.connections) {
          workflow.connections.forEach((edge, index) => {
            // Handle both backend format (from_node/to_node) and React Flow format (source/target)
            const edgeWithSource = edge as {
              id?: string;
              from_node?: string;
              to_node?: string;
              source?: string;
              target?: string;
              output_key?: string;
            };
            const sourceNode = edge.from_node || edgeWithSource.source;
            const targetNode = edge.to_node || edgeWithSource.target;

            if (!sourceNode || !targetNode) return;

            connections.push({
              id: edgeWithSource.id || `conn_${index}`,
              from_node: sourceNode,
              to_node: targetNode,
              output_key: edgeWithSource.output_key || "result",
            });
          });
        }

        // Extract trigger node IDs from nodes
        const triggerNodeIds: string[] = [];
        if (workflow.nodes) {
          workflow.nodes.forEach((node) => {
            if (node.type === "TRIGGER") {
              triggerNodeIds.push(node.id);
            }
          });
        }

        // Prepare metadata according to CreateWorkflowRequest format
        const createData = {
          nodes: workflow.nodes || [],
          connections: connections,
          triggers: triggerNodeIds,
          metadata: {
            name: workflow.name || workflowName,
            description: workflow.description || workflowDescription,
            tags: workflow.tags || [],
          },
        };

        const newWorkflow = await createWorkflow(createData);

        if (newWorkflow && newWorkflow.id) {
          toast({
            title: "Success",
            description: "Workflow created successfully",
          });

          // Redirect to the new workflow detail page
          router.push(`/workflow/${newWorkflow.id}`);
        }
      } catch (error) {
        console.error("Failed to create workflow:", error);
        toast({
          title: "Error",
          description: "Failed to create workflow. Please try again.",
          variant: "destructive",
        });
      } finally {
        setIsSavingWorkflow(false);
      }
    },
    [currentWorkflow, workflowName, workflowDescription, createWorkflow, toast, router]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamCancelFn) {
        streamCancelFn();
      }
    };
  }, [streamCancelFn]);

  const leftPanelWidth = `calc(100% - ${rightPanelWidth}px)`;

  return (
    <div className="bg-[#F8F8F8] dark:bg-background transition-colors duration-300 h-full">
      <motion.div
        className="flex h-full pt-12"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        {/* Left Side - Workflow Editor */}
        <motion.div
          className="pb-2 pl-2 pr-2 h-full"
          style={{ width: leftPanelWidth }}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <div className="h-full flex flex-col">
            {/* Workflow Header */}
            <div className="px-4 py-3 bg-background/95 backdrop-blur-sm rounded-t-lg border border-b-0 border-border">
              <h2 className="text-lg font-semibold text-foreground">
                {workflowName}
              </h2>
              {workflowDescription && (
                <p className="text-sm text-muted-foreground mt-1">
                  {workflowDescription}
                </p>
              )}
              {/* Status */}
              <div className="flex items-center gap-3 mt-2">
                <div className="flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-gray-600" />
                  <span className="text-xs font-medium text-gray-600">
                    Draft
                  </span>
                </div>
              </div>
            </div>
            {/* Workflow Editor */}
            <div className="flex-1 bg-muted/20 rounded-lg border border-border overflow-hidden">
              {currentWorkflow ? (
                <WorkflowEditor
                  initialWorkflow={currentWorkflow}
                  onSave={handleWorkflowChange}
                  onApiSave={handleSaveWorkflow}
                  isSaving={isSavingWorkflow}
                  readOnly={false}
                  className="h-full"
                  onToggleFullscreen={() => setIsWorkflowExpanded(true)}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm">
                      Describe your workflow to get started
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Resize Handle */}
        <PanelResizer
          isResizing={isResizing}
          resizerProps={resizerProps}
          overlayProps={overlayProps}
        />

        {/* Right Side - Info Panel */}
        <motion.div
          className="flex flex-col bg-background/95 backdrop-blur-sm h-full border-l border-t border-border/30 rounded-tl-lg overflow-hidden"
          style={{ width: `${rightPanelWidth}px` }}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          {/* Execution Logs Section - Collapsed by default for new workflow */}
          <div className="flex flex-col border-b border-border/30">
            {/* Execution Logs Header */}
            <button
              onClick={() =>
                setIsExecutionLogsExpanded(!isExecutionLogsExpanded)
              }
              className="flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <History className="w-4 h-4" />
                <h3 className="text-sm font-semibold">Execution Logs</h3>
              </div>
              {isExecutionLogsExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>

            {/* Execution Logs Content */}
            <AnimatePresence>
              {isExecutionLogsExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-4 max-h-[300px] overflow-y-auto">
                    <div className="text-xs text-muted-foreground text-center py-8">
                      No execution logs yet
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Chat Section - Expanded by default */}
          <div className="flex flex-col flex-1 min-h-0">
            {/* Chat Header */}
            <button
              onClick={() => setIsChatExpanded(!isChatExpanded)}
              className="flex items-center justify-between p-4 border-b border-border/30 hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                <h3 className="text-sm font-semibold">Workflow Assistant</h3>
              </div>
              {isChatExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>

            {/* Chat Content */}
            <AnimatePresence>
              {isChatExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="flex flex-col flex-1 min-h-0 overflow-hidden"
                >
                  {/* Chat Messages */}
                  <div
                    ref={chatContainerRef}
                    className="flex-1 p-4 overflow-y-auto pt-2"
                  >
                    <div className="space-y-4">
                      {messages.map((message) => (
                        <motion.div
                          key={message.id}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -20 }}
                          transition={{ duration: 0.3 }}
                          className={`flex ${
                            message.sender === "user"
                              ? "justify-end"
                              : "justify-start"
                          }`}
                        >
                          <div
                            className={`max-w-[80%] p-3 rounded-2xl ${
                              message.sender === "user"
                                ? "bg-primary text-primary-foreground ml-4"
                                : "bg-muted text-muted-foreground mr-4"
                            }`}
                          >
                            <div className="flex items-start gap-2">
                              {message.sender === "assistant" && (
                                <Image
                                  src="/icons/bot.svg"
                                  alt="Assistant"
                                  width={25}
                                  height={25}
                                  className="mt-0.5 flex-shrink-0"
                                />
                              )}
                              {message.sender === "user" && (
                                <Image
                                  src="/icons/user.svg"
                                  alt="User"
                                  width={25}
                                  height={25}
                                  className="mt-0.5 flex-shrink-0"
                                />
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

                      <div ref={messagesEndRef} />

                      {isLoading && !isStreaming && (
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="flex justify-start"
                        >
                          <div className="bg-muted text-muted-foreground p-3 rounded-2xl mr-4">
                            <div className="flex items-center gap-2">
                              <Image
                                src="/icons/bot.svg"
                                alt="Assistant"
                                width={25}
                                height={25}
                              />
                              <div className="flex gap-1">
                                <div className="w-2 h-2 bg-current rounded-full animate-bounce" />
                                <div
                                  className="w-2 h-2 bg-current rounded-full animate-bounce"
                                  style={{ animationDelay: "0.1s" }}
                                />
                                <div
                                  className="w-2 h-2 bg-current rounded-full animate-bounce"
                                  style={{ animationDelay: "0.2s" }}
                                />
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
                  <div className="p-4 bg-background/95 backdrop-blur-sm flex-shrink-0">
                    <PromptInputBox
                      onSend={handleSendMessage}
                      isLoading={isLoading}
                      placeholder="Describe your workflow or ask for modifications..."
                      className="shadow-sm"
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
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
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    setIsWorkflowExpanded(false);
                    router.push("/canvas");
                  }}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded hover:bg-accent"
                >
                  Assistants
                </button>
                <span className="text-muted-foreground px-1">/</span>
                <span className="text-sm font-medium px-2 py-1">
                  {workflowName}
                </span>
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
                onToggleFullscreen={() => setIsWorkflowExpanded(false)}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default NewWorkflowPage;
