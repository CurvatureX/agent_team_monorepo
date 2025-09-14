import React, { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  Play,
  Calendar,
  Filter,
  Search,
  Eye,
  ChevronDown,
  ChevronRight,
  Activity
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import { ExecutionRecord } from '../types';

const statusConfig = {
  completed: {
    icon: CheckCircle,
    color: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-200',
    label: 'Completed'
  },
  failed: {
    icon: XCircle,
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    label: 'Failed'
  },
  running: {
    icon: Activity,
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    label: 'Running'
  },
  cancelled: {
    icon: Clock,
    color: 'text-gray-600',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    label: 'Cancelled'
  }
};

interface ExecutionHistoryProps {
  executions: ExecutionRecord[];
  onExecutionSelect: (executionId: string) => void;
}

export const ExecutionHistory: React.FC<ExecutionHistoryProps> = ({
  executions,
  onExecutionSelect
}) => {
  const [filter, setFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedExecution, setExpandedExecution] = useState<string | null>(null);

  const filteredExecutions = executions.filter(execution => {
    const matchesFilter = filter === 'all' || execution.status === filter;
    const matchesSearch = searchTerm === '' ||
      execution.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      execution.triggerType.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const statusCounts = executions.reduce((counts, execution) => {
    counts[execution.status] = (counts[execution.status] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  const handleExecutionClick = (execution: ExecutionRecord) => {
    if (expandedExecution === execution.id) {
      setExpandedExecution(null);
    } else {
      setExpandedExecution(execution.id);
    }
  };

  const getExecutionDuration = (execution: ExecutionRecord): string => {
    if (execution.duration) {
      return `${execution.duration}s`;
    }
    if (execution.endTime && execution.startTime) {
      const duration = Math.floor((execution.endTime.getTime() - execution.startTime.getTime()) / 1000);
      return `${duration}s`;
    }
    if (execution.status === 'running') {
      const duration = Math.floor((Date.now() - execution.startTime.getTime()) / 1000);
      return `${duration}s (running)`;
    }
    return '-';
  };

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Execution History</h3>
          <p className="text-sm text-gray-600">
            View and analyze past workflow executions
          </p>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search executions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            />
          </div>

          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
          >
            <option value="all">All Status ({executions.length})</option>
            {Object.entries(statusCounts).map(([status, count]) => (
              <option key={status} value={status}>
                {statusConfig[status as keyof typeof statusConfig].label} ({count})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(statusCounts).map(([status, count]) => {
          const config = statusConfig[status as keyof typeof statusConfig];
          const StatusIcon = config.icon;
          return (
            <div key={status} className={clsx("p-4 rounded-lg border", config.bg, config.border)}>
              <div className="flex items-center gap-2">
                <StatusIcon className={clsx("h-5 w-5", config.color)} />
                <div className="text-2xl font-bold text-gray-900">{count}</div>
              </div>
              <div className="text-sm text-gray-600 mt-1">{config.label}</div>
            </div>
          );
        })}
      </div>

      {/* Execution List */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {filteredExecutions.length === 0 ? (
          <div className="p-8 text-center">
            <Clock className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Executions Found</h3>
            <p className="text-gray-500">
              {searchTerm || filter !== 'all'
                ? 'Try adjusting your search or filter criteria.'
                : 'This workflow hasn\'t been executed yet.'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredExecutions.map((execution) => {
              const config = statusConfig[execution.status];
              const StatusIcon = config.icon;
              const isExpanded = expandedExecution === execution.id;

              return (
                <div key={execution.id} className="hover:bg-gray-50 transition-colors">
                  <div
                    className="p-6 cursor-pointer"
                    onClick={() => handleExecutionClick(execution)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={clsx("p-2 rounded-full", config.bg)}>
                          <StatusIcon className={clsx("h-5 w-5", config.color)} />
                        </div>

                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">
                              Execution {execution.id.slice(-6)}
                            </span>
                            <span className={clsx("px-2 py-1 text-xs font-medium rounded-full", config.bg, config.color)}>
                              {config.label}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                            <span>
                              {format(execution.startTime, 'MMM d, yyyy HH:mm')}
                            </span>
                            <span>•</span>
                            <span>Duration: {getExecutionDuration(execution)}</span>
                            <span>•</span>
                            <span className="capitalize">{execution.triggerType} trigger</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onExecutionSelect(execution.id);
                          }}
                          className="p-2 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="View logs"
                        >
                          <Eye className="h-4 w-4" />
                        </button>

                        <button
                          className="p-1 text-gray-400 hover:text-gray-600"
                          title={isExpanded ? 'Collapse' : 'Expand'}
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="px-6 pb-6 border-t border-gray-100 bg-gray-50">
                      <div className="pt-4 space-y-4">
                        {execution.error && (
                          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                            <div className="flex items-start gap-2">
                              <XCircle className="h-4 w-4 text-red-500 mt-0.5" />
                              <div>
                                <h4 className="text-sm font-medium text-red-900">Error Details</h4>
                                <p className="text-sm text-red-700 mt-1">{execution.error}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div>
                            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Start Time</label>
                            <p className="text-sm text-gray-900 mt-1">
                              {format(execution.startTime, 'MMM d, yyyy HH:mm:ss')}
                            </p>
                          </div>

                          {execution.endTime && (
                            <div>
                              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">End Time</label>
                              <p className="text-sm text-gray-900 mt-1">
                                {format(execution.endTime, 'MMM d, yyyy HH:mm:ss')}
                              </p>
                            </div>
                          )}

                          <div>
                            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Trigger</label>
                            <p className="text-sm text-gray-900 mt-1 capitalize">
                              {execution.triggerType}
                            </p>
                          </div>
                        </div>

                        {execution.nodeExecutions && execution.nodeExecutions.length > 0 && (
                          <div>
                            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
                              Node Executions ({execution.nodeExecutions.length})
                            </label>
                            <div className="space-y-2">
                              {execution.nodeExecutions.map((node) => (
                                <div key={node.nodeId} className="flex items-center justify-between p-2 bg-white rounded border">
                                  <div className="flex items-center gap-2">
                                    <div className={clsx(
                                      "w-2 h-2 rounded-full",
                                      node.status === 'completed' ? 'bg-green-500' :
                                      node.status === 'failed' ? 'bg-red-500' :
                                      node.status === 'running' ? 'bg-orange-500' :
                                      'bg-gray-400'
                                    )} />
                                    <span className="text-sm font-medium text-gray-900">{node.nodeName}</span>
                                  </div>
                                  <span className="text-xs text-gray-500 capitalize">{node.status}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
