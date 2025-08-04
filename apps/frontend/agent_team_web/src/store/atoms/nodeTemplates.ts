import { atom } from 'jotai';
import type { NodeTemplate, NodeCategory } from '@/types/node-template';
import { searchQueryAtom, selectedCategoryAtom } from './ui';

// Node templates data
export const nodeTemplatesAtom = atom<NodeTemplate[]>([]);

// Loading state
export const nodeTemplatesLoadingAtom = atom(true);

// Error state
export const nodeTemplatesErrorAtom = atom<string | null>(null);

// Derived atom - filtered templates based on search and category
export const filteredTemplatesAtom = atom((get) => {
  const templates = get(nodeTemplatesAtom);
  const query = get(searchQueryAtom).toLowerCase();
  const category = get(selectedCategoryAtom);

  return templates.filter((template) => {
    // Filter by search query
    const matchesSearch =
      !query ||
      template.name.toLowerCase().includes(query) ||
      template.description.toLowerCase().includes(query) ||
      template.node_type.toLowerCase().includes(query) ||
      template.node_subtype.toLowerCase().includes(query);

    // Filter by category
    const matchesCategory = !category || template.category === category;

    return matchesSearch && matchesCategory;
  });
});

// Derived atom - templates grouped by category
export const templatesByCategoryAtom = atom((get) => {
  const templates = get(nodeTemplatesAtom);
  
  return templates.reduce((acc, template) => {
    const category = template.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(template);
    return acc;
  }, {} as Record<NodeCategory, NodeTemplate[]>);
});

// Derived atom - available categories
export const availableCategoriesAtom = atom((get) => {
  const templates = get(nodeTemplatesAtom);
  const categories = new Set<NodeCategory>();
  
  templates.forEach((template) => {
    categories.add(template.category);
  });
  
  return Array.from(categories).sort();
});

// Derived atom - category counts
export const categoryCounts = atom((get) => {
  const templatesByCategory = get(templatesByCategoryAtom);
  
  return Object.entries(templatesByCategory).reduce((acc, [category, templates]) => {
    acc[category as NodeCategory] = templates.length;
    return acc;
  }, {} as Record<NodeCategory, number>);
});

// Action atom - load templates
export const loadNodeTemplatesAtom = atom(
  null,
  async (get, set) => {
    set(nodeTemplatesLoadingAtom, true);
    set(nodeTemplatesErrorAtom, null);
    
    try {
      // Try to load from API first
      const response = await fetch('/api/node-templates');
      if (!response.ok) {
        throw new Error('Failed to fetch node templates');
      }
      
      const data = await response.json();
      set(nodeTemplatesAtom, data.node_templates);
    } catch (error) {
      console.error('Failed to load node templates from API:', error);
      
      // Fallback to local JSON file
      try {
        const localData = await import('@/lib/node-template.json');
        set(nodeTemplatesAtom, localData.default.node_templates);
      } catch (localError) {
        console.error('Failed to load local node templates:', localError);
        set(nodeTemplatesErrorAtom, 'Failed to load node templates');
      }
    } finally {
      set(nodeTemplatesLoadingAtom, false);
    }
  }
);

// Action atom - get template by ID
export const getTemplateByIdAtom = atom(
  null,
  (get, set, templateId: string) => {
    const templates = get(nodeTemplatesAtom);
    return templates.find((t) => t.id === templateId);
  }
);