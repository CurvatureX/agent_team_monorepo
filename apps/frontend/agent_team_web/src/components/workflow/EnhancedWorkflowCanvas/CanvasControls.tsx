"use client";

import React from 'react';
import { Panel, useReactFlow } from 'reactflow';
import {
  ZoomIn,
  ZoomOut,
  Fullscreen,
  Grid3X3,
  Map,
  Lock,
  Save,
  Play,
  Square,
  RefreshCw,
  Maximize2,
  Library,
  Rocket
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useEditorUI } from '@/store/hooks';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

interface CanvasControlsProps {
  readOnly?: boolean;
  onSave?: () => void;
  isSaving?: boolean;
  onDeploy?: () => void;
  isDeploying?: boolean;
  onExecute?: () => void;
  onStopExecution?: () => void;
  isExecuting?: boolean;
  executionStatus?: 'idle' | 'running' | 'completed' | 'failed';
  onToggleFullscreen?: () => void;
}

export const CanvasControls: React.FC<CanvasControlsProps> = ({
  readOnly = false,
  onSave,
  isSaving = false,
  onDeploy,
  isDeploying = false,
  onExecute,
  onStopExecution,
  isExecuting = false,
  executionStatus = 'idle',
  onToggleFullscreen
}) => {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const { showGrid, showMinimap, setShowGrid, setShowMinimap, sidebarCollapsed, setSidebarCollapsed } = useEditorUI();

  const ControlButton: React.FC<{
    onClick: () => void;
    icon: React.ElementType;
    title: string;
    active?: boolean;
  }> = ({ onClick, icon: Icon, title, active }) => (
    <motion.div
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      <Button
        variant={active ? "default" : "ghost"}
        size="sm"
        onClick={onClick}
        title={title}
        className="h-8 w-8 p-0"
      >
        <Icon className="w-4 h-4" />
      </Button>
    </motion.div>
  );

  return (
    <Panel position="top-right" className="m-4">
      <div className="bg-background/80 backdrop-blur-sm border border-border rounded-lg p-1 shadow-lg">
        <div className="flex items-center gap-1">
          {/* Zoom controls */}
          <ControlButton
            onClick={() => zoomIn()}
            icon={ZoomIn}
            title="Zoom In"
          />
          <ControlButton
            onClick={() => zoomOut()}
            icon={ZoomOut}
            title="Zoom Out"
          />
          <ControlButton
            onClick={() => fitView({ padding: 0.2, duration: 200 })}
            icon={Fullscreen}
            title="Fit View"
          />

          <Separator orientation="vertical" className="h-6 mx-1" />

          {/* View controls */}
          <ControlButton
            onClick={() => setShowGrid(!showGrid)}
            icon={Grid3X3}
            title={showGrid ? "Hide Grid" : "Show Grid"}
            active={showGrid}
          />
          <ControlButton
            onClick={() => setShowMinimap(!showMinimap)}
            icon={Map}
            title={showMinimap ? "Hide Minimap" : "Show Minimap"}
            active={showMinimap}
          />

          {/* Node Template Sidebar toggle */}
          <ControlButton
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            icon={Library}
            title={sidebarCollapsed ? "Show Node Library" : "Hide Node Library"}
            active={!sidebarCollapsed}
          />

          {/* Fullscreen button */}
          {onToggleFullscreen && (
            <>
              <Separator orientation="vertical" className="h-6 mx-1" />
              <ControlButton
                onClick={onToggleFullscreen}
                icon={Maximize2}
                title="Toggle Fullscreen"
              />
            </>
          )}

          {/* Save button */}
          {!readOnly && onSave && (
            <>
              <Separator orientation="vertical" className="h-6 mx-1" />
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Button
                  variant="default"
                  size="sm"
                  onClick={onSave}
                  disabled={isSaving}
                  title="Save Workflow"
                  className="h-8 px-3"
                >
                  <Save className="w-4 h-4 mr-1" />
                  {isSaving ? 'Saving...' : 'Save'}
                </Button>
              </motion.div>
              {onDeploy && (
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Button
                    variant="default"
                    size="sm"
                    onClick={onDeploy}
                    disabled={isDeploying}
                    title="Deploy Workflow"
                    className="h-8 px-3 bg-yellow-500 hover:bg-yellow-600 text-black ml-1"
                  >
                    <Rocket className="w-4 h-4 mr-1" />
                    {isDeploying ? 'Deploying...' : 'Deploy'}
                  </Button>
                </motion.div>
              )}
            </>
          )}

          {/* Execution controls */}
          {!readOnly && onExecute && (
            <>
              <Separator orientation="vertical" className="h-6 mx-1" />
              {isExecuting ? (
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={onStopExecution}
                    title="Stop Execution"
                    className="h-8 px-3"
                  >
                    <Square className="w-4 h-4 mr-1" />
                    Stop
                  </Button>
                </motion.div>
              ) : (
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Button
                    variant={executionStatus === 'failed' ? 'destructive' : 'default'}
                    size="sm"
                    onClick={onExecute}
                    title="Execute Workflow"
                    className="h-8 px-3"
                  >
                    {executionStatus === 'completed' ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-1" />
                        Re-run
                      </>
                    ) : executionStatus === 'failed' ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-1" />
                        Retry
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-1" />
                        Run
                      </>
                    )}
                  </Button>
                </motion.div>
              )}
              {isExecuting && (
                <div className="px-2 py-1 text-xs text-muted-foreground flex items-center gap-1">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Running...
                </div>
              )}
            </>
          )}

          {readOnly && (
            <>
              <Separator orientation="vertical" className="h-6 mx-1" />
              <div className="px-2 py-1 text-xs text-muted-foreground flex items-center gap-1">
                <Lock className="w-3 h-3" />
                Read Only
              </div>
            </>
          )}
        </div>
      </div>
    </Panel>
  );
};
