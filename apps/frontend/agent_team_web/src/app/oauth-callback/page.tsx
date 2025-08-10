"use client";

import React, { useEffect } from 'react';

export default function OAuth2CallbackPage() {
  useEffect(() => {
    // 这个页面只是为了处理OAuth2回调
    // 实际的处理逻辑在弹窗检测中完成
    console.log('OAuth2 callback page loaded');
    
    // 检查URL参数
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const error = urlParams.get('error');
    // const state = urlParams.get('state');
    
    if (code) {
      console.log('Authorization code received:', code);
    } else if (error) {
      console.error('OAuth2 error:', error);
    }
  }, []);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">OAuth2 授权处理中...</h1>
        <p className="text-gray-600">请稍等，正在处理授权结果...</p>
        <script dangerouslySetInnerHTML={{
          __html: `
            // 自动关闭弹窗（如果是弹窗）
            if (window.opener) {
              console.log('Closing OAuth2 popup...');
              setTimeout(() => window.close(), 1000);
            }
          `
        }} />
      </div>
    </div>
  );
}