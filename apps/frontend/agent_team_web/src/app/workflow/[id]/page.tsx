"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { PanelResizer } from "@/components/ui/panel-resizer";
import { WorkflowEditor } from "@/components/workflow/WorkflowEditor";
import {
  User,
  Bot,
  Maximize2,
  StopCircle,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  History,
} from "lucide-react";
import { useResizablePanel } from "@/hooks";
import {
  WorkflowData,
  WorkflowDataStructure,
} from "@/types/workflow";
import { useWorkflowActions } from "@/lib/api/hooks/useWorkflowsApi";
import { useRecentExecutionLogs } from "@/lib/api/hooks/useExecutionApi";
import { useToast } from "@/hooks/use-toast";
import { chatService, ChatSSEEvent } from "@/lib/api/chatService";
import { useLayout } from "@/components/ui/layout-wrapper";
import { usePageTitle } from "@/contexts/page-title-context";
import { useAuth } from "@/contexts/auth-context";
import { Skeleton } from "@/components/ui/skeleton";

interface Message {
  id: string;
  content: string;
  sender: "user" | "assistant";
  timestamp: Date;
}

// Helper function to get status badge variant and icon
const getExecutionStatusInfo = (status: string | null) => {
  if (!status)
    return {
      variant: "secondary" as const,
      icon: AlertCircle,
      label: "No runs yet",
    };

  const statusLower = status.toLowerCase();
  if (statusLower === "success" || statusLower === "completed") {
    return {
      variant: "default" as const,
      icon: CheckCircle,
      label: "Success",
      color: "text-green-600",
    };
  }
  if (statusLower === "error" || statusLower === "failed") {
    return {
      variant: "destructive" as const,
      icon: XCircle,
      label: "Failed",
      color: "text-red-600",
    };
  }
  if (statusLower === "running" || statusLower === "in_progress") {
    return {
      variant: "outline" as const,
      icon: RefreshCw,
      label: "Running",
      color: "text-blue-600",
    };
  }
  return {
    variant: "secondary" as const,
    icon: AlertCircle,
    label: status,
    color: "text-gray-600",
  };
};

// Helper function to format execution time
const formatExecutionTime = (time: string | null) => {
  if (!time) return "Never";

  try {
    const date = new Date(time);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  } catch {
    return time;
  }
};

