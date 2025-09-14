import React from "react";
import { motion } from "framer-motion";
import { Bot, ArrowRight, Workflow, Clock, Activity, AlertTriangle, Play, Pause } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";
import { AIWorker } from "@/types/workflow";

// Deployment status configuration
const deploymentStatusConfig = {
  DRAFT: {
    icon: Clock,
    color: 'text-gray-500',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    label: 'Draft',
    pulse: false
  },
  PENDING: {
    icon: Activity,
    color: 'text-blue-500',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    label: 'Deploying',
    pulse: true
  },
  DEPLOYED: {
    icon: Play,
    color: 'text-green-500',
    bg: 'bg-green-50',
    border: 'border-green-200',
    label: 'Deployed',
    pulse: false
  },
  FAILED: {
    icon: AlertTriangle,
    color: 'text-red-500',
    bg: 'bg-red-50',
    border: 'border-red-200',
    label: 'Deploy Failed',
    pulse: false
  },
  UNDEPLOYED: {
    icon: Pause,
    color: 'text-gray-500',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    label: 'Undeployed',
    pulse: false
  }
};

// Execution status configuration
const executionStatusConfig = {
  DRAFT: {
    icon: Clock,
    color: 'text-gray-500',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    label: 'Never Run',
    pulse: false
  },
  RUNNING: {
    icon: Activity,
    color: 'text-orange-500',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    label: 'Running',
    pulse: true
  },
  SUCCESS: {
    icon: Play,
    color: 'text-green-500',
    bg: 'bg-green-50',
    border: 'border-green-200',
    label: 'Success',
    pulse: false
  },
  ERROR: {
    icon: AlertTriangle,
    color: 'text-red-500',
    bg: 'bg-red-50',
    border: 'border-red-200',
    label: 'Error',
    pulse: false
  },
  CANCELED: {
    icon: Pause,
    color: 'text-gray-500',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    label: 'Canceled',
    pulse: false
  },
  WAITING_FOR_HUMAN: {
    icon: Clock,
    color: 'text-blue-500',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    label: 'Waiting',
    pulse: true
  }
};

interface AIWorkerListProps {
  workers: AIWorker[];
  onWorkerSelect: (workerId: string) => void;
}

