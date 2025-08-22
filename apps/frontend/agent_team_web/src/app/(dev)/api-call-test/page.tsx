"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  Globe, 
  CheckCircle, 
  XCircle, 
  Loader2,
  Send,
  Link2,
  Database,
  Key
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const USER_ID = '7ba36345-a2bb-4ec9-a001-bb46d79d629d';

interface APICallOutput {
  status_code?: number;
  headers?: Record<string, string>;
  body?: unknown;
  error?: string;
  success?: boolean;
  method?: string;
  content_length?: number;
  url?: string;
  data?: unknown;
}

interface ExecutionResult {
  execution_id: string;
  status: string;
  output_data: APICallOutput | null;
  error_message?: string;
  logs: string[];
}

interface APICallFormData {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS';
  url: string;
  headers: string;
  queryParams: string;
  body: string;
  timeout: number;
  authentication: 'none' | 'bearer' | 'basic' | 'api_key';
  authToken: string;
  apiKeyHeader: string;
  username: string;
  password: string;
}

// 预设的API示例
const API_EXAMPLES = {
  'jsonplaceholder': {
    name: 'JSONPlaceholder (GET Posts)',
    method: 'GET' as const,
    url: 'https://jsonplaceholder.typicode.com/posts',
    headers: '{}',
    queryParams: '{"_limit": "5"}',
    body: '',
    authentication: 'none' as const
  },
  'httpbin-get': {
    name: 'HTTPBin (GET Request)',
    method: 'GET' as const,
    url: 'https://httpbin.org/get',
    headers: '{"User-Agent": "Agent-Team-Test"}',
    queryParams: '{"test": "true", "source": "agent-team"}',
    body: '',
    authentication: 'none' as const
  },
  'httpbin-post': {
    name: 'HTTPBin (POST JSON)',
    method: 'POST' as const,
    url: 'https://httpbin.org/post',
    headers: '{"Content-Type": "application/json"}',
    queryParams: '{}',
    body: '{\n  "message": "Hello from Agent Team!",\n  "timestamp": "2025-01-01T00:00:00Z",\n  "test": true\n}',
    authentication: 'none' as const
  },
  'github-api': {
    name: 'GitHub API (需要Token)',
    method: 'GET' as const,
    url: 'https://api.github.com/user',
    headers: '{}',
    queryParams: '{}',
    body: '',
    authentication: 'bearer' as const
  }
};

