"use client";

import React from 'react';
import { Panel, useReactFlow } from 'reactflow';
import { 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Grid3X3, 
  Map,
  Lock
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useEditorUI } from '@/store/hooks';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

interface CanvasControlsProps {
  readOnly?: boolean;
}

export const CanvasControls: React.FC<CanvasControlsProps> = ({ readOnly = false }) => {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const { showGrid, showMinimap, setShowGrid, setShowMinimap } = useEditorUI();

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
            icon={Maximize2}
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