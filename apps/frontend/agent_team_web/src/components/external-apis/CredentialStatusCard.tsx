/**
 * Credential Status Card Component
 * 凭证状态显示卡片
 */

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { CredentialInfo } from './external-api-service';

interface CredentialStatusCardProps {
  provider: string;
  credential: CredentialInfo;
  onRevoke: () => void;
  className?: string;
}

export const CredentialStatusCard: React.FC<CredentialStatusCardProps> = ({
  provider,
  credential,
  onRevoke,
  className = ""
}) => {
  const [isRevoking, setIsRevoking] = useState(false);

  // 格式化日期显示
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '未知时间';
    }
  };

  // 计算过期状态
  const getExpirationStatus = () => {
    if (!credential.expires_at) {
      return { status: 'no_expiry', message: '永久有效', color: 'green' };
    }

    const expiresAt = new Date(credential.expires_at);
    const now = new Date();
    const timeDiff = expiresAt.getTime() - now.getTime();
    const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));

    if (timeDiff <= 0) {
      return { status: 'expired', message: '已过期', color: 'red' };
    } else if (daysDiff <= 7) {
      return { status: 'expiring_soon', message: `${daysDiff}天后过期`, color: 'yellow' };
    } else {
      return { status: 'valid', message: `${daysDiff}天后过期`, color: 'green' };
    }
  };

  // 处理撤销确认
  const handleRevoke = async () => {
    const confirmed = window.confirm(
      `确定要撤销 ${provider} 的访问权限吗？\n\n撤销后，相关的工作流将无法访问此服务，直到重新授权。`
    );

    if (confirmed) {
      setIsRevoking(true);
      try {
        await onRevoke();
      } catch (error) {
        console.error('Failed to revoke credential:', error);
      } finally {
        setIsRevoking(false);
      }
    }
  };

  const expirationInfo = getExpirationStatus();

  return (
    <Card className={`border-l-4 ${
      credential.is_valid 
        ? 'border-l-green-500 bg-green-50' 
        : 'border-l-red-500 bg-red-50'
    } ${className}`}>
      <CardContent className="pt-4 space-y-3">
        {/* 连接状态 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className={`text-lg ${credential.is_valid ? '✅' : '❌'}`}>
              {credential.is_valid ? '✅' : '❌'}
            </span>
            <span className="font-medium">
              {credential.is_valid ? '连接正常' : '连接异常'}
            </span>
          </div>
          
          {/* 过期状态标识 */}
          <Badge 
            variant="outline" 
            className={`
              ${expirationInfo.color === 'green' ? 'border-green-500 text-green-700' : ''}
              ${expirationInfo.color === 'yellow' ? 'border-yellow-500 text-yellow-700' : ''}
              ${expirationInfo.color === 'red' ? 'border-red-500 text-red-700' : ''}
            `}
          >
            {expirationInfo.message}
          </Badge>
        </div>

        {/* 详细信息 */}
        <div className="text-sm text-gray-600 space-y-1">
          <div className="flex justify-between">
            <span>创建时间:</span>
            <span>{formatDate(credential.created_at)}</span>
          </div>
          
          <div className="flex justify-between">
            <span>更新时间:</span>
            <span>{formatDate(credential.updated_at)}</span>
          </div>
          
          {credential.last_used_at && (
            <div className="flex justify-between">
              <span>最后使用:</span>
              <span>{formatDate(credential.last_used_at)}</span>
            </div>
          )}

          {credential.expires_at && (
            <div className="flex justify-between">
              <span>过期时间:</span>
              <span>{formatDate(credential.expires_at)}</span>
            </div>
          )}
        </div>

        {/* 权限范围 */}
        {credential.scope && credential.scope.length > 0 && (
          <div className="text-sm">
            <p className="font-medium text-gray-700 mb-1">授权权限:</p>
            <div className="flex flex-wrap gap-1">
              {credential.scope.map((scope, index) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  {scope}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex space-x-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRevoke}
            disabled={isRevoking}
            className="flex-1 text-red-600 border-red-200 hover:bg-red-50"
          >
            {isRevoking ? (
              <div className="flex items-center space-x-1">
                <div className="animate-spin h-3 w-3 border-2 border-red-600 border-t-transparent rounded-full"></div>
                <span>撤销中...</span>
              </div>
            ) : (
              '撤销授权'
            )}
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => {
              // TODO: 实现刷新令牌功能
              alert('令牌刷新功能将在后续版本中实现');
            }}
          >
            刷新令牌
          </Button>
        </div>

        {/* 警告信息 */}
        {!credential.is_valid && (
          <div className="bg-red-100 border border-red-200 rounded p-2 text-sm text-red-700">
            <strong>⚠️ 连接异常:</strong> 
            <br />
            此服务的连接可能已失效，请尝试重新授权以恢复功能。
          </div>
        )}
      </CardContent>
    </Card>
  );
};