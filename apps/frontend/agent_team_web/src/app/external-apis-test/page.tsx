"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Calendar, 
  Github, 
  MessageSquare, 
  Play, 
  Settings, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Eye,
  Loader2
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

// Types
interface OAuthProvider {
  id: string;
  name: string;
  icon: React.ComponentType<any>;
  color: string;
  scopes: string[];
  connected: boolean;
}

interface WorkflowTest {
  id: string;
  name: string;
  description: string;
  provider: string;
  icon: React.ComponentType<any>;
  status: 'idle' | 'running' | 'success' | 'error';
  result?: any;
  requiresAuth: boolean;
}

interface APICallLog {
  id: string;
  provider: string;
  operation: string;
  success: boolean;
  response_time_ms: number;
  called_at: string;
  error_message?: string;
}

const ExternalAPIsTestPage: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const [workflowTests, setWorkflowTests] = useState<WorkflowTest[]>([]);
  const [apiLogs, setAPILogs] = useState<APICallLog[]>([]);
  const [selectedTest, setSelectedTest] = useState<string | null>(null);
  
  // Mock JWT token - in real app, get from auth context
  const [authToken, setAuthToken] = useState<string>('');

  // Initialize providers
  useEffect(() => {
    setProviders([
      {
        id: 'google_calendar',
        name: 'Google Calendar',
        icon: Calendar,
        color: 'bg-blue-500',
        scopes: [
          'https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/calendar.events'
        ],
        connected: false
      },
      {
        id: 'github',
        name: 'GitHub',
        icon: Github,
        color: 'bg-gray-800',
        scopes: ['repo', 'read:user', 'write:repo_hook'],
        connected: false
      },
      {
        id: 'slack',
        name: 'Slack',
        icon: MessageSquare,
        color: 'bg-purple-600',
        scopes: ['chat:write', 'channels:read', 'files:write', 'users:read'],
        connected: false
      }
    ]);

    // Initialize workflow tests
    setWorkflowTests([
      {
        id: 'github_issue',
        name: 'Create GitHub Issue',
        description: 'Create a test issue in your GitHub repository',
        provider: 'github',
        icon: Github,
        status: 'idle',
        requiresAuth: true
      },
      {
        id: 'google_calendar_event',
        name: 'Create Calendar Event',
        description: 'Create a test event in your Google Calendar',
        provider: 'google_calendar',
        icon: Calendar,
        status: 'idle',
        requiresAuth: true
      },
      {
        id: 'slack_message',
        name: 'Send Slack Message',
        description: 'Send a test message to your Slack workspace',
        provider: 'slack',
        icon: MessageSquare,
        status: 'idle',
        requiresAuth: true
      },
      {
        id: 'compound_workflow',
        name: 'Multi-API Workflow',
        description: 'Execute a workflow that uses all three APIs in sequence',
        provider: 'multi',
        icon: Settings,
        status: 'idle',
        requiresAuth: true
      }
    ]);

    loadCredentialStatus();
    
    // Check for OAuth2 completion and retry pending node execution
    const checkOAuth2Completion = () => {
      const authCode = localStorage.getItem('google_auth_code');
      const pendingWorkflowId = localStorage.getItem('pending_workflow_id');
      const pendingNodeId = localStorage.getItem('pending_node_id');
      
      if (authCode && pendingWorkflowId && pendingNodeId) {
        // OAuth2 was completed, retry node execution with credentials
        retryNodeWithCredentials(pendingWorkflowId, pendingNodeId, authCode);
      }
    };
    
    checkOAuth2Completion();
  }, []);

  const loadCredentialStatus = async () => {
    if (!authToken) return;
    
    try {
      const response = await fetch('http://localhost:8000/api/app/external-apis/credentials', {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setProviders(prev => prev.map(provider => ({
          ...provider,
          connected: data.credentials?.some((cred: any) => cred.provider === provider.id && cred.is_valid) || false
        })));
      }
    } catch (error) {
      console.error('Failed to load credential status:', error);
    }
  };

  const startOAuthFlow = useCallback(async (providerId: string) => {
    const provider = providers.find(p => p.id === providerId);
    if (!provider) return;

    setLoading(true);
    
    try {
      // For MVP: Direct Google OAuth2 URL generation
      if (providerId === 'google_calendar') {
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
        const redirectUri = encodeURIComponent(window.location.origin + '/auth/callback');
        const scopes = encodeURIComponent(provider.scopes.join(' '));
        const state = `google_calendar_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
          `client_id=${clientId}&` +
          `response_type=code&` +
          `scope=${scopes}&` +
          `redirect_uri=${redirectUri}&` +
          `state=${state}&` +
          `access_type=offline&` +
          `prompt=consent`;
        
        // Store state for verification (simple approach)
        localStorage.setItem('oauth_state', state);
        localStorage.setItem('oauth_provider', providerId);
        
        const popup = window.open(
          googleAuthUrl,
          'oauth_popup',
          'width=500,height=600,scrollbars=yes,resizable=yes'
        );

        if (popup) {
          // Monitor popup for completion
          const checkClosed = setInterval(() => {
            if (popup.closed) {
              clearInterval(checkClosed);
              // Check if authorization was successful
              setTimeout(() => {
                loadCredentialStatus();
                toast({
                  title: "Authorization Check",
                  description: `Checking ${provider.name} authorization status...`
                });
              }, 1000);
            }
          }, 1000);

          toast({
            title: "Authorization Started",
            description: `Please complete authorization for ${provider.name} in the popup window`
          });
        } else {
          toast({
            title: "Popup Blocked",
            description: "Please allow popups and try again",
            variant: "destructive"
          });
        }
      } else {
        throw new Error('Failed to start OAuth flow');
      }
    } catch (error) {
      console.error('OAuth error:', error);
      toast({
        title: "Authorization Error",
        description: `Failed to start ${provider.name} authorization`,
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [authToken, providers, toast]);

  const executeWorkflowNodeTest = async () => {
    if (!authToken) {
      toast({
        title: "Authentication Required",
        description: "Please set your JWT token first",
        variant: "destructive"
      });
      return;
    }

    // First create a workflow with Google Calendar node
    try {
      const createResponse = await fetch('http://localhost:8002/v1/workflows', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          name: "Frontend Google Calendar Test",
          description: "Test workflow with Google Calendar external node from frontend",
          user_id: "7ba36345-a2bb-4ec9-a001-bb46d79d629d",
          settings: {
            timeout_seconds: 300,
            max_retries: 3,
            retry_delay_seconds: 5
          },
          nodes: [
            {
              id: "google_calendar_node_1",
              name: "Create Calendar Event",
              type: "EXTERNAL_ACTION_NODE",
              subtype: "GOOGLE_CALENDAR",
              parameters: {
                action: "create_event",
                calendar_id: "primary",
                summary: "Frontend Test Meeting - OAuth2 集成测试",
                description: "通过前端OAuth2弹窗授权后创建的Google Calendar事件",
                start: "2025-08-10T16:00:00+08:00",
                end: "2025-08-10T17:00:00+08:00",
                location: "前端测试环境"
              },
              position: { x: 100, y: 100 }
            }
          ],
          edges: [],
          metadata: { created_by: "frontend_oauth2_test", version: "1.0" }
        })
      });

      if (!createResponse.ok) {
        throw new Error('Failed to create workflow');
      }

      const workflowData = await createResponse.json();
      const workflowId = workflowData.workflow.id;

      // Now test the single node
      const nodeResponse = await fetch(`http://localhost:8002/v1/workflows/${workflowId}/nodes/google_calendar_node_1/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          user_id: "7ba36345-a2bb-4ec9-a001-bb46d79d629d",
          input_data: { test_source: "frontend_oauth2" },
          execution_context: {
            override_parameters: {},
            credentials: {},
            use_previous_results: false
          }
        })
      });

      if (!nodeResponse.ok) {
        throw new Error('Failed to execute node');
      }

      const nodeResult = await nodeResponse.json();

      // Check if OAuth2 is required
      if (nodeResult.output_data && nodeResult.output_data.requires_auth) {
        toast({
          title: "OAuth2 Authorization Required",
          description: "Google Calendar needs authorization. Starting OAuth2 flow...",
        });

        // Trigger OAuth2 flow
        await startOAuthFlow('google_calendar');

        // Store workflow and node info for later retry
        localStorage.setItem('pending_workflow_id', workflowId);
        localStorage.setItem('pending_node_id', 'google_calendar_node_1');
        
        return;
      }

      // Display results
      toast({
        title: "Node Test Completed",
        description: nodeResult.status === 'COMPLETED' ? 'Google Calendar node executed successfully!' : 'Node execution failed',
        variant: nodeResult.status === 'COMPLETED' ? 'default' : 'destructive'
      });

    } catch (error) {
      console.error('Node test error:', error);
      toast({
        title: "Node Test Failed",
        description: `Error: ${(error as Error).message}`,
        variant: "destructive"
      });
    }
  };

  const executeWorkflowTest = async (testId: string) => {
    if (!authToken) {
      toast({
        title: "Authentication Required", 
        description: "Please set your JWT token first",
        variant: "destructive"
      });
      return;
    }

    const test = workflowTests.find(t => t.id === testId);
    if (!test) return;

    // Check if provider is connected (for single-provider tests)
    if (test.provider !== 'multi') {
      const provider = providers.find(p => p.id === test.provider);
      if (provider && !provider.connected) {
        toast({
          title: "Authorization Required",
          description: `Please connect ${provider.name} first`,
          variant: "destructive"
        });
        return;
      }
    }

    setSelectedTest(testId);
    setWorkflowTests(prev => prev.map(t => 
      t.id === testId ? { ...t, status: 'running', result: undefined } : t
    ));

    try {
      let workflowBody: any;
      
      switch (testId) {
        case 'github_issue':
          workflowBody = {
            name: "GitHub Issue Creation Test",
            description: "Test workflow for creating GitHub issues",
            nodes: [{
              id: "github_node_1",
              name: "Create GitHub Issue",
              type: "EXTERNAL_ACTION_NODE",
              subtype: "GITHUB",
              parameters: {
                action: "create_issue",
                repository: "test-repo",
                owner: "test-user",
                title: `Test Issue from Frontend - ${new Date().toISOString()}`,
                body: "This issue was created by the frontend test interface via workflow engine external API integration.",
                labels: ["test", "frontend-generated"],
                assignees: []
              },
              position: { x: 100, y: 100 }
            }],
            edges: [],
            metadata: { created_by: "frontend_test", version: "1.0" }
          };
          break;

        case 'google_calendar_event':
          const startTime = new Date();
          startTime.setHours(startTime.getHours() + 1);
          const endTime = new Date(startTime);
          endTime.setHours(endTime.getHours() + 1);
          
          workflowBody = {
            name: "Google Calendar Event Test",
            description: "Test workflow for creating calendar events", 
            nodes: [{
              id: "calendar_node_1",
              name: "Create Calendar Event",
              type: "EXTERNAL_ACTION_NODE", 
              subtype: "GOOGLE_CALENDAR",
              parameters: {
                action: "create_event",
                calendar_id: "primary",
                event_data: {
                  summary: `Test Meeting - ${new Date().toLocaleString()}`,
                  description: "This event was created by the frontend test interface",
                  start: { dateTime: startTime.toISOString() },
                  end: { dateTime: endTime.toISOString() },
                  location: "Virtual Meeting Room"
                }
              },
              position: { x: 100, y: 100 }
            }],
            edges: [],
            metadata: { created_by: "frontend_test", version: "1.0" }
          };
          break;

        case 'slack_message':
          workflowBody = {
            name: "Slack Message Test",
            description: "Test workflow for sending Slack messages",
            nodes: [{
              id: "slack_node_1", 
              name: "Send Slack Message",
              type: "EXTERNAL_ACTION_NODE",
              subtype: "SLACK",
              parameters: {
                action: "send_message",
                channel: "#general",
                message_data: {
                  text: `🚀 Test message from Frontend - ${new Date().toLocaleString()}`,
                  blocks: [{
                    type: "section",
                    text: {
                      type: "mrkdwn",
                      text: "*Frontend Integration Test* ✅\n\nThis message was sent via the frontend test interface using external API integration."
                    }
                  }]
                },
                username: "TestBot",
                icon_emoji: ":test_tube:"
              },
              position: { x: 100, y: 100 }
            }],
            edges: [],
            metadata: { created_by: "frontend_test", version: "1.0" }
          };
          break;

        case 'compound_workflow':
          workflowBody = {
            name: "Multi-API Integration Test",
            description: "Test workflow that uses multiple external APIs",
            nodes: [
              {
                id: "github_issue_node",
                name: "Create GitHub Issue",
                type: "EXTERNAL_ACTION_NODE",
                subtype: "GITHUB",
                parameters: {
                  action: "create_issue",
                  repository: "integration-test",
                  owner: "test-org", 
                  title: `Multi-API Test Issue - ${new Date().toISOString()}`,
                  body: "This issue was created as part of a multi-API integration test",
                  labels: ["integration-test", "multi-api"]
                },
                position: { x: 100, y: 100 }
              },
              {
                id: "slack_notification_node",
                name: "Notify Team",
                type: "EXTERNAL_ACTION_NODE",
                subtype: "SLACK", 
                parameters: {
                  action: "send_message",
                  channel: "#dev-team",
                  message_data: {
                    text: "📋 Multi-API integration test completed!",
                    blocks: [{
                      type: "section",
                      text: {
                        type: "mrkdwn",
                        text: "*Integration Test Results*\n• GitHub issue created ✅\n• Slack notification sent ✅\n• Multi-API workflow executed successfully"
                      }
                    }]
                  }
                },
                position: { x: 300, y: 100 }
              }
            ],
            edges: [{
              source: "github_issue_node",
              target: "slack_notification_node"
            }],
            metadata: { created_by: "frontend_test", version: "1.0" }
          };
          break;

        default:
          throw new Error('Unknown test type');
      }

      // Create workflow
      const createResponse = await fetch('http://localhost:8002/v1/workflows', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(workflowBody)
      });

      if (!createResponse.ok) {
        throw new Error('Failed to create workflow');
      }

      const workflowData = await createResponse.json();
      const workflowId = workflowData.id || workflowData.workflow_id;

      // Execute workflow
      const executeResponse = await fetch(`http://localhost:8002/v1/workflows/${workflowId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          user_id: "test-user-123", // In real app, get from JWT
          input_data: { source: "frontend_test" }
        })
      });

      if (!executeResponse.ok) {
        throw new Error('Failed to execute workflow');
      }

      const executionResult = await executeResponse.json();

      setWorkflowTests(prev => prev.map(t => 
        t.id === testId ? { 
          ...t, 
          status: 'success', 
          result: { 
            workflowId, 
            executionId: executionResult.execution_id || executionResult.id,
            ...executionResult 
          }
        } : t
      ));

      toast({
        title: "Test Completed",
        description: `${test.name} executed successfully!`
      });

      // Load API logs
      loadAPILogs();

    } catch (error) {
      console.error('Test execution error:', error);
      setWorkflowTests(prev => prev.map(t => 
        t.id === testId ? { 
          ...t, 
          status: 'error', 
          result: { error: (error as Error).message }
        } : t
      ));

      toast({
        title: "Test Failed",
        description: `${test.name} failed: ${(error as Error).message}`,
        variant: "destructive"
      });
    }
  };

  const retryNodeWithCredentials = async (workflowId: string, nodeId: string, authCode: string) => {
    if (!authToken) return;

    try {
      toast({
        title: "Retrying with OAuth2 Credentials",
        description: "Executing Google Calendar node with authorized credentials...",
      });

      // Execute the node with OAuth2 credentials
      const response = await fetch(`http://localhost:8002/v1/workflows/${workflowId}/nodes/${nodeId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          user_id: "7ba36345-a2bb-4ec9-a001-bb46d79d629d",
          input_data: { test_source: "frontend_oauth2_retry" },
          execution_context: {
            override_parameters: {},
            credentials: {
              google_calendar: {
                authorization_code: authCode,
                client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
                redirect_uri: window.location.origin + '/auth/callback'
              }
            },
            use_previous_results: false
          }
        })
      });

      if (!response.ok) {
        throw new Error('Failed to retry node execution');
      }

      const result = await response.json();
      
      // Clean up stored values
      localStorage.removeItem('google_auth_code');
      localStorage.removeItem('pending_workflow_id');
      localStorage.removeItem('pending_node_id');

      if (result.status === 'COMPLETED' && result.output_data && result.output_data.success !== false) {
        toast({
          title: "🎉 Google Calendar Integration Success!",
          description: "Node executed successfully with OAuth2 credentials! Event created in your Google Calendar.",
        });
      } else {
        toast({
          title: "Node Execution Completed",
          description: `Result: ${result.output_data?.error || 'Unknown result'}`,
          variant: result.output_data?.success === false ? "destructive" : "default"
        });
      }

    } catch (error) {
      console.error('Retry node execution error:', error);
      toast({
        title: "Retry Failed",
        description: `Error: ${(error as Error).message}`,
        variant: "destructive"
      });
    }
  };

  const loadAPILogs = async () => {
    if (!authToken) return;
    
    try {
      const response = await fetch('http://localhost:8000/api/app/external-apis/metrics?limit=10', {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAPILogs(data.recent_calls || []);
      }
    } catch (error) {
      console.error('Failed to load API logs:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Play className="w-4 h-4" />;
    }
  };

  const getProviderStatus = (provider: OAuthProvider) => {
    if (provider.connected) {
      return <Badge variant="default" className="bg-green-500">Connected</Badge>;
    }
    return <Badge variant="outline">Not Connected</Badge>;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">External APIs Integration Test</h1>
          <p className="text-gray-600 mt-2">Test and manage external API integrations with real OAuth2 authorization</p>
        </div>
        <Button onClick={loadCredentialStatus} variant="outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh Status
        </Button>
      </div>

      {/* Auth Token Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Authentication Setup
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">JWT Authentication Token</label>
              <div className="flex gap-2">
                <input
                  type="password"
                  placeholder="Paste your JWT token here..."
                  value={authToken}
                  onChange={(e) => setAuthToken(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <Button 
                  variant="outline" 
                  onClick={() => {
                    // Demo token for testing
                    setAuthToken('demo-jwt-token-for-testing');
                    toast({
                      title: "Demo Token Set",
                      description: "Using demo token for testing. In production, use real JWT from login."
                    });
                  }}
                >
                  Use Demo Token
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Get your JWT token from the API Gateway authentication endpoint
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* OAuth Providers */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ExternalLink className="w-5 h-5" />
            OAuth2 Providers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {providers.map((provider) => (
              <div key={provider.id} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${provider.color} text-white`}>
                    <provider.icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium">{provider.name}</h3>
                    {getProviderStatus(provider)}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <p className="text-xs text-gray-500">Scopes:</p>
                  <div className="flex flex-wrap gap-1">
                    {provider.scopes.map((scope) => (
                      <Badge key={scope} variant="secondary" className="text-xs">
                        {scope}
                      </Badge>
                    ))}
                  </div>
                </div>

                <Button
                  onClick={() => startOAuthFlow(provider.id)}
                  disabled={loading || provider.connected}
                  className="w-full"
                  variant={provider.connected ? "outline" : "default"}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Connecting...
                    </>
                  ) : provider.connected ? (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Connected
                    </>
                  ) : (
                    <>
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Connect {provider.name}
                    </>
                  )}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Node Debug Test */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Node Debug Test - OAuth2 Integration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h3 className="font-medium text-blue-900 mb-2">🎯 Complete OAuth2 Integration Test</h3>
            <p className="text-sm text-blue-700 mb-3">
              This test demonstrates the complete workflow integration with OAuth2:
              <br />1. Creates a workflow with Google Calendar node
              <br />2. Tests single node execution 
              <br />3. Detects OAuth2 requirement and triggers authorization popup
              <br />4. Retries execution with real credentials
            </p>
            <Button
              onClick={executeWorkflowNodeTest}
              disabled={loading || !authToken}
              className="w-full"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Testing Node...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Test Google Calendar Node with OAuth2
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Workflow Tests */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="w-5 h-5" />
            Workflow Tests
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {workflowTests.map((test) => (
              <div key={test.id} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gray-100">
                    <test.icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium">{test.name}</h3>
                    <p className="text-sm text-gray-600">{test.description}</p>
                  </div>
                  {getStatusIcon(test.status)}
                </div>

                {test.result && (
                  <div className="bg-gray-50 rounded p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <Eye className="w-4 h-4" />
                      <span className="text-sm font-medium">Result:</span>
                    </div>
                    <pre className="text-xs overflow-auto max-h-32">
                      {JSON.stringify(test.result, null, 2)}
                    </pre>
                  </div>
                )}

                <Button
                  onClick={() => executeWorkflowTest(test.id)}
                  disabled={test.status === 'running'}
                  className="w-full"
                  variant={test.status === 'success' ? "outline" : "default"}
                >
                  {test.status === 'running' ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Running Test...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Run Test
                    </>
                  )}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* API Call Logs */}
      {apiLogs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              Recent API Calls
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {apiLogs.map((log) => (
                <div key={log.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Badge variant={log.success ? "default" : "destructive"}>
                      {log.provider}
                    </Badge>
                    <span className="font-medium">{log.operation}</span>
                    <span className="text-sm text-gray-600">
                      {log.response_time_ms}ms
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {log.success ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span className="text-xs text-gray-500">
                      {new Date(log.called_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ExternalAPIsTestPage;