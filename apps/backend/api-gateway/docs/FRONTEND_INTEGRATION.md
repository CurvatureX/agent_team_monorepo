# 前端集成文档

API Gateway 前端调用指南，包含Session管理和Chat流式响应的完整示例。

## 🔐 认证要求

所有API调用都需要在请求头中包含Supabase JWT token：

```javascript
const headers = {
  'Authorization': `Bearer ${userToken}`,
  'Content-Type': 'application/json'
};
```

## 📋 API接口调用示例

### 1. 创建会话 (Session)

**POST** `/api/v1/session`

```javascript
// 创建新的workflow
const createSession = async (action = 'create', workflowId = null) => {
  try {
    const response = await fetch('/api/v1/session', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action: action,        // 'create', 'edit', 'copy'
        workflow_id: workflowId // 仅在edit/copy时需要
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Session created:', data);
    return data.session_id;
  } catch (error) {
    console.error('Failed to create session:', error);
    throw error;
  }
};

// 使用示例
const sessionId = await createSession('create');
const editSessionId = await createSession('edit', 'existing-workflow-id');
```

### 2. 流式Chat (SSE)

**GET** `/api/v1/chat/stream?session_id=xxx&user_message=yyy`

```javascript
// 发送消息并接收流式响应
const sendMessage = async (sessionId, message) => {
  const url = new URL('/api/v1/chat/stream', window.location.origin);
  url.searchParams.append('session_id', sessionId);
  url.searchParams.append('user_message', message);

  const eventSource = new EventSource(url, {
    headers: {
      'Authorization': `Bearer ${userToken}`
    }
  });

  let fullResponse = '';

  return new Promise((resolve, reject) => {
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'message') {
          // 增量模式：累积拼接delta内容
          fullResponse += data.delta;

          // 实时更新UI
          updateChatUI(fullResponse, data.is_complete);

          // 检查是否完成
          if (data.is_complete) {
            eventSource.close();
            resolve(fullResponse);
          }
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error);
        eventSource.close();
        reject(error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      eventSource.close();
      reject(error);
    };

    // 设置超时
    setTimeout(() => {
      eventSource.close();
      reject(new Error('SSE timeout'));
    }, 30000); // 30秒超时
  });
};

// UI更新函数示例
const updateChatUI = (content, isComplete) => {
  const messageElement = document.getElementById('ai-response');
  messageElement.textContent = content;

  if (isComplete) {
    messageElement.classList.add('complete');
    // 隐藏loading状态等
  }
};

// 使用示例
try {
  const response = await sendMessage(sessionId, '你好，请帮我创建一个workflow');
  console.log('Complete response:', response);
} catch (error) {
  console.error('Chat failed:', error);
}
```

### 3. Workflow生成进度 (SSE)

**GET** `/api/v1/workflow_generation?session_id=xxx`

