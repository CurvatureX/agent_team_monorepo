/**
 * External API Manager Component
 * 外部API集成管理主界面
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { OAuth2AuthButton } from './OAuth2AuthButton';
import { CredentialStatusCard } from './CredentialStatusCard';
import { APICallTester } from './APICallTester';
import { ExternalAPIService, CredentialInfo, ExternalAPIProvider } from './external-api-service';

interface ExternalAPIManagerProps {
  onAuthSuccess?: (provider: string) => void;
  onAuthError?: (error: string) => void;
}

const PROVIDERS: { id: ExternalAPIProvider; name: string; description: string; icon: string }[] = [
  {
    id: 'google_calendar',
    name: 'Google Calendar',
    description: '管理日历事件，创建会议和提醒',
    icon: '📅'
  },
  {
    id: 'github',
    name: 'GitHub',
    description: '管理代码仓库，Issues和Pull Requests',
    icon: '🐱'
  },
  {
    id: 'slack',
    name: 'Slack',
    description: '发送消息，管理频道和文件',
    icon: '💬'
  }
];

export const ExternalAPIManager: React.FC<ExternalAPIManagerProps> = ({
  onAuthSuccess,
  onAuthError
}) => {
  const [credentials, setCredentials] = useState<CredentialInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authInProgress, setAuthInProgress] = useState<Record<string, boolean>>({});

  // 加载用户凭证
  const loadCredentials = async () => {
    try {
      setLoading(true);
      const userCredentials = await ExternalAPIService.getUserCredentials();
      setCredentials(userCredentials);
      setError(null);
    } catch (err) {
      console.error('Failed to load credentials:', err);
      setError('加载凭证失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时加载凭证
  useEffect(() => {
    loadCredentials();
  }, []);

  // 处理授权开始
  const handleAuthStart = (provider: string) => {
    setAuthInProgress(prev => ({ ...prev, [provider]: true }));
  };

  // 处理授权完成
  const handleAuthComplete = async (provider: string, success: boolean) => {
    setAuthInProgress(prev => ({ ...prev, [provider]: false }));
    
    if (success) {
      // 重新加载凭证列表
      await loadCredentials();
      onAuthSuccess?.(provider);
    } else {
      onAuthError?.(`${provider} 授权失败`);
    }
  };

  // 处理凭证撤销
  const handleRevoke = async (provider: string) => {
    try {
      await ExternalAPIService.revokeCredential(provider as ExternalAPIProvider);
      await loadCredentials(); // 重新加载凭证列表
    } catch (err) {
      console.error('Failed to revoke credential:', err);
      setError(`撤销 ${provider} 凭证失败`);
    }
  };

  // 获取提供商的凭证信息
  const getCredentialForProvider = (providerId: string): CredentialInfo | undefined => {
    return credentials.find(cred => cred.provider === providerId);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">加载外部API集成...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">外部API集成</h1>
        <p className="text-gray-600">连接和管理您的外部服务，在工作流中使用它们</p>
      </div>

      {/* 错误提示 */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <span className="text-red-500">❌</span>
              <span className="text-red-700">{error}</span>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setError(null)}
                className="ml-auto"
              >
                关闭
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 提供商网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {PROVIDERS.map((provider) => {
          const credential = getCredentialForProvider(provider.id);
          const isAuthorized = credential?.is_valid ?? false;
          const isInProgress = authInProgress[provider.id] ?? false;

          return (
            <Card key={provider.id} className="h-full">
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{provider.icon}</span>
                  <div>
                    <CardTitle className="text-lg">{provider.name}</CardTitle>
                    <CardDescription>{provider.description}</CardDescription>
                  </div>
                </div>
                
                {/* 状态标识 */}
                <div className="mt-2">
                  {isAuthorized ? (
                    <Badge variant="default" className="bg-green-100 text-green-800">
                      ✅ 已连接
                    </Badge>
                  ) : (
                    <Badge variant="secondary">
                      🔗 未连接
                    </Badge>
                  )}
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* 授权按钮或凭证状态 */}
                {isAuthorized && credential ? (
                  <CredentialStatusCard
                    provider={provider.id}
                    credential={credential}
                    onRevoke={() => handleRevoke(provider.id)}
                  />
                ) : (
                  <OAuth2AuthButton
                    provider={provider.id as ExternalAPIProvider}
                    scopes={[]} // 使用默认scope
                    onAuthStart={() => handleAuthStart(provider.id)}
                    onAuthComplete={(success) => handleAuthComplete(provider.id, success)}
                    loading={isInProgress}
                  />
                )}

                {/* 权限范围显示 */}
                {isAuthorized && credential && credential.scope.length > 0 && (
                  <div className="text-sm">
                    <p className="font-medium text-gray-700 mb-1">授权范围:</p>
                    <div className="flex flex-wrap gap-1">
                      {credential.scope.map((scope, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {scope}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* API调用测试区域 */}
      <Card>
        <CardHeader>
          <CardTitle>API调用测试</CardTitle>
          <CardDescription>
            测试已连接的外部API，验证集成是否正常工作
          </CardDescription>
        </CardHeader>
        <CardContent>
          <APICallTester 
            availableProviders={credentials.filter(c => c.is_valid).map(c => c.provider)}
          />
        </CardContent>
      </Card>

      {/* 统计信息 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {credentials.filter(c => c.is_valid).length}
              </div>
              <p className="text-sm text-gray-600">已连接的服务</p>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {PROVIDERS.length}
              </div>
              <p className="text-sm text-gray-600">可用的集成</p>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {credentials.reduce((sum, c) => sum + c.scope.length, 0)}
              </div>
              <p className="text-sm text-gray-600">总授权权限</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};