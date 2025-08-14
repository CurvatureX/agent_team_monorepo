import { mutate as globalMutate } from 'swr';
import { useAuth } from '@/contexts/auth-context';
import { API_PATHS } from '../config';
import { useAuthSWR, apiRequest } from '../fetcher';

// 获取工作流列表
export function useWorkflowsApi(params?: {
  active_only?: boolean;
  tags?: string;
  limit?: number;
  offset?: number;
}) {
  const queryString = params
    ? '?' + new URLSearchParams(
        Object.entries(params)
          .filter(([_, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      ).toString()
    : '';
  
  const { data, error, isLoading, mutate } = useAuthSWR(
    API_PATHS.WORKFLOWS + queryString,
    { revalidateOnFocus: false }
  );

  return {
    workflows: data || [],
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}

// 获取单个工作流
export function useWorkflowApi(workflowId: string | null) {
  const { data, error, isLoading, mutate } = useAuthSWR(
    workflowId ? API_PATHS.WORKFLOW(workflowId) : null,
    { revalidateOnFocus: false }
  );

  return {
    workflow: data,
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}

// 工作流操作 (创建、更新、删除等)
export function useWorkflowActions() {
  const { session } = useAuth();
  
  if (!session?.access_token) {
    return {
      createWorkflow: async () => { throw new Error('Not authenticated'); },
      updateWorkflow: async () => { throw new Error('Not authenticated'); },
      deleteWorkflow: async () => { throw new Error('Not authenticated'); },
      executeWorkflow: async () => { throw new Error('Not authenticated'); },
      deployWorkflow: async () => { throw new Error('Not authenticated'); },
    };
  }
  
  const token = session.access_token;

  return {
    createWorkflow: async (data: any) => {
      const result = await apiRequest(API_PATHS.WORKFLOWS, token, 'POST', data);
      // 刷新列表
      globalMutate((key) => 
        Array.isArray(key) && key[0]?.includes('/workflows/')
      );
      return result;
    },
    
    updateWorkflow: async (id: string, data: any) => {
      const result = await apiRequest(API_PATHS.WORKFLOW(id), token, 'PUT', data);
      // 刷新该工作流和列表
      globalMutate([API_PATHS.WORKFLOW(id), token]);
      globalMutate((key) => 
        Array.isArray(key) && key[0]?.includes('/workflows/')
      );
      return result;
    },
    
    deleteWorkflow: async (id: string) => {
      await apiRequest(API_PATHS.WORKFLOW(id), token, 'DELETE');
      // 刷新列表
      globalMutate((key) => 
        Array.isArray(key) && key[0]?.includes('/workflows/')
      );
    },
    
    executeWorkflow: async (id: string, data?: any) => {
      return apiRequest(API_PATHS.WORKFLOW_EXECUTE(id), token, 'POST', data);
    },
    
    deployWorkflow: async (id: string) => {
      return apiRequest(API_PATHS.WORKFLOW_DEPLOY(id), token, 'POST');
    },
  };
}