/**
 * API Call Tester Component
 * API调用测试组件，用于验证外部API集成
 */

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalAPIService, TestAPICallRequest, TestAPICallResponse } from './external-api-service';

interface APICallTesterProps {
  availableProviders: string[];
}

// 预定义的测试用例
const TEST_CASES = {
  google_calendar: [
    {
      name: '获取日历事件列表',
      operation: 'list_events',
      parameters: {
        calendar_id: 'primary',
        time_min: new Date().toISOString(),
        time_max: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 未来7天
        max_results: 10
      }
    },
    {
      name: '创建测试事件',
      operation: 'create_event',
      parameters: {
        calendar_id: 'primary',
        event: {
          summary: '测试会议 - API集成验证',
          description: '这是一个由API集成系统创建的测试事件',
          start: {
            dateTime: new Date(Date.now() + 60 * 60 * 1000).toISOString() // 1小时后
          },
          end: {
            dateTime: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString() // 2小时后
          }
        }
      }
    }
  ],
  github: [
    {
      name: '获取用户仓库',
      operation: 'list_repos',
      parameters: {
        type: 'owner',
        sort: 'updated',
        per_page: 5
      }
    },
    {
      name: '创建测试Issue',
      operation: 'create_issue',
      parameters: {
        owner: 'YOUR_USERNAME', // 需要用户替换
        repo: 'YOUR_REPOSITORY', // 需要用户替换
        issue: {
          title: 'API集成测试 Issue',
          body: '这是通过API集成系统创建的测试Issue',
          labels: ['test', 'api-integration']
        }
      }
    }
  ],
  slack: [
    {
      name: '获取频道列表',
      operation: 'list_channels',
      parameters: {
        types: 'public_channel,private_channel',
        limit: 10
      }
    },
    {
      name: '发送测试消息',
      operation: 'send_message',
      parameters: {
        channel: '#general', // 需要用户替换为实际频道
        message: {
          text: '🤖 API集成测试消息',
          blocks: [
            {
              type: 'section',
              text: {
                type: 'mrkdwn',
                text: '*API集成测试* ✅\n\n外部API集成系统正常工作！'
              }
            }
          ]
        }
      }
    }
  ]
};

