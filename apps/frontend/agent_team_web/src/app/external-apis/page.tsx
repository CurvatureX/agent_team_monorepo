/**
 * External APIs Integration Page
 * 外部API集成管理页面
 */

'use client';

import React from 'react';
import { ExternalAPIManager } from '@/components/external-apis/ExternalAPIManager';

export default function ExternalAPIsPage() {
  const handleAuthSuccess = (provider: string) => {
    console.log(`Successfully connected to ${provider}`);
    // 可以在这里显示成功通知
    // 例如: toast.success(`Successfully connected to ${provider}!`);
  };

  const handleAuthError = (error: string) => {
    console.error('Authentication error:', error);
    // 可以在这里显示错误通知
    // 例如: toast.error(error);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 页面容器 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ExternalAPIManager
          onAuthSuccess={handleAuthSuccess}
          onAuthError={handleAuthError}
        />
      </div>
    </div>
  );
}