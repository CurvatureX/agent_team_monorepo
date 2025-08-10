"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Calendar, 
  Play, 
  CheckCircle, 
  XCircle, 
  // AlertCircle,
  Loader2,
  Shield
  // ExternalLink
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

// Google OAuth2 配置 - 从环境变量或配置获取
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
const GOOGLE_SCOPES = 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events';
const REDIRECT_URI = 'http://localhost:3003/oauth-callback';
const USER_ID = '7ba36345-a2bb-4ec9-a001-bb46d79d629d'; // 固定用户ID

interface ExecutionResult {
  execution_id: string;
  status: string;
  output_data: unknown;
  error_message?: string;
  logs: string[];
}

export default function GoogleCalendarTestPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [hasCredentials, setHasCredentials] = useState(false);
  const [lastResult, setLastResult] = useState<ExecutionResult | null>(null);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const { toast } = useToast();

  // 检查是否已有存储的凭据
  const checkCredentials = async () => {
    try {
      const response = await fetch(`http://localhost:8002/api/v1/credentials/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          provider: 'google_calendar'
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setHasCredentials(result.has_credentials);
      }
    } catch {
      console.log('Credentials check failed, assuming no credentials');
      setHasCredentials(false);
    }
  };

  // 创建测试工作流
  const createTestWorkflow = async () => {
    const response = await fetch('http://localhost:8002/v1/workflows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        name: 'Google Calendar OAuth2 Test',
        description: 'Test workflow for Google Calendar OAuth2 integration',
        settings: {
          timeout: 300,
          retry_count: 3
        },
        nodes: [{
          id: 'google_calendar_node',
          name: 'Google Calendar Node',
          type: 'EXTERNAL_ACTION_NODE',
          subtype: 'GOOGLE_CALENDAR',
          parameters: {
            action: 'list_events',
            calendar_id: 'primary',
            max_results: '10'
          },
          position: { x: 100, y: 100 }
        }],
        connections: {},
        trigger: {
          type: 'manual',
          config: {}
        }
      })
    });

    if (!response.ok) {
      throw new Error('Failed to create workflow');
    }

    const data = await response.json();
    return data.workflow.id;
  };

  // 执行Google Calendar节点
  const executeGoogleCalendarNode = async (credentials?: any) => {
    try {
      // 确保有工作流ID
      let currentWorkflowId = workflowId;
      if (!currentWorkflowId) {
        currentWorkflowId = await createTestWorkflow();
        setWorkflowId(currentWorkflowId);
      }

      // 构建执行请求
      const requestBody: Record<string, unknown> = {
        user_id: USER_ID,
        input_data: {
          calendar_id: 'primary',
          time_min: new Date().toISOString(),
          time_max: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString() // 未来7天
        },
        execution_context: {
          override_parameters: {
            action: 'list_events',
            max_results: '10'
          }
        }
      };

      // 如果有凭据，添加到请求中
      if (credentials) {
        requestBody.credentials = {
          google_calendar: credentials
        };
      }

      const response = await fetch(
        `http://localhost:8002/v1/workflows/${currentWorkflowId}/nodes/google_calendar_node/execute`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody)
        }
      );

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Execute node error:', error);
      throw error;
    }
  };

  // OAuth2授权流程
  const startOAuth2Flow = () => {
    return new Promise<string>((resolve, reject) => {
      // 生成state参数
      const state = `google_calendar_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // 构建Google OAuth2 URL
      const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
      authUrl.searchParams.set('client_id', GOOGLE_CLIENT_ID);
      authUrl.searchParams.set('response_type', 'code');
      authUrl.searchParams.set('scope', GOOGLE_SCOPES);
      authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
      authUrl.searchParams.set('state', state);
      authUrl.searchParams.set('access_type', 'offline');
      authUrl.searchParams.set('prompt', 'consent');

      // 存储state用于验证
      sessionStorage.setItem('oauth2_state', state);

      // 打开弹窗
      const popup = window.open(
        authUrl.toString(),
        'google-oauth2',
        'width=500,height=600,scrollbars=yes,resizable=yes'
      );

      if (!popup) {
        reject(new Error('Popup blocked. Please allow popups for this site.'));
        return;
      }

      // 监听弹窗URL变化
      const checkClosed = setInterval(() => {
        try {
          if (popup.closed) {
            clearInterval(checkClosed);
            reject(new Error('OAuth2 authorization was cancelled'));
            return;
          }

          // 检查是否重定向回我们的回调页面
          const popupUrl = popup.location.href;
          if (popupUrl.includes('/oauth-callback')) {
            const urlParams = new URLSearchParams(popup.location.search);
            const code = urlParams.get('code');
            const returnedState = urlParams.get('state');
            const error = urlParams.get('error');

            if (error) {
              popup.close();
              clearInterval(checkClosed);
              reject(new Error(`OAuth2 error: ${error}`));
              return;
            }

            if (code && returnedState === state) {
              popup.close();
              clearInterval(checkClosed);
              sessionStorage.removeItem('oauth2_state');
              resolve(code);
            }
          }
        } catch {
          // 忽略跨域错误，继续检查
        }
      }, 1000);

      // 10分钟后超时
      setTimeout(() => {
        if (!popup.closed) {
          popup.close();
        }
        clearInterval(checkClosed);
        reject(new Error('OAuth2 authorization timed out'));
      }, 10 * 60 * 1000);
    });
  };

  // 存储授权码到后端
  const storeCredentials = async (authorizationCode: string) => {
    const response = await fetch('http://localhost:8002/api/v1/credentials/store', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        provider: 'google_calendar',
        authorization_code: authorizationCode,
        client_id: GOOGLE_CLIENT_ID,
        redirect_uri: REDIRECT_URI
      })
    });

    if (!response.ok) {
      throw new Error('Failed to store credentials');
    }

    return await response.json();
  };

  // 主要的执行函数 - N8N风格的智能执行
  const handleExecuteNode = async () => {
    setIsLoading(true);
    setLastResult(null);

    try {
      // 步骤1: 尝试直接执行节点
      toast({
        title: "执行Google Calendar节点",
        description: "正在检查是否需要授权..."
      });

      let result = await executeGoogleCalendarNode();

      // 步骤2: 检查是否需要OAuth2授权
      if (result.output_data?.requires_auth || result.output_data?.error?.includes('credentials')) {
        toast({
          title: "需要授权",
          description: "正在启动Google OAuth2授权流程...",
          variant: "default"
        });

        // 步骤3: 启动OAuth2授权流程
        const authorizationCode = await startOAuth2Flow();
        
        toast({
          title: "授权成功",
          description: "正在存储凭据并重新执行节点..."
        });

        // 步骤4: 存储凭据到后端
        await storeCredentials(authorizationCode);

        // 步骤5: 使用新凭据重新执行节点
        result = await executeGoogleCalendarNode({
          authorization_code: authorizationCode,
          client_id: GOOGLE_CLIENT_ID,
          redirect_uri: REDIRECT_URI
        });

        // 更新凭据状态
        setHasCredentials(true);
      }

      // 显示最终结果
      setLastResult(result);

      if (result.status === 'COMPLETED' && result.output_data?.success !== false) {
        toast({
          title: "执行成功！",
          description: "Google Calendar节点执行完成，已获取日历数据。",
          variant: "default"
        });
      } else {
        toast({
          title: "执行失败",
          description: result.error_message || result.output_data?.error || "节点执行出现错误",
          variant: "destructive"
        });
      }

    } catch (error) {
      console.error('Execution error:', error);
      toast({
        title: "执行失败",
        description: error instanceof Error ? error.message : "发生未知错误",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 页面加载时检查凭据状态
  useEffect(() => {
    checkCredentials();
    
    // 检查URL参数，处理OAuth2回调
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const error = urlParams.get('error');

    if (error) {
      toast({
        title: "授权失败",
        description: `OAuth2 error: ${error}`,
        variant: "destructive"
      });
      // 清理URL参数
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (code && state) {
      // OAuth2回调成功，清理URL参数
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Calendar className="w-8 h-8" />
            Google Calendar OAuth2 测试
          </h1>
          <p className="text-gray-600 mt-2">
            N8N风格的智能OAuth2授权流程 - 自动检测、弹窗授权、存储凭据
          </p>
        </div>
      </div>

      {/* OAuth2状态卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            OAuth2 授权状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            {hasCredentials ? (
              <>
                <CheckCircle className="w-5 h-5 text-green-500" />
                <span className="text-green-600 font-medium">已授权</span>
                <Badge variant="outline" className="text-green-600 border-green-200">
                  Google Calendar 已连接
                </Badge>
              </>
            ) : (
              <>
                <XCircle className="w-5 h-5 text-red-500" />
                <span className="text-red-600 font-medium">未授权</span>
                <Badge variant="outline" className="text-red-600 border-red-200">
                  需要授权
                </Badge>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 执行测试卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="w-5 h-5" />
            Google Calendar 节点测试
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-medium text-blue-900 mb-2">🎯 智能执行流程</h3>
            <div className="text-sm text-blue-700 space-y-1">
              <p>1. 点击执行按钮</p>
              <p>2. 自动检测是否需要OAuth2授权</p>
              <p>3. 如需授权，自动弹出Google授权页面</p>
              <p>4. 授权完成后自动存储凭据</p>
              <p>5. 自动重新执行节点，获取真实数据</p>
            </div>
          </div>

          <Button 
            onClick={handleExecuteNode}
            disabled={isLoading}
            className="w-full"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                执行中...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                执行 Google Calendar 节点
              </>
            )}
          </Button>

          {/* 执行结果 */}
          {lastResult && (
            <div className="mt-4 space-y-3">
              <div className="flex items-center gap-2">
                <h4 className="font-medium">执行结果:</h4>
                {lastResult.status === 'COMPLETED' ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500" />
                )}
                <Badge 
                  variant={lastResult.status === 'COMPLETED' ? 'default' : 'destructive'}
                >
                  {lastResult.status}
                </Badge>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <pre className="text-sm overflow-auto max-h-96">
                  {JSON.stringify(lastResult.output_data, null, 2)}
                </pre>
              </div>

              {lastResult.logs.length > 0 && (
                <div>
                  <h5 className="font-medium mb-2">执行日志:</h5>
                  <div className="bg-gray-100 rounded p-3 text-sm">
                    {lastResult.logs.map((log, index) => (
                      <div key={index} className="mb-1">• {log}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 使用说明 */}
      <Card>
        <CardHeader>
          <CardTitle>使用说明</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-gray-600">
          <p>• <strong>智能检测</strong>: 系统会自动检测是否需要OAuth2授权</p>
          <p>• <strong>弹窗授权</strong>: 如需授权会自动弹出Google授权页面</p>
          <p>• <strong>自动重试</strong>: 授权完成后会自动重新执行节点</p>
          <p>• <strong>凭据存储</strong>: 授权信息会安全存储，下次无需重新授权</p>
          <p>• <strong>真实API</strong>: 执行成功后会调用真实的Google Calendar API</p>
        </CardContent>
      </Card>
    </div>
  );
}