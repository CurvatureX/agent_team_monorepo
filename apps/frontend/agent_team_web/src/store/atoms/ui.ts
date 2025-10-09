import { atom } from 'jotai';
import type { XYPosition } from 'reactflow';
import type { NodeCategory } from '@/types/node-template';

// Selected node ID
export const selectedNodeIdAtom = atom<string | null>(null);

// Sidebar state
export const sidebarCollapsedAtom = atom(false);

// Details panel state
export const detailsPanelOpenAtom = atom(false);

// Search query for node templates
export const searchQueryAtom = atom('');

// Selected category filter
export const selectedCategoryAtom = atom<NodeCategory | null>(null);

// Canvas zoom level
export const canvasZoomAtom = atom(1);

// Canvas position
export const canvasPositionAtom = atom<XYPosition>({ x: 0, y: 0 });

// Dragging state for node templates
export const isDraggingNodeAtom = atom(false);

// Show grid on canvas
export const showGridAtom = atom(true);

// Show minimap
export const showMinimapAtom = atom(true);

// Editor mode
export const editorModeAtom = atom<'edit' | 'preview'>('edit');

// Derived atom - is any panel open
export const isAnyPanelOpenAtom = atom((get) => {
  return !get(sidebarCollapsedAtom) || get(detailsPanelOpenAtom);
});

// Action atom - toggle sidebar
export const toggleSidebarAtom = atom(
  null,
  (get, set) => {
    set(sidebarCollapsedAtom, !get(sidebarCollapsedAtom));
  }
);

// Action atom - toggle details panel
export const toggleDetailsPanelAtom = atom(
  null,
  (get, set) => {
    set(detailsPanelOpenAtom, !get(detailsPanelOpenAtom));
  }
);

// Action atom - reset UI state
export const resetUIStateAtom = atom(
  null,
  (get, set) => {
    set(selectedNodeIdAtom, null);
    set(sidebarCollapsedAtom, false); // Show Node Library by default
    set(detailsPanelOpenAtom, false); // Hide Node Details by default
    set(searchQueryAtom, '');
    set(selectedCategoryAtom, null);
    set(canvasZoomAtom, 1);
    set(canvasPositionAtom, { x: 0, y: 0 });
  }
);