export const AIWorkerList: React.FC<AIWorkerListProps> = ({ workers, onWorkerSelect }) => {
  // Sort workers: deployed first, then by deployment status, then by name
  const sortedWorkers = [...workers].sort((a, b) => {
    // Primary sort: deployed status (DEPLOYED first)
    if (a.deploymentStatus === 'DEPLOYED' && b.deploymentStatus !== 'DEPLOYED') return -1;
    if (b.deploymentStatus === 'DEPLOYED' && a.deploymentStatus !== 'DEPLOYED') return 1;

    // Secondary sort: by deployment status priority
    const deploymentPriority = { 'DEPLOYED': 0, 'PENDING': 1, 'DRAFT': 2, 'FAILED': 3, 'UNDEPLOYED': 4 };
    const aPriority = deploymentPriority[a.deploymentStatus] ?? 5;
    const bPriority = deploymentPriority[b.deploymentStatus] ?? 5;
    if (aPriority !== bPriority) return aPriority - bPriority;

    // Tertiary sort: by name
    return a.name.localeCompare(b.name);
  });

  const deploymentCounts = workers.reduce((counts, worker) => {
    const status = worker.deploymentStatus;
    counts[status] = (counts[status] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  const executionCounts = workers.reduce((counts, worker) => {
    const status = worker.latestExecutionStatus;
    counts[status] = (counts[status] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  return (
    <div className="w-full h-full font-sans">
      <motion.div
        layout
        className="w-full h-full overflow-hidden rounded-2xl bg-background text-foreground shadow-lg border border-border/20"
        initial={{
          height: "100%",
          width: "100%",
        }}
        animate={{
          height: "100%",
          width: "100%",
        }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
      >
        <motion.div
          key="list"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
          className="h-full flex flex-col"
        >
          {/* Header */}
          <div className="p-6 border-b border-border/20">
            <h2 className="text-2xl font-semibold text-foreground mb-2">AI Workers</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Monitor and manage your automated workflow execution
            </p>

            {/* Status Overview */}
            <div className="space-y-3">
              <div>
                <h4 className="text-xs font-medium text-muted-foreground mb-2">Deployment Status</h4>
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(deploymentCounts).map(([status, count]) => {
                    const config = deploymentStatusConfig[status as keyof typeof deploymentStatusConfig];
                    if (!config) return null;
                    const StatusIcon = config.icon;
                    return (
                      <div key={status} className={clsx("flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium", config.bg, config.color)}>
                        <StatusIcon className="h-3 w-3" />
                        <span>{count}</span>
                        <span>{config.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <h4 className="text-xs font-medium text-muted-foreground mb-2">Execution Status</h4>
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(executionCounts).map(([status, count]) => {
                    const config = executionStatusConfig[status as keyof typeof executionStatusConfig];
                    if (!config) return null;
                    const StatusIcon = config.icon;
                    return (
                      <div key={status} className={clsx("flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium", config.bg, config.color)}>
                        <StatusIcon className="h-3 w-3" />
                        <span>{count}</span>
                        <span>{config.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Worker Grid */}
          <div className="p-6 flex-1 overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4">
              {sortedWorkers.map((worker) => {
                const deploymentConfig = deploymentStatusConfig[worker.deploymentStatus];
                const executionConfig = executionStatusConfig[worker.latestExecutionStatus];
                const DeploymentIcon = deploymentConfig.icon;
                const ExecutionIcon = executionConfig.icon;
                const isDeployed = worker.deploymentStatus === 'DEPLOYED';
                const isUndeployed = worker.deploymentStatus === 'UNDEPLOYED';

                return (
                  <motion.div
                    key={worker.id}
                    layoutId={`worker-${worker.id}`}
                    className={clsx(
                      "group cursor-pointer rounded-lg p-4 transition-all duration-200",
                      "border bg-card",
                      // Deployed cards - highlighted
                      isDeployed && [
                        "hover:shadow-xl hover:-translate-y-2",
                        "border-green-200/50 bg-gradient-to-br from-green-50/30 to-card",
                        "shadow-md shadow-green-100/20",
                        "ring-1 ring-green-100/30"
                      ],
                      // Undeployed cards - subdued
                      isUndeployed && [
                        "opacity-60 hover:opacity-80",
                        "border-border/10 bg-muted/30",
                        "hover:shadow-sm hover:-translate-y-0.5"
                      ],
                      // Other cards - normal
                      !isDeployed && !isUndeployed && [
                        "hover:shadow-lg hover:-translate-y-1",
                        "border-border/20"
                      ],
                      executionConfig.pulse && "ring-2 ring-opacity-20",
                      executionConfig.pulse && executionConfig.color.replace('text-', 'ring-')
                    )}
                    onClick={() => onWorkerSelect(worker.id)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    {/* Header with Status */}
                    <div className="flex items-start justify-between mb-3">
                      <motion.div
                        layoutId={`avatar-${worker.id}`}
                        className={clsx(
                          "relative w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
                          deploymentConfig.bg,
                          deploymentConfig.border,
                          "border-2"
                        )}
                        transition={{ duration: 0.5 }}
                      >
                        <Bot className={clsx("w-5 h-5", deploymentConfig.color)} />
                        <div
                          className={clsx(
                            "absolute -top-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center border-2 border-background",
                            executionConfig.bg
                          )}
                        >
                          <ExecutionIcon className={clsx("w-2.5 h-2.5", executionConfig.color, executionConfig.pulse && "animate-pulse")} />
                        </div>
                      </motion.div>

                      <div className="flex flex-col gap-1">
                        <div className="flex items-center justify-end gap-1.5">
                          <span className="text-xs text-muted-foreground">Deployment:</span>
                          <span className={clsx("px-2 py-1 text-xs font-medium rounded-full", deploymentConfig.bg, deploymentConfig.color)}>
                            {deploymentConfig.label}
                          </span>
                        </div>
                        <div className="flex items-center justify-end gap-1.5">
                          <span className="text-xs text-muted-foreground">Execution:</span>
                          <span className={clsx("px-2 py-1 text-xs font-medium rounded-full", executionConfig.bg, executionConfig.color)}>
                            {executionConfig.label}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Worker Info */}
                    <div className="mb-3">
                      <motion.h3
                        layoutId={`name-${worker.id}`}
                        className={clsx(
                          "font-semibold text-base mb-1 group-hover:text-primary transition-colors",
                          isUndeployed ? "text-muted-foreground" : "text-foreground"
                        )}
                      >
                        {worker.name}
                      </motion.h3>

                      <motion.p
                        layoutId={`description-${worker.id}`}
                        className={clsx(
                          "text-xs line-clamp-3 leading-relaxed",
                          isUndeployed ? "text-muted-foreground/70" : "text-muted-foreground"
                        )}
                      >
                        {worker.description}
                      </motion.p>
                    </div>

                    {/* Stats */}
                    <div className={clsx(
                      "space-y-1.5 text-xs",
                      isUndeployed ? "text-muted-foreground/50" : "text-muted-foreground"
                    )}>
                      <div className="flex items-center justify-between">
                        <span>Total Runs</span>
                        <span className={clsx(
                          "font-medium",
                          isUndeployed ? "text-muted-foreground" : "text-foreground"
                        )}>
                          {worker.executionHistory.length}
                        </span>
                      </div>

                      {worker.lastRunTime && (
                        <div className="flex items-center justify-between">
                          <span>Last Run</span>
                          <span className={clsx(
                            "font-medium",
                            isUndeployed ? "text-muted-foreground" : "text-foreground"
                          )}>
                            {formatDistanceToNow(worker.lastRunTime, { addSuffix: true })}
                          </span>
                        </div>
                      )}

                      {worker.nextRunTime && worker.deploymentStatus === 'DEPLOYED' && worker.latestExecutionStatus !== 'ERROR' && (
                        <div className="flex items-center justify-between">
                          <span>Next Run</span>
                          <span className={clsx(
                            "font-medium",
                            isUndeployed ? "text-muted-foreground" : "text-foreground"
                          )}>
                            {formatDistanceToNow(worker.nextRunTime, { addSuffix: true })}
                          </span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};
