"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  ArrowLeft,
  Maximize2,
  Workflow,
  Home,
  User,
  Play,
  Clock,
  Activity,
  AlertTriangle,
  Pause,
  ChevronDown,
  ChevronUp,
  RefreshCw,
} from "lucide-react";
import { AIWorkerList } from "@/components/ui/AIWorkerList";
import { WorkflowVisualization } from "@/components/workflow/WorkflowVisualization";
import {
  useWorkflowData,
  useWorkflowDetail,
  useExecutionData,
  useRealtimeExecution,
  useExecutionLogs,
} from "@/hooks/useApiData";
import { useAuth } from "@/contexts/auth-context";
import { AIWorker, ExecutionRecord } from "@/types/workflow";
import clsx from "clsx";

// Deployment status configuration
const deploymentStatusConfig = {
  DRAFT: {
    icon: Clock,
    color: "text-gray-500",
    bg: "bg-gray-50",
    border: "border-gray-200",
    label: "Draft",
    pulse: false,
  },
  PENDING: {
    icon: Activity,
    color: "text-blue-500",
    bg: "bg-blue-50",
    border: "border-blue-200",
    label: "Deploying",
    pulse: true,
  },
  DEPLOYED: {
    icon: Play,
    color: "text-green-500",
    bg: "bg-green-50",
    border: "border-green-200",
    label: "Deployed",
    pulse: false,
  },
  FAILED: {
    icon: AlertTriangle,
    color: "text-red-500",
    bg: "bg-red-50",
    border: "border-red-200",
    label: "Deploy Failed",
    pulse: false,
  },
  UNDEPLOYED: {
    icon: Pause,
    color: "text-gray-500",
    bg: "bg-gray-50",
    border: "border-gray-200",
    label: "Undeployed",
    pulse: false,
  },
};

// Execution status configuration
const executionStatusConfig = {
  DRAFT: {
    icon: Clock,
    color: "text-gray-500",
    bg: "bg-gray-50",
    border: "border-gray-200",
    label: "Never Run",
    pulse: false,
  },
  RUNNING: {
    icon: Activity,
    color: "text-orange-500",
    bg: "bg-orange-50",
    border: "border-orange-200",
    label: "Running",
    pulse: true,
  },
  SUCCESS: {
    icon: Play,
    color: "text-green-500",
    bg: "bg-green-50",
    border: "border-green-200",
    label: "Success",
    pulse: false,
  },
  ERROR: {
    icon: AlertTriangle,
    color: "text-red-500",
    bg: "bg-red-50",
    border: "border-red-200",
    label: "Error",
    pulse: false,
  },
  CANCELED: {
    icon: Pause,
    color: "text-gray-500",
    bg: "bg-gray-50",
    border: "border-gray-200",
    label: "Canceled",
    pulse: false,
  },
  WAITING_FOR_HUMAN: {
    icon: Clock,
    color: "text-blue-500",
    bg: "bg-blue-50",
    border: "border-blue-200",
    label: "Waiting",
    pulse: true,
  },
};