export default function APICallTestPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [lastResult, setLastResult] = useState<ExecutionResult | null>(null);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const { toast } = useToast();

  const [formData, setFormData] = useState<APICallFormData>({
    method: 'GET',
    url: 'https://jsonplaceholder.typicode.com/posts',
    headers: '{}',
    queryParams: '{"_limit": "5"}',
    body: '',
    timeout: 30,
    authentication: 'none',
    authToken: '',
    apiKeyHeader: 'X-API-Key',
    username: '',
    password: ''
  });

  // 加载预设示例
  const loadExample = (exampleKey: keyof typeof API_EXAMPLES) => {
    const example = API_EXAMPLES[exampleKey];
    setFormData({
      ...formData,
      method: example.method,
      url: example.url,
      headers: example.headers,
      queryParams: example.queryParams,
      body: example.body,
      authentication: example.authentication
    });
  };

  // 创建测试工作流
  const createTestWorkflow = async () => {
    const response = await fetch('http://localhost:8002/v1/workflows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        name: `API Call ${formData.method} Test`,
        description: `Test workflow for ${formData.method} ${formData.url}`,
        settings: {
          timeout: 300,
          retry_count: 3
        },
        nodes: [{
          id: 'api_call_node',
          name: `API Call ${formData.method}`,
          type: 'EXTERNAL_ACTION_NODE',
          subtype: 'API_CALL',
          parameters: {
            method: formData.method,
            url: formData.url
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

  // 执行API Call节点
  const executeAPICallNode = async () => {
    try {
      let currentWorkflowId = workflowId;
      if (!currentWorkflowId) {
        currentWorkflowId = await createTestWorkflow();
        setWorkflowId(currentWorkflowId);
      }

      // 解析JSON字段
      let headers = {};
      let queryParams = {};
      let body: unknown = null;

      try {
        headers = JSON.parse(formData.headers || '{}');
      } catch (_e) {
        throw new Error('Headers必须是有效的JSON格式');
      }

      try {
        queryParams = JSON.parse(formData.queryParams || '{}');
      } catch (_e) {
        throw new Error('Query Parameters必须是有效的JSON格式');
      }

      if (formData.body.trim()) {
        try {
          body = JSON.parse(formData.body);
        } catch (_e) {
          // 如果不是JSON，作为字符串处理
          body = formData.body;
        }
      }

      // 构建参数
      const parameters: Record<string, unknown> = {
        method: formData.method,
        url: formData.url,
        headers: headers,
        query_params: queryParams,
        timeout: formData.timeout,
        authentication: formData.authentication
      };

      if (body !== null) {
        parameters.body = body;
      }

      // 添加认证相关参数
      if (formData.authentication === 'bearer' && formData.authToken) {
        parameters.auth_token = formData.authToken;
      } else if (formData.authentication === 'api_key') {
        parameters.auth_token = formData.authToken;
        parameters.api_key_header = formData.apiKeyHeader;
      } else if (formData.authentication === 'basic') {
        parameters.username = formData.username;
        parameters.password = formData.password;
      }

      const requestBody: Record<string, unknown> = {
        user_id: USER_ID,
        input_data: {},
        execution_context: {
          override_parameters: parameters
        }
      };

      const response = await fetch(
        `http://localhost:8002/v1/workflows/${currentWorkflowId}/nodes/api_call_node/execute`,
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

  // 主执行函数
  const handleExecuteNode = async () => {
    setIsLoading(true);
    setLastResult(null);

    try {
      toast({
        title: `执行API调用`,
        description: `正在发送 ${formData.method} 请求到 ${formData.url}...`
      });

      const result = await executeAPICallNode();
      setLastResult(result);

      if (result.status === 'COMPLETED' && result.output_data?.success !== false) {
        toast({
          title: "API调用成功！",
          description: `${formData.method} 请求成功完成，状态码: ${result.output_data?.status_code}`,
          variant: "default"
        });
      } else {
        toast({
          title: "调用失败",
          description: result.error_message || result.output_data?.error || "API调用出现错误",
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

  // 格式化JSON
  const formatJSON = (field: 'headers' | 'queryParams' | 'body') => {
    try {
      const value = formData[field];
      if (value.trim()) {
        const parsed = JSON.parse(value);
        const formatted = JSON.stringify(parsed, null, 2);
        setFormData({...formData, [field]: formatted});
      }
    } catch (_e) {
      toast({
        title: "JSON格式错误",
        description: `${field} 不是有效的JSON格式`,
        variant: "destructive"
      });
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Globe className="w-8 h-8" />
            Generic API Call 集成测试
          </h1>
          <p className="text-gray-600 mt-2">
            测试通用HTTP API调用 - 支持各种HTTP方法、认证方式和数据格式
          </p>
        </div>
      </div>

      {/* 预设示例 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            快速示例
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(API_EXAMPLES).map(([key, example]) => (
              <Button
                key={key}
                variant="outline"
                size="sm"
                onClick={() => loadExample(key as keyof typeof API_EXAMPLES)}
                className="text-left h-auto p-3"
              >
                <div>
                  <div className="font-medium text-sm">{example.name}</div>
                  <div className="text-xs text-gray-500">{example.method} {new URL(example.url).hostname}</div>
                </div>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* HTTP请求配置 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="w-5 h-5" />
            HTTP请求配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="method">HTTP方法 *</Label>
              <select 
                className="w-full p-2 border rounded-md"
                value={formData.method}
                onChange={(e) => setFormData({...formData, method: e.target.value as any})}
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
                <option value="PATCH">PATCH</option>
                <option value="HEAD">HEAD</option>
                <option value="OPTIONS">OPTIONS</option>
              </select>
            </div>
            <div className="md:col-span-2 space-y-2">
              <Label htmlFor="url">请求URL *</Label>
              <Input
                id="url"
                value={formData.url}
                onChange={(e) => setFormData({...formData, url: e.target.value})}
                placeholder="https://api.example.com/endpoint"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeout">超时时间(秒)</Label>
              <Input
                id="timeout"
                type="number"
                value={formData.timeout}
                onChange={(e) => setFormData({...formData, timeout: parseInt(e.target.value) || 30})}
                placeholder="30"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="headers">HTTP Headers (JSON)</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => formatJSON('headers')}
                >
                  格式化
                </Button>
              </div>
              <Textarea
                id="headers"
                value={formData.headers}
                onChange={(e) => setFormData({...formData, headers: e.target.value})}
                placeholder='{"Content-Type": "application/json"}'
                rows={4}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="queryParams">Query Parameters (JSON)</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => formatJSON('queryParams')}
                >
                  格式化
                </Button>
              </div>
              <Textarea
                id="queryParams"
                value={formData.queryParams}
                onChange={(e) => setFormData({...formData, queryParams: e.target.value})}
                placeholder='{"param1": "value1", "param2": "value2"}'
                rows={4}
              />
            </div>
          </div>

          {(formData.method === 'POST' || formData.method === 'PUT' || formData.method === 'PATCH') && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="body">请求体 (JSON或字符串)</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => formatJSON('body')}
                >
                  格式化JSON
                </Button>
              </div>
              <Textarea
                id="body"
                value={formData.body}
                onChange={(e) => setFormData({...formData, body: e.target.value})}
                placeholder='{"key": "value", "message": "Hello World"}'
                rows={6}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* 认证配置 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="w-5 h-5" />
            认证配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="authentication">认证方式</Label>
            <select 
              className="w-full p-2 border rounded-md"
              value={formData.authentication}
              onChange={(e) => setFormData({...formData, authentication: e.target.value as any})}
            >
              <option value="none">无认证</option>
              <option value="bearer">Bearer Token</option>
              <option value="basic">Basic Auth</option>
              <option value="api_key">API Key</option>
            </select>
          </div>

          {formData.authentication === 'bearer' && (
            <div className="space-y-2">
              <Label htmlFor="authToken">Bearer Token</Label>
              <Input
                id="authToken"
                type="password"
                value={formData.authToken}
                onChange={(e) => setFormData({...formData, authToken: e.target.value})}
                placeholder="输入Bearer Token"
              />
            </div>
          )}

          {formData.authentication === 'basic' && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="username">用户名</Label>
                <Input
                  id="username"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  placeholder="username"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  placeholder="password"
                />
              </div>
            </div>
          )}

          {formData.authentication === 'api_key' && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="apiKeyHeader">API Key Header</Label>
                <Input
                  id="apiKeyHeader"
                  value={formData.apiKeyHeader}
                  onChange={(e) => setFormData({...formData, apiKeyHeader: e.target.value})}
                  placeholder="X-API-Key"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="authToken">API Key Value</Label>
                <Input
                  id="authToken"
                  type="password"
                  value={formData.authToken}
                  onChange={(e) => setFormData({...formData, authToken: e.target.value})}
                  placeholder="输入API Key"
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
            <Send className="w-5 h-5" />
            执行 API 调用
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <h3 className="font-medium text-orange-900 mb-2">🚀 API调用流程</h3>
            <div className="text-sm text-orange-700 space-y-1">
              <p>1. 配置HTTP方法和目标URL</p>
              <p>2. 设置请求头和查询参数（JSON格式）</p>
              <p>3. 如需要，配置请求体数据</p>
              <p>4. 选择合适的认证方式</p>
              <p>5. 点击执行按钮发送请求</p>
              <p>6. 查看响应状态码和返回数据</p>
            </div>
          </div>

          <Button 
            onClick={handleExecuteNode}
            disabled={isLoading}
            className="w-full bg-orange-600 hover:bg-orange-700"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                调用中...
              </>
            ) : (
              <>
                <Globe className="w-4 h-4 mr-2" />
                执行 {formData.method} 请求
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
              {lastResult.status === 'COMPLETED' && lastResult.output_data && lastResult.output_data?.success !== false && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-3">
                  <h5 className="font-medium text-green-800 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    API调用成功！
                  </h5>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <p><strong>状态码:</strong> 
                        <Badge variant={(lastResult.output_data.status_code ?? 0) < 300 ? 'default' : 'destructive'} className="ml-2">
                          {lastResult.output_data.status_code}
                        </Badge>
                      </p>
                    </div>
                    <div>
                      <p><strong>请求方法:</strong> {lastResult.output_data.method}</p>
                    </div>
                    <div>
                      <p><strong>响应大小:</strong> {lastResult.output_data.content_length} bytes</p>
                    </div>
                  </div>
                  
                  <div>
                    <p><strong>请求URL:</strong></p>
                    <code className="text-xs bg-gray-100 p-1 rounded break-all">{lastResult.output_data.url}</code>
                  </div>

                  {lastResult.output_data.data !== undefined && (
                    <div>
                      <p><strong>响应数据预览:</strong></p>
                      <div className="bg-gray-50 border rounded p-3 max-h-40 overflow-auto">
                        <pre className="text-xs">
                          {typeof lastResult.output_data.data === 'object' 
                            ? JSON.stringify(lastResult.output_data.data, null, 2) 
                            : String(lastResult.output_data.data)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 详细响应数据 */}
              <details className="bg-gray-50 rounded-lg">
                <summary className="cursor-pointer p-3 font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
                  查看完整响应数据
                </summary>
                <div className="p-3 pt-0">
                  <div className="space-y-3">
                    {/* 响应头 */}
                    {lastResult.output_data && lastResult.output_data.headers && (
                      <div>
                        <h6 className="font-medium mb-2">响应头:</h6>
                        <pre className="text-xs overflow-auto bg-white p-3 rounded border max-h-32">
                          {JSON.stringify(lastResult.output_data.headers, null, 2)}
                        </pre>
                      </div>
                    )}
                    
                    {/* 完整响应 */}
                    <div>
                      <h6 className="font-medium mb-2">完整响应:</h6>
                      <pre className="text-xs overflow-auto bg-white p-3 rounded border max-h-80">
                        {JSON.stringify(lastResult.output_data, null, 2)}
                      </pre>
                    </div>
                  </div>
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
          <p>• <strong>HTTP方法</strong>: 支持所有标准HTTP方法，根据API接口要求选择</p>
          <p>• <strong>JSON格式</strong>: Headers、Query Parameters和Body都支持JSON格式</p>
          <p>• <strong>认证方式</strong>: 支持Bearer Token、Basic Auth、API Key等常见认证</p>
          <p>• <strong>预设示例</strong>: 提供了多个公开API的测试示例，可快速上手</p>
          <p>• <strong>响应解析</strong>: 自动解析JSON响应，同时保留原始文本</p>
          <p>• <strong>错误处理</strong>: 完整的HTTP状态码处理和错误信息展示</p>
          <p>• <strong>安全性</strong>: 敏感信息（Token、密码）会被安全处理</p>
        </CardContent>
      </Card>
    </div>
  );
}