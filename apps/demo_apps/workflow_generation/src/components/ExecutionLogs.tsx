import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  Download,
  Filter,
  Search,
  RefreshCw,
  Play,
  Pause,
  ChevronDown,
  ChevronRight,
  Info,
  AlertTriangle,
  AlertCircle,
  Bug,
  Activity
} from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { ExecutionRecord, LogEntry, NodeExecution } from '../types';

const logLevelConfig = {
  debug: {
    icon: Bug,
    color: 'text-gray-600',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    label: 'DEBUG'
  },
  info: {
    icon: Info,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    label: 'INFO'
  },
  warn: {
    icon: AlertTriangle,
    color: 'text-yellow-600',
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    label: 'WARN'
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    label: 'ERROR'
  }
};

const nodeStatusConfig = {
  pending: { color: 'text-gray-500', bg: 'bg-gray-100' },
  running: { color: 'text-orange-500', bg: 'bg-orange-100' },
  completed: { color: 'text-green-500', bg: 'bg-green-100' },
  failed: { color: 'text-red-500', bg: 'bg-red-100' },
  skipped: { color: 'text-gray-400', bg: 'bg-gray-100' }
};

interface ExecutionLogsProps {
  execution: ExecutionRecord;
}

export const ExecutionLogs: React.FC<ExecutionLogsProps> = ({ execution }) => {
  const [selectedLevel, setSelectedLevel] = useState<string>('all');
  const [selectedNode, setSelectedNode] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  const logsContainerRef = useRef<HTMLDivElement>(null);
  const isRunning = execution.status === 'running';

  // Collect all logs from node executions
  const allLogs: (LogEntry & { nodeId?: string; nodeName?: string })[] = [];

  execution.nodeExecutions?.forEach((node) => {
    node.logs.forEach((log) => {
      allLogs.push({
        ...log,
        nodeId: node.nodeId,
        nodeName: node.nodeName
      });
    });
  });

  // Sort logs by timestamp
  allLogs.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

  // Filter logs
  const filteredLogs = allLogs.filter((log) => {
    const matchesLevel = selectedLevel === 'all' || log.level === selectedLevel;
    const matchesNode = selectedNode === 'all' || log.nodeId === selectedNode;
    const matchesSearch = searchTerm === '' ||
      log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.nodeName && log.nodeName.toLowerCase().includes(searchTerm.toLowerCase()));

    return matchesLevel && matchesNode && matchesSearch;
  });

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const handleNodeToggle = (nodeId: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const handleExportLogs = () => {
    const logsText = filteredLogs.map(log =>
      `[${format(log.timestamp, 'yyyy-MM-dd HH:mm:ss.SSS')}] ${log.level.toUpperCase()} ${log.nodeName || 'SYSTEM'}: ${log.message}`
    ).join('\n');

    const blob = new Blob([logsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execution-${execution.id}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const logCounts = allLogs.reduce((counts, log) => {
    counts[log.level] = (counts[log.level] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  const nodeOptions = execution.nodeExecutions?.map(node => ({
    id: node.nodeId,
    name: node.nodeName,
    status: node.status
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Terminal className="h-5 w-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Execution Logs</h3>
            {isRunning && (
              <div className="flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full">
                <Activity className="h-3 w-3 animate-pulse" />
                Live
              </div>
            )}
          </div>
          <p className="text-sm text-gray-600">
            Execution {execution.id} • Started {format(execution.startTime, 'MMM d, yyyy HH:mm:ss')}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm w-48"
            />
          </div>

          {/* Level Filter */}
          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
          >
            <option value="all">All Levels ({allLogs.length})</option>
            {Object.entries(logCounts).map(([level, count]) => (
              <option key={level} value={level}>
                {level.toUpperCase()} ({count})
              </option>
            ))}
          </select>

          {/* Node Filter */}
          <select
            value={selectedNode}
            onChange={(e) => setSelectedNode(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
          >
            <option value="all">All Nodes</option>
            {nodeOptions.map((node) => (
              <option key={node.id} value={node.id}>
                {node.name}
              </option>
            ))}
          </select>

          {/* Auto-scroll Toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={clsx(
              "px-3 py-2 border rounded-lg text-sm font-medium transition-colors",
              autoScroll
                ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
            )}
          >
            {autoScroll ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>

          {/* Export Logs */}
          <button
            onClick={handleExportLogs}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Node Execution Overview */}
      {execution.nodeExecutions && execution.nodeExecutions.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">Node Execution Status</h4>
          <div className="space-y-2">
            {execution.nodeExecutions.map((node) => {
              const config = nodeStatusConfig[node.status];
              const isExpanded = expandedNodes.has(node.nodeId);

              return (
                <div key={node.nodeId} className="border border-gray-200 rounded-lg">
                  <div
                    className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
                    onClick={() => handleNodeToggle(node.nodeId)}
                  >
                    <div className="flex items-center gap-3">
                      <button className="p-1 hover:bg-gray-100 rounded">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-gray-500" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-500" />
                        )}
                      </button>

                      <div className={clsx("px-2 py-1 rounded-full text-xs font-medium", config.bg, config.color)}>
                        <div className={clsx("w-2 h-2 rounded-full inline-block mr-1",
                          node.status === 'running' ? 'animate-pulse' : ''
                        )} style={{ backgroundColor: 'currentColor' }} />
                        {node.status.toUpperCase()}
                      </div>

                      <span className="font-medium text-gray-900">{node.nodeName}</span>

                      <span className="text-sm text-gray-500">
                        {node.logs.length} logs
                      </span>
                    </div>

                    <div className="text-sm text-gray-500">
                      {format(node.startTime, 'HH:mm:ss')}
                      {node.endTime && ` - ${format(node.endTime, 'HH:mm:ss')}`}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-3 pb-3 space-y-2">
                      {node.input && (
                        <div>
                          <label className="text-xs font-medium text-gray-500">Input:</label>
                          <pre className="text-xs bg-gray-50 p-2 rounded border mt-1 overflow-x-auto">
                            {JSON.stringify(node.input, null, 2)}
                          </pre>
                        </div>
                      )}

                      {node.output && (
                        <div>
                          <label className="text-xs font-medium text-gray-500">Output:</label>
                          <pre className="text-xs bg-gray-50 p-2 rounded border mt-1 overflow-x-auto">
                            {JSON.stringify(node.output, null, 2)}
                          </pre>
                        </div>
                      )}

                      {node.error && (
                        <div>
                          <label className="text-xs font-medium text-red-500">Error:</label>
                          <div className="text-xs bg-red-50 text-red-700 p-2 rounded border border-red-200 mt-1">
                            {node.error}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Logs Display */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="p-4 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-gray-900">
              Log Stream ({filteredLogs.length} entries)
            </h4>
            {isRunning && (
              <div className="flex items-center gap-1 text-sm text-orange-600">
                <RefreshCw className="h-4 w-4 animate-spin" />
                Updating...
              </div>
            )}
          </div>
        </div>

        <div
          ref={logsContainerRef}
          className="h-96 overflow-y-auto bg-gray-900 text-gray-100 font-mono text-sm"
        >
          {filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <Terminal className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No logs found matching your criteria</p>
              </div>
            </div>
          ) : (
            <div className="p-4 space-y-1">
              {filteredLogs.map((log, index) => {
                const config = logLevelConfig[log.level];
                const LogIcon = config.icon;

                return (
                  <div key={index} className="flex items-start gap-3 py-1 hover:bg-gray-800 px-2 -mx-2 rounded">
                    <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">
                      {format(log.timestamp, 'HH:mm:ss.SSS')}
                    </span>

                    <div className={clsx(
                      "w-1 h-1 rounded-full mt-2 flex-shrink-0",
                      log.level === 'error' ? 'bg-red-400' :
                      log.level === 'warn' ? 'bg-yellow-400' :
                      log.level === 'info' ? 'bg-blue-400' :
                      'bg-gray-400'
                    )} />

                    <span className={clsx(
                      "text-xs font-medium w-12 flex-shrink-0",
                      log.level === 'error' ? 'text-red-400' :
                      log.level === 'warn' ? 'text-yellow-400' :
                      log.level === 'info' ? 'text-blue-400' :
                      'text-gray-400'
                    )}>
                      {log.level.toUpperCase()}
                    </span>

                    {log.nodeName && (
                      <span className="text-xs text-purple-400 font-medium w-24 flex-shrink-0 truncate">
                        [{log.nodeName}]
                      </span>
                    )}

                    <span className="text-gray-100 flex-1 min-w-0 break-words">
                      {log.message}
                    </span>

                    {log.data && (
                      <button
                        className="text-xs text-gray-400 hover:text-gray-200 flex-shrink-0"
                        onClick={() => {
                          console.log('Log data:', log.data);
                        }}
                        title="View data (check console)"
                      >
                        •••
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