const CanvasPage = () => {
  // UI state
  const [selectedWorkerId, setSelectedWorkerId] = useState<string | null>(null);

  // API hooks
  const { user, session, loading: authLoading, signIn, signOut } = useAuth();
  const {
    workers,
    isLoading: dataLoading,
    error: dataError,
    refresh,
  } = useWorkflowData();
  const {
    workflow: detailedWorkflow,
    isLoading: workflowDetailLoading,
    error: workflowDetailError,
    fetchWorkflowDetail,
  } = useWorkflowDetail(selectedWorkerId);
  const { getExecution, fetchExecution } = useExecutionData();

  const [isWorkflowExpanded, setIsWorkflowExpanded] = useState(false);
  const [currentExecution, setCurrentExecution] =
    useState<ExecutionRecord | null>(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(
    null
  );
  const [currentLogPage, setCurrentLogPage] = useState(1);
  const [logsPerPage] = useState(50); // Show 50 logs per page
  const [showLoginForm, setShowLoginForm] = useState(false);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Use detailed workflow data if available, otherwise fall back to list data
  // Merge with fresh execution data from the dedicated hook
  const selectedWorker = selectedWorkerId
    ? (() => {
        const baseWorker =
          detailedWorkflow || workers.find((w) => w.id === selectedWorkerId);
        if (baseWorker && detailedWorkflow?.executionHistory && detailedWorkflow.executionHistory.length > 0) {
          // Use fresh execution data from the hook instead of stale data
          return {
            ...baseWorker,
            executionHistory: detailedWorkflow.executionHistory,
          };
        }
        return baseWorker;
      })()
    : null;

  // Auto-select the most recent execution if none is selected
  const effectiveSelectedExecutionId = selectedExecutionId ||
    (selectedWorker?.executionHistory && selectedWorker.executionHistory.length > 0
      ? selectedWorker.executionHistory[0].id
      : null);

  // Determine if the selected execution is currently running
  const selectedExecution = selectedWorker?.executionHistory?.find(
    exec => exec.id === effectiveSelectedExecutionId
  );
  const isSelectedExecutionRunning = selectedExecution?.status === "RUNNING";

  // Use static API for completed executions, real-time for running executions
  const {
    logs: staticLogs,
    isLoading: staticLogsLoading,
    error: staticLogsError,
    clearLogs: clearStaticLogs,
  } = useExecutionLogs(!isSelectedExecutionRunning ? effectiveSelectedExecutionId : null);

  // Use real-time streaming for currently running executions
  const {
    logs: realtimeLogs,
    isConnected: logsConnected,
    error: realtimeLogsError,
    isComplete: logsComplete,
    clearLogs: clearRealtimeLogs,
    reconnect: reconnectLogs,
  } = useRealtimeExecution(
    isSelectedExecutionRunning ? effectiveSelectedExecutionId : null,
    isSelectedExecutionRunning
  );

  // Determine which logs to display based on execution status
  const allDisplayLogs = isSelectedExecutionRunning ? realtimeLogs : staticLogs;
  const displayLoading = !isSelectedExecutionRunning ? staticLogsLoading : false;
  const displayError = isSelectedExecutionRunning ? realtimeLogsError : staticLogsError;
  const clearDisplayLogs = isSelectedExecutionRunning ? clearRealtimeLogs : clearStaticLogs;

  // Pagination logic
  const totalPages = Math.ceil(allDisplayLogs.length / logsPerPage);
  const startIndex = (currentLogPage - 1) * logsPerPage;
  const endIndex = startIndex + logsPerPage;
  const displayLogs = allDisplayLogs.slice(startIndex, endIndex);

  // Reset pagination when execution changes
  useEffect(() => {
    setCurrentLogPage(1);
  }, [effectiveSelectedExecutionId]);

  const isAuthenticated = !!session && !!user;

  // Helper to get execution logs
  const getExecutionLogs = (execution: ExecutionRecord) => {
    // Try to get logs from nodeExecutions first
    if (execution.nodeExecutions) {
      return execution.nodeExecutions.flatMap((node) => node.logs || []);
    }

    // Fallback to empty logs
    return [];
  };

  // Set current execution for selected worker
  useEffect(() => {
    if (selectedWorker && selectedWorker.executionHistory.length > 0) {
      // Get the latest execution for the selected worker
      const latestExecution = selectedWorker.executionHistory[0];
      setCurrentExecution(latestExecution);
    } else {
      setCurrentExecution(null);
    }
  }, [selectedWorker]);

  const handleWorkerSelect = (workerId: string) => {
    setSelectedWorkerId(workerId);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const { error } = await signIn(loginEmail, loginPassword);
      if (error) {
        console.error("Login error:", error);
      } else {
        setShowLoginForm(false);
      }
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  const handleDefaultLogin = async () => {
    const defaultEmail = process.env.NEXT_PUBLIC_DEFAULT_USERNAME;
    const defaultPassword = process.env.NEXT_PUBLIC_DEFAULT_PASSWORD;

    if (!defaultEmail || !defaultPassword) {
      console.error("Default credentials not configured");
      return;
    }

    try {
      const { error } = await signIn(defaultEmail, defaultPassword);
      if (error) {
        console.error("Default login error:", error);
      } else {
        setShowLoginForm(false);
      }
    } catch (error) {
      console.error("Default login failed:", error);
    }
  };

  return (
    <div className="h-screen bg-background text-foreground flex flex-col">
      {/* Top App Navigation */}
      <div className="border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 py-3">
          {/* App Icon */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
          </div>

          {/* Center Navigation */}
          <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
            <button className="flex items-center gap-2 px-4 py-2 rounded-md bg-background shadow-sm text-foreground text-sm font-medium">
              <Home className="w-4 h-4" />
              Home
            </button>
          </div>

          {/* User Icon */}
          <div className="flex items-center gap-3">
            <button className="w-8 h-8 bg-muted rounded-full flex items-center justify-center hover:bg-accent transition-colors">
              <User className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
        </div>
      </div>

      {/* Workflow Thumbnails - Only show when a workflow is selected */}
      <AnimatePresence>
        {selectedWorker && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
            className="border-b border-border bg-card overflow-hidden"
          >
            <div className="px-6 py-4">
              <div className="flex items-center gap-4 overflow-x-auto scrollbar-thin">
                {workers.map((worker) => {
                  const deploymentConfig =
                    deploymentStatusConfig[worker.deploymentStatus];
                  const executionConfig =
                    executionStatusConfig[worker.latestExecutionStatus];
                  const isSelected = worker.id === selectedWorkerId;

                  return (
                    <motion.button
                      key={worker.id}
                      layoutId={`thumbnail-${worker.id}`}
                      onClick={() => setSelectedWorkerId(worker.id)}
                      className={clsx(
                        "flex-shrink-0 flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200",
                        "border border-border/20 bg-background hover:bg-accent",
                        isSelected &&
                          "ring-2 ring-primary border-primary bg-primary/5"
                      )}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <div
                        className={clsx(
                          "relative w-12 h-8 rounded-md flex items-center justify-center flex-shrink-0",
                          deploymentConfig.bg,
                          "border border-border/20"
                        )}
                      >
                        <Bot
                          className={clsx("w-4 h-4", deploymentConfig.color)}
                        />
                        {/* Deployment status indicator */}
                        <div
                          className={clsx(
                            "absolute -top-1 -left-1 w-3 h-3 rounded-full flex items-center justify-center border border-background",
                            deploymentConfig.bg
                          )}
                        >
                          <deploymentConfig.icon
                            className={clsx("w-2 h-2", deploymentConfig.color)}
                          />
                        </div>
                        {/* Execution status indicator */}
                        <div
                          className={clsx(
                            "absolute -top-1 -right-1 w-3 h-3 rounded-full flex items-center justify-center border border-background",
                            executionConfig.bg
                          )}
                        >
                          <executionConfig.icon
                            className={clsx(
                              "w-2 h-2",
                              executionConfig.color,
                              executionConfig.pulse && "animate-pulse"
                            )}
                          />
                        </div>
                      </div>
                      <span
                        className={clsx(
                          "text-sm font-medium whitespace-nowrap",
                          isSelected ? "text-primary" : "text-foreground"
                        )}
                      >
                        {worker.name}
                      </span>
                    </motion.button>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {/* Loading State - Only show on initial load, not on refresh */}
        {(authLoading || (dataLoading && workers.length === 0)) && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Activity className="w-8 h-8 mx-auto mb-4 animate-spin text-primary" />
              <p className="text-muted-foreground">
                {authLoading ? "Authenticating..." : "Loading workflows..."}
              </p>
            </div>
          </div>
        )}

        {/* Login State */}
        {!isAuthenticated && !authLoading && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md mx-auto p-6">
              <Bot className="w-12 h-12 mx-auto mb-4 text-primary" />
              <h2 className="text-2xl font-bold mb-2">AI Worker Dashboard</h2>
              <p className="text-muted-foreground mb-6">
                Please sign in to access your workflows
              </p>

              {!showLoginForm ? (
                <button
                  onClick={() => setShowLoginForm(true)}
                  className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
                >
                  Sign In
                </button>
              ) : (
                <form onSubmit={handleLogin} className="space-y-4">
                  <input
                    type="email"
                    placeholder="Email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    className="w-full px-4 py-2 border border-border rounded-lg bg-background text-foreground"
                    required
                  />
                  <input
                    type="password"
                    placeholder="Password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    className="w-full px-4 py-2 border border-border rounded-lg bg-background text-foreground"
                    required
                  />
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
                      >
                        Sign In
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowLoginForm(false)}
                        className="px-4 py-2 border border-border rounded-lg hover:bg-muted"
                      >
                        Cancel
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={handleDefaultLogin}
                      className="w-full px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 border border-border"
                    >
                      Use Default Account
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* Error State */}
        {dataError && !authLoading && !dataLoading && isAuthenticated && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <AlertTriangle className="w-8 h-8 mx-auto mb-4 text-red-500" />
              <p className="text-red-600 mb-2">{dataError}</p>
              <button
                onClick={refresh}
                className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Main Content - Workers List */}
        {!selectedWorker && isAuthenticated && !authLoading && !dataError && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="h-full"
          >
            <AIWorkerList
              workers={workers}
              onWorkerSelect={handleWorkerSelect}
            />
          </motion.div>
        )}

        {selectedWorker && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="h-full flex flex-col"
          >
            {/* Workflow Header */}
            <div className="p-4 bg-card border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setSelectedWorkerId(null)}
                    className="p-2 hover:bg-accent rounded-lg transition-colors mr-2"
                    title="Back to Workers"
                  >
                    <ArrowLeft className="w-4 h-4" />
                  </motion.button>
                  <Workflow className="w-5 h-5 text-primary" />
                  <h3 className="text-lg font-semibold">
                    {selectedWorker.name}&apos;s Workflow
                  </h3>
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setIsWorkflowExpanded(!isWorkflowExpanded)}
                  className="p-2 hover:bg-accent rounded-lg transition-colors"
                  title="Expand Workflow"
                >
                  <Maximize2 className="w-4 h-4" />
                </motion.button>
              </div>
            </div>

            {/* Content Layout - Left and Right Panels */}
            <div className="flex-1 flex overflow-hidden">
              {/* Left Panel - Workflow Graph (60% width) */}
              <div className="w-[60%] border-r border-border bg-card flex flex-col">
                {/* Workflow Description */}
                <div className="p-4 bg-background border-b border-border">
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {selectedWorker.name}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {selectedWorker.description}
                  </p>
                </div>

                {/* Status Overview */}
                <div className="p-4 bg-background border-b border-border">
                  <div className="grid grid-cols-4 gap-3">
                    <div className="text-center">
                      <div className="text-xl font-bold text-foreground">
                        {selectedWorker.executionHistory.length}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Total Runs
                      </div>
                    </div>
                    <div className="text-center">
                      <div
                        className={clsx(
                          "text-lg font-bold",
                          selectedWorker.deploymentStatus === "DEPLOYED"
                            ? "text-green-500"
                            : selectedWorker.deploymentStatus === "PENDING"
                            ? "text-blue-500"
                            : selectedWorker.deploymentStatus === "FAILED"
                            ? "text-red-500"
                            : "text-gray-500"
                        )}
                      >
                        {deploymentStatusConfig[selectedWorker.deploymentStatus]
                          ?.label || selectedWorker.deploymentStatus}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Deployment
                      </div>
                    </div>
                    <div className="text-center">
                      <div
                        className={clsx(
                          "text-lg font-bold",
                          selectedWorker.latestExecutionStatus === "RUNNING"
                            ? "text-orange-500"
                            : selectedWorker.latestExecutionStatus === "SUCCESS"
                            ? "text-green-500"
                            : selectedWorker.latestExecutionStatus === "ERROR"
                            ? "text-red-500"
                            : "text-gray-500"
                        )}
                      >
                        {executionStatusConfig[
                          selectedWorker.latestExecutionStatus
                        ]?.label || selectedWorker.latestExecutionStatus}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Last Execution
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-foreground">
                        {selectedWorker.lastRunTime
                          ? (() => {
                              const minsAgo = Math.floor(
                                (Date.now() - selectedWorker.lastRunTime.getTime()) /
                                1000 /
                                60
                              );
                              return minsAgo === 0 ? "<1" : minsAgo.toString();
                            })()
                          : "--"}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Mins Ago
                      </div>
                    </div>
                  </div>
                </div>

                {/* Workflow Visualization with Current Execution */}
                <div className="flex-1 overflow-hidden">
                  <WorkflowVisualization
                    workflow={selectedWorker}
                    currentExecution={
                      selectedWorker?.latestExecutionStatus === "RUNNING" && currentExecution
                        ? currentExecution
                        : undefined
                    }
                    className="h-full"
                  />
                </div>
              </div>

              {/* Right Panel - Recent Executions (40% width) */}
              <div className="w-[40%] flex flex-col overflow-hidden border-t border-border bg-card">
                {/* Header */}
                <div className="p-4 border-b border-border flex items-center justify-between">
                  <h4 className="text-sm font-semibold">Recent Executions</h4>
                  <button
                    onClick={() => selectedWorkerId && fetchWorkflowDetail(selectedWorkerId)}
                    className="p-1 hover:bg-accent rounded transition-colors"
                    title="Refresh executions"
                  >
                    <RefreshCw
                      className={clsx(
                        "w-4 h-4",
                        workflowDetailLoading && "animate-spin"
                      )}
                    />
                  </button>
                </div>

                {/* Loading state */}
                {workflowDetailLoading && (
                  <div className="flex items-center justify-center p-4">
                    <Activity className="w-4 h-4 animate-spin text-primary mr-2" />
                    <span className="text-sm text-muted-foreground">
                      Loading executions...
                    </span>
                  </div>
                )}

                {/* Error state */}
                {workflowDetailError && (
                  <div className="flex items-center justify-center p-4">
                    <AlertTriangle className="w-4 h-4 text-red-500 mr-2" />
                    <span className="text-sm text-red-600">
                      {workflowDetailError}
                    </span>
                    <button
                      onClick={() => selectedWorkerId && fetchWorkflowDetail(selectedWorkerId)}
                      className="ml-2 px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                    >
                      Retry
                    </button>
                  </div>
                )}

                {/* Empty state */}
                {selectedWorker?.executionHistory?.length === 0 &&
                  !workflowDetailLoading && (
                    <div className="flex items-center justify-center p-8 text-muted-foreground">
                      <div className="text-center">
                        <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No executions yet</p>
                        <p className="text-xs">
                          Run this workflow to see execution history
                        </p>
                      </div>
                    </div>
                  )}

                {/* Executions List */}
                <div className="flex-1 overflow-y-auto px-4 py-2 space-y-2">
                  {selectedWorker?.executionHistory?.map((exec) => (
                    <div key={exec.id} className="space-y-2">
                      {/* Execution Item */}
                      <div
                        onClick={() => {
                          const newSelectedId =
                            effectiveSelectedExecutionId === exec.id ? null : exec.id;
                          setSelectedExecutionId(newSelectedId);
                          // Clear logs when switching
                          clearStaticLogs();
                          clearRealtimeLogs();
                        }}
                        className={clsx(
                          "flex items-center justify-between text-sm p-3 rounded transition-colors border cursor-pointer",
                          effectiveSelectedExecutionId === exec.id
                            ? "border-primary bg-primary/10"
                            : "border-border/20 hover:bg-accent/50"
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className={clsx(
                              "w-2 h-2 rounded-full",
                              exec.status === "SUCCESS"
                                ? "bg-green-500"
                                : exec.status === "ERROR"
                                ? "bg-red-500"
                                : exec.status === "RUNNING"
                                ? "bg-orange-500 animate-pulse"
                                : "bg-gray-400"
                            )}
                          />
                          <div className="flex flex-col">
                            <span className="text-muted-foreground text-xs">
                              {exec.startTime.toLocaleString()}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {exec.duration && !isNaN(exec.duration) && (
                            <span className="text-muted-foreground text-xs">
                              {exec.duration}s
                            </span>
                          )}
                          <span
                            className={clsx(
                              "px-2 py-1 rounded text-xs font-medium",
                              exec.status === "SUCCESS"
                                ? "bg-green-100 text-green-700"
                                : exec.status === "ERROR"
                                ? "bg-red-100 text-red-700"
                                : exec.status === "RUNNING"
                                ? "bg-orange-100 text-orange-700"
                                : "bg-gray-100 text-gray-700"
                            )}
                          >
                            {exec.status}
                          </span>
                        </div>
                      </div>

                      {/* Expanded Logs for Selected Execution */}
                      {effectiveSelectedExecutionId === exec.id && (
                        <div className="border border-border rounded bg-background">
                          {/* Connection Status */}
                          <div
                            className={clsx(
                              "px-3 py-2 text-xs flex items-center gap-2 border-b border-border",
                              exec.status === "RUNNING"
                                ? logsConnected
                                  ? "bg-green-50 text-green-700 border-green-200"
                                  : displayError
                                  ? "bg-red-50 text-red-700 border-red-200"
                                  : "bg-blue-50 text-blue-700 border-blue-200"
                                : displayLoading
                                ? "bg-blue-50 text-blue-700 border-blue-200"
                                : "bg-gray-50 text-gray-700 border-gray-200"
                            )}
                          >
                            <div
                              className={clsx(
                                "w-2 h-2 rounded-full",
                                exec.status === "RUNNING"
                                  ? logsConnected
                                    ? "bg-green-500 animate-pulse"
                                    : displayError
                                    ? "bg-red-500"
                                    : "bg-blue-500 animate-pulse"
                                  : displayLoading
                                  ? "bg-blue-500 animate-pulse"
                                  : "bg-gray-500"
                              )}
                            ></div>
                            <span>
                              {exec.status === "RUNNING"
                                ? logsConnected
                                  ? "Connected to real-time logs"
                                  : displayError
                                  ? `Error: ${displayError}`
                                  : "Connecting to logs..."
                                : displayLoading
                                ? "Loading execution logs..."
                                : "Execution logs"}
                            </span>
                            {displayError && exec.status === "RUNNING" && (
                              <button
                                onClick={reconnectLogs}
                                className="ml-auto text-xs underline hover:no-underline"
                              >
                                Retry
                              </button>
                            )}
                          </div>

                          {/* Logs Display */}
                          <div className="h-[600px] overflow-y-auto bg-gray-900 text-gray-100 font-mono text-sm">
                            {displayLogs.length > 0 ? (
                              <div className="p-3 space-y-1">
                                {displayLogs.map((log, index) => {
                                  const timestamp = new Date(log.timestamp);
                                  const timeStr = timestamp.toLocaleTimeString();

                                  let messagePrefix = "";
                                  if (log.is_milestone) {
                                    messagePrefix = "🎯 ";
                                  } else if (log.display_priority <= 3) {
                                    messagePrefix = "⚡ ";
                                  } else if (log.step_number && log.total_steps) {
                                    messagePrefix = `📋 Step ${log.step_number}/${log.total_steps}: `;
                                  }

                                  return (
                                    <div
                                      key={log.id || `log-${index}`}
                                      className={clsx(
                                        "flex items-start gap-3 py-1 border-l-2 pl-3",
                                        log.is_milestone
                                          ? "border-yellow-400 bg-yellow-900/10"
                                          : log.display_priority <= 3
                                          ? "border-blue-400 bg-blue-900/10"
                                          : log.level === "error"
                                          ? "border-red-400 bg-red-900/10"
                                          : log.level === "warn"
                                          ? "border-yellow-400 bg-yellow-900/10"
                                          : "border-gray-600"
                                      )}
                                    >
                                      <span className="text-gray-500 text-xs w-16 flex-shrink-0">
                                        {timeStr}
                                      </span>
                                      <span
                                        className={clsx(
                                          "text-xs font-medium w-10 flex-shrink-0",
                                          log.level === "error"
                                            ? "text-red-400"
                                            : log.level === "warn"
                                            ? "text-yellow-400"
                                            : log.level === "info"
                                            ? "text-blue-400"
                                            : "text-gray-400"
                                        )}
                                      >
                                        {log.level?.toUpperCase() || "INFO"}
                                      </span>
                                      {log.node_id && (
                                        <span className="text-purple-400 text-xs w-16 flex-shrink-0 truncate">
                                          [{log.node_id}]
                                        </span>
                                      )}
                                      <span className="text-gray-100 flex-1 min-w-0 break-words">
                                        {messagePrefix}
                                        {log.message}
                                        {exec.status === "RUNNING" && log.is_realtime && (
                                          <span className="ml-2 text-xs text-green-400">
                                            ●
                                          </span>
                                        )}
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <div className="flex items-center justify-center h-full text-muted-foreground">
                                <div className="text-center">
                                  <Activity
                                    className={clsx(
                                      "w-8 h-8 mx-auto mb-2 opacity-50",
                                      displayLoading && "animate-spin"
                                    )}
                                  />
                                  <p className="text-sm">
                                    {exec.status === "RUNNING"
                                      ? logsConnected
                                        ? "Waiting for real-time logs..."
                                        : "Connecting to logs..."
                                      : displayLoading
                                      ? "Loading execution logs..."
                                      : "No logs found"}
                                  </p>
                                  {displayError && (
                                    <p className="text-xs text-red-400 mt-2">
                                      {displayError}
                                    </p>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Log Controls and Pagination */}
                          {allDisplayLogs.length > 0 && (
                            <div className="border-t border-border px-3 py-2 space-y-2">
                              {/* Log info and clear button */}
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">
                                  Showing {startIndex + 1}-{Math.min(endIndex, allDisplayLogs.length)} of {allDisplayLogs.length} log entries{" "}
                                  {exec.status === "RUNNING" ? "(real-time)" : "(static)"}
                                </span>
                                <button
                                  onClick={clearDisplayLogs}
                                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                                >
                                  Clear
                                </button>
                              </div>

                              {/* Pagination Controls */}
                              {totalPages > 1 && (
                                <div className="flex items-center justify-center gap-2">
                                  <button
                                    onClick={() => setCurrentLogPage(Math.max(1, currentLogPage - 1))}
                                    disabled={currentLogPage === 1}
                                    className="px-2 py-1 text-xs border border-border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent transition-colors"
                                  >
                                    Previous
                                  </button>
                                  <span className="text-xs text-muted-foreground px-2">
                                    Page {currentLogPage} of {totalPages}
                                  </span>
                                  <button
                                    onClick={() => setCurrentLogPage(Math.min(totalPages, currentLogPage + 1))}
                                    disabled={currentLogPage === totalPages}
                                    className="px-2 py-1 text-xs border border-border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent transition-colors"
                                  >
                                    Next
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Expanded Workflow View */}
      <AnimatePresence>
        {isWorkflowExpanded && selectedWorker && (
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
                  {selectedWorker.name}&apos;s Workflow
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
            {/* Workflow Visualization */}
            <div className="flex-1">
              <WorkflowVisualization
                workflow={selectedWorker}
                currentExecution={
                  selectedWorker?.latestExecutionStatus === "RUNNING" && currentExecution
                    ? currentExecution
                    : undefined
                }
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