const WorkflowDetailPage = () => {
  const params = useParams();
  const router = useRouter();
  const workflowId = params?.id as string;

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
  const [isLoadingWorkflow, setIsLoadingWorkflow] = useState(true);
  const [workflowName, setWorkflowName] = useState<string>("");
  const [workflowDescription, setWorkflowDescription] = useState<string>("");
  const [latestExecutionStatus, setLatestExecutionStatus] = useState<
    string | null
  >(null);
  const [latestExecutionTime, setLatestExecutionTime] = useState<string | null>(
    null
  );
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [isExecutionLogsExpanded, setIsExecutionLogsExpanded] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const { toast } = useToast();
  const { session } = useAuth();
  const { updateWorkflow, getWorkflow } = useWorkflowActions();

  // Fetch recent execution logs
  const { logs: executionLogs, isLoading: isLoadingLogs } =
    useRecentExecutionLogs(workflowId, 10);
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

  // Fetch workflow details by ID
  useEffect(() => {
    const fetchWorkflowDetails = async () => {
      if (!workflowId) return;

      // Wait for authentication
      if (!session?.access_token) {
        console.log("Waiting for authentication...");
        return;
      }

      setIsLoadingWorkflow(true);
      try {
        const response = await getWorkflow(workflowId);

        // Handle no authentication case
        if (!response) {
          console.log("No response - user may not be authenticated");
          setIsLoadingWorkflow(false);
          return;
        }

        console.log("Workflow API response:", response);

        let workflowData: WorkflowDataStructure | null = null;

        // Handle different response structures
        if (response?.workflow) {
          // Response has a workflow property
          const workflow = response.workflow;

          // Check if workflow_data is a string and needs parsing
          if (typeof workflow.workflow_data === "string") {
            workflowData = JSON.parse(workflow.workflow_data);
          } else if (workflow.nodes && workflow.connections) {
            // workflow already has nodes and connections
            workflowData = workflow;
          } else {
            // workflow_data might be an object
            workflowData = workflow.workflow_data || workflow;
          }
        } else if (response?.workflow_data) {
          // Direct workflow_data in response
          if (typeof response.workflow_data === "string") {
            workflowData = JSON.parse(response.workflow_data);
          } else {
            workflowData = response.workflow_data;
          }
        } else if (response?.nodes) {
          // Direct workflow structure
          workflowData = response;
        }

        // Ensure workflowData has required properties
        if (workflowData) {
          // Don't manually convert connections - let the workflow editor's converter handle it
          // The apiWorkflowToEditor converter will properly map connections to React Flow edges
          console.log("📦 Workflow data loaded:", {
            nodes: workflowData.nodes?.length,
            connections: Array.isArray(workflowData.connections)
              ? workflowData.connections.length
              : "not array",
            hasEdges: !!workflowData.edges,
          });

          console.log("Processed workflow data:", workflowData);
          setCurrentWorkflow(workflowData as unknown as WorkflowData);

          // Set workflow name and description from metadata or fallback locations
          // Priority: workflow.metadata > workflowData.metadata > workflow direct > workflowData direct
          const metadata = workflowData?.metadata as { name?: string; description?: string } | undefined;
          const name =
            response?.workflow?.metadata?.name ||
            metadata?.name ||
            response?.workflow?.name ||
            response?.name ||
            workflowData?.name ||
            "Untitled Workflow";
          const description =
            response?.workflow?.metadata?.description ||
            metadata?.description ||
            response?.workflow?.description ||
            response?.description ||
            workflowData?.description ||
            "";

          setWorkflowName(name);
          setWorkflowDescription(description);

          console.log("Extracted workflow info:", {
            name,
            description,
            metadata: response?.workflow?.metadata,
          });

          // Extract execution status and time from response (check metadata first)
          const executionStatus =
            response?.workflow?.metadata?.last_execution_status ||
            response?.workflow?.latest_execution_status ||
            response?.latest_execution_status ||
            null;
          const executionTime =
            response?.workflow?.metadata?.last_execution_time ||
            response?.workflow?.latest_execution_time ||
            response?.latest_execution_time ||
            null;

          setLatestExecutionStatus(executionStatus);
          setLatestExecutionTime(executionTime);

          // Update workflow data with name and description if not present
          if (
            workflowData &&
            (!workflowData.name || !workflowData.description)
          ) {
            workflowData.name = name;
            workflowData.description = description;
          }
        } else {
          throw new Error("Invalid workflow data structure");
        }
      } catch (error) {
        console.error("Failed to fetch workflow:", error);
        toast({
          title: "Error",
          description: "Failed to load workflow details",
          variant: "destructive",
        });
      } finally {
        setIsLoadingWorkflow(false);
      }
    };

    fetchWorkflowDetails();
  }, [workflowId, getWorkflow, session, toast]);

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
          {workflowName || "Loading..."}
        </span>
      </div>
    );

    setCustomTitle(breadcrumbTitle);

    // Clear custom title when leaving
    return () => {
      setCustomTitle(null);
    };
  }, [setCustomTitle, workflowName, router]);

  // Initialize chat session
  useEffect(() => {
    const initializeChat = async () => {
      try {
        console.log("Initializing chat session for workflow...");
        const sessionId = await chatService.createNewSession();
        console.log("Chat session initialized:", sessionId);

        // Load chat history if exists
        const history = await chatService.getChatHistory();
        if (history.messages && history.messages.length > 0) {
          const formattedMessages: Message[] = history.messages.map((msg) => ({
            id: msg.id,
            content: msg.content,
            sender: msg.role === "user" ? "user" : "assistant",
            timestamp: new Date(msg.created_at),
          }));
          setMessages(formattedMessages);
        }
      } catch (error) {
        console.log("Error initializing chat:", error);
      }
    };

    initializeChat();
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
                console.log("Received workflow update:", event.data.workflow);
                setCurrentWorkflow(event.data.workflow);
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

        const updateData = {
          name: workflow.name,
          description: workflow.description,
          nodes: workflow.nodes || [],
          connections: connections,
          settings: workflow.settings,
          tags: workflow.tags || [],
        };

        await updateWorkflow(workflow.id, updateData);

        if (workflowToSave) {
          setCurrentWorkflow(workflowToSave);
        }

        toast({
          title: "Success",
          description: "Workflow saved successfully",
        });
      } catch (error) {
        console.error("Failed to save workflow:", error);
        toast({
          title: "Error",
          description: "Failed to save workflow. Please try again.",
          variant: "destructive",
        });
      } finally {
        setIsSavingWorkflow(false);
      }
    },
    [currentWorkflow, updateWorkflow, toast]
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

  if (isLoadingWorkflow) {
    return (
      <div className="h-full bg-[#F8F8F8] dark:bg-background transition-colors duration-300">
        <div className="flex h-full pt-12">
          {/* Left Side - Full Workflow Canvas Skeleton */}
          <div className="flex-1 pb-2 pl-2 pr-2 h-full">
            <div className="h-full flex flex-col">
              <div className="flex-1 bg-muted/20 rounded-lg border border-border overflow-hidden relative">
                {/* Control Panel Skeleton in top-right */}
                <div className="absolute top-4 right-4 z-10">
                  <div className="bg-background/80 backdrop-blur-sm border border-border rounded-lg p-1 shadow-lg">
                    <div className="flex items-center gap-1">
                      <Skeleton className="h-8 w-8 rounded" />
                      <Skeleton className="h-8 w-8 rounded" />
                      <Skeleton className="h-8 w-8 rounded" />
                      <div className="w-px h-6 bg-border mx-1" />
                      <Skeleton className="h-8 w-8 rounded" />
                      <Skeleton className="h-8 w-8 rounded" />
                      <Skeleton className="h-8 w-8 rounded" />
                    </div>
                  </div>
                </div>
                {/* Canvas Grid Background */}
                <div className="h-full w-full bg-muted/10" />
              </div>
            </div>
          </div>

          {/* Right Side - Chat Area Skeleton */}
          <div className="w-96 flex flex-col bg-background/95 backdrop-blur-sm h-full border-l border-t border-border/30 rounded-tl-lg">
            {/* Chat Header Skeleton */}
            <div className="p-4 border-b border-border/30">
              <div className="flex items-center gap-2">
                <Skeleton className="w-[20px] h-[20px] rounded-full" />
                <Skeleton className="h-5 w-32" />
              </div>
            </div>

            {/* Chat Messages Area Skeleton */}
            <div className="flex-1 p-4 space-y-4 overflow-hidden">
              <div className="flex justify-start">
                <Skeleton className="h-16 w-3/4 rounded-2xl" />
              </div>
              <div className="flex justify-end">
                <Skeleton className="h-12 w-2/3 rounded-2xl" />
              </div>
              <div className="flex justify-start">
                <Skeleton className="h-20 w-3/4 rounded-2xl" />
              </div>
            </div>

            {/* Input Area Skeleton */}
            <div className="p-4 mt-auto">
              <Skeleton className="h-12 w-full rounded-lg" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!currentWorkflow) {
    return (
      <div className="h-full pt-12 flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Workflow not found</p>
          <button
            onClick={() => router.push("/canvas")}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Back to Assistants
          </button>
        </div>
      </div>
    );
  }

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
            {/* Workflow Info */}
            <div className="px-4 py-3 bg-background/95 backdrop-blur-sm rounded-t-lg border border-b-0 border-border">
              {workflowDescription && (
                <p className="text-sm text-muted-foreground">
                  {workflowDescription}
                </p>
              )}
              {/* Execution Status and Time */}
              <div className={`flex items-center gap-3 ${workflowDescription ? 'mt-2' : ''}`}>
                {(() => {
                  const statusInfo = getExecutionStatusInfo(
                    latestExecutionStatus
                  );
                  const StatusIcon = statusInfo.icon;
                  return (
                    <div className="flex items-center gap-1.5">
                      <StatusIcon
                        className={`w-3.5 h-3.5 ${statusInfo.color}`}
                      />
                      <span
                        className={`text-xs font-medium ${statusInfo.color}`}
                      >
                        {statusInfo.label}
                      </span>
                    </div>
                  );
                })()}
                {latestExecutionTime && (
                  <>
                    <span className="text-muted-foreground/30">•</span>
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Clock className="w-3.5 h-3.5" />
                      <span className="text-xs">
                        Last run: {formatExecutionTime(latestExecutionTime)}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
            {/* Workflow Editor */}
            <div className="flex-1 bg-muted/20 rounded-lg border border-border overflow-hidden">
              <WorkflowEditor
                initialWorkflow={currentWorkflow}
                onSave={handleWorkflowChange}
                onApiSave={handleSaveWorkflow}
                isSaving={isSavingWorkflow}
                readOnly={false}
                className="h-full"
                onToggleFullscreen={() => setIsWorkflowExpanded(true)}
              />
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
          {/* Execution Logs Section */}
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
                <h3 className="text-sm font-semibold">Last Execution Logs</h3>
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
                    {/* Execution logs */}
                    {isLoadingLogs ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-primary rounded-full animate-bounce" />
                          <div
                            className="w-2 h-2 bg-primary rounded-full animate-bounce"
                            style={{ animationDelay: "0.1s" }}
                          />
                          <div
                            className="w-2 h-2 bg-primary rounded-full animate-bounce"
                            style={{ animationDelay: "0.2s" }}
                          />
                        </div>
                      </div>
                    ) : executionLogs.length === 0 ? (
                      <div className="text-xs text-muted-foreground text-center py-8">
                        No execution logs yet
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {executionLogs.map((log, index) => {
                          const statusInfo = getExecutionStatusInfo(log.status);
                          const StatusIcon = statusInfo.icon;
                          return (
                            <div
                              key={log.execution_id || index}
                              className="flex items-center justify-between p-2 rounded-md hover:bg-accent/50 transition-colors cursor-pointer"
                            >
                              <div className="flex items-center gap-2 flex-1 min-w-0">
                                <StatusIcon
                                  className={`w-3.5 h-3.5 flex-shrink-0 ${statusInfo.color}`}
                                />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span
                                      className={`text-xs font-medium ${statusInfo.color}`}
                                    >
                                      {statusInfo.label}
                                    </span>
                                    {log.duration && (
                                      <span className="text-xs text-muted-foreground">
                                        {log.duration}
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-xs text-muted-foreground truncate">
                                    {formatExecutionTime(log.timestamp)}
                                  </p>
                                  {log.error_message && (
                                    <p className="text-xs text-red-600 dark:text-red-400 truncate mt-0.5">
                                      {log.error_message}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Chat Section */}
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
                                <Bot className="w-4 h-4 mt-0.5 flex-shrink-0" />
                              )}
                              {message.sender === "user" && (
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
                      placeholder="Ask about this workflow..."
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
                  {workflowName || "Untitled Workflow"}
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

export default WorkflowDetailPage;