```javascript
// 监听workflow生成进度
const listenWorkflowProgress = async (sessionId) => {
  const url = new URL('/api/v1/workflow_generation', window.location.origin);
  url.searchParams.append('session_id', sessionId);

  const eventSource = new EventSource(url, {
    headers: {
      'Authorization': `Bearer ${userToken}`
    }
  });

  return new Promise((resolve, reject) => {
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        console.log('Workflow event:', data);

        switch (data.type) {
          case 'waiting':
            updateWorkflowUI('等待开始...', data.workflow_id, data.data);
            break;

          case 'start':
            updateWorkflowUI('开始生成workflow...', data.workflow_id, data.data);
            break;

          case 'draft':
            updateWorkflowUI('生成草稿中...', data.workflow_id, data.data);
            break;

          case 'debugging':
            updateWorkflowUI('调试优化中...', data.workflow_id, data.data);
            break;

          case 'complete':
            updateWorkflowUI('生成完成!', data.workflow_id, data.data);
            eventSource.close();
            resolve({
              workflowId: data.workflow_id,
              data: data.data
            });
            break;

          case 'error':
            updateWorkflowUI('生成失败', null, data.data);
            eventSource.close();
            reject(new Error(data.data?.message || 'Workflow generation failed'));
            break;
        }
      } catch (error) {
        console.error('Error parsing workflow SSE data:', error);
        eventSource.close();
        reject(error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('Workflow SSE connection error:', error);
      eventSource.close();
      reject(error);
    };

    // 设置超时 (workflow生成可能需要较长时间)
    setTimeout(() => {
      eventSource.close();
      reject(new Error('Workflow generation timeout'));
    }, 120000); // 2分钟超时
  });
};

// UI更新函数示例
const updateWorkflowUI = (message, workflowId = null, data = null) => {
  // 更新状态消息
  const statusElement = document.getElementById('workflow-status');
  if (statusElement) {
    statusElement.textContent = message;
  }

  // 更新workflow ID显示
  if (workflowId) {
    const idElement = document.getElementById('workflow-id');
    if (idElement) {
      idElement.textContent = `Workflow ID: ${workflowId}`;
    }
  }

  // 显示详细数据 (如果有)
  if (data) {
    const dataElement = document.getElementById('workflow-data');
    if (dataElement) {
      dataElement.textContent = JSON.stringify(data, null, 2);
    }
  }

  // 显示当前状态指示器
  const stageIndicator = document.getElementById('workflow-stage');
  if (stageIndicator) {
    stageIndicator.className = `stage-${message.includes('等待') ? 'waiting' :
                                     message.includes('开始') ? 'start' :
                                     message.includes('草稿') ? 'draft' :
                                     message.includes('调试') ? 'debugging' :
                                     message.includes('完成') ? 'complete' : 'unknown'}`;
  }

  console.log(`Workflow: ${message}`, data);
};

// 使用示例
try {
  const result = await listenWorkflowProgress(sessionId);
  console.log('Workflow generation completed:', result);
} catch (error) {
  console.error('Workflow generation failed:', error);
}
```

## 🔄 完整的前端集成示例

```javascript
class WorkflowChat {
  constructor(userToken) {
    this.userToken = userToken;
    this.sessionId = null;
    this.currentChatSource = null;
    this.currentWorkflowSource = null;
  }

  // 初始化会话
  async initSession(action = 'create', workflowId = null) {
    try {
      const response = await fetch('/api/v1/session', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.userToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: action,
          workflow_id: workflowId
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to create session: ${response.status}`);
      }

      const data = await response.json();
      this.sessionId = data.session_id;
      console.log('Session initialized:', this.sessionId);
      return this.sessionId;
    } catch (error) {
      console.error('Session initialization failed:', error);
      throw error;
    }
  }

  // 发送消息
  async sendMessage(message, onUpdate = null, onComplete = null) {
    if (!this.sessionId) {
      throw new Error('Session not initialized');
    }

    // 关闭之前的聊天连接
    if (this.currentChatSource) {
      this.currentChatSource.close();
    }

    const url = new URL('/api/v1/chat/stream', window.location.origin);
    url.searchParams.append('session_id', this.sessionId);
    url.searchParams.append('user_message', message);

    this.currentChatSource = new EventSource(url);

    let fullResponse = '';

    return new Promise((resolve, reject) => {
      this.currentChatSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'message') {
            // 累积增量内容
            fullResponse += data.delta;

            // 回调函数更新UI
            if (onUpdate) {
              onUpdate(fullResponse, data.is_complete);
            }

            // 完成时解析Promise
            if (data.is_complete) {
              this.currentChatSource.close();
              this.currentChatSource = null;

              if (onComplete) {
                onComplete(fullResponse);
              }

              resolve(fullResponse);
            }
          }
        } catch (error) {
          console.error('Error parsing chat SSE data:', error);
          this.disconnectChat();
          reject(error);
        }
      };

      this.currentChatSource.onerror = (error) => {
        console.error('Chat SSE connection error:', error);
        this.disconnectChat();
        reject(error);
      };
    });
  }

  // 监听workflow生成进度
  async listenWorkflowProgress(onUpdate = null, onComplete = null) {
    if (!this.sessionId) {
      throw new Error('Session not initialized');
    }

    // 关闭之前的workflow连接
    if (this.currentWorkflowSource) {
      this.currentWorkflowSource.close();
    }

    const url = new URL('/api/v1/workflow_generation', window.location.origin);
    url.searchParams.append('session_id', this.sessionId);

    this.currentWorkflowSource = new EventSource(url);

    return new Promise((resolve, reject) => {
      this.currentWorkflowSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // 回调函数更新UI
          if (onUpdate) {
            onUpdate(data);
          }

          // 检查是否完成
          if (data.type === 'complete') {
            this.currentWorkflowSource.close();
            this.currentWorkflowSource = null;

            if (onComplete) {
              onComplete(data);
            }

            resolve({
              workflowId: data.workflow_id,
              data: data.data
            });
          } else if (data.type === 'error') {
            this.currentWorkflowSource.close();
            this.currentWorkflowSource = null;
            reject(new Error(data.data?.message || 'Workflow generation failed'));
          }
        } catch (error) {
          console.error('Error parsing workflow SSE data:', error);
          this.disconnectWorkflow();
          reject(error);
        }
      };

      this.currentWorkflowSource.onerror = (error) => {
        console.error('Workflow SSE connection error:', error);
        this.disconnectWorkflow();
        reject(error);
      };
    });
  }

  // 断开聊天连接
  disconnectChat() {
    if (this.currentChatSource) {
      this.currentChatSource.close();
      this.currentChatSource = null;
    }
  }

  // 断开workflow连接
  disconnectWorkflow() {
    if (this.currentWorkflowSource) {
      this.currentWorkflowSource.close();
      this.currentWorkflowSource = null;
    }
  }

  // 断开所有连接
  disconnect() {
    this.disconnectChat();
    this.disconnectWorkflow();
  }
}

