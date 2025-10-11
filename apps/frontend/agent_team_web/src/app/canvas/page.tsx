"use client";

import React, { useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import {
  Bot,
  Activity,
  AlertTriangle,
  Pause,
  CheckCircle,
  XCircle,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";
import { useWorkflowsApi } from "@/lib/api/hooks/useWorkflowsApi";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { WorkflowDeploymentStatus } from "@/types/workflow-enums";

// Type definitions
interface WorkflowItem {
  id: string;
  name: string;
  description: string;
  status: string;
  deploymentStatus: string;
  lastExecutionStatus: string;
  lastRunTime: Date | null;
  createdAt: Date;
  updatedAt: Date;
  executionCount: number;
  successRate: number;
  averageDuration: number;
  trigger: string | null;
  tags: string[];
  iconUrl: string | null;
  active: boolean;
  version: string;
}

interface RawWorkflow {
  id: string;
  name?: string;
  description?: string | null;
  status?: string;
  deployment_status?: string | null;
  latest_execution_status?: string | null;
  latest_execution_time?: number | string | null;
  created_at?: number | string | null;
  updated_at?: number | string | null;
  execution_count?: number;
  success_rate?: number;
  average_duration?: number;
  trigger?: string | null;
  tags?: string[];
  icon_url?: string | null;
  logo_url?: string | null;  // API returns logo_url (will be deprecated)
  active?: boolean;
  version?: string;
}

// Define deployment status configuration outside component for consistency
// Aligned with backend WorkflowDeploymentStatus enum
const deploymentStatusConfig = {
  UNDEPLOYED: {
    icon: Pause,
    label: "Undeployed",
    color: "text-gray-500",
    bg: "bg-gray-50",
    variant: "outline" as const,
  },
  DEPLOYING: {
    icon: Activity,
    label: "Deploying",
    color: "text-blue-500",
    bg: "bg-blue-50",
    variant: "secondary" as const,
  },
  DEPLOYED: {
    icon: CheckCircle,
    label: "Deployed",
    color: "text-green-500",
    bg: "bg-green-50",
    variant: "default" as const,
  },
  DEPLOYMENT_FAILED: {
    icon: XCircle,
    label: "Failed",
    color: "text-red-500",
    bg: "bg-red-50",
    variant: "destructive" as const,
  },
};

function CanvasPage() {
  const router = useRouter();
  const { session, loading: authLoading } = useAuth();
  const { workflows, isLoading, isError, error, mutate } = useWorkflowsApi();
  const [searchQuery] = React.useState("");
  const [statusFilter] = React.useState("all");
  const scrollRefs = useRef<Record<string, HTMLElement | null>>({});
  const [scrollStates, setScrollStates] = React.useState<
    Record<string, { showLeft: boolean; showRight: boolean }>
  >({});

  const handleRefresh = () => {
    mutate();
  };

  // Handle scroll events to show/hide navigation buttons
  const handleScroll = (e: React.UIEvent<HTMLDivElement>, status: string) => {
    const element = e.currentTarget;
    const showLeft = element.scrollLeft > 0;
    const showRight =
      element.scrollLeft < element.scrollWidth - element.clientWidth - 10;

    setScrollStates((prev) => ({
      ...prev,
      [status]: { showLeft, showRight },
    }));
  };

  // Scroll left function
  const scrollLeft = (status: string) => {
    const element = scrollRefs.current[status];
    if (element) {
      element.scrollBy({ left: -1000, behavior: "smooth" });
    }
  };

  // Scroll right function
  const scrollRight = (status: string) => {
    const element = scrollRefs.current[status];
    if (element) {
      element.scrollBy({ left: 1000, behavior: "smooth" });
    }
  };

  // Transform API data to display format
  const workflowsList = React.useMemo(() => {
    // Handle the API response structure
    let workflowArray: RawWorkflow[] = [];

    if (workflows) {
      if (Array.isArray(workflows)) {
        workflowArray = workflows;
      } else if (
        typeof workflows === "object" &&
        "workflows" in workflows &&
        Array.isArray((workflows as { workflows: RawWorkflow[] }).workflows)
      ) {
        workflowArray = (workflows as { workflows: RawWorkflow[] }).workflows;
      }
    }

    // Debug logging to check icon_url (can be removed after verification)
    if (workflowArray.length > 0 && process.env.NODE_ENV === 'development') {
      console.log("🔍 First workflow icon_url:", workflowArray[0].icon_url);
    }

    if (workflowArray.length === 0) return [];

    let filteredWorkflows = workflowArray.map(
      (workflow: RawWorkflow): WorkflowItem => ({
        id: workflow.id,
        name: workflow.name || "Unnamed Workflow",
        description: workflow.description || "",
        status: workflow.status || "pending",
        deploymentStatus:
          workflow.deployment_status || WorkflowDeploymentStatus.Undeployed,
        lastExecutionStatus: workflow.latest_execution_status || "pending",
        lastRunTime: workflow.latest_execution_time
          ? new Date(
              typeof workflow.latest_execution_time === "number"
                ? (workflow.latest_execution_time < 1_000_000_000_000
                    ? workflow.latest_execution_time * 1000
                    : workflow.latest_execution_time)
                : Date.parse(workflow.latest_execution_time)
            )
          : null,
        createdAt: workflow.created_at
          ? new Date(
              typeof workflow.created_at === "number"
                ? (workflow.created_at < 1_000_000_000_000
                    ? workflow.created_at * 1000
                    : workflow.created_at)
                : Date.parse(workflow.created_at)
            )
          : new Date(),
        updatedAt: workflow.updated_at
          ? new Date(
              typeof workflow.updated_at === "number"
                ? (workflow.updated_at < 1_000_000_000_000
                    ? workflow.updated_at * 1000
                    : workflow.updated_at)
                : Date.parse(workflow.updated_at)
            )
          : new Date(),
        executionCount: workflow.execution_count || 0,
        successRate: workflow.success_rate || 0,
        averageDuration: workflow.average_duration || 0,
        trigger: workflow.trigger || null,
        tags: workflow.tags || [],
        iconUrl: workflow.icon_url || workflow.logo_url || null,  // Support both fields
        active: workflow.active !== undefined ? workflow.active : true,
        version: workflow.version || "1.0.0",
      })
    );

    // Apply filters
    if (searchQuery) {
      filteredWorkflows = filteredWorkflows.filter(
        (w: WorkflowItem) =>
          w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          w.description.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (statusFilter !== "all") {
      filteredWorkflows = filteredWorkflows.filter(
        (w: WorkflowItem) => w.deploymentStatus === statusFilter
      );
    }

    return filteredWorkflows;
  }, [workflows, searchQuery, statusFilter]);

  // Initialize scroll states after data loads
  React.useEffect(() => {
    if (!workflows || isLoading) return;

    // Use setTimeout to ensure DOM is ready
    const timer = setTimeout(() => {
      const initialStates: Record<
        string,
        { showLeft: boolean; showRight: boolean }
      > = {};
      Object.keys(deploymentStatusConfig).forEach((status) => {
        const element = scrollRefs.current[status];
        if (element) {
          initialStates[status] = {
            showLeft: false,
            showRight: element.scrollWidth > element.clientWidth,
          };
        }
      });
      setScrollStates(initialStates);
    }, 100);

    return () => clearTimeout(timer);
  }, [workflows, isLoading]);

  const getTimeAgo = (date: Date | null): string => {
    if (!date) return "Never";
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;

    return date.toLocaleDateString();
  };

  // Helper function to get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case "deployed":
        return "text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-950 dark:border-green-800";
      case "undeployed":
        return "text-orange-600 bg-orange-50 border-orange-200 dark:text-orange-400 dark:bg-orange-950 dark:border-orange-800";
      case "pending":
        return "text-blue-600 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-950 dark:border-blue-800";
      case "failed":
        return "text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950 dark:border-red-800";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200 dark:text-gray-400 dark:bg-gray-950 dark:border-gray-800";
    }
  };

  // Skeleton Loading Component
  const SkeletonCard = () => (
    <Card className="flex-shrink-0 w-96 h-72 overflow-hidden rounded-2xl border bg-card text-card-foreground shadow-sm relative">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-lg bg-gray-200 dark:bg-gray-700 animate-pulse" />
            <div className="flex-1">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-2" />
              <div className="flex items-center gap-1.5">
                <div className="h-6 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                <div className="h-6 w-12 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pb-8">
        <div>
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-1.5" />
          <div className="space-y-1">
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-3/4" />
          </div>
        </div>
      </CardContent>
      <div className="absolute bottom-3 left-0 right-0 px-4 py-1 flex justify-between items-center">
        <div className="h-3 w-12 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        <div className="h-3 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
    </Card>
  );

  // Loading state with skeleton
  if (authLoading || (isLoading && workflowsList.length === 0)) {
    return (
      <div className="h-full">
        <div className="px-6 pt-16 pb-6">
          {/* Skeleton for each status group */}
          {Object.entries(deploymentStatusConfig).map(([status, config]) => (
            <div key={status} className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <config.icon className={`w-4 h-4 ${config.color}`} />
                  <div className="h-4 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                  <div className="h-5 w-6 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                </div>
                <div className="h-4 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              </div>

              <div className="overflow-x-auto">
                <div
                  className="flex gap-4 pb-4"
                  style={{ width: "max-content" }}
                >
                  {[1, 2, 3, 4, 5].map((i) => (
                    <SkeletonCard key={i} />
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!session) {
    return (
      <div className="h-full flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <Bot className="w-12 h-12 mx-auto mb-4 text-primary" />
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>
              Please sign in to access your workflows
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  // Error state
  if (isError && !isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 mx-auto mb-4 text-destructive" />
          <p className="text-destructive mb-2">
            {error?.message || "Failed to load workflows"}
          </p>
          <Button onClick={handleRefresh}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      <div className="px-6 pt-16 pb-6">
        {/* Group by Status */}
        {Object.entries(deploymentStatusConfig).map(([status, config]) => {
          const statusWorkflows = workflowsList.filter(
            (w: WorkflowItem) => w.deploymentStatus === status
          );

          if (statusWorkflows.length === 0) return null;

          return (
            <div key={status} className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <config.icon className={cn("w-4 h-4", config.color)} />
                  <h2 className="text-sm font-medium">{config.label}</h2>
                  <Badge variant="outline" className="text-xs">
                    {statusWorkflows.length}
                  </Badge>
                </div>
                <button className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">
                  View all
                  <ChevronRight className="h-3 w-3" />
                </button>
              </div>

              {/* Horizontal Scrolling Cards with Navigation */}
              <div className="relative">
                {/* Left Edge Shadow */}
                {scrollStates[status]?.showLeft && (
                  <div className="absolute left-0 top-0 bottom-0 w-20 pointer-events-none z-10 bg-gradient-to-r from-[#F8F8F8] dark:from-background to-transparent" />
                )}

                {/* Right Edge Shadow */}
                {scrollStates[status]?.showRight && (
                  <div className="absolute right-0 top-0 bottom-0 w-20 pointer-events-none z-10 bg-gradient-to-l from-[#F8F8F8] dark:from-background to-transparent" />
                )}

                {/* Scroll Container */}
                <div
                  className="overflow-x-auto scroll-smooth"
                  ref={(el) => {
                    // Store ref for this status group
                    if (!scrollRefs.current) scrollRefs.current = {};
                    scrollRefs.current[status] = el;
                  }}
                  onScroll={(e) => handleScroll(e, status)}
                >
                  <div
                    className="flex gap-4 pb-4"
                    style={{ width: "max-content" }}
                  >
                    {statusWorkflows.map((workflow: WorkflowItem) => {
                      const deploymentConfig =
                        deploymentStatusConfig[
                          workflow.deploymentStatus as keyof typeof deploymentStatusConfig
                        ] || deploymentStatusConfig.UNDEPLOYED;

                      return (
                        <Card
                          key={workflow.id}
                          className="flex-shrink-0 w-96 h-72 overflow-hidden rounded-2xl border bg-card text-card-foreground shadow-sm transition-shadow duration-300 hover:shadow-md relative cursor-pointer"
                          onClick={() =>
                            router.push(`/workflow/${workflow.id}`)
                          }
                        >
                          <CardHeader className="pb-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex items-center gap-3">
                                <div className="relative h-12 w-12 overflow-hidden rounded-lg bg-muted">
                                  {workflow.iconUrl ? (
                                    <Image
                                      src={workflow.iconUrl}
                                      alt={`${workflow.name} icon`}
                                      fill
                                      className="object-cover"
                                      loading="lazy"
                                    />
                                  ) : (
                                    <div className="h-full w-full flex items-center justify-center bg-primary/10">
                                      <Bot className="w-6 h-6 text-primary" />
                                    </div>
                                  )}
                                </div>
                                <div className="flex-1">
                                  <h3 className="text-sm font-semibold leading-tight text-foreground">
                                    {workflow.name}
                                  </h3>
                                  <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                                    <Badge
                                      variant="outline"
                                      className={cn(
                                        "font-medium text-[10px] px-1 py-0",
                                        getStatusColor(status)
                                      )}
                                    >
                                      {deploymentConfig.label}
                                    </Badge>
                                    {/* Tags inline with status */}
                                    {workflow.tags &&
                                      workflow.tags.length > 0 && (
                                        <>
                                          {workflow.tags.map(
                                            (tag: string, index: number) => (
                                              <Badge
                                                key={index}
                                                variant="secondary"
                                                className="text-[10px] px-1 py-0"
                                              >
                                                {tag}
                                              </Badge>
                                            )
                                          )}
                                        </>
                                      )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </CardHeader>

                          <CardContent className="space-y-4 pb-8">
                            <div>
                              <h4 className="text-xs font-medium text-foreground mb-1.5">
                                Description
                              </h4>
                              <TooltipProvider delayDuration={650}>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <p className="text-xs leading-relaxed text-muted-foreground line-clamp-3">
                                      {workflow.description ||
                                        "No description available"}
                                    </p>
                                  </TooltipTrigger>
                                  {workflow.description &&
                                    workflow.description.length > 100 && (
                                      <TooltipContent className="max-w-xs">
                                        <p className="text-sm">
                                          {workflow.description}
                                        </p>
                                      </TooltipContent>
                                    )}
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                          </CardContent>

                          {/* Fixed bottom row with version and timestamp at very bottom of card */}
                          <div className="absolute bottom-3 left-0 right-0 px-4 py-1 flex justify-between items-center text-xs text-muted-foreground">
                            <span>v{workflow.version}</span>
                            <span>
                              Updated: {getTimeAgo(workflow.updatedAt)}
                            </span>
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                </div>

                {/* Navigation Buttons */}
                {scrollStates[status]?.showLeft && (
                  <button
                    className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-white dark:bg-gray-900 rounded-full flex items-center justify-center hover:scale-105 transition-transform z-20"
                    style={{
                      boxShadow:
                        "0 2px 8px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.08)",
                    }}
                    onClick={() => scrollLeft(status)}
                  >
                    <ChevronLeft className="h-4 w-4 text-gray-700 dark:text-gray-200" />
                  </button>
                )}

                {scrollStates[status]?.showRight && (
                  <button
                    className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-white dark:bg-gray-900 rounded-full flex items-center justify-center hover:scale-105 transition-transform z-20"
                    style={{
                      boxShadow:
                        "0 2px 8px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.08)",
                    }}
                    onClick={() => scrollRight(status)}
                  >
                    <ChevronRight className="h-4 w-4 text-gray-700 dark:text-gray-200" />
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {/* Empty State */}
        {workflowsList.length === 0 && (
          <div className="mb-8">
            <Card className="p-8">
              <div className="text-center">
                <Bot className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <p className="text-lg font-medium mb-2">No assistants yet</p>
                <p className="text-sm text-muted-foreground">
                  Create your first assistant to get started
                </p>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

export default CanvasPage;
