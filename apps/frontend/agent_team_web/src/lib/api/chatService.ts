import { v4 as uuidv4 } from 'uuid';
import { createClient } from '@/lib/supabase/client';
import { WorkflowData } from '@/types/workflow';

export interface ChatMessage {
  id: string;
  content: string;
  message_type: 'user' | 'assistant';  // Aligned with backend database schema
  session_id: string;
  user_id?: string;
  sequence_number?: number;
  created_at: string;
}

export interface ChatRequest {
  session_id: string;
  user_message: string;
}

export interface ChatHistory {
  messages: ChatMessage[];
  session_id: string;
  total_count: number;
}

export interface ChatSSEEvent {
  type: 'message' | 'status_change' | 'workflow' | 'error' | 'debug';
  data: {
    text?: string;
    workflow?: WorkflowData;
    message?: string;
    status?: string;
    message_type?: 'assistant' | 'user';  // Aligned with backend
    previous_stage?: string;
    current_stage?: string;
    stage_state?: Record<string, unknown>;
    node_name?: string;
    [key: string]: unknown;
  };
  session_id: string;
  timestamp: string;
  is_final?: boolean;
}

class ChatService {
  private baseUrl: string;
  private sessionId: string | null = null;
  private supabase = createClient();
  private sessionInitPromise: Promise<string> | null = null; // Lock to prevent concurrent session creation

  constructor() {
    // Use the proxy API route that forwards to backend
    this.baseUrl = '/api/proxy';
  }

  /**
   * Get auth token from Supabase
   */
  private async getAuthToken(): Promise<string | null> {
    try {
      const { data: { session } } = await this.supabase.auth.getSession();
      if (session?.access_token) {
        return session.access_token;
      }

      // Try to refresh the session if no token
      const { data: { session: refreshedSession } } = await this.supabase.auth.refreshSession();
      return refreshedSession?.access_token || null;
    } catch (error) {
      console.error('Failed to get auth token from Supabase:', error);
      return null;
    }
  }

  /**
   * Initialize a new chat session by creating it on the backend
   */
  async initSession(): Promise<string> {
    try {
      const authToken = await this.getAuthToken();
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      console.log('Creating new session...');
      const response = await fetch(`${this.baseUrl}/v1/app/sessions`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          action: 'create',
          workflow_id: null
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to create session:', errorText);
        throw new Error(`Failed to create session: ${response.status}`);
      }

      const data = await response.json();
      console.log('Session created:', data);

      // Backend returns { session: { id, ... }, message?: string }
      // Extract session ID from response
      if (data.session?.id) {
        this.sessionId = data.session.id;
        return data.session.id;
      } else if (data.id) {
        // Fallback for direct session object (legacy)
        this.sessionId = data.id;
        return data.id;
      } else {
        throw new Error('Session ID not found in response');
      }
    } catch (error) {
      console.error('Error creating session:', error);
      // Fallback to local UUID if backend fails
      this.sessionId = uuidv4();
      return this.sessionId;
    }
  }

  /**
   * Get current session ID, creating one if needed
   * Uses a lock mechanism to prevent concurrent session creation (React StrictMode safe)
   */
  async getSessionId(): Promise<string> {
    // If session already exists, return it immediately
    if (this.sessionId) {
      console.log('[ChatService] Using existing session ID:', this.sessionId);
      return this.sessionId;
    }

    // If session creation is already in progress, wait for it
    if (this.sessionInitPromise) {
      console.log('[ChatService] Session creation already in progress, waiting...');
      return this.sessionInitPromise;
    }

    // Start new session creation with lock
    console.log('[ChatService] No session ID found, creating new session...');
    this.sessionInitPromise = this.initSession();

    try {
      const sessionId = await this.sessionInitPromise;
      console.log('[ChatService] Created session ID:', sessionId);
      return sessionId;
    } finally {
      // Clear the lock after completion
      this.sessionInitPromise = null;
    }
  }

