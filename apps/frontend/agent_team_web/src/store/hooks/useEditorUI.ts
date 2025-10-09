import { useAtom, useAtomValue, useSetAtom } from 'jotai';
import { useCallback } from 'react';
import {
  selectedNodeIdAtom,
  sidebarCollapsedAtom,
  detailsPanelOpenAtom,
  searchQueryAtom,
  selectedCategoryAtom,
  canvasZoomAtom,
  canvasPositionAtom,
  isDraggingNodeAtom,
  showGridAtom,
  showMinimapAtom,
  editorModeAtom,
  isAnyPanelOpenAtom,
  toggleSidebarAtom,
  toggleDetailsPanelAtom,
  resetUIStateAtom,
} from '../atoms/ui';
import type { XYPosition } from 'reactflow';

export const useEditorUI = () => {
  const [selectedNodeId, setSelectedNodeId] = useAtom(selectedNodeIdAtom);
  const [sidebarCollapsed, setSidebarCollapsed] = useAtom(sidebarCollapsedAtom);
  const [detailsPanelOpen, setDetailsPanelOpen] = useAtom(detailsPanelOpenAtom);
  const [searchQuery, setSearchQuery] = useAtom(searchQueryAtom);
  const [selectedCategory, setSelectedCategory] = useAtom(selectedCategoryAtom);
  const [canvasZoom, setCanvasZoom] = useAtom(canvasZoomAtom);
  const [canvasPosition, setCanvasPosition] = useAtom(canvasPositionAtom);
  const [isDraggingNode, setIsDraggingNode] = useAtom(isDraggingNodeAtom);
  const [showGrid, setShowGrid] = useAtom(showGridAtom);
  const [showMinimap, setShowMinimap] = useAtom(showMinimapAtom);
  const [editorMode, setEditorMode] = useAtom(editorModeAtom);

  const isAnyPanelOpen = useAtomValue(isAnyPanelOpenAtom);
  const toggleSidebar = useSetAtom(toggleSidebarAtom);
  const toggleDetailsPanel = useSetAtom(toggleDetailsPanelAtom);
  const resetUI = useSetAtom(resetUIStateAtom);

  // Select node and open details panel
  const selectNode = useCallback(
    (nodeId: string | null) => {
      setSelectedNodeId(nodeId);
      if (nodeId) {
        setDetailsPanelOpen(true);
        setSidebarCollapsed(true); // Hide Node Library when showing Node Details
      }
    },
    [setSelectedNodeId, setDetailsPanelOpen, setSidebarCollapsed]
  );

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedNodeId(null);
    setDetailsPanelOpen(false);
    setSidebarCollapsed(false); // Show Node Library when hiding Node Details
  }, [setSelectedNodeId, setDetailsPanelOpen, setSidebarCollapsed]);

  // Set canvas view
  const setCanvasView = useCallback(
    (zoom: number, position: XYPosition) => {
      setCanvasZoom(zoom);
      setCanvasPosition(position);
    },
    [setCanvasZoom, setCanvasPosition]
  );

  // Reset search and filters
  const resetFilters = useCallback(() => {
    setSearchQuery('');
    setSelectedCategory(null);
  }, [setSearchQuery, setSelectedCategory]);

  // Toggle editor mode
  const toggleEditorMode = useCallback(() => {
    setEditorMode((mode) => (mode === 'edit' ? 'preview' : 'edit'));
  }, [setEditorMode]);

  // Keyboard shortcuts handler
  const handleKeyboardShortcuts = useCallback(
    (event: KeyboardEvent) => {
      // Toggle sidebar: Cmd/Ctrl + B
      if ((event.metaKey || event.ctrlKey) && event.key === 'b') {
        event.preventDefault();
        toggleSidebar();
      }

      // Toggle details panel: Cmd/Ctrl + D
      if ((event.metaKey || event.ctrlKey) && event.key === 'd') {
        event.preventDefault();
        toggleDetailsPanel();
      }

      // Clear selection: Escape
      if (event.key === 'Escape') {
        clearSelection();
      }

      // Search focus: Cmd/Ctrl + K
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        // This would focus the search input - implement in component
      }
    },
    [toggleSidebar, toggleDetailsPanel, clearSelection]
  );

  // Custom setter for details panel that also toggles sidebar
  const setDetailsPanelOpenWithSidebar = useCallback(
    (open: boolean) => {
      setDetailsPanelOpen(open);
      setSidebarCollapsed(open); // When details panel opens, hide sidebar; when it closes, show sidebar
    },
    [setDetailsPanelOpen, setSidebarCollapsed]
  );

  return {
    // State
    selectedNodeId,
    sidebarCollapsed,
    detailsPanelOpen,
    searchQuery,
    selectedCategory,
    canvasZoom,
    canvasPosition,
    isDraggingNode,
    showGrid,
    showMinimap,
    editorMode,
    isAnyPanelOpen,

    // Actions
    selectNode,
    clearSelection,
    setCanvasView,
    resetFilters,
    toggleEditorMode,
    toggleSidebar,
    toggleDetailsPanel,
    resetUI,
    handleKeyboardShortcuts,

    // Setters
    setSelectedNodeId,
    setSidebarCollapsed,
    setDetailsPanelOpen: setDetailsPanelOpenWithSidebar, // Use custom setter that handles sidebar
    setSearchQuery,
    setSelectedCategory,
    setCanvasZoom,
    setCanvasPosition,
    setIsDraggingNode,
    setShowGrid,
    setShowMinimap,
    setEditorMode,
  };
};
