
"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  Github, 
  Play, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader2,
  Shield,
  ExternalLink,
  GitBranch,
  FileText,
  MessageSquare
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

// GitHub OAuth2 配置
const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || '';
const GITHUB_SCOPES = 'repo user';
const REDIRECT_URI = 'http://localhost:3000/oauth-callback';
const USER_ID = '7ba36345-a2bb-4ec9-a001-bb46d79d629d';

interface ExecutionResult {
  execution_id: string;
  status: string;
  output_data: any;
  error_message?: string;
  logs: string[];
}

interface GitHubFormData {
  action: 'create_issue' | 'create_pull_request' | 'add_comment' | 'list_issues' | 'get_issue';
  repository: string;
  title: string;
  body: string;
  issueNumber: string;
  head: string;
  base: string;
  labels: string;
  assignees: string;
}

export default function GitHubTestPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [hasCredentials, setHasCredentials] = useState(false);
  const [lastResult, setLastResult] = useState<ExecutionResult | null>(null);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const { toast } = useToast();

  const [formData, setFormData] = useState<GitHubFormData>({
    action: 'create_issue',
    repository: 'username/repository',
    title: 'Test Issue from Agent Team',
    body: 'This is a test issue created through our external API integration system',
    issueNumber: '1',
    head: 'feature-branch',
    base: 'main',
    labels: 'bug,enhancement',
    assignees: 'username'
  });

  // 检查凭据
  const checkCredentials = async () => {
    try {
      const response = await fetch(`http://localhost:8002/api/v1/credentials/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          provider: 'github'
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
        name: `GitHub ${formData.action} Test`,
        description: `Test workflow for GitHub ${formData.action}`,
        settings: {
          timeout: 300,
          retry_count: 3
        },
        nodes: [{
          id: 'github_action_node',
          name: `GitHub ${formData.action}`,
          type: 'EXTERNAL_ACTION_NODE',
          subtype: 'GITHUB',
          parameters: {
            action: formData.action,
            repository: formData.repository,
            title: formData.title,
            body: formData.body
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

  // 执行GitHub节点
  const executeGitHubNode = async (credentials?: Record<string, unknown>) => {
    try {
      let currentWorkflowId = workflowId;
      if (!currentWorkflowId) {
        currentWorkflowId = await createTestWorkflow();
        setWorkflowId(currentWorkflowId);
      }

      // 构建参数
      const parameters: Record<string, unknown> = {
        action: formData.action,
        repository: formData.repository
      };

      // 根据操作类型添加特定参数
      if (formData.action === 'create_issue') {
        parameters.title = formData.title;
        parameters.body = formData.body;
        if (formData.labels) {
          parameters.labels = formData.labels.split(',').map(l => l.trim());
        }
        if (formData.assignees) {
          parameters.assignees = formData.assignees.split(',').map(a => a.trim());
        }
      } else if (formData.action === 'create_pull_request') {
        parameters.title = formData.title;
        parameters.body = formData.body;
        parameters.head = formData.head;
        parameters.base = formData.base;
      } else if (formData.action === 'add_comment') {
        parameters.issue_number = parseInt(formData.issueNumber);
        parameters.body = formData.body;
      } else if (formData.action === 'get_issue') {
        parameters.issue_number = parseInt(formData.issueNumber);
      }

      const requestBody: Record<string, unknown> = {
        user_id: USER_ID,
        input_data: {},
        execution_context: {
          override_parameters: parameters
        }
      };

      if (credentials) {
        requestBody.credentials = {
          github: credentials
        };
      }

      const response = await fetch(
        `http://localhost:8002/v1/workflows/${currentWorkflowId}/nodes/github_action_node/execute`,
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

  // GitHub OAuth2授权流程
  const startOAuth2Flow = () => {
    return new Promise<string>((resolve, reject) => {
      const state = `github_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      const authUrl = new URL('https://github.com/login/oauth/authorize');
      authUrl.searchParams.set('client_id', GITHUB_CLIENT_ID);
      authUrl.searchParams.set('response_type', 'code');
      authUrl.searchParams.set('scope', GITHUB_SCOPES);
      authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
      authUrl.searchParams.set('state', state);

      sessionStorage.setItem('oauth2_state', state);

      const popup = window.open(
        authUrl.toString(),
        'github-oauth2',
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
        } catch (_e) {
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
        provider: 'github',
        authorization_code: authorizationCode,
        client_id: GITHUB_CLIENT_ID,
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
        title: `执行GitHub ${formData.action}`,
        description: "正在检查是否需要授权..."
      });

      let result = await executeGitHubNode();

      if (result.output_data?.requires_auth || result.output_data?.error?.includes('credentials')) {
        toast({
          title: "需要授权",
          description: "正在启动GitHub OAuth2授权流程...",
          variant: "default"
        });

        const authorizationCode = await startOAuth2Flow();
        
        toast({
          title: "授权成功",
          description: "正在存储凭据并重新执行节点..."
        });

        await storeCredentials(authorizationCode);

        result = await executeGitHubNode({
          authorization_code: authorizationCode,
          client_id: GITHUB_CLIENT_ID,
          redirect_uri: REDIRECT_URI
        });

        setHasCredentials(true);
      }

      setLastResult(result);

      if (result.status === 'COMPLETED' && result.output_data?.success !== false) {
        toast({
          title: "GitHub操作成功！",
          description: `${formData.action} 操作已成功完成`,
          variant: "default"
        });
      } else {
        toast({
          title: "操作失败",
          description: result.error_message || result.output_data?.error || "GitHub操作出现错误",
          variant: "destructive"
        });
      }

    } catch (error) {
      console.error('Execution error:', error);
      const errorMessage = error instanceof Error ? error.message : "发生未知错误";
      toast({
        title: "执行失败",
        description: errorMessage,
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
            <Github className="w-8 h-8" />
            GitHub 集成测试
          </h1>
          <p className="text-gray-600 mt-2">
            测试GitHub API集成 - Issues, Pull Requests, Comments
          </p>
        </div>
      </div>

      {/* OAuth2状态卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            GitHub OAuth2 授权状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            {hasCredentials ? (
              <>
                <CheckCircle className="w-5 h-5 text-green-500" />
                <span className="text-green-600 font-medium">已授权</span>
                <Badge variant="outline" className="text-green-600 border-green-200">
                  GitHub 已连接
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

      {/* GitHub操作表单 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="w-5 h-5" />
            GitHub 操作配置
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
                <option value="create_issue">创建 Issue</option>
                <option value="create_pull_request">创建 Pull Request</option>
                <option value="add_comment">添加评论</option>
                <option value="list_issues">列出 Issues</option>
                <option value="get_issue">获取 Issue</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="repository">仓库 (owner/repo)</Label>
              <Input
                id="repository"
                value={formData.repository}
                onChange={(e) => setFormData({...formData, repository: e.target.value})}
                placeholder="例: octocat/Hello-World"
              />
            </div>
          </div>

          {(formData.action === 'create_issue' || formData.action === 'create_pull_request') && (
            <>
              <div className="space-y-2">
                <Label htmlFor="title">标题</Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  placeholder="输入标题"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="body">内容</Label>
                <Textarea
                  id="body"
                  value={formData.body}
                  onChange={(e) => setFormData({...formData, body: e.target.value})}
                  placeholder="输入详细内容"
                  rows={3}
                />
              </div>
            </>
          )}

          {formData.action === 'create_pull_request' && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="head">Head分支</Label>
                <Input
                  id="head"
                  value={formData.head}
                  onChange={(e) => setFormData({...formData, head: e.target.value})}
                  placeholder="feature-branch"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="base">Base分支</Label>
                <Input
                  id="base"
                  value={formData.base}
                  onChange={(e) => setFormData({...formData, base: e.target.value})}
                  placeholder="main"
                />
              </div>
            </div>
          )}

          {(formData.action === 'add_comment' || formData.action === 'get_issue') && (
            <div className="space-y-2">
              <Label htmlFor="issueNumber">Issue编号</Label>
              <Input
                id="issueNumber"
                value={formData.issueNumber}
                onChange={(e) => setFormData({...formData, issueNumber: e.target.value})}
                placeholder="1"
                type="number"
              />
            </div>
          )}

          {formData.action === 'add_comment' && (
            <div className="space-y-2">
              <Label htmlFor="commentBody">评论内容</Label>
              <Textarea
                id="commentBody"
                value={formData.body}
                onChange={(e) => setFormData({...formData, body: e.target.value})}
                placeholder="输入评论内容"
                rows={3}
              />
            </div>
          )}

          {formData.action === 'create_issue' && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="labels">标签 (逗号分隔)</Label>
                <Input
                  id="labels"
                  value={formData.labels}
                  onChange={(e) => setFormData({...formData, labels: e.target.value})}
                  placeholder="bug,enhancement"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="assignees">指派人 (逗号分隔)</Label>
                <Input
                  id="assignees"
                  value={formData.assignees}
                  onChange={(e) => setFormData({...formData, assignees: e.target.value})}
                  placeholder="username"
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 执行按钮 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="w-5 h-5" />
            执行 GitHub 操作
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
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
                <Github className="w-4 h-4 mr-2" />
                执行 {formData.action}
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
                    GitHub操作成功！
                  </h5>
                  
                  {lastResult.output_data?.url && (
                    <p>
                      <strong>GitHub链接:</strong> 
                      <a 
                        href={lastResult.output_data.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="ml-2 text-blue-600 hover:underline inline-flex items-center gap-1"
                      >
                        查看结果 <ExternalLink className="w-3 h-3" />
                      </a>
                    </p>
                  )}
                  
                  {lastResult.output_data?.issue_number && (
                    <p><strong>Issue/PR 编号:</strong> #{lastResult.output_data.issue_number}</p>
                  )}
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
    </div>
  );
}