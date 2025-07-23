import React from 'react';
import { cn } from '@/lib/utils';

interface PanelResizerProps {
    isResizing: boolean;
    resizerProps: {
        onMouseDown: (e: React.MouseEvent) => void;
    };
    overlayProps: {
        onMouseMove: (e: React.MouseEvent) => void;
        onMouseUp: (e: React.MouseEvent) => void;
        style: React.CSSProperties;
    } | null;
    className?: string;
}

export const PanelResizer: React.FC<PanelResizerProps> = ({
    isResizing,
    resizerProps,
    overlayProps,
    className
}) => {
    return (
        <>
            <div
                className={cn(
                    'relative cursor-col-resize select-none',
                    'w-0 bg-transparent',
                    className
                )}
                {...resizerProps}
            >
                {/* 拖拽时的指示器 */}
                <div
                    className={cn(
                        'absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2',
                        'w-1 h-12 rounded-full bg-foreground transition-all duration-200',
                        isResizing ? 'opacity-80 scale-110' : 'opacity-0'
                    )}
                />

                {/* 扩展的交互区域 - 完全透明 */}
                <div className="absolute inset-y-0 -left-1 -right-4" />
            </div>

            {/* 拖拽时的全屏遮罩层 */}
            {overlayProps && (
                <div {...overlayProps} />
            )}
        </>
    );
}; 