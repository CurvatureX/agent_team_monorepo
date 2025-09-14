import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Bot,
  Play,
  Pause,
  Square,
  RefreshCw,
  Clock,
  Calendar,
  Activity,
  CheckCircle,
  AlertTriangle,
  FileText,
  Settings,
  Zap
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import { AIWorker, ExecutionRecord } from '../types';
import { mockAIWorkers, mockExecutionDetails, mockCurrentExecution } from '../data/mockData';
import { WorkflowGraph } from './WorkflowGraph';
import { ExecutionHistory } from './ExecutionHistory';
import { ExecutionLogs } from './ExecutionLogs';

const statusConfig = {
  active: { color: 'text-green-500', bg: 'bg-green-50', label: 'Active', icon: Play },
  idle: { color: 'text-blue-500', bg: 'bg-blue-50', label: 'Idle', icon: Clock },
  running: { color: 'text-orange-500', bg: 'bg-orange-50', label: 'Running', icon: Activity },
  error: { color: 'text-red-500', bg: 'bg-red-50', label: 'Error', icon: AlertTriangle },
  paused: { color: 'text-gray-500', bg: 'bg-gray-50', label: 'Paused', icon: Pause }
};

const triggerTypeLabels = {
  schedule: 'Scheduled',
  webhook: 'Webhook',
  manual: 'Manual',
  event: 'Event-driven'
};

type TabType = 'overview' | 'graph' | 'history' | 'logs';

