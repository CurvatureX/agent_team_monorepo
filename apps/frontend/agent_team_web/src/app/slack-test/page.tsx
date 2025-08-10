"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  MessageSquare, 
  Play, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader2,
  Shield,
  ExternalLink,
  Send,
  Hash,
  Users,
  Upload
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

// Slack OAuth2 配置
const SLACK_CLIENT_ID = process.env.NEXT_PUBLIC_SLACK_CLIENT_ID || '';
const SLACK_SCOPES = 'chat:write channels:read users:read files:write';
const REDIRECT_URI = 'http://localhost:3000/oauth-callback';
const USER_ID = '7ba36345-a2bb-4ec9-a001-bb46d79d629d';

interface ExecutionResult {
  execution_id: string;
  status: string;
  output_data: any;
  error_message?: string;
  logs: string[];
}

interface SlackFormData {
  action: 'send_message' | 'update_message' | 'delete_message' | 'upload_file' | 'get_user_info' | 'list_channels';
  channel: string;
  message: string;
  username: string;
  iconEmoji: string;
  iconUrl: string;
  threadTs: string;
  userId: string;
  fileName: string;
  fileContent: string;
  title: string;
  initialComment: string;
}

export default function SlackTestPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [hasCredentials, setHasCredentials] = useState(false);
  const [lastResult, setLastResult] = useState<ExecutionResult | null>(null);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const { toast } = useToast();

  const [formData, setFormData] = useState<SlackFormData>({
    action: 'send_message',
    channel: '#general',
    message: 'Hello from Agent Team! 🚀\n\nThis is a test message sent through our external API integration system.',
    username: 'Agent Team Bot',
    iconEmoji: ':robot_face:',
    iconUrl: '',
    threadTs: '',
    userId: '',
    fileName: 'test-file.txt',
    fileContent: 'This is a test file uploaded via Agent Team integration',
    title: 'Test File Upload',
    initialComment: 'Uploading a test file through our integration'
  });

  // 检查凭据
  const checkCredentials = async () => {
    try {
      const response = await fetch(`http://localhost:8002/api/v1/credentials/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          provider: 'slack'
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setHasCredentials(result.has_credentials);
      }
    } catch (error) {
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
        name: `Slack ${formData.action} Test`,
        description: `Test workflow for Slack ${formData.action}`,
        settings: {
          timeout: 300,
          retry_count: 3
        },
        nodes: [{
          id: 'slack_action_node',
          name: `Slack ${formData.action}`,
          type: 'EXTERNAL_ACTION_NODE',
          subtype: 'SLACK',
          parameters: {
            action: formData.action,
            channel: formData.channel,
            message: formData.message
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

  // 执行Slack节点
  const executeSlackNode = async (credentials?: any) => {
    try {
      let currentWorkflowId = workflowId;
      if (!currentWorkflowId) {
        currentWorkflowId = await createTestWorkflow();
        setWorkflowId(currentWorkflowId);
      }

      // 构建参数
      const parameters: any = {
        channel: formData.channel,
        message: formData.message
      };

      // 根据操作类型添加特定参数
      if (formData.action === 'send_message') {
        if (formData.username) parameters.username = formData.username;
        if (formData.iconEmoji) parameters.icon_emoji = formData.iconEmoji;
        if (formData.iconUrl) parameters.icon_url = formData.iconUrl;
        if (formData.threadTs) parameters.thread_ts = formData.threadTs;
      } else if (formData.action === 'upload_file') {
        parameters.channels = formData.channel;
        parameters.file_content = formData.fileContent;
        if (formData.fileName) parameters.filename = formData.fileName;
        if (formData.title) parameters.title = formData.title;
        if (formData.initialComment) parameters.initial_comment = formData.initialComment;
      } else if (formData.action === 'get_user_info') {
        parameters.user_id = formData.userId;
      }

      const requestBody: any = {
        user_id: USER_ID,
        input_data: {},
        execution_context: {
          override_parameters: parameters
        }
      };

      if (credentials) {
        requestBody.credentials = {
          slack: credentials
        };
      }

      const response = await fetch(
        `http://localhost:8002/v1/workflows/${currentWorkflowId}/nodes/slack_action_node/execute`,
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

  // Slack OAuth2授权流程
  const startOAuth2Flow = () => {
    return new Promise<string>((resolve, reject) => {
      const state = `slack_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      const authUrl = new URL('https://slack.com/oauth/v2/authorize');
      authUrl.searchParams.set('client_id', SLACK_CLIENT_ID);
      authUrl.searchParams.set('response_type', 'code');
      authUrl.searchParams.set('scope', SLACK_SCOPES);
      authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
      authUrl.searchParams.set('state', state);

      sessionStorage.setItem('oauth2_state', state);

      const popup = window.open(
        authUrl.toString(),
        'slack-oauth2',
        'width=500,height=600,scrollbars=yes,resizable=yes'
      );

      if (!popup) {
        reject(new Error('Popup blocked. Please allow popups for this site.'));
        return;
      }

      const checkClosed = setInterval(() => {
        try {
          if (popup.closed) {
            clearInterval(checkClosed);
            reject(new Error('OAuth2 authorization was cancelled'));
            return;
          }

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
        } catch (e) {
          // 忽略跨域错误
        }
      }, 1000);

      setTimeout(() => {
        if (!popup.closed) {
          popup.close();
        }
        clearInterval(checkClosed);
        reject(new Error('OAuth2 authorization timed out'));
      }, 10 * 60 * 1000);
    });
  };

  // 存储凭据
  const storeCredentials = async (authorizationCode: string) => {
    const response = await fetch('http://localhost:8002/api/v1/credentials/store', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        provider: 'slack',
        authorization_code: authorizationCode,
        client_id: SLACK_CLIENT_ID,
        redirect_uri: REDIRECT_URI
      })
    });

    if (!response.ok) {
      throw new Error('Failed to store credentials');
    }

    return await response.json();
  };

  // 主执行函数
  const handleExecuteNode = async () => {
    setIsLoading(true);
    setLastResult(null);

    try {
      toast({
        title: `执行Slack ${formData.action}`,
        description: "正在检查是否需要授权..."
      });

      let result = await executeSlackNode();

      if (result.output_data?.requires_auth || result.output_data?.error?.includes('credentials')) {
        toast({
          title: "需要授权",
          description: "正在启动Slack OAuth2授权流程...",
          variant: "default"
        });

        const authorizationCode = await startOAuth2Flow();
        
        toast({
          title: "授权成功",
          description: "正在存储凭据并重新执行节点..."
        });

        await storeCredentials(authorizationCode);

        result = await executeSlackNode({
          authorization_code: authorizationCode,
          client_id: SLACK_CLIENT_ID,
          redirect_uri: REDIRECT_URI
        });

        setHasCredentials(true);
      }

      setLastResult(result);

      if (result.status === 'COMPLETED' && result.output_data?.success !== false) {
        toast({
          title: "Slack操作成功！",
          description: `${formData.action} 操作已成功完成`,
          variant: "default"
        });
      } else {
        toast({
          title: "操作失败",
          description: result.error_message || result.output_data?.error || "Slack操作出现错误",
          variant: "destructive"
        });
      }

    } catch (error: any) {
      console.error('Execution error:', error);
      toast({
        title: "执行失败",
        description: error.message || "发生未知错误",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkCredentials();
  }, []);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <MessageSquare className="w-8 h-8" />
            Slack 集成测试
          </h1>
          <p className="text-gray-600 mt-2">
            测试Slack API集成 - 消息发送、文件上传、用户信息等功能
          </p>
        </div>
      </div>

      {/* OAuth2状态卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Slack OAuth2 授权状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            {hasCredentials ? (
              <>
                <CheckCircle className="w-5 h-5 text-green-500" />
                <span className="text-green-600 font-medium">已授权</span>
                <Badge variant="outline" className="text-green-600 border-green-200">
                  Slack 已连接
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

      {/* Slack操作表单 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hash className="w-5 h-5" />
            Slack 操作配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="action">操作类型</Label>
              <select 
                className="w-full p-2 border rounded-md"
                value={formData.action}
                onChange={(e) => setFormData({...formData, action: e.target.value as any})}
              >
                <option value="send_message">发送消息</option>
                <option value="upload_file">上传文件</option>
                <option value="get_user_info">获取用户信息</option>
                <option value="list_channels">列出频道</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="channel">频道</Label>
              <Input
                id="channel"
                value={formData.channel}
                onChange={(e) => setFormData({...formData, channel: e.target.value})}
                placeholder="#general 或频道ID"
              />
            </div>
          </div>

          {formData.action === 'send_message' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="message">消息内容</Label>
                <Textarea
                  id="message"
                  value={formData.message}
                  onChange={(e) => setFormData({...formData, message: e.target.value})}
                  placeholder="输入要发送的消息内容"
                  rows={4}
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">自定义用户名</Label>
                  <Input
                    id="username"
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    placeholder="可选"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="iconEmoji">图标Emoji</Label>
                  <Input
                    id="iconEmoji"
                    value={formData.iconEmoji}
                    onChange={(e) => setFormData({...formData, iconEmoji: e.target.value})}
                    placeholder=":robot_face:"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="threadTs">回复消息ID</Label>
                  <Input
                    id="threadTs"
                    value={formData.threadTs}
                    onChange={(e) => setFormData({...formData, threadTs: e.target.value})}
                    placeholder="可选 - 回复特定消息"
                  />
                </div>
              </div>
            </>
          )}

          {formData.action === 'upload_file' && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="fileName">文件名</Label>
                  <Input
                    id="fileName"
                    value={formData.fileName}
                    onChange={(e) => setFormData({...formData, fileName: e.target.value})}
                    placeholder="test-file.txt"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="title">文件标题</Label>
                  <Input
                    id="title"
                    value={formData.title}
                    onChange={(e) => setFormData({...formData, title: e.target.value})}
                    placeholder="文件标题"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="fileContent">文件内容</Label>
                <Textarea
                  id="fileContent"
                  value={formData.fileContent}
                  onChange={(e) => setFormData({...formData, fileContent: e.target.value})}
                  placeholder="输入文件内容"
                  rows={4}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="initialComment">初始评论</Label>
                <Input
                  id="initialComment"
                  value={formData.initialComment}
                  onChange={(e) => setFormData({...formData, initialComment: e.target.value})}
                  placeholder="可选 - 上传时的评论"
                />
              </div>
            </>
          )}

          {formData.action === 'get_user_info' && (
            <div className="space-y-2">
              <Label htmlFor="userId">用户ID</Label>
              <Input
                id="userId"
                value={formData.userId}
                onChange={(e) => setFormData({...formData, userId: e.target.value})}
                placeholder="U1234567890"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* 执行按钮 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="w-5 h-5" />
            执行 Slack 操作
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-medium text-blue-900 mb-2">🎯 智能执行流程</h3>
            <div className="text-sm text-blue-700 space-y-1">
              <p>1. 配置上方Slack操作参数</p>
              <p>2. 点击执行按钮</p>
              <p>3. 系统自动检测OAuth2授权状态</p>
              <p>4. 如需授权，自动弹出Slack授权页面</p>
              <p>5. 授权完成后自动执行Slack操作</p>
              <p>6. 您可以在Slack工作区中查看结果</p>
            </div>
          </div>

          <Button 
            onClick={handleExecuteNode}
            disabled={isLoading}
            className="w-full bg-purple-600 hover:bg-purple-700"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                执行中...
              </>
            ) : (
              <>
                <MessageSquare className="w-4 h-4 mr-2" />
                执行 Slack {formData.action}
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
                    Slack操作成功！
                  </h5>
                  
                  {lastResult.output_data?.ts && (
                    <p><strong>消息时间戳:</strong> {lastResult.output_data.ts}</p>
                  )}
                  
                  {lastResult.output_data?.channel && (
                    <p><strong>频道:</strong> {lastResult.output_data.channel}</p>
                  )}
                  
                  {lastResult.output_data?.file_url && (
                    <p>
                      <strong>文件链接:</strong> 
                      <a 
                        href={lastResult.output_data.file_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="ml-2 text-blue-600 hover:underline inline-flex items-center gap-1"
                      >
                        查看文件 <ExternalLink className="w-3 h-3" />
                      </a>
                    </p>
                  )}

                  <div className="bg-blue-50 border border-blue-200 rounded p-3 text-blue-800">
                    <p className="font-medium">🎉 验证步骤：</p>
                    <p className="text-sm mt-1">
                      1. 打开您的Slack工作区<br/>
                      2. 检查指定频道中的消息或文件<br/>
                      3. 确认操作结果是否正确
                    </p>
                  </div>
                </div>
              )}

              {/* 详细响应数据 */}
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
          <p>• <strong>消息发送</strong>: 支持发送文本消息，可自定义用户名、图标和回复特定消息</p>
          <p>• <strong>文件上传</strong>: 支持上传文本文件到指定频道，可添加标题和初始评论</p>
          <p>• <strong>用户信息</strong>: 获取指定用户的详细信息和状态</p>
          <p>• <strong>频道列表</strong>: 列出可访问的所有频道信息</p>
          <p>• <strong>智能授权</strong>: 自动检测并处理OAuth2授权流程</p>
          <p>• <strong>Block Kit支持</strong>: 可在消息中使用Slack的Block Kit格式</p>
          <p>• <strong>即时验证</strong>: 操作完成后可直接在Slack工作区中验证结果</p>
        </CardContent>
      </Card>
    </div>
  );
}