import { useState, useRef, useCallback } from 'react';

interface UseResizablePanelOptions {
  initialWidth: number;
  minWidth: number;
  maxWidthRatio: number;
}

interface UseResizablePanelReturn {
  width: number;
  isResizing: boolean;
  resizerProps: {
    onMouseDown: (e: React.MouseEvent) => void;
  };
  overlayProps: {
    onMouseMove: (e: React.MouseEvent) => void;
    onMouseUp: (e: React.MouseEvent) => void;
    style: React.CSSProperties;
  } | null;
}

export const useResizablePanel = ({
  initialWidth,
  minWidth,
  maxWidthRatio
}: UseResizablePanelOptions): UseResizablePanelReturn => {
  const [width, setWidth] = useState(initialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const startXRef = useRef<number>(0);
  const startWidthRef = useRef<number>(initialWidth);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = width;
    e.preventDefault();
  }, [width]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isResizing) return;
    
    const deltaX = startXRef.current - e.clientX;
    const newWidth = startWidthRef.current + deltaX;
    const maxWidth = window.innerWidth * maxWidthRatio;
    
    const clampedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
    setWidth(clampedWidth);
  }, [isResizing, minWidth, maxWidthRatio]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  return {
    width,
    isResizing,
    resizerProps: {
      onMouseDown: handleMouseDown,
    },
    overlayProps: isResizing ? {
      onMouseMove: handleMouseMove,
      onMouseUp: handleMouseUp,
      style: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        cursor: 'col-resize',
        userSelect: 'none',
        zIndex: 9999,
        backgroundColor: 'transparent',
      },
    } : null,
  };
}; 