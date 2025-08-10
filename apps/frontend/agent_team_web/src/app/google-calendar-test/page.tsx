"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  Calendar, 
  Play, 
  CheckCircle, 
  XCircle, 
  // AlertCircle,
  Loader2,
  Shield,
  ExternalLink,
  Plus,
  Copy,
  Code,
  Settings,
  RefreshCw
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

// Google OAuth2 配置 - 从环境变量或配置获取
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
const GOOGLE_SCOPES = 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events';
const REDIRECT_URI = 'http://localhost:3000/oauth-callback';
const USER_ID = '7ba36345-a2bb-4ec9-a001-bb46d79d629d'; // 固定用户ID

interface ExecutionResult {
  execution_id: string;
  status: string;
  output_data: unknown;
  error_message?: string;
  logs: string[];
}

interface EventFormData {
  summary: string;
  description: string;
  location: string;
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
}

interface ProviderStatus {
  authorized: boolean;
  client_id?: string;
  expires_at?: string;
  last_updated?: string;
  error?: string;
}

interface AllProvidersStatus {
  user_id: string;
  providers: Record<string, ProviderStatus>;
}

export default function GoogleCalendarTestPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [hasCredentials, setHasCredentials] = useState(false);
  const [lastResult, setLastResult] = useState<ExecutionResult | null>(null);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [authorizationCode, setAuthorizationCode] = useState<string>('');
  const [storedCredentials, setStoredCredentials] = useState<any>(null);
  const [allProvidersStatus, setAllProvidersStatus] = useState<AllProvidersStatus | null>(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(false);
  const { toast } = useToast();

  // 复制到剪贴板功能
  const copyToClipboard = async (text: string, description: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({
        title: "复制成功",
        description: `已复制${description}到剪贴板`,
        variant: "default"
      });
    } catch (err) {
      console.error('复制失败:', err);
      toast({
        title: "复制失败",
        description: "无法复制到剪贴板，请手动选择并复制",
        variant: "destructive"
      });
    }
  };

  // 事件表单数据
  const [eventForm, setEventForm] = useState<EventFormData>({
    summary: 'Test Event from Agent Team',
    description: 'This is a test event created through our external API integration system',
    location: 'Virtual Meeting',
    startDate: new Date().toISOString().split('T')[0],
    startTime: '10:00',
    endDate: new Date().toISOString().split('T')[0],
    endTime: '11:00'
  });

  // 获取所有提供商的授权状态 (N8N 风格)
  const fetchAllProvidersStatus = async () => {
    try {
      const response = await fetch(`http://localhost:8002/api/v1/credentials/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID
        })
      });
      
      if (response.ok) {
        const result: AllProvidersStatus = await response.json();
        setAllProvidersStatus(result);
        
        // 更新 Google Calendar 凭据状态
        const googleCalendarStatus = result.providers?.google_calendar;
        setHasCredentials(googleCalendarStatus?.authorized || false);
        
        return result;
      } else {
        console.log('Failed to fetch providers status');
        return null;
      }
    } catch (error) {
      console.log('Providers status check failed:', error);
      return null;
    }
  };

  // 检查是否已有存储的凭据 (向后兼容)
  const checkCredentials = async () => {
    const status = await fetchAllProvidersStatus();
    if (!status) {
      setHasCredentials(false);
    }
  };

  // 获取存储的凭据详情（包括authorization_code）
  const getStoredCredentials = async () => {
    try {
      const response = await fetch(`http://localhost:8002/api/v1/credentials/get`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          provider: 'google_calendar'
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.credentials) {
          setStoredCredentials(result.credentials);
          // 如果有存储的authorization_code，显示它
          if (result.credentials.authorization_code) {
            setAuthorizationCode(result.credentials.authorization_code);
          }
        }
      } else {
        console.log('No stored credentials found');
      }
    } catch (error) {
      console.log('Failed to get stored credentials:', error);
    }
  };

  // 创建测试工作流
  const createTestWorkflow = async () => {
    const response = await fetch('http://localhost:8002/v1/workflows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        name: 'Google Calendar Create Event Test',
        description: 'Test workflow for creating Google Calendar events',
        settings: {
          timeout: 300,
          retry_count: 3
        },
        nodes: [{
          id: 'google_calendar_create_node',
          name: 'Create Google Calendar Event',
          type: 'EXTERNAL_ACTION_NODE',
          subtype: 'GOOGLE_CALENDAR',
          parameters: {
            action: 'create_event',
            calendar_id: 'primary',
            summary: eventForm.summary,
            description: eventForm.description,
            location: eventForm.location
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

      // 构建事件的开始和结束时间 - Google Calendar API需要时区信息
      const startDateTime = `${eventForm.startDate}T${eventForm.startTime}:00+08:00`;
      const endDateTime = `${eventForm.endDate}T${eventForm.endTime}:00+08:00`;

      // 构建执行请求 (N8N风格 - 不包含凭据)
      const requestBody: Record<string, unknown> = {
        user_id: USER_ID,
        input_data: {},
        execution_context: {
          override_parameters: {
            action: 'create_event',
            calendar_id: 'primary',
            summary: eventForm.summary,
            description: eventForm.description,
            location: eventForm.location,
            start: startDateTime,
            end: endDateTime
          }
        }
      };
      
      // N8N风格：不传递凭据，让后端自动查询

      const response = await fetch(
        `http://localhost:8002/v1/workflows/${currentWorkflowId}/nodes/google_calendar_create_node/execute`,
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
              setAuthorizationCode(code); // 保存授权码用于显示
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

  // N8N风格的节点执行 - 后端自动查询凭据
  const handleExecuteNode = async () => {
    setIsLoading(true);
    setLastResult(null);

    try {
      // 步骤1: 直接执行节点 (后端会自动查询凭据)
      toast({
        title: "创建Google Calendar事件",
        description: "正在执行..."
      });

      // 简化的执行请求 - 不传递凭据
      const result = await executeGoogleCalendarNode();

      // 步骤2: 检查是否是授权错误
      if (result.status === 'FAILED' && 
          (result.error_details?.error_type === 'MISSING_CREDENTIALS' || 
           result.error_details?.requires_auth)) {
        
        // MVP版本: 显示错误，让用户手动授权
        toast({
          title: "需要授权",
          description: `请在授权管理区域为 ${result.error_details?.provider || 'Google Calendar'} 完成授权后重试`,
          variant: "destructive"
        });
      } else if (result.status === 'COMPLETED' && result.output_data?.success !== false) {
        toast({
          title: "事件创建成功！",
          description: "Google Calendar事件已成功创建，请查看您的Google日历。",
          variant: "default"
        });
      } else {
        toast({
          title: "创建失败",
          description: result.error_message || result.output_data?.error || "事件创建出现错误",
          variant: "destructive"
        });
      }

      // 显示执行结果
      setLastResult(result);

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

  // 手动授权单个提供商
  const handleManualAuthorize = async (provider: string) => {
    setIsLoadingAuth(true);
    
    try {
      if (provider === 'google_calendar') {
        toast({
          title: "启动授权",
          description: "正在打开Google授权页面..."
        });
        
        // 启动OAuth2流程
        const authorizationCode = await startOAuth2Flow();
        
        toast({
          title: "授权成功",
          description: "正在存储凭据..."
        });
        
        // 存储凭据
        await storeCredentials(authorizationCode);
        
        toast({
          title: "授权完成",
          description: "Google Calendar授权已完成，可以执行节点了"
        });
        
        // 刷新状态
        await fetchAllProvidersStatus();
        
      } else {
        toast({
          title: "暂不支持",
          description: `${provider} 授权功能正在开发中`,
          variant: "default"
        });
      }
    } catch (error) {
      toast({
        title: "授权失败",
        description: error instanceof Error ? error.message : "授权过程中发生错误",
        variant: "destructive"
      });
    } finally {
      setIsLoadingAuth(false);
    }
  };

  // 页面加载时检查所有提供商状态
  useEffect(() => {
    fetchAllProvidersStatus();
    getStoredCredentials(); // 获取已存储的凭据详情 (用于测试)
    
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
            Google Calendar 事件创建测试
          </h1>
          <p className="text-gray-600 mt-2">
            创建真实的Google Calendar事件 - N8N风格的智能OAuth2授权流程
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

      {/* N8N 风格的授权管理区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              授权管理 (N8N 风格)
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => fetchAllProvidersStatus()}
              disabled={isLoadingAuth}
            >
              <RefreshCw className={`w-3 h-3 mr-2 ${isLoadingAuth ? 'animate-spin' : ''}`} />
              刷新状态
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800 mb-2">
                <strong>💡 N8N 风格说明：</strong> 这是类似 N8N 的外部 API 集成管理方式
              </p>
              <ul className="text-xs text-blue-700 space-y-1">
                <li>• 节点执行时后端自动查询存储的凭据</li>
                <li>• 没有授权时返回标准错误格式</li>
                <li>• 前端显示错误，用户手动完成授权</li>
                <li>• 授权完成后重新执行节点即可</li>
              </ul>
            </div>

            {allProvidersStatus ? (
              <div className="grid gap-3">
                {Object.entries(allProvidersStatus.providers).map(([provider, status]) => (
                  <div key={provider} className="flex items-center justify-between p-3 bg-white border rounded-lg shadow-sm">
                    <div className="flex items-center gap-3">
                      {status.authorized ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-500" />
                      )}
                      <div>
                        <div className="font-medium capitalize text-gray-800">
                          {provider.replace('_', ' ')}
                        </div>
                        <div className="text-xs text-gray-600">
                          {status.authorized ? (
                            <>
                              <span className="text-green-600 font-medium">已授权</span>
                              {status.last_updated && (
                                <span className="text-gray-500"> • 更新于 {new Date(status.last_updated).toLocaleString()}</span>
                              )}
                            </>
                          ) : (
                            <span className="text-red-600 font-medium">未授权</span>
                          )}
                          {status.error && (
                            <div className="mt-1 text-xs text-red-600 bg-red-50 p-1 rounded">
                              错误: {status.error.length > 80 ? status.error.substring(0, 80) + '...' : status.error}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {status.authorized ? (
                        <Badge variant="outline" className="text-green-600 border-green-200">
                          已连接
                        </Badge>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => handleManualAuthorize(provider)}
                          disabled={isLoadingAuth}
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          {isLoadingAuth ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            '授权'
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin mx-auto mb-2" />
                正在加载提供商状态...
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* OAuth2参数显示卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code className="w-5 h-5" />
            OAuth2 参数（供cURL调用使用）
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800 mb-3">
              <strong>💡 使用说明：</strong> 页面会自动显示当前可用的OAuth2参数值，你可以复制用于手动cURL调用。如果没有显示授权码，请先完成OAuth2授权。
            </p>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-white rounded border">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-700">Client ID:</div>
                  <div className="text-xs font-mono text-gray-600 break-all">
                    {GOOGLE_CLIENT_ID || '未配置环境变量 NEXT_PUBLIC_GOOGLE_CLIENT_ID'}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(GOOGLE_CLIENT_ID, 'Client ID')}
                  disabled={!GOOGLE_CLIENT_ID}
                  className="ml-2"
                >
                  <Copy className="w-3 h-3" />
                </Button>
              </div>

              <div className="flex items-center justify-between p-3 bg-white rounded border">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-700">Redirect URI:</div>
                  <div className="text-xs font-mono text-gray-600">{REDIRECT_URI}</div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(REDIRECT_URI, 'Redirect URI')}
                  className="ml-2"
                >
                  <Copy className="w-3 h-3" />
                </Button>
              </div>

              <div className="flex items-center justify-between p-3 bg-white rounded border">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-700">User ID:</div>
                  <div className="text-xs font-mono text-gray-600">{USER_ID}</div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(USER_ID, 'User ID')}
                  className="ml-2"
                >
                  <Copy className="w-3 h-3" />
                </Button>
              </div>

              <div className="flex items-center justify-between p-3 bg-white rounded border">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-700">
                    Authorization Code:
                    {authorizationCode && (
                      <span className="ml-2 text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                        当前可用
                      </span>
                    )}
                  </div>
                  <div className="text-xs font-mono text-gray-600 break-all">
                    {authorizationCode || (hasCredentials ? '加载中...' : '需要先完成OAuth2授权')}
                  </div>
                  {authorizationCode && (
                    <div className="text-xs text-gray-500 mt-1">
                      💡 这是当前存储的有效授权码，可直接用于cURL调用
                    </div>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(authorizationCode, 'Authorization Code')}
                  disabled={!authorizationCode}
                  className="ml-2"
                >
                  <Copy className="w-3 h-3" />
                </Button>
              </div>

              {/* 工作流ID */}
              {workflowId && (
                <div className="flex items-center justify-between p-3 bg-white rounded border">
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-700">Workflow ID:</div>
                    <div className="text-xs font-mono text-gray-600 break-all">{workflowId}</div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(workflowId, 'Workflow ID')}
                    className="ml-2"
                  >
                    <Copy className="w-3 h-3" />
                  </Button>
                </div>
              )}
            </div>

            {/* 完整的cURL命令模板 - N8N风格 */}
            {workflowId && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium text-blue-800 hover:text-blue-900">
                  📋 点击查看 N8N 风格的 cURL 命令模板
                </summary>
                <div className="mt-3 p-3 bg-gray-100 rounded text-xs font-mono overflow-auto">
                  <div className="mb-2 text-gray-600">N8N风格执行命令（后端自动查询凭据）：</div>
                  <pre className="whitespace-pre-wrap break-all text-gray-800">
{`curl --location --request POST 'http://localhost:8002/v1/workflows/${workflowId}/nodes/google_calendar_create_node/execute' \\
--header 'Content-Type: application/json' \\
--data-raw '{
  "user_id": "${USER_ID}",
  "input_data": {},
  "execution_context": {
    "override_parameters": {
      "action": "create_event",
      "calendar_id": "primary",
      "summary": "${eventForm.summary}",
      "description": "${eventForm.description}",
      "location": "${eventForm.location}",
      "start": "${eventForm.startDate}T${eventForm.startTime}:00+08:00",
      "end": "${eventForm.endDate}T${eventForm.endTime}:00+08:00"
    }
  }
}'`}
                  </pre>
                  <div className="text-xs text-green-700 bg-green-50 p-2 rounded mt-2 mb-2">
                    💡 注意：N8N风格不需要在请求中传递credentials，后端会自动查询存储的凭据
                  </div>
                  <Button
                    size="sm"
                    onClick={() => copyToClipboard(`curl --location --request POST 'http://localhost:8002/v1/workflows/${workflowId}/nodes/google_calendar_create_node/execute' \\
--header 'Content-Type: application/json' \\
--data-raw '{
  "user_id": "${USER_ID}",
  "input_data": {},
  "execution_context": {
    "override_parameters": {
      "action": "create_event",
      "calendar_id": "primary",
      "summary": "${eventForm.summary}",
      "description": "${eventForm.description}",
      "location": "${eventForm.location}",
      "start": "${eventForm.startDate}T${eventForm.startTime}:00+08:00",
      "end": "${eventForm.endDate}T${eventForm.endTime}:00+08:00"
    }
  }
}'`, 'N8N风格 cURL命令')}
                    className="mt-2"
                  >
                    <Copy className="w-3 h-3 mr-2" />
                    复制 N8N 风格 cURL 命令
                  </Button>
                </div>

                {/* Legacy命令（包含凭据的版本）*/}
                {authorizationCode && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded text-xs font-mono overflow-auto">
                    <div className="mb-2 text-yellow-800">Legacy风格执行命令（手动传递凭据）：</div>
                    <pre className="whitespace-pre-wrap break-all text-gray-800">
{`curl --location --request POST 'http://localhost:8002/v1/workflows/${workflowId}/nodes/google_calendar_create_node/execute' \\
--header 'Content-Type: application/json' \\
--data-raw '{
  "user_id": "${USER_ID}",
  "input_data": {},
  "execution_context": {
    "override_parameters": {
      "action": "create_event",
      "calendar_id": "primary",
      "summary": "${eventForm.summary}",
      "description": "${eventForm.description}",
      "location": "${eventForm.location}",
      "start": "${eventForm.startDate}T${eventForm.startTime}:00+08:00",
      "end": "${eventForm.endDate}T${eventForm.endTime}:00+08:00"
    }
  },
  "credentials": {
    "google_calendar": {
      "authorization_code": "${authorizationCode}",
      "client_id": "${GOOGLE_CLIENT_ID}",
      "redirect_uri": "${REDIRECT_URI}"
    }
  }
}'`}
                    </pre>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyToClipboard(`curl --location --request POST 'http://localhost:8002/v1/workflows/${workflowId}/nodes/google_calendar_create_node/execute' \\
--header 'Content-Type: application/json' \\
--data-raw '{
  "user_id": "${USER_ID}",
  "input_data": {},
  "execution_context": {
    "override_parameters": {
      "action": "create_event",
      "calendar_id": "primary",
      "summary": "${eventForm.summary}",
      "description": "${eventForm.description}",
      "location": "${eventForm.location}",
      "start": "${eventForm.startDate}T${eventForm.startTime}:00+08:00",
      "end": "${eventForm.endDate}T${eventForm.endTime}:00+08:00"
    }
  },
  "credentials": {
    "google_calendar": {
      "authorization_code": "${authorizationCode}",
      "client_id": "${GOOGLE_CLIENT_ID}",
      "redirect_uri": "${REDIRECT_URI}"
    }
  }
}'`, 'Legacy cURL命令')}
                      className="mt-2"
                    >
                      <Copy className="w-3 h-3 mr-2" />
                      复制 Legacy cURL 命令
                    </Button>
                  </div>
                )}
              </details>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 事件表单卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            事件详情
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="summary">事件标题</Label>
              <Input
                id="summary"
                value={eventForm.summary}
                onChange={(e) => setEventForm({...eventForm, summary: e.target.value})}
                placeholder="输入事件标题"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="location">地点</Label>
              <Input
                id="location"
                value={eventForm.location}
                onChange={(e) => setEventForm({...eventForm, location: e.target.value})}
                placeholder="输入事件地点"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">事件描述</Label>
            <Textarea
              id="description"
              value={eventForm.description}
              onChange={(e) => setEventForm({...eventForm, description: e.target.value})}
              placeholder="输入事件描述"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>开始时间</Label>
              <div className="flex gap-2">
                <Input
                  type="date"
                  value={eventForm.startDate}
                  onChange={(e) => setEventForm({...eventForm, startDate: e.target.value})}
                />
                <Input
                  type="time"
                  value={eventForm.startTime}
                  onChange={(e) => setEventForm({...eventForm, startTime: e.target.value})}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>结束时间</Label>
              <div className="flex gap-2">
                <Input
                  type="date"
                  value={eventForm.endDate}
                  onChange={(e) => setEventForm({...eventForm, endDate: e.target.value})}
                />
                <Input
                  type="time"
                  value={eventForm.endTime}
                  onChange={(e) => setEventForm({...eventForm, endTime: e.target.value})}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 执行测试卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            创建Google Calendar事件
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h3 className="font-medium text-green-900 mb-2">🎯 N8N 风格创建流程</h3>
            <div className="text-sm text-green-700 space-y-1">
              <p>1. 填写上方事件详情表单</p>
              <p>2. 点击创建按钮（后端自动查询存储的凭据）</p>
              <p>3. 如果未授权，会显示错误提示</p>
              <p>4. 在"授权管理"区域手动完成授权</p>
              <p>5. 重新点击创建按钮执行节点</p>
              <p>6. 创建成功后可在Google Calendar中查看</p>
            </div>
          </div>

          <Button 
            onClick={handleExecuteNode}
            disabled={isLoading}
            className="w-full bg-green-600 hover:bg-green-700"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                创建中...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                创建 Google Calendar 事件
              </>
            )}
          </Button>

          {/* 执行结果 */}
          {lastResult && (
            <div className="mt-4 space-y-4">
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

              {/* 成功结果展示 */}
              {lastResult.status === 'COMPLETED' && lastResult.output_data?.success && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-3">
                  <h5 className="font-medium text-green-800 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    事件创建成功！
                  </h5>
                  
                  {lastResult.output_data?.event && (
                    <div className="space-y-2 text-sm">
                      {lastResult.output_data.event_id && (
                        <p><strong>事件ID:</strong> {lastResult.output_data.event_id}</p>
                      )}
                      {lastResult.output_data.html_link && (
                        <p>
                          <strong>Google Calendar链接:</strong> 
                          <a 
                            href={lastResult.output_data.html_link} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="ml-2 text-blue-600 hover:underline inline-flex items-center gap-1"
                          >
                            查看事件 <ExternalLink className="w-3 h-3" />
                          </a>
                        </p>
                      )}
                      
                      <div className="mt-3 p-3 bg-white rounded border">
                        <p><strong>标题:</strong> {eventForm.summary}</p>
                        <p><strong>时间:</strong> {eventForm.startDate} {eventForm.startTime} - {eventForm.endDate} {eventForm.endTime}</p>
                        <p><strong>地点:</strong> {eventForm.location}</p>
                        <p><strong>描述:</strong> {eventForm.description}</p>
                      </div>
                      
                      <div className="bg-blue-50 border border-blue-200 rounded p-3 text-blue-800">
                        <p className="font-medium">🎉 验证步骤：</p>
                        <p className="text-sm mt-1">
                          1. 打开您的 <a href="https://calendar.google.com" target="_blank" className="underline">Google Calendar</a><br/>
                          2. 查找刚创建的事件："{eventForm.summary}"<br/>
                          3. 确认事件详情是否正确
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 详细数据展示 */}
              <details className="bg-gray-50 rounded-lg">
                <summary className="cursor-pointer p-3 font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
                  查看详细响应数据
                </summary>
                <div className="p-3 pt-0">
                  <pre className="text-xs overflow-auto max-h-80 bg-white p-3 rounded border">
                    {JSON.stringify(lastResult.output_data, null, 2)}
                  </pre>
                </div>
              </details>

              {lastResult.logs && lastResult.logs.length > 0 && (
                <details className="bg-gray-50 rounded-lg">
                  <summary className="cursor-pointer p-3 font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
                    查看执行日志
                  </summary>
                  <div className="p-3 pt-0">
                    <div className="bg-white rounded border p-3 text-sm space-y-1">
                      {lastResult.logs.map((log, index) => (
                        <div key={index} className="font-mono text-xs">• {log}</div>
                      ))}
                    </div>
                  </div>
                </details>
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
          <p>• <strong>事件创建</strong>: 填写事件详情后点击创建按钮，系统会在您的Google Calendar中创建真实事件</p>
          <p>• <strong>智能检测</strong>: 系统会自动检测是否需要OAuth2授权</p>
          <p>• <strong>弹窗授权</strong>: 如需授权会自动弹出Google授权页面，完成后自动关闭</p>
          <p>• <strong>自动重试</strong>: 授权完成后会自动重新执行事件创建</p>
          <p>• <strong>凭据存储</strong>: 授权信息会安全存储，下次创建事件无需重新授权</p>
          <p>• <strong>即时验证</strong>: 创建成功后可直接在Google Calendar中查看和验证事件</p>
          <p>• <strong>完整集成</strong>: 展示了与N8N等平台相同的外部API集成体验</p>
        </CardContent>
      </Card>
    </div>
  );
}