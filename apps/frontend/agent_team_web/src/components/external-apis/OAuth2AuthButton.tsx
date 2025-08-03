/**
 * OAuth2 Authorization Button Component
 * OAuth2授权按钮，处理授权流程
 */

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { ExternalAPIService, ExternalAPIProvider } from './external-api-service';

interface OAuth2AuthButtonProps {
  provider: ExternalAPIProvider;
  scopes: string[];
  onAuthStart: () => void;
  onAuthComplete: (success: boolean) => void;
  loading?: boolean;
  className?: string;
}

export const OAuth2AuthButton: React.FC<OAuth2AuthButtonProps> = ({
  provider,
  scopes,
  onAuthStart,
  onAuthComplete,
  loading = false,
  className = ""
}) => {
  const [isAuthorizing, setIsAuthorizing] = useState(false);

  // 获取提供商的显示名称
  const getProviderDisplayName = (provider: ExternalAPIProvider): string => {
    const names = {
      google_calendar: 'Google Calendar',
      github: 'GitHub',
      slack: 'Slack'
    };
    return names[provider] || provider;
  };

  // 启动OAuth2授权流程
  const handleAuthorization = async () => {
    try {
      setIsAuthorizing(true);
      onAuthStart();

      // 调用API获取授权URL
      const authResponse = await ExternalAPIService.startAuthorization(provider, scopes);
      
      // 在新窗口中打开授权页面
      const authWindow = window.open(
        authResponse.auth_url,
        'oauth2_authorization',
        'width=600,height=700,scrollbars=yes,resizable=yes'
      );

      if (!authWindow) {
        throw new Error('无法打开授权窗口，请检查浏览器弹窗设置');
      }

      // 监听授权窗口关闭或消息
      const checkClosed = () => {
        const timer = setInterval(() => {
          if (authWindow.closed) {
            clearInterval(timer);
            setIsAuthorizing(false);
            // 假设用户关闭窗口意味着取消授权
            onAuthComplete(false);
          }
        }, 1000);

        // 监听来自授权窗口的消息
        const messageHandler = (event: MessageEvent) => {
          // 验证消息来源（生产环境中应该检查origin）
          if (event.data && event.data.type === 'oauth2_callback') {
            clearInterval(timer);
            authWindow.close();
            window.removeEventListener('message', messageHandler);
            
            setIsAuthorizing(false);
            
            if (event.data.success) {
              onAuthComplete(true);
            } else {
              console.error('OAuth2 authorization failed:', event.data.error);
              onAuthComplete(false);
            }
          }
        };

        window.addEventListener('message', messageHandler);
        
        // 设置超时，避免无限等待
        setTimeout(() => {
          if (!authWindow.closed) {
            authWindow.close();
            clearInterval(timer);
            window.removeEventListener('message', messageHandler);
            setIsAuthorizing(false);
            onAuthComplete(false);
          }
        }, 300000); // 5分钟超时
      };

      checkClosed();

    } catch (error) {
      console.error('Failed to start OAuth2 authorization:', error);
      setIsAuthorizing(false);
      onAuthComplete(false);
      
      // 显示错误提示
      alert(`授权失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const isLoading = loading || isAuthorizing;

  return (
    <Button
      onClick={handleAuthorization}
      disabled={isLoading}
      className={`w-full ${className}`}
      variant="default"
    >
      {isLoading ? (
        <div className="flex items-center space-x-2">
          <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
          <span>授权中...</span>
        </div>
      ) : (
        <div className="flex items-center space-x-2">
          <span>🔗</span>
          <span>连接 {getProviderDisplayName(provider)}</span>
        </div>
      )}
    </Button>
  );
};