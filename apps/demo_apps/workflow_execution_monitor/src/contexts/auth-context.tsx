'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { createClient } from '@/lib/supabase/client';
import { apiClient } from '@/services/api';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const supabase = createClient();

  const refreshSession = async () => {
    try {
      const { data, error } = await supabase.auth.refreshSession();
      if (error) {
        console.error('Error refreshing session:', error);
        throw error;
      } else {
        setSession(data.session);
        setUser(data.session?.user ?? null);

        // Update API client token after session refresh
        if (data.session?.access_token) {
          apiClient.setAccessToken(data.session.access_token);
          console.log('[Auth] Set API client token after session refresh');
        }
      }
    } catch (error) {
      console.error('Error refreshing session:', error);
      throw error;
    }
  };

  useEffect(() => {
    // Register refresh callback with API client
    apiClient.setRefreshCallback(refreshSession);

    // Get initial session
    const getSession = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        console.log('[Auth] Initial session check:', { session: !!session, user: session?.user?.email, error });

        if (error) {
          console.error('Error getting session:', error);
        } else {
          setSession(session);
          setUser(session?.user ?? null);

          // Update API client token immediately
          if (session?.access_token) {
            apiClient.setAccessToken(session.access_token);
            console.log('[Auth] Set initial API client token');
          }

          // Auto-login for development if no session exists
          if (!session) {
            const defaultEmail = process.env.NEXT_PUBLIC_DEFAULT_USERNAME;
            const defaultPassword = process.env.NEXT_PUBLIC_DEFAULT_PASSWORD;

            console.log('[Auth] Environment check:', {
              NODE_ENV: process.env.NODE_ENV,
              allEnvVars: Object.keys(process.env).filter(key => key.startsWith('NEXT_PUBLIC'))
            });

            console.log('[Auth] No session found. Auto-login config:', {
              defaultEmail: !!defaultEmail,
              defaultPassword: !!defaultPassword,
              actualEmail: defaultEmail,
              actualPassword: defaultPassword?.substring(0, 4) + '...'
            });

            if (defaultEmail && defaultPassword) {
              console.log('[Auth] Attempting auto-login for development...');
              try {
                const { data, error } = await supabase.auth.signInWithPassword({
                  email: defaultEmail,
                  password: defaultPassword,
                });

                if (!error && data.session) {
                  console.log('[Auth] Auto-login successful:', data.session.user.email);
                  setSession(data.session);
                  setUser(data.session.user);

                  // Update API client token after auto-login
                  apiClient.setAccessToken(data.session.access_token);
                  console.log('[Auth] Set API client token after auto-login');
                } else {
                  console.warn('[Auth] Auto-login failed:', error?.message);
                }
              } catch (autoLoginError) {
                console.warn('[Auth] Auto-login error:', autoLoginError);
              }
            } else {
              console.log('[Auth] Auto-login credentials not configured');
            }
          } else {
            console.log('[Auth] Existing session found for:', session.user?.email);
          }
        }
      } catch (error) {
        console.error('Error getting session:', error);
      } finally {
        setLoading(false);
      }
    };

    getSession();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[Auth] Auth state changed:', event, session?.user?.email);
      setSession(session);
      setUser(session?.user ?? null);

      // Update API client token immediately on session change
      if (session?.access_token) {
        apiClient.setAccessToken(session.access_token);
        console.log('[Auth] Updated API client token after auth state change');
      } else {
        apiClient.setAccessToken(null);
        console.log('[Auth] Cleared API client token after auth state change');
      }

      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        console.log('[Auth] Token refreshed or signed in');
      } else if (event === 'SIGNED_OUT') {
        console.log('[Auth] Signed out');
      }

      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, [supabase.auth]);

  const signIn = async (email: string, password: string) => {
    try {
      setLoading(true);
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        return { error };
      }

      setSession(data.session);
      setUser(data.session?.user ?? null);

      // Update API client token after manual sign in
      if (data.session?.access_token) {
        apiClient.setAccessToken(data.session.access_token);
        console.log('[Auth] Set API client token after manual sign in');
      }

      return { error: null };
    } catch (error) {
      return { error: error as Error };
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('Error signing out:', error);
      }
      setSession(null);
      setUser(null);

      // Clear API client token on sign out
      apiClient.setAccessToken(null);
      console.log('[Auth] Cleared API client token on sign out');
    } catch (error) {
      console.error('Error signing out:', error);
    } finally {
      setLoading(false);
    }
  };


  const value: AuthContextType = {
    user,
    session,
    loading,
    signIn,
    signOut,
    refreshSession,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