export const APICallTester: React.FC<APICallTesterProps> = ({
  availableProviders
}) => {
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedTest, setSelectedTest] = useState<number>(0);
  const [customParameters, setCustomParameters] = useState<string>('');
  const [testResults, setTestResults] = useState<TestAPICallResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // 获取当前选中提供商的测试用例
  const getCurrentTestCases = () => {
    if (!selectedProvider || !(selectedProvider in TEST_CASES)) {
      return [];
    }
    return TEST_CASES[selectedProvider as keyof typeof TEST_CASES] || [];
  };

  // 执行API测试
  const runTest = async () => {
    if (!selectedProvider) {
      alert('请先选择一个API提供商');
      return;
    }

    const testCases = getCurrentTestCases();
    if (testCases.length === 0) {
      alert('该提供商暂无可用的测试用例');
      return;
    }

    const testCase = testCases[selectedTest];
    if (!testCase) {
      alert('请选择一个有效的测试用例');
      return;
    }

    setIsLoading(true);
    
    try {
      // 准备测试请求
      let parameters = testCase.parameters;
      
      // 如果有自定义参数，尝试解析并合并
      if (customParameters.trim()) {
        try {
          const customParams = JSON.parse(customParameters);
          parameters = { ...parameters, ...customParams };
        } catch (error) {
          console.warn('Custom parameters parsing failed, using default:', error);
        }
      }

      const testRequest: TestAPICallRequest = {
        provider: selectedProvider as any,
        operation: testCase.operation,
        parameters: parameters
      };

      // 执行测试调用
      const response = await ExternalAPIService.testAPICall(testRequest);
      
      // 将结果添加到测试历史
      setTestResults(prev => [{
        ...response,
        timestamp: new Date().toISOString(),
        testName: testCase.name
      } as any, ...prev.slice(0, 9)]); // 保留最近10次测试结果

    } catch (error) {
      console.error('API test failed:', error);
      
      // 添加错误结果到历史
      setTestResults(prev => [{
        success: false,
        data: {},
        error: error instanceof Error ? error.message : '未知错误',
        execution_time_ms: 0,
        timestamp: new Date().toISOString(),
        testName: testCase.name
      } as any, ...prev.slice(0, 9)]);
      
    } finally {
      setIsLoading(false);
    }
  };

  // 格式化JSON显示
  const formatJSON = (obj: any): string => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  };

  const currentTestCases = getCurrentTestCases();

  return (
    <div className="space-y-6">
      {/* 测试配置 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 提供商选择 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            选择API提供商
          </label>
          <select
            value={selectedProvider}
            onChange={(e) => {
              setSelectedProvider(e.target.value);
              setSelectedTest(0);
              setCustomParameters('');
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">请选择提供商</option>
            {availableProviders.map(provider => (
              <option key={provider} value={provider}>
                {provider === 'google_calendar' ? 'Google Calendar' : 
                 provider === 'github' ? 'GitHub' : 
                 provider === 'slack' ? 'Slack' : provider}
              </option>
            ))}
          </select>
        </div>

        {/* 测试用例选择 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            选择测试用例
          </label>
          <select
            value={selectedTest}
            onChange={(e) => setSelectedTest(Number(e.target.value))}
            disabled={!selectedProvider || currentTestCases.length === 0}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          >
            {currentTestCases.map((testCase, index) => (
              <option key={index} value={index}>
                {testCase.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 测试参数 */}
      {selectedProvider && currentTestCases.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            测试参数 (JSON格式)
          </label>
          <div className="space-y-2">
            {/* 默认参数显示 */}
            <div className="bg-gray-50 p-3 rounded border">
              <p className="text-sm text-gray-600 mb-1">默认参数:</p>
              <pre className="text-xs bg-white p-2 rounded border overflow-x-auto">
                {formatJSON(currentTestCases[selectedTest]?.parameters)}
              </pre>
            </div>
            
            {/* 自定义参数输入 */}
            <textarea
              value={customParameters}
              onChange={(e) => setCustomParameters(e.target.value)}
              placeholder="输入自定义参数 (JSON格式) 来覆盖默认参数..."
              className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      )}

      {/* 执行测试按钮 */}
      <div>
        <Button
          onClick={runTest}
          disabled={!selectedProvider || currentTestCases.length === 0 || isLoading}
          className="w-full md:w-auto"
        >
          {isLoading ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
              <span>测试执行中...</span>
            </div>
          ) : (
            '🧪 执行API测试'
          )}
        </Button>
      </div>

      {/* 测试结果 */}
      {testResults.length > 0 && (
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-4">测试结果历史</h3>
          <div className="space-y-4">
            {testResults.map((result, index) => (
              <Card key={index} className={`border-l-4 ${
                result.success ? 'border-l-green-500 bg-green-50' : 'border-l-red-500 bg-red-50'
              }`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">
                      {(result as any).testName || '未知测试'}
                    </CardTitle>
                    <div className="flex items-center space-x-2">
                      <Badge variant={result.success ? 'default' : 'destructive'}>
                        {result.success ? '✅ 成功' : '❌ 失败'}
                      </Badge>
                      <span className="text-sm text-gray-500">
                        {result.execution_time_ms}ms
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    {new Date((result as any).timestamp).toLocaleString('zh-CN')}
                  </p>
                </CardHeader>
                <CardContent>
                  {result.success ? (
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-2">响应数据:</p>
                      <pre className="text-xs bg-white p-3 rounded border overflow-x-auto max-h-64">
                        {formatJSON(result.data)}
                      </pre>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-medium text-red-700 mb-2">错误信息:</p>
                      <div className="bg-red-100 p-3 rounded border text-sm text-red-800">
                        {result.error || '未知错误'}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* 使用说明 */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h4 className="font-medium text-blue-900 mb-2">💡 使用说明</h4>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• 选择已连接的API提供商和测试用例</li>
            <li>• 可以通过自定义参数覆盖默认设置</li>
            <li>• GitHub测试需要替换YOUR_USERNAME和YOUR_REPOSITORY</li>
            <li>• Slack测试需要替换#general为实际的频道名</li>
            <li>• 测试结果会显示API调用的实际响应数据</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};