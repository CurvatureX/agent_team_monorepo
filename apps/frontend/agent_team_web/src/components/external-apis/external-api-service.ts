/**
 * External API Service Client
 * 外部API服务客户端，处理与后端API的通信
 */

// 类型定义
export type ExternalAPIProvider = 'google_calendar' | 'github' | 'slack';

export interface AuthUrlResponse {
  auth_url: string;
  state: string;
  expires_at: string;
  provider: string;
  scopes: string[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_at?: string;
  scope: string[];
}

export interface CredentialInfo {
  provider: string;
  is_valid: boolean;
  scope: string[];
  created_at: string;
  updated_at: string;
  last_used_at?: string;
  expires_at?: string;
}

export interface TestAPICallRequest {
  provider: ExternalAPIProvider;
  operation: string;
  parameters: Record<string, any>;
}

export interface TestAPICallResponse {
  success: boolean;
  data: Record<string, any>;
  error?: string;
  execution_time_ms: number;
  metadata?: {
    provider: string;
    operation: string;
    api_call_id?: string;
    rate_limit_remaining?: number;
  };
}

/**
 * External API Service Client Class
 */
export class ExternalAPIService {
  private static readonly BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  private static readonly API_BASE = `${this.BASE_URL}/api/app/external-apis`;

  /**
   * 获取认证headers
   */
  private static getAuthHeaders(): HeadersInit {
    // 在实际应用中，这里应该从认证状态管理中获取JWT token
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * 处理API响应
   */
  private static async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * 启动OAuth2授权流程
   */
  static async startAuthorization(
    provider: ExternalAPIProvider, 
    scopes: string[] = [],
    redirectUri?: string
  ): Promise<AuthUrlResponse> {
    const response = await fetch(`${this.API_BASE}/auth/authorize`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        provider,
        scopes,
        redirect_uri: redirectUri
      })
    });

    return this.handleResponse<AuthUrlResponse>(response);
  }

  /**
   * 处理OAuth2授权回调
   */
  static async handleCallback(
    code: string,
    state: string,
    provider: ExternalAPIProvider
  ): Promise<TokenResponse> {
    const response = await fetch(`${this.API_BASE}/auth/callback`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        code,
        state,
        provider
      })
    });

    return this.handleResponse<TokenResponse>(response);
  }

  /**
   * 获取用户的外部API凭证列表
   */
  static async getUserCredentials(): Promise<CredentialInfo[]> {
    const response = await fetch(`${this.API_BASE}/credentials`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });

    const data = await this.handleResponse<{ credentials: CredentialInfo[] }>(response);
    return data.credentials;
  }

  /**
   * 撤销指定提供商的凭证
   */
  static async revokeCredential(provider: ExternalAPIProvider): Promise<boolean> {
    const response = await fetch(`${this.API_BASE}/credentials/${provider}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });

    const data = await this.handleResponse<{ success: boolean; message: string }>(response);
    return data.success;
  }

  /**
   * 测试API调用
   */
  static async testAPICall(request: TestAPICallRequest): Promise<TestAPICallResponse> {
    const response = await fetch(`${this.API_BASE}/test-call`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(request)
    });

    return this.handleResponse<TestAPICallResponse>(response);
  }

  /**
   * 获取外部API集成状态
   */
  static async getAPIStatus(): Promise<{
    total_providers: number;
    connected_providers: number;
    providers: Array<{
      provider: string;
      status: 'connected' | 'disconnected' | 'error';
      last_check: string;
    }>;
  }> {
    const response = await fetch(`${this.API_BASE}/status`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });

    return this.handleResponse(response);
  }

  /**
   * 获取API调用指标
   */
  static async getAPIMetrics(): Promise<{
    total_calls_today: number;
    successful_calls_today: number;
    failed_calls_today: number;
    providers: Array<{
      provider: string;
      calls_today: number;
      success_rate: number;
      avg_response_time_ms: number;
    }>;
  }> {
    const response = await fetch(`${this.API_BASE}/metrics`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });

    return this.handleResponse(response);
  }

  /**
   * 刷新访问令牌 (TODO: 后续实现)
   */
  static async refreshToken(provider: ExternalAPIProvider): Promise<TokenResponse> {
    // 这个功能需要在后端OAuth2Service中实现
    throw new Error('Token refresh functionality is not yet implemented');
  }

  /**
   * 验证凭证是否有效 (TODO: 后续实现)
   */
  static async validateCredential(provider: ExternalAPIProvider): Promise<boolean> {
    // 这个功能可以通过测试一个简单的API调用来实现
    try {
      const testRequests: Record<ExternalAPIProvider, TestAPICallRequest> = {
        google_calendar: {
          provider: 'google_calendar',
          operation: 'list_calendars',
          parameters: { max_results: 1 }
        },
        github: {
          provider: 'github',
          operation: 'get_user',
          parameters: {}
        },
        slack: {
          provider: 'slack',
          operation: 'auth_test',
          parameters: {}
        }
      };

      const testRequest = testRequests[provider];
      const result = await this.testAPICall(testRequest);
      return result.success;
    } catch {
      return false;
    }
  }
}

/**
 * OAuth2 Authorization Window Helper
 * OAuth2授权窗口辅助类
 */
export class OAuth2AuthWindow {
  private static readonly WINDOW_FEATURES = 'width=600,height=700,scrollbars=yes,resizable=yes,status=yes';

  /**
   * 打开OAuth2授权窗口并处理回调
   */
  static async authorize(
    provider: ExternalAPIProvider,
    scopes: string[] = []
  ): Promise<boolean> {
    try {
      // 获取授权URL
      const authResponse = await ExternalAPIService.startAuthorization(provider, scopes);
      
      // 打开授权窗口
      const authWindow = window.open(
        authResponse.auth_url,
        `oauth2_${provider}`,
        this.WINDOW_FEATURES
      );

      if (!authWindow) {
        throw new Error('无法打开授权窗口，请检查浏览器弹窗设置');
      }

      // 等待授权完成
      return new Promise((resolve, reject) => {
        const checkInterval = 1000; // 1秒检查一次
        const timeout = 300000; // 5分钟超时
        let elapsed = 0;

        const timer = setInterval(() => {
          elapsed += checkInterval;

          // 检查超时
          if (elapsed >= timeout) {
            clearInterval(timer);
            authWindow.close();
            reject(new Error('授权超时，请重试'));
            return;
          }

          // 检查窗口是否关闭
          if (authWindow.closed) {
            clearInterval(timer);
            // 假设用户关闭窗口意味着取消授权
            reject(new Error('用户取消了授权'));
            return;
          }

          // 检查URL变化 (如果回调到了我们的域名)
          try {
            const currentUrl = authWindow.location.href;
            if (currentUrl.includes('callback') || currentUrl.includes('code=')) {
              clearInterval(timer);
              authWindow.close();
              resolve(true);
            }
          } catch (e) {
            // 跨域限制，无法访问URL，这是正常的
          }
        }, checkInterval);

        // 监听消息事件
        const messageHandler = (event: MessageEvent) => {
          if (event.data && event.data.type === 'oauth2_callback') {
            clearInterval(timer);
            authWindow.close();
            window.removeEventListener('message', messageHandler);
            
            if (event.data.success) {
              resolve(true);
            } else {
              reject(new Error(event.data.error || '授权失败'));
            }
          }
        };

        window.addEventListener('message', messageHandler);
      });

    } catch (error) {
      console.error('OAuth2 authorization failed:', error);
      throw error;
    }
  }
}

export default ExternalAPIService;