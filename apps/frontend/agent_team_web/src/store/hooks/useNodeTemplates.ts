import { useAtom, useAtomValue, useSetAtom } from 'jotai';
import { useEffect, useCallback } from 'react';
import {
  nodeTemplatesAtom,
  nodeTemplatesLoadingAtom,
  nodeTemplatesErrorAtom,
  filteredTemplatesAtom,
  templatesByCategoryAtom,
  availableCategoriesAtom,
  categoryCounts,
  getTemplateByIdAtom,
} from '../atoms/nodeTemplates';
import type { NodeCategory, NodeTemplate } from '@/types/node-template';
import { useNodeTemplatesApi } from '@/lib/api';

// Normalize category names to match the expected format
const normalizeCategoryName = (category: string | null | undefined): NodeCategory => {
  if (!category) {
    // Default category based on node_type if category is null
    return 'Actions'; // Default fallback
  }
  
  const categoryMap: Record<string, NodeCategory> = {
    'trigger': 'Trigger',
    'triggers': 'Trigger',
    'ai_agent': 'AI Agents',
    'ai_agents': 'AI Agents',
    'ai agents': 'AI Agents',
    'action': 'Actions',
    'actions': 'Actions',
    'flow_control': 'Flow Control',
    'flow control': 'Flow Control',
    'human_interaction': 'Human Interaction',
    'human interaction': 'Human Interaction',
    'memory': 'Memory',
    'tool': 'Tools',
    'tools': 'Tools',
  };

  const lowerCategory = category.toLowerCase();
  return categoryMap[lowerCategory] || (category as NodeCategory);
};

// Normalize templates data
const normalizeTemplates = (templates: NodeTemplate[]): NodeTemplate[] => {
  return templates.map(template => ({
    ...template,
    category: normalizeCategoryName(template.category),
  }));
};

export const useNodeTemplates = () => {
  const [templates, setTemplates] = useAtom(nodeTemplatesAtom);
  const [, setLoading] = useAtom(nodeTemplatesLoadingAtom);
  const [, setError] = useAtom(nodeTemplatesErrorAtom);
  const filteredTemplates = useAtomValue(filteredTemplatesAtom);
  const templatesByCategory = useAtomValue(templatesByCategoryAtom);
  const categories = useAtomValue(availableCategoriesAtom);
  const counts = useAtomValue(categoryCounts);
  const getTemplateById = useSetAtom(getTemplateByIdAtom);

  // Use SWR hook to fetch data
  const { templates: apiTemplates, isLoading, isError, error: apiError } = useNodeTemplatesApi();

  // Sync API data with Jotai atoms
  useEffect(() => {
    if (apiTemplates && apiTemplates.length > 0) {
      // Normalize templates before setting
      const normalized = normalizeTemplates(apiTemplates);
      setTemplates(normalized);
      setLoading(false);
      setError(null);
    }
  }, [apiTemplates, setTemplates, setLoading, setError]);

  // Update loading and error states
  useEffect(() => {
    setLoading(isLoading);
    if (isError) {
      setError(apiError?.message || 'Failed to load node templates');
    }
  }, [isLoading, isError, apiError, setLoading, setError]);

  // Get templates for a specific category
  const getTemplatesByCategory = useCallback(
    (category: NodeCategory) => {
      return templatesByCategory[category] || [];
    },
    [templatesByCategory]
  );

  // Get template by node type and subtype
  const getTemplateByType = useCallback(
    (nodeType: string, nodeSubtype: string) => {
      return templates.find(
        (t) => t.node_type === nodeType && t.node_subtype === nodeSubtype
      );
    },
    [templates]
  );

  // Search templates
  const searchTemplates = useCallback(
    (query: string) => {
      const lowerQuery = query.toLowerCase();
      return templates.filter(
        (template) =>
          template.name.toLowerCase().includes(lowerQuery) ||
          template.description.toLowerCase().includes(lowerQuery) ||
          template.node_type.toLowerCase().includes(lowerQuery) ||
          template.node_subtype.toLowerCase().includes(lowerQuery)
      );
    },
    [templates]
  );

  // Get category color
  const getCategoryColor = useCallback((category: NodeCategory) => {
    const colorMap: Record<NodeCategory, { primary: string; secondary: string }> = {
      'Trigger': { primary: '#10b981', secondary: '#d1fae5' },
      'AI Agents': { primary: '#6366f1', secondary: '#e0e7ff' },
      'Actions': { primary: '#f59e0b', secondary: '#fef3c7' },
      'Flow Control': { primary: '#8b5cf6', secondary: '#ede9fe' },
      'Human Interaction': { primary: '#ec4899', secondary: '#fce7f3' },
      'Memory': { primary: '#f97316', secondary: '#fed7aa' },
      'Tools': { primary: '#06b6d4', secondary: '#cffafe' },
    };
    
    return colorMap[category] || { primary: '#6b7280', secondary: '#f3f4f6' };
  }, []);

  // Get category icon
  const getCategoryIcon = useCallback((category: NodeCategory) => {
    const iconMap: Record<NodeCategory, string> = {
      'Trigger': 'play',
      'AI Agents': 'bot',
      'Actions': 'zap',
      'Flow Control': 'git-branch',
      'Human Interaction': 'users',
      'Memory': 'database',
      'Tools': 'wrench',
    };
    
    return iconMap[category] || 'circle';
  }, []);

  return {
    // State
    templates,
    loading: isLoading,
    error: isError ? (apiError?.message || 'Failed to load node templates') : null,
    filteredTemplates,
    templatesByCategory,
    categories,
    counts,
    
    // Actions
    loadTemplates: () => {}, // No-op since SWR handles loading
    getTemplateById,
    getTemplatesByCategory,
    getTemplateByType,
    searchTemplates,
    
    // Utilities
    getCategoryColor,
    getCategoryIcon,
    
    // Setters
    setTemplates,
  };
};