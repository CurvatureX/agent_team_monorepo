import { API_PATHS } from '../config';
import { useAuthSWR } from '../fetcher';
import type { NodeTemplate } from '@/types/node-template';

interface NodeTemplatesResponse {
  node_templates: NodeTemplate[];
}

export function useNodeTemplatesApi() {
  const { data, error, isLoading, mutate } = useAuthSWR<NodeTemplatesResponse>(
    API_PATHS.NODE_TEMPLATES,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000, // 1 minute
    }
  );

  return {
    templates: data?.node_templates || [],
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}