// 使用示例
const chat = new WorkflowChat(userToken);

// 完整的workflow创建流程
const createWorkflowExample = async () => {
  try {
    // 1. 创建会话
    await chat.initSession('create');

    // 2. 同时启动workflow状态监听
    const workflowPromise = chat.listenWorkflowProgress(
      // 状态更新回调
      (data) => {
        updateWorkflowUI(data.data?.message || data.type, data.workflow_id, data.data);
      },
      // 完成回调
      (data) => {
        console.log('Workflow generation completed:', data);
      }
    );

    // 3. 发送消息触发workflow生成
    const chatResponse = await chat.sendMessage(
      '请帮我创建一个电商库存监控的workflow，需要监控BestBuy和Amazon',
      // 聊天实时更新回调
      (content, isComplete) => {
        document.getElementById('ai-response').textContent = content;
        if (isComplete) {
          console.log('Chat response complete!');
        }
      },
      // 聊天完成回调
      (finalContent) => {
        console.log('Final chat response:', finalContent);
      }
    );

    // 4. 等待workflow生成完成
    const workflowResult = await workflowPromise;

    console.log('Complete workflow creation:', {
      chatResponse,
      workflowResult
    });

  } catch (error) {
    console.error('Workflow creation failed:', error);
  } finally {
    // 确保断开连接
    chat.disconnect();
  }
};

// 编辑已有workflow示例
const editWorkflowExample = async (existingWorkflowId) => {
  try {
    // 1. 创建编辑会话
    await chat.initSession('edit', existingWorkflowId);

    // 2. 监听workflow更新进度
    chat.listenWorkflowProgress(
      (data) => console.log('Workflow update progress:', data),
      (data) => console.log('Workflow update completed:', data)
    );

    // 3. 发送编辑指令
    await chat.sendMessage(
      '请在现有workflow中添加邮件通知功能',
      (content) => console.log('Chat update:', content)
    );

  } catch (error) {
    console.error('Workflow edit failed:', error);
  }
};
```

## 🛠️ 错误处理

### 常见错误情况

```javascript
const handleApiError = (error, response) => {
  if (response?.status === 401) {
    // JWT token过期或无效
    console.error('Authentication failed - redirect to login');
    // redirectToLogin();
  } else if (response?.status === 404) {
    // Session不存在
    console.error('Session not found - create new session');
  } else if (response?.status === 500) {
    // 服务器错误
    console.error('Server error - try again later');
  } else {
    console.error('Unknown error:', error);
  }
};

