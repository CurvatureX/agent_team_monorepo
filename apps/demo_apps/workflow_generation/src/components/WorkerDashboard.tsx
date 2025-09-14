import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bot,
  Clock,
  PlayCircle,
  PauseCircle,
  AlertTriangle,
  CheckCircle,
  Activity,
  Calendar,
  Zap
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import { AIWorker } from '../types';
import { mockAIWorkers } from '../data/mockData';

const statusConfig = {
  active: {
    icon: PlayCircle,
    color: 'text-green-500',
    bg: 'bg-green-50',
    border: 'border-green-200',
    label: 'Active',
    pulse: true
  },
  idle: {
    icon: Clock,
    color: 'text-blue-500',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    label: 'Idle',
    pulse: false
  },
  running: {
    icon: Activity,
    color: 'text-orange-500',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    label: 'Running',
    pulse: true
  },
  error: {
    icon: AlertTriangle,
    color: 'text-red-500',
    bg: 'bg-red-50',
    border: 'border-red-200',
    label: 'Error',
    pulse: false
  },
  paused: {
    icon: PauseCircle,
    color: 'text-gray-500',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    label: 'Paused',
    pulse: false
  }
};

const triggerTypeIcons = {
  schedule: Calendar,
  webhook: Zap,
  manual: PlayCircle,
  event: Activity
};

interface WorkerCardProps {
  worker: AIWorker;
  onClick: () => void;
}

const WorkerCard: React.FC<WorkerCardProps> = ({ worker, onClick }) => {
  const config = statusConfig[worker.status];
  const StatusIcon = config.icon;
  const TriggerIcon = triggerTypeIcons[worker.trigger.type] || Activity;

  return (
    <div
      onClick={onClick}
      className={clsx(
        "relative p-6 bg-white rounded-lg shadow-sm border cursor-pointer transition-all duration-200 hover:shadow-md hover:scale-[1.02] group",
        config.border
      )}
    >
      {/* Status Indicator */}
      <div className={clsx("absolute top-4 right-4 p-2 rounded-full", config.bg)}>
        <StatusIcon
          className={clsx("h-4 w-4", config.color, config.pulse && "animate-pulse")}
        />
      </div>

      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 bg-indigo-50 rounded-lg">
          <Bot className="h-6 w-6 text-indigo-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">
            {worker.name}
          </h3>
          <span className={clsx("inline-flex items-center gap-1 text-sm font-medium", config.color)}>
            <StatusIcon className="h-3 w-3" />
            {config.label}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="text-gray-600 text-sm mb-4 line-clamp-2 leading-relaxed">
        {worker.description}
      </p>

      {/* Trigger Info */}
      <div className="flex items-center gap-2 mb-4 p-2 bg-gray-50 rounded-md">
        <TriggerIcon className="h-4 w-4 text-gray-500" />
        <span className="text-sm text-gray-600 capitalize">{worker.trigger.type}</span>
        <span className="text-xs text-gray-500">•</span>
        <span className="text-xs text-gray-500 truncate">{worker.trigger.description}</span>
      </div>

      {/* Stats */}
      <div className="space-y-2">
        {worker.lastRunTime && (
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-500">Last run:</span>
            <span className="text-gray-700 font-medium">
              {formatDistanceToNow(worker.lastRunTime, { addSuffix: true })}
            </span>
          </div>
        )}

        {worker.nextRunTime && worker.status !== 'paused' && worker.status !== 'error' && (
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-500">Next run:</span>
            <span className="text-gray-700 font-medium">
              {formatDistanceToNow(worker.nextRunTime, { addSuffix: true })}
            </span>
          </div>
        )}

        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-500">Executions:</span>
          <span className="text-gray-700 font-medium">{worker.executionHistory.length}</span>
        </div>
      </div>

      {/* Running Indicator */}
      {worker.status === 'running' && (
        <div className="absolute inset-0 rounded-lg ring-2 ring-orange-300 ring-opacity-50 animate-pulse" />
      )}
    </div>
  );
};

export const WorkerDashboard: React.FC = () => {
  const [workers, setWorkers] = useState<AIWorker[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Simulate loading
    setTimeout(() => {
      setWorkers(mockAIWorkers);
      setLoading(false);
    }, 500);
  }, []);

  // Real-time updates simulation
  useEffect(() => {
    const interval = setInterval(() => {
      setWorkers(current =>
        current.map(worker => {
          // Simulate status changes
          if (worker.status === 'running' && Math.random() < 0.1) {
            return {
              ...worker,
              status: 'idle' as const,
              lastRunTime: new Date(),
              nextRunTime: new Date(Date.now() + Math.random() * 60 * 60 * 1000)
            };
          }
          return worker;
        })
      );
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const statusCounts = workers.reduce((counts, worker) => {
    counts[worker.status] = (counts[worker.status] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  const handleWorkerClick = (workerId: string) => {
    navigate(`/workflow/${workerId}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Bot className="h-12 w-12 text-indigo-600 animate-bounce mx-auto mb-4" />
          <p className="text-gray-600">Loading AI Workers...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Workers Dashboard</h1>
              <p className="text-gray-600">Monitor and manage your automated workflows</p>
            </div>

            {/* Status Overview */}
            <div className="flex gap-4">
              {Object.entries(statusCounts).map(([status, count]) => {
                const config = statusConfig[status as keyof typeof statusConfig];
                const StatusIcon = config.icon;
                return (
                  <div key={status} className="text-center">
                    <div className={clsx("inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium", config.bg, config.color)}>
                      <StatusIcon className="h-4 w-4" />
                      {count}
                    </div>
                    <div className="text-xs text-gray-500 mt-1 capitalize">{config.label}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Workers Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {workers.map((worker) => (
            <WorkerCard
              key={worker.id}
              worker={worker}
              onClick={() => handleWorkerClick(worker.id)}
            />
          ))}
        </div>

        {/* Empty State */}
        {workers.length === 0 && (
          <div className="text-center py-12">
            <Bot className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No AI Workers Found</h3>
            <p className="text-gray-500">Create your first AI worker to get started with automation.</p>
          </div>
        )}
      </div>
    </div>
  );
};
