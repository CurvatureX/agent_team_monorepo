"use client";

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle, XCircle, Loader2, ArrowLeft } from 'lucide-react';

const AuthCallbackPage: React.FC = () => {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [provider, setProvider] = useState('');

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const providerParam = searchParams.get('provider');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      setProvider(providerParam || 'unknown');

      // Handle OAuth errors
      if (error) {
        setStatus('error');
        setMessage(errorDescription || error);
        return;
      }

      // Validate required parameters
      if (!code || !state) {
        setStatus('error');
        setMessage('Missing required OAuth parameters');
        return;
      }

      // For MVP: verify state matches what we stored
      const storedState = localStorage.getItem('oauth_state');
      const storedProvider = localStorage.getItem('oauth_provider');
      
      if (!storedState || storedState !== state) {
        setStatus('error');
        setMessage('Invalid OAuth state parameter');
        return;
      }

      const finalProvider = providerParam || storedProvider || 'google_calendar';

      try {
        // For MVP: Show success immediately for Google Calendar
        if (finalProvider === 'google_calendar' && code) {
          // Store the authorization code for later use
          localStorage.setItem('google_auth_code', code);
          localStorage.removeItem('oauth_state');
          localStorage.removeItem('oauth_provider');
          
          setStatus('success');
          setMessage(`Successfully connected ${getProviderDisplayName(finalProvider)}!`);
          
          // Notify parent window
          if (window.opener && window.opener !== window) {
            try {
              window.opener.postMessage({
                type: 'oauth_success',
                provider: finalProvider,
                data: { code, state }
              }, window.location.origin);
              
              setTimeout(() => {
                window.close();
              }, 2000);
            } catch (e) {
              console.error('Failed to notify parent window:', e);
            }
          }
          
          return;
        }

        // Original flow for other providers or authenticated flow
        let authToken = '';
        
        // Try to get token from parent window
        if (window.opener && window.opener !== window) {
          try {
            // This would work if same origin
            const parentToken = window.opener.localStorage.getItem('authToken');
            if (parentToken) {
              authToken = parentToken;
            }
          } catch (e) {
            // Cross-origin access blocked, try postMessage
            console.log('Cross-origin access blocked, using postMessage');
          }
        }

        // If no token from parent, try localStorage
        if (!authToken) {
          authToken = localStorage.getItem('authToken') || '';
        }

        // If still no token, try to get from URL fragment or query
        if (!authToken) {
          const urlParams = new URLSearchParams(window.location.search);
          authToken = urlParams.get('token') || '';
        }

        if (!authToken) {
          setStatus('error');
          setMessage('Authentication token not found. Please make sure you are logged in.');
          return;
        }

        // Send callback to API Gateway (public test endpoint)
        const response = await fetch(`http://localhost:8000/api/v1/public/oauth2-callback?code=${code}&state=${state}&provider=${providerParam}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          setStatus('success');
          setMessage(`Successfully connected ${getProviderDisplayName(providerParam)}!`);
          
          // Notify parent window if this is a popup
          if (window.opener && window.opener !== window) {
            try {
              window.opener.postMessage({
                type: 'oauth_success',
                provider: providerParam,
                data: data
              }, window.location.origin);
              
              // Close popup after delay
              setTimeout(() => {
                window.close();
              }, 2000);
            } catch (e) {
              console.error('Failed to notify parent window:', e);
            }
          }
        } else {
          const errorData = await response.json().catch(() => ({}));
          setStatus('error');
          setMessage(errorData.message || `Failed to complete ${getProviderDisplayName(providerParam)} authorization`);
        }
      } catch (error) {
        console.error('OAuth callback error:', error);
        setStatus('error');
        setMessage(`Error processing OAuth callback: ${(error as Error).message}`);
      }
    };

    handleCallback();
  }, [searchParams]);

  const getProviderDisplayName = (providerId: string): string => {
    switch (providerId) {
      case 'google_calendar':
        return 'Google Calendar';
      case 'github':
        return 'GitHub';
      case 'slack':
        return 'Slack';
      default:
        return providerId;
    }
  };

  const getProviderColor = (providerId: string): string => {
    switch (providerId) {
      case 'google_calendar':
        return 'text-blue-600';
      case 'github':
        return 'text-gray-800';
      case 'slack':
        return 'text-purple-600';
      default:
        return 'text-gray-600';
    }
  };

  const handleReturnToApp = () => {
    // If this is a popup, close it
    if (window.opener && window.opener !== window) {
      window.close();
    } else {
      // If this is a regular page, redirect back to the app
      window.location.href = '/external-apis-test';
    }
  };

  const handleRetry = () => {
    // Redirect back to the main app for retry
    if (window.opener && window.opener !== window) {
      window.opener.focus();
      window.close();
    } else {
      window.location.href = '/external-apis-test';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="flex items-center justify-center gap-3">
            {status === 'loading' && <Loader2 className="w-6 h-6 animate-spin text-blue-600" />}
            {status === 'success' && <CheckCircle className="w-6 h-6 text-green-600" />}
            {status === 'error' && <XCircle className="w-6 h-6 text-red-600" />}
            
            <span className={getProviderColor(provider)}>
              {getProviderDisplayName(provider)} Authorization
            </span>
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="text-center">
            {status === 'loading' && (
              <div className="space-y-2">
                <p className="text-gray-600">Processing authorization...</p>
                <p className="text-sm text-gray-500">
                  Please wait while we complete the OAuth flow.
                </p>
              </div>
            )}

            {status === 'success' && (
              <div className="space-y-2">
                <p className="text-green-600 font-medium">{message}</p>
                <p className="text-sm text-gray-500">
                  You can now use {getProviderDisplayName(provider)} APIs in your workflows.
                </p>
                {window.opener && window.opener !== window && (
                  <p className="text-xs text-gray-400">
                    This window will close automatically in a few seconds...
                  </p>
                )}
              </div>
            )}

            {status === 'error' && (
              <div className="space-y-2">
                <p className="text-red-600 font-medium">Authorization Failed</p>
                <p className="text-sm text-gray-600">{message}</p>
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-3">
                  <p className="text-xs text-red-700">
                    <strong>Common issues:</strong>
                  </p>
                  <ul className="text-xs text-red-700 mt-1 list-disc list-inside space-y-1">
                    <li>Authentication token expired or missing</li>
                    <li>OAuth application not configured properly</li>
                    <li>User denied permission during authorization</li>
                    <li>Network connectivity issues</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Debug Information */}
          {status === 'error' && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs font-medium text-gray-700 mb-2">Debug Information:</p>
              <div className="text-xs text-gray-600 space-y-1">
                <div>Provider: {provider}</div>
                <div>Code: {searchParams.get('code') ? 'Present' : 'Missing'}</div>
                <div>State: {searchParams.get('state') ? 'Present' : 'Missing'}</div>
                <div>Error: {searchParams.get('error') || 'None'}</div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-4">
            {status === 'success' && (
              <Button 
                onClick={handleReturnToApp}
                className="w-full"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Return to App
              </Button>
            )}

            {status === 'error' && (
              <>
                <Button 
                  onClick={handleRetry}
                  variant="outline"
                  className="flex-1"
                >
                  Try Again
                </Button>
                <Button 
                  onClick={handleReturnToApp}
                  className="flex-1"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Return to App
                </Button>
              </>
            )}
          </div>

          {/* Additional Help */}
          {status === 'error' && (
            <div className="text-center pt-2">
              <p className="text-xs text-gray-500">
                Need help? Check the console for detailed error logs or contact support.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AuthCallbackPage;