// SSE连接错误处理
eventSource.onerror = (event) => {
  console.error('SSE Error:', event);

  // 检查连接状态
  if (eventSource.readyState === EventSource.CLOSED) {
    console.log('SSE connection closed');
  } else if (eventSource.readyState === EventSource.CONNECTING) {
    console.log('SSE reconnecting...');
  }

  // 实现重连逻辑
  setTimeout(() => {
    if (eventSource.readyState !== EventSource.OPEN) {
      // 重新创建连接
      console.log('Attempting to reconnect...');
    }
  }, 5000);
};
```

## 📱 React集成示例

```jsx
import React, { useState, useCallback, useEffect } from 'react';

const WorkflowChatComponent = ({ userToken }) => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Workflow状态
  const [workflowStatus, setWorkflowStatus] = useState('');
  const [workflowStage, setWorkflowStage] = useState('');
  const [workflowId, setWorkflowId] = useState(null);
  const [workflowData, setWorkflowData] = useState(null);
  const [isGeneratingWorkflow, setIsGeneratingWorkflow] = useState(false);

  // 创建会话
  const createSession = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/session', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${userToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'create' })
      });

      const data = await response.json();
      setSessionId(data.session_id);
      return data.session_id;
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  }, [userToken]);

  // 启动workflow状态监听
  const startWorkflowListener = useCallback(() => {
    if (!sessionId || isGeneratingWorkflow) return;

    setIsGeneratingWorkflow(true);
    setWorkflowStatus('启动监听...');

    const url = new URL('/api/v1/workflow_generation', window.location.origin);
    url.searchParams.append('session_id', sessionId);

    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      setWorkflowStage(data.type);
      setWorkflowStatus(data.data?.message || data.type);

      if (data.workflow_id) {
        setWorkflowId(data.workflow_id);
      }

      if (data.type === 'complete') {
        setWorkflowData(data.data);
        setIsGeneratingWorkflow(false);
        eventSource.close();
      } else if (data.type === 'error') {
        setWorkflowStatus('生成失败: ' + (data.data?.message || '未知错误'));
        setIsGeneratingWorkflow(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setWorkflowStatus('连接错误');
      setIsGeneratingWorkflow(false);
      eventSource.close();
    };

    return eventSource;
  }, [sessionId, isGeneratingWorkflow]);

  // 发送消息
  const sendMessage = useCallback(async (message) => {
    if (!sessionId) return;

    setIsLoading(true);
    setCurrentResponse('');

    // 添加用户消息到UI
    setMessages(prev => [...prev, { type: 'user', content: message }]);

    // 如果消息可能触发workflow生成，启动监听
    if (message.includes('创建') || message.includes('workflow') || message.includes('生成')) {
      startWorkflowListener();
    }

    try {
      const url = new URL('/api/v1/chat/stream', window.location.origin);
      url.searchParams.append('session_id', sessionId);
      url.searchParams.append('user_message', message);

      const eventSource = new EventSource(url);
      let fullResponse = '';

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'message') {
          fullResponse += data.delta;
          setCurrentResponse(fullResponse);

          if (data.is_complete) {
            eventSource.close();
            setMessages(prev => [...prev, { type: 'assistant', content: fullResponse }]);
            setCurrentResponse('');
            setIsLoading(false);
          }
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setIsLoading(false);
        console.error('Chat SSE connection failed');
      };

    } catch (error) {
      setIsLoading(false);
      console.error('Send message failed:', error);
    }
  }, [sessionId, startWorkflowListener]);

  return (
    <div className="workflow-chat-container">
      {/* 会话控制 */}
      <div className="session-control">
        {!sessionId ? (
          <button onClick={createSession}>创建会话</button>
        ) : (
          <div className="session-info">
            会话ID: {sessionId}
          </div>
        )}
      </div>

      {/* Workflow状态显示 */}
      {isGeneratingWorkflow && (
        <div className="workflow-status-panel">
          <h3>Workflow生成状态</h3>
          <div className="status-stages">
            <div className={`stage ${workflowStage === 'waiting' ? 'active' : workflowStage === 'start' || workflowStage === 'draft' || workflowStage === 'debugging' || workflowStage === 'complete' ? 'completed' : ''}`}>
              等待中
            </div>
            <div className={`stage ${workflowStage === 'start' ? 'active' : workflowStage === 'draft' || workflowStage === 'debugging' || workflowStage === 'complete' ? 'completed' : ''}`}>
              开始生成
            </div>
            <div className={`stage ${workflowStage === 'draft' ? 'active' : workflowStage === 'debugging' || workflowStage === 'complete' ? 'completed' : ''}`}>
              生成草稿
            </div>
            <div className={`stage ${workflowStage === 'debugging' ? 'active' : workflowStage === 'complete' ? 'completed' : ''}`}>
              调试优化
            </div>
            <div className={`stage ${workflowStage === 'complete' ? 'completed' : ''}`}>
              完成
            </div>
          </div>
          <div className="status-message">{workflowStatus}</div>
          {workflowId && (
            <div className="workflow-id">Workflow ID: {workflowId}</div>
          )}
        </div>
      )}

      {/* 完成的Workflow显示 */}
      {workflowData && !isGeneratingWorkflow && (
        <div className="workflow-result">
          <h3>生成的Workflow</h3>
          <div className="workflow-info">
            <p><strong>ID:</strong> {workflowId}</p>
            <p><strong>状态:</strong> 已完成</p>
            <pre>{JSON.stringify(workflowData, null, 2)}</pre>
          </div>
        </div>
      )}

      {/* 聊天消息区域 */}
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.type}`}>
            {msg.content}
          </div>
        ))}
        {currentResponse && (
          <div className="message assistant streaming">
            {currentResponse}
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="input-area">
        <input
          type="text"
          placeholder="输入消息 (例如: 请创建一个电商库存监控workflow)..."
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !isLoading && sessionId) {
              sendMessage(e.target.value);
              e.target.value = '';
            }
          }}
          disabled={isLoading || !sessionId}
        />
        <div className="status-indicators">
          {isLoading && <span className="loading">💬 发送中...</span>}
          {isGeneratingWorkflow && <span className="generating">⚙️ 生成中...</span>}
        </div>
      </div>

      {/* 示例按钮 */}
      <div className="example-buttons">
        <button
          onClick={() => sendMessage('请帮我创建一个电商库存监控的workflow')}
          disabled={!sessionId || isLoading}
        >
          创建库存监控Workflow
        </button>
        <button
          onClick={() => sendMessage('请创建一个数据分析的workflow')}
          disabled={!sessionId || isLoading}
        >
          创建数据分析Workflow
        </button>
      </div>
    </div>
  );
};

// CSS样式示例
const styles = `
.workflow-chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.workflow-status-panel {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.status-stages {
  display: flex;
  justify-content: space-between;
  margin: 15px 0;
  position: relative;
}

.status-stages::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  background: #e0e0e0;
  z-index: 1;
}

