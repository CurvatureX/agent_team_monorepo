"use client";

import React, { useEffect, DragEvent, useRef } from 'react';
import { X, Menu, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useNodeTemplates, useEditorUI } from '@/store/hooks';
import type { NodeTemplate } from '@/types/node-template';
import { SearchBar } from './SearchBar';
import { NodeCategory } from './NodeCategory';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

interface NodeSidebarProps {
  onNodeSelect: (template: NodeTemplate) => void;
  className?: string;
}

export const NodeSidebar: React.FC<NodeSidebarProps> = ({
  onNodeSelect,
  className,
}) => {
  const {
    filteredTemplates,
    templatesByCategory,
    categories,
    loading,
    error,
    loadTemplates,
  } = useNodeTemplates();

  const {
    sidebarCollapsed,
    searchQuery,
    selectedCategory,
    setSidebarCollapsed,
    setSearchQuery,
    setSelectedCategory,
    setIsDraggingNode,
  } = useEditorUI();

  const sidebarRef = useRef<HTMLDivElement>(null);

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const handleNodeDragStart = (e: DragEvent<HTMLDivElement>, template: NodeTemplate) => {
    // Set the drag data
    e.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: 'nodeTemplate',
      template,
    }));
    e.dataTransfer.effectAllowed = 'copy';
    setIsDraggingNode(true);
  };

  const handleNodeDragEnd = () => {
    setIsDraggingNode(false);
  };

  // Handle global drag end
  useEffect(() => {
    const handleDragEnd = () => {
      setIsDraggingNode(false);
    };
    
    document.addEventListener('dragend', handleDragEnd);
    return () => document.removeEventListener('dragend', handleDragEnd);
  }, [setIsDraggingNode]);

  if (loading) {
    return (
      <div className={cn('w-64 h-full bg-card border-r border-border p-4', className)}>
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('w-64 h-full bg-card border-r border-border p-4', className)}>
        <div className="text-sm text-destructive">Error loading templates: {error}</div>
      </div>
    );
  }

  const displayTemplates = selectedCategory
    ? templatesByCategory[selectedCategory] || []
    : filteredTemplates;

  const categoriesToShow = selectedCategory
    ? [selectedCategory]
    : searchQuery
    ? categories.filter(cat => 
        templatesByCategory[cat]?.some(t => 
          displayTemplates.includes(t)
        )
      )
    : categories;

  return (
    <>
      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {!sidebarCollapsed && (
          <motion.div
            ref={sidebarRef}
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 250, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className={cn(
              'h-full bg-card border-r border-border overflow-hidden',
              'flex flex-col',
              className
            )}
          >
            {/* Header */}
            <div className="p-4 border-b border-border">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <h3 className="font-semibold text-sm">Node Library</h3>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSidebarCollapsed(true)}
                  className="h-6 w-6 p-0"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
              
              {/* Search */}
              <SearchBar
                value={searchQuery}
                onChange={setSearchQuery}
                placeholder="Search nodes..."
              />
              
              {/* Category filter */}
              {!searchQuery && (
                <div className="mt-3 flex flex-wrap gap-1">
                  <Button
                    variant={!selectedCategory ? "default" : "secondary"}
                    size="sm"
                    onClick={() => setSelectedCategory(null)}
                    className="h-7 px-2 text-xs"
                  >
                    All
                  </Button>
                  {categories.map((cat) => (
                    <Button
                      key={cat}
                      variant={cat === selectedCategory ? "default" : "secondary"}
                      size="sm"
                      onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
                      className="h-7 px-2 text-xs"
                    >
                      {cat}
                    </Button>
                  ))}
                </div>
              )}
            </div>

            {/* Categories and nodes */}
            <ScrollArea className="flex-1 p-4" onDragEnd={handleNodeDragEnd}>
              {searchQuery && displayTemplates.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-8">
                  No nodes found for &quot;{searchQuery}&quot;
                </div>
              ) : (
                <div className="space-y-2">
                  {categoriesToShow.map((category) => {
                    const categoryTemplates = selectedCategory
                      ? displayTemplates
                      : templatesByCategory[category]?.filter(t => 
                          displayTemplates.includes(t)
                        ) || [];
                    
                    if (categoryTemplates.length === 0) return null;
                    
                    return (
                      <NodeCategory
                        key={category}
                        category={category}
                        templates={categoryTemplates}
                        count={categoryTemplates.length}
                        defaultExpanded={!!searchQuery || !!selectedCategory}
                        onNodeSelect={onNodeSelect}
                        onNodeDragStart={handleNodeDragStart}
                      />
                    );
                  })}
                </div>
              )}
            </ScrollArea>

            {/* Footer */}
            <Separator />
            <div className="p-4">
              <p className="text-xs text-muted-foreground text-center">
                Drag nodes to canvas or click to add
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapsed state - floating button */}
      {sidebarCollapsed && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          className="absolute left-4 top-4 z-10"
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSidebarCollapsed(false)}
            className="shadow-lg"
          >
            <Menu className="w-4 h-4" />
          </Button>
        </motion.div>
      )}
    </>
  );
};