  /**
   * Force create a new session
   */
  async createNewSession(): Promise<string> {
    this.sessionId = null; // Clear existing session
    return await this.initSession();
  }

  /**
   * Send a chat message using SSE (Server-Sent Events) for streaming response
   */
  async sendChatMessage(
    message: string,
    onMessage: (event: ChatSSEEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void,
    // context?: any,
    // workflowId?: string
  ): Promise<() => void> {
    const sessionId = await this.getSessionId();

    const requestBody: ChatRequest = {
      session_id: sessionId,
      user_message: message
    };

    console.log('[ChatService] Sending chat request to:', `${this.baseUrl}/v1/app/chat/stream`);
    console.log('[ChatService] Using session ID:', sessionId);
    console.log('[ChatService] Request body:', requestBody);

    try {
      // Get auth token from Supabase
      const authToken = await this.getAuthToken();
      console.log('Auth token found:', authToken ? 'Yes' : 'No');

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
        console.log('Authorization header set');
      } else {
        console.warn('No auth token found, request may fail');
      }

      const response = await fetch(`${this.baseUrl}/v1/app/chat/stream`, {
        method: 'POST',
        headers,
        credentials: 'include', // Include cookies
        body: JSON.stringify(requestBody),
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const processStream = async () => {
        if (!reader) return;

        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              if (onComplete) onComplete();
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') {
                  if (onComplete) onComplete();
                  return;
                }

                try {
                  const event: ChatSSEEvent = JSON.parse(data);
                  onMessage(event);

                  // Check if this is the final message
                  if (event.is_final) {
                    if (onComplete) onComplete();
                    reader.cancel();
                    return;
                  }
                } catch (e) {
                  console.error('Failed to parse SSE event:', e);
                }
              }
            }
          }
        } catch (error) {
          if (onError) {
            onError(error instanceof Error ? error : new Error(String(error)));
          }
        }
      };

      processStream();

      // Return a cleanup function to cancel the stream
      return () => {
        reader?.cancel();
      };
    } catch (error) {
      if (onError) {
        onError(error instanceof Error ? error : new Error(String(error)));
      }
      return () => {};
    }
  }

  /**
   * Get chat history for a session
   */
  async getChatHistory(sessionId?: string, limit: number = 50, offset: number = 0): Promise<ChatHistory> {
    const sid = sessionId || await this.getSessionId();

    console.log('[ChatService] Fetching chat history for session:', sid);
    console.log('[ChatService] Current internal session ID:', this.sessionId);

    try {
      const authToken = await this.getAuthToken();
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const url = `${this.baseUrl}/v1/app/chat/${sid}/history?limit=${limit}&offset=${offset}`;
      console.log('[ChatService] Fetching from URL:', url);

      const response = await fetch(url, {
        method: 'GET',
        headers,
        credentials: 'include',
      });

      console.log('[ChatService] History response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('[ChatService] Chat history received:', {
        messageCount: data.messages?.length || 0,
        sessionId: data.session_id,
        totalCount: data.total_count
      });
      return data;
    } catch (error) {
      console.error('[ChatService] Failed to fetch chat history:', error);
      throw error;
    }
  }

  /**
   * Set an existing session ID (for reusing sessions)
   */
  setSessionId(sessionId: string) {
    console.log('[ChatService] Setting session ID:', sessionId, '(previous:', this.sessionId, ')');
    this.sessionId = sessionId;
  }

  /**
   * Clear current session
   */
  clearSession() {
    this.sessionId = null;
    this.sessionInitPromise = null; // Clear any pending initialization
  }

  /**
   * Simple non-streaming chat (for fallback or simple responses)
   */
  async sendSimpleMessage(message: string): Promise<string> {
    return new Promise(async (resolve, reject) => {
      let fullResponse = '';

      await this.sendChatMessage(
        message,
        (event) => {
          if (event.type === 'message' && event.data?.text) {
            fullResponse += event.data.text;
          }
        },
        (error) => reject(error),
        () => resolve(fullResponse)
      );
    });
  }
}

// Export singleton instance
export const chatService = new ChatService();
