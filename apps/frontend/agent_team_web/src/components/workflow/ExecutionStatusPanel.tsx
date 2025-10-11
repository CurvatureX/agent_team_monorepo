"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Activity,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { ExecutionStatus } from "@/lib/api/hooks/useExecutionApi";
import { ExecutionStatusEnum } from "@/types/workflow-enums";

interface ExecutionStatusPanelProps {
  status: ExecutionStatus | null;
  isPolling: boolean;
  className?: string;
  onClose?: () => void;
}

export const ExecutionStatusPanel: React.FC<ExecutionStatusPanelProps> = ({
  status,
  isPolling,
  className,
  onClose,
}) => {
  const [isExpanded, setIsExpanded] = React.useState(true);

  if (!status && !isPolling) return null;

  const getStatusIcon = (execStatus?: string) => {
    switch (execStatus) {
      case ExecutionStatusEnum.Completed:
      case ExecutionStatusEnum.Success:
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case "FAILED":
      case ExecutionStatusEnum.Error:
        return <XCircle className="w-4 h-4 text-red-500" />;
      case ExecutionStatusEnum.Running:
        return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
      case ExecutionStatusEnum.Idle:
      case ExecutionStatusEnum.Pending:
      case ExecutionStatusEnum.New:
      case ExecutionStatusEnum.Waiting:
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case ExecutionStatusEnum.Cancelled:
      case ExecutionStatusEnum.Canceled:
      case ExecutionStatusEnum.Paused:
      case ExecutionStatusEnum.WaitingForHuman:
      case ExecutionStatusEnum.Timeout:
      case ExecutionStatusEnum.Skipped:
        return <AlertCircle className="w-4 h-4 text-gray-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (execStatus?: string) => {
    switch (execStatus) {
      case ExecutionStatusEnum.Completed:
      case ExecutionStatusEnum.Success:
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      case "FAILED":
      case ExecutionStatusEnum.Error:
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      case ExecutionStatusEnum.Running:
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
      case ExecutionStatusEnum.Idle:
      case ExecutionStatusEnum.Pending:
      case ExecutionStatusEnum.New:
      case ExecutionStatusEnum.Waiting:
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      case ExecutionStatusEnum.Cancelled:
      case ExecutionStatusEnum.Canceled:
      case ExecutionStatusEnum.Paused:
      case ExecutionStatusEnum.WaitingForHuman:
      case ExecutionStatusEnum.Timeout:
      case ExecutionStatusEnum.Skipped:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  const toMs = (v?: string | number) => {
    if (v === undefined || v === null) return undefined;
    if (typeof v === 'number') return v < 1_000_000_000_000 ? v * 1000 : v;
    const s = v.trim();
    if (/^\d+$/.test(s)) {
      const iv = parseInt(s, 10);
      return iv < 1_000_000_000_000 ? iv * 1000 : iv;
    }
    const t = new Date(s).getTime();
    return isNaN(t) ? undefined : t;
  };

  const formatTime = (time?: string | number) => {
    if (!time) return "N/A";
    const ms = toMs(time);
    if (ms === undefined) return "N/A";
    return new Date(ms).toLocaleTimeString();
  };

  const calculateDuration = (
    start?: string | number,
    end?: string | number
  ) => {
    if (!start) return "N/A";

    const startTime = toMs(start);
    const endTime = end ? toMs(end) : Date.now();
    if (startTime === undefined || endTime === undefined) return "N/A";

    const duration = endTime - startTime;

    const seconds = Math.floor(duration / 1000);
    if (seconds < 60) return `${seconds}s`;

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        className={cn("fixed bottom-4 right-4 z-50 w-96", className)}
      >
        <Card className="shadow-lg border-border/50 bg-background/95 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm font-medium">
                  Execution Status
                </CardTitle>
                {status && (
                  <Badge
                    className={cn("text-xs", getStatusColor(status.status))}
                  >
                    {status.status}
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="p-1 hover:bg-accent rounded transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronUp className="w-4 h-4" />
                  )}
                </button>
                {onClose && (
                  <button
                    onClick={onClose}
                    className="p-1 hover:bg-accent rounded transition-colors"
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </CardHeader>

          {isExpanded && status && (
            <CardContent className="pt-0">
              <div className="space-y-3">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Execution ID:</span>
                    <span className="font-mono text-xs">
                      {status.execution_id?.slice(0, 8)}...
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Started:</span>
                    <span>{formatTime(status.start_time)}</span>
                  </div>
                  {status.end_time && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Ended:</span>
                      <span>{formatTime(status.end_time)}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Duration:</span>
                    <span>
                      {calculateDuration(status.start_time, status.end_time)}
                    </span>
                  </div>
                </div>

                {status.node_executions && status.node_executions.length > 0 ? (
                  <>
                    <Separator />
                    <div className="space-y-2">
                      <p className="text-xs font-medium">Node Executions:</p>
                      <ScrollArea className="h-32">
                        <div className="space-y-2">
                          {status.node_executions.map((node, index) => (
                            <div
                              key={node.node_id || index}
                              className="flex items-center justify-between p-2 rounded bg-accent/50"
                            >
                              <div className="flex items-center gap-2">
                                {getStatusIcon(node.status)}
                                <span className="text-xs font-medium">
                                  {node.node_id}
                                </span>
                              </div>
                              <span className="text-xs text-muted-foreground">
                                {calculateDuration(
                                  node.start_time,
                                  node.end_time
                                )}
                              </span>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </div>
                  </>
                ) : null}

                {status.result ? (
                  <>
                    <Separator />
                    <div className="space-y-1">
                      <p className="text-xs font-medium">Result:</p>
                      <ScrollArea className="h-24">
                        <pre className="text-xs text-muted-foreground bg-accent/30 p-2 rounded">
                          {JSON.stringify(status.result, null, 2)}
                        </pre>
                      </ScrollArea>
                    </div>
                  </>
                ) : null}
              </div>
            </CardContent>
          )}
        </Card>
      </motion.div>
    </AnimatePresence>
  );
};