export const WorkflowDetailView: React.FC = () => {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();
  const [selectedWorkflow, setSelectedWorkflow] = useState<AIWorker | null>(null);
  const [workers, setWorkers] = useState<AIWorker[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
  const [currentExecution, setCurrentExecution] = useState<ExecutionRecord | null>(null);

  useEffect(() => {
    setWorkers(mockAIWorkers);
    const workflow = mockAIWorkers.find(w => w.id === workflowId);
    setSelectedWorkflow(workflow || mockAIWorkers[0]);

    // Set up current execution if workflow is running
    if (workflow?.status === 'running') {
      setCurrentExecution(mockCurrentExecution);
    }
  }, [workflowId]);

  // Real-time updates for running executions
  useEffect(() => {
    if (!selectedWorkflow || selectedWorkflow.status !== 'running') return;

    const interval = setInterval(() => {
      // Simulate log updates for current execution
      setCurrentExecution(current => {
        if (!current) return current;

        const newLog = {
          timestamp: new Date(),
          level: 'debug' as const,
          message: `Processing step ${Math.floor(Math.random() * 10) + 1}...`,
          nodeId: current.nodeExecutions?.[1]?.nodeId || 'ai-3'
        };

        return {
          ...current,
          nodeExecutions: current.nodeExecutions?.map(node =>
            node.status === 'running' ? {
              ...node,
              logs: [...node.logs, newLog]
            } : node
          ) || []
        };
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [selectedWorkflow]);

  const handleWorkflowSelect = (workflowId: string) => {
    navigate(`/workflow/${workflowId}`);
  };

  const handleExecutionSelect = (executionId: string) => {
    setSelectedExecutionId(executionId);
    setActiveTab('logs');
  };

  if (!selectedWorkflow) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">Workflow not found</p>
        </div>
      </div>
    );
  }

  const config = statusConfig[selectedWorkflow.status];
  const StatusIcon = config.icon;

  const lastExecution = selectedWorkflow.executionHistory[0];
  const executionData = selectedExecutionId
    ? mockExecutionDetails[selectedExecutionId] || selectedWorkflow.executionHistory.find(e => e.id === selectedExecutionId)
    : currentExecution || lastExecution;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation Bar - Scrollable Workflow List */}
      <div className="bg-white shadow-sm border-b">
        <div className="px-6 py-4">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="h-5 w-5 text-gray-600" />
            </button>
            <h1 className="text-xl font-semibold text-gray-900">Workflow Details</h1>
          </div>

          {/* Horizontal Scrollable Workflow Navigation */}
          <div className="overflow-x-auto pb-2">
            <div className="flex gap-3" style={{ minWidth: 'max-content' }}>
              {workers.map((worker) => {
                const isSelected = worker.id === selectedWorkflow.id;
                const workerConfig = statusConfig[worker.status];
                const WorkerStatusIcon = workerConfig.icon;

                return (
                  <button
                    key={worker.id}
                    onClick={() => handleWorkflowSelect(worker.id)}
                    className={clsx(
                      "flex items-center gap-3 px-4 py-3 rounded-lg border-2 transition-all min-w-0 flex-shrink-0",
                      isSelected
                        ? "border-indigo-200 bg-indigo-50 shadow-sm"
                        : "border-gray-200 bg-white hover:bg-gray-50"
                    )}
                  >
                    <div className={clsx("p-1.5 rounded", workerConfig.bg)}>
                      <Bot className={clsx("h-4 w-4", workerConfig.color)} />
                    </div>
                    <div className="text-left min-w-0">
                      <div className="font-medium text-gray-900 truncate max-w-32">
                        {worker.name}
                      </div>
                      <div className="flex items-center gap-1">
                        <WorkerStatusIcon className={clsx("h-3 w-3", workerConfig.color)} />
                        <span className={clsx("text-xs", workerConfig.color)}>{workerConfig.label}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Workflow Header */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-start gap-4">
              <div className={clsx("p-3 rounded-lg", config.bg)}>
                <Bot className={clsx("h-8 w-8", config.color)} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-1">{selectedWorkflow.name}</h2>
                <p className="text-gray-600 mb-3">{selectedWorkflow.description}</p>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <StatusIcon className={clsx("h-4 w-4", config.color)} />
                    <span className={clsx("font-medium", config.color)}>{config.label}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Zap className="h-4 w-4 text-gray-400" />
                    <span className="text-gray-600">{triggerTypeLabels[selectedWorkflow.trigger.type]}</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <button className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
                <Settings className="h-5 w-5" />
              </button>
              <button className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
                <RefreshCw className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Key Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">
                {selectedWorkflow.executionHistory.length}
              </div>
              <div className="text-sm text-gray-500">Total Runs</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">
                {selectedWorkflow.lastRunTime
                  ? formatDistanceToNow(selectedWorkflow.lastRunTime, { addSuffix: true })
                  : 'Never'
                }
              </div>
              <div className="text-sm text-gray-500">Last Run</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">
                {lastExecution?.duration ? `${lastExecution.duration}s` : '-'}
              </div>
              <div className="text-sm text-gray-500">Avg Duration</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">
                {selectedWorkflow.trigger.description}
              </div>
              <div className="text-sm text-gray-500">Trigger</div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow-sm border mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex gap-6 px-6">
              {[
                { key: 'overview', label: 'Overview', icon: FileText },
                { key: 'graph', label: 'Workflow Graph', icon: Activity },
                { key: 'history', label: 'Execution History', icon: Clock },
                { key: 'logs', label: 'Logs', icon: CheckCircle }
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key as TabType)}
                  className={clsx(
                    "flex items-center gap-2 py-4 px-2 border-b-2 font-medium text-sm transition-colors",
                    activeTab === key
                      ? "border-indigo-500 text-indigo-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Current Execution Status */}
                {selectedWorkflow.status === 'running' && currentExecution && (
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="h-5 w-5 text-orange-500 animate-pulse" />
                      <h3 className="font-semibold text-orange-900">Currently Running</h3>
                    </div>
                    <p className="text-orange-700 text-sm mb-3">
                      Started {formatDistanceToNow(currentExecution.startTime, { addSuffix: true })}
                    </p>
                    <div className="space-y-2">
                      {currentExecution.nodeExecutions?.map((node, index) => (
                        <div key={node.nodeId} className="flex items-center gap-2 text-sm">
                          <div className={clsx(
                            "w-2 h-2 rounded-full",
                            node.status === 'completed' ? 'bg-green-500' :
                            node.status === 'running' ? 'bg-orange-500 animate-pulse' :
                            'bg-gray-300'
                          )} />
                          <span className="text-gray-700">{node.nodeName}</span>
                          <span className={clsx(
                            "text-xs capitalize",
                            node.status === 'completed' ? 'text-green-600' :
                            node.status === 'running' ? 'text-orange-600' :
                            'text-gray-500'
                          )}>
                            {node.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Trigger Configuration */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Trigger Configuration</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-gray-500">Type</label>
                        <p className="text-gray-900 capitalize">{selectedWorkflow.trigger.type}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Description</label>
                        <p className="text-gray-900">{selectedWorkflow.trigger.description}</p>
                      </div>
                    </div>
                    {selectedWorkflow.trigger.config && (
                      <div className="mt-4">
                        <label className="text-sm font-medium text-gray-500">Configuration</label>
                        <pre className="text-sm text-gray-600 mt-1 bg-white p-2 rounded border">
                          {JSON.stringify(selectedWorkflow.trigger.config, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>

                {/* Recent Executions Summary */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Recent Activity</h3>
                  <div className="space-y-3">
                    {selectedWorkflow.executionHistory.slice(0, 5).map((execution) => (
                      <div key={execution.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className={clsx(
                            "w-2 h-2 rounded-full",
                            execution.status === 'completed' ? 'bg-green-500' :
                            execution.status === 'failed' ? 'bg-red-500' :
                            execution.status === 'running' ? 'bg-orange-500' :
                            'bg-gray-400'
                          )} />
                          <div>
                            <span className="text-sm font-medium text-gray-900 capitalize">
                              {execution.status}
                            </span>
                            <div className="text-xs text-gray-500">
                              {format(execution.startTime, 'MMM d, HH:mm')}
                              {execution.duration && ` • ${execution.duration}s`}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => handleExecutionSelect(execution.id)}
                          className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                        >
                          View Logs
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'graph' && (
              <WorkflowGraph workflow={selectedWorkflow} />
            )}

            {activeTab === 'history' && (
              <ExecutionHistory
                executions={selectedWorkflow.executionHistory}
                onExecutionSelect={handleExecutionSelect}
              />
            )}

            {activeTab === 'logs' && executionData && (
              <ExecutionLogs execution={executionData} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
