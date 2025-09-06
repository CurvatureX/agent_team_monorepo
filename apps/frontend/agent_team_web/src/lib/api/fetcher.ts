import useSWR, { SWRConfiguration } from 'swr';
import { useAuth } from '@/contexts/auth-context';

/**
 * 通用的 SWR fetcher
 */
type FetcherArgs = [string, string]; // [url, token]

export const fetcher = async ([url, token]: FetcherArgs) => {
  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
  
  if (!res.ok) {
    const error = new Error(`API Error: ${res.statusText}`);
    (error as any).status = res.status;
    throw error;
  }
  
  return res.json();
};

// HTTP 操作的通用函数
export const apiRequest = async (
  url: string,
  token: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  data?: any
) => {
  const res = await fetch(url, {
    method,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: method !== 'GET' && data ? JSON.stringify(data) : undefined,
  });
  
  if (!res.ok) {
    const error = new Error(`API Error: ${res.statusText}`);
    (error as any).status = res.status;
    throw error;
  }
  
  return res.status === 204 ? null : res.json();
};


export function useAuthSWR<T = any>(
  url: string | null,
  config?: SWRConfiguration
) {
  const { session } = useAuth();
  
  return useSWR<T>(
    session?.access_token && url ? [url, session.access_token] : null,
    fetcher,
    config
  );
}