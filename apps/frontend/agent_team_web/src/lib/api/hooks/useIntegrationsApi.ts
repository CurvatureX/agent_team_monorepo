import { API_PATHS } from '../config';
import { useAuthSWR } from '../fetcher';

interface Connection {
  id?: string;
  integration_id?: string;
  provider: string;
  integration_type?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  credential_data?: Record<string, any>;
  configuration?: Record<string, any>;
}

interface Integration {
  provider: string;
  name: string;
  description: string;
  install_url: string;
  is_connected: boolean;
  connection: Connection | null;
}

interface IntegrationsResponse {
  success: boolean;
  user_id: string;
  integrations: Integration[];
}

export function useIntegrationsApi() {
  const redirectUri = typeof window !== 'undefined'
    ? `${window.location.origin}/authorizations`
    : '';

  const apiUrl = redirectUri
    ? `${API_PATHS.INTEGRATIONS}?redirect_uri=${encodeURIComponent(redirectUri)}`
    : API_PATHS.INTEGRATIONS;

  const { data: integrationsData, error: integrationsError, isLoading: integrationsLoading, mutate } = useAuthSWR<IntegrationsResponse>(
    apiUrl,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
    }
  );

  return {
    integrations: integrationsData?.integrations || [],
    isLoading: integrationsLoading,
    isError: !!integrationsError,
    error: integrationsError,
    mutate,
  };
}