.stage {
  background: #e0e0e0;
  color: #666;
  padding: 8px 12px;
  border-radius: 20px;
  font-size: 12px;
  position: relative;
  z-index: 2;
  transition: all 0.3s ease;
}

.stage.active {
  background: #2196F3;
  color: white;
  animation: pulse 1.5s infinite;
}

.stage.completed {
  background: #4CAF50;
  color: white;
}

.workflow-result {
  background: #e8f5e8;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.message {
  padding: 10px;
  margin: 5px 0;
  border-radius: 8px;
}

.message.user {
  background: #e3f2fd;
  text-align: right;
}

.message.assistant {
  background: #f5f5f5;
}

.message.streaming {
  border-left: 3px solid #2196F3;
  animation: pulse 1s infinite;
}

.example-buttons {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.example-buttons button {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

.example-buttons button:hover:not(:disabled) {
  background: #f0f0f0;
}

.example-buttons button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
`;

export default WorkflowChatComponent;
```

## 🔧 技术要点

1. **JWT Token管理**：确保token有效性，处理过期情况
2. **多SSE连接管理**：同时管理chat和workflow连接，正确关闭避免内存泄漏
3. **增量内容处理**：累积拼接delta内容构建完整消息
4. **工作流进度跟踪**：实时显示workflow生成的各个阶段
5. **错误处理**：网络错误、认证错误、超时等情况
6. **用户体验**：loading状态、实时更新、连接状态提示、阶段状态显示

## 🎯 Workflow事件类型说明

| 事件类型 | 说明 | 数据字段 |
|---------|------|----------|
| `waiting` | 等待开始生成 | `message` |
| `start` | 开始生成workflow | `workflow_id`, `message` |
| `draft` | 生成草稿阶段 | `workflow_id`, `data` |
| `debugging` | 调试优化阶段 | `workflow_id`, `data` |
| `complete` | 生成完成 | `workflow_id`, `data` |
| `error` | 生成失败 | `message` |

## 📝 注意事项

- **多SSE连接管理**：同时处理chat和workflow两个SSE连接，需要分别管理
- **连接生命周期**：SSE连接需要在组件卸载时正确关闭，避免内存泄漏
- **增量模式处理**：chat使用增量模式，需要前端累积拼接delta内容
- **JWT Token**：需要包含在EventSource请求中（部分浏览器可能需要特殊处理）
- **超时设置**：workflow生成可能需要较长时间，建议设置2分钟以上超时
- **状态反馈**：提供清晰的阶段指示和状态反馈，提升用户体验
- **错误恢复**：实现重连机制和错误处理策略
- **CORS配置**：生产环境需要配置正确的CORS策略

## 🚀 高级用法

### 同时监听多个workflow
```javascript
// 可以为不同session同时监听多个workflow
const multiWorkflowManager = {
  connections: new Map(),

  startListening(sessionId, onUpdate) {
    if (this.connections.has(sessionId)) {
      this.connections.get(sessionId).close();
    }

    const eventSource = new EventSource(`/api/v1/workflow_generation?session_id=${sessionId}`);
    this.connections.set(sessionId, eventSource);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onUpdate(sessionId, data);
    };
  },

  stopListening(sessionId) {
    if (this.connections.has(sessionId)) {
      this.connections.get(sessionId).close();
      this.connections.delete(sessionId);
    }
  },

  stopAll() {
    this.connections.forEach(source => source.close());
    this.connections.clear();
  }
};
```

### 断网重连机制
```javascript
const createReconnectingEventSource = (url, options = {}) => {
  let eventSource;
  let reconnectTimer;
  const maxReconnects = options.maxReconnects || 5;
  let reconnectCount = 0;

  const connect = () => {
    eventSource = new EventSource(url);

    eventSource.onopen = () => {
      reconnectCount = 0; // 重置重连计数
      if (options.onOpen) options.onOpen();
    };

    eventSource.onerror = () => {
      eventSource.close();

      if (reconnectCount < maxReconnects) {
        reconnectCount++;
        const delay = Math.min(1000 * Math.pow(2, reconnectCount), 30000);

        reconnectTimer = setTimeout(() => {
          console.log(`Attempting reconnect ${reconnectCount}/${maxReconnects}`);
          connect();
        }, delay);
      } else if (options.onMaxReconnects) {
        options.onMaxReconnects();
      }
    };

    if (options.onMessage) {
      eventSource.onmessage = options.onMessage;
    }
  };

  connect();

  return {
    close: () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (eventSource) eventSource.close();
    }
  };
};
```
