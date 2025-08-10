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
  loadNodeTemplatesAtom,
  getTemplateByIdAtom,
} from '../atoms/nodeTemplates';
import type { NodeCategory } from '@/types/node-template';

export const useNodeTemplates = () => {
  const [templates, setTemplates] = useAtom(nodeTemplatesAtom);
  const loading = useAtomValue(nodeTemplatesLoadingAtom);
  const error = useAtomValue(nodeTemplatesErrorAtom);
  const filteredTemplates = useAtomValue(filteredTemplatesAtom);
  const templatesByCategory = useAtomValue(templatesByCategoryAtom);
  const categories = useAtomValue(availableCategoriesAtom);
  const counts = useAtomValue(categoryCounts);
  const loadTemplates = useSetAtom(loadNodeTemplatesAtom);
  const getTemplateById = useSetAtom(getTemplateByIdAtom);

  // Load templates on mount
  useEffect(() => {
    if (templates.length === 0 && !loading && !error) {
      loadTemplates();
    }
  }, [templates.length, loading, error, loadTemplates]);

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
    loading,
    error,
    filteredTemplates,
    templatesByCategory,
    categories,
    counts,
    
    // Actions
    loadTemplates,
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