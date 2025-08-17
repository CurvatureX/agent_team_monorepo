"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  User,
  Mail,
  Calendar,
  Shield,
  LogOut,
  Settings,
  Loader2,
  CheckCircle,
  Clock
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function ProfilePage() {
  const { user, session, loading, signOut } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const [signOutLoading, setSignOutLoading] = useState(false);

  useEffect(() => {
    // If not loading and no user, redirect to login
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  const handleSignOut = async () => {
    try {
      setSignOutLoading(true);
      await signOut();
      toast({
        title: "Signed out successfully",
        description: "You have been logged out of your account.",
      });
      router.push('/login');
    } catch {
      toast({
        title: "Error signing out",
        description: "Failed to sign out. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSignOutLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!user) {
    return null; // Will redirect in useEffect
  }

  // Extract user info
  const userMetadata = user.user_metadata || {};
  // const appMetadata = user.app_metadata || {};
  const identities = user.identities || [];

  // Get avatar URL
  const avatarUrl = userMetadata.avatar_url || userMetadata.picture;
  const displayName = userMetadata.full_name || userMetadata.name || user.email?.split('@')[0];
  const initials = displayName?.split(' ').map(n => n[0]).join('').toUpperCase() || '?';

  // Format dates
  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container max-w-4xl mx-auto py-10 px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Profile</h1>
          <p className="text-muted-foreground">Manage your account settings and preferences</p>
        </div>

        {/* Main Profile Card */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Avatar className="h-20 w-20">
                  <AvatarImage src={avatarUrl} alt={displayName} />
                  <AvatarFallback className="text-lg">{initials}</AvatarFallback>
                </Avatar>
                <div>
                  <CardTitle className="text-2xl">{displayName}</CardTitle>
                  <CardDescription className="flex items-center mt-1">
                    <Mail className="w-4 h-4 mr-2" />
                    {user.email}
                  </CardDescription>
                  {user.confirmed_at && (
                    <Badge variant="secondary" className="mt-2">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Verified Account
                    </Badge>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleSignOut}
                  disabled={signOutLoading}
                >
                  {signOutLoading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <LogOut className="w-4 h-4 mr-2" />
                  )}
                  Sign Out
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Account Information */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              <User className="w-5 h-5 mr-2" />
              Account Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">User ID</p>
                <p className="text-sm font-mono mt-1">{user.id}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Role</p>
                <p className="text-sm mt-1">{user.role || 'User'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Created At</p>
                <p className="text-sm mt-1 flex items-center">
                  <Calendar className="w-3 h-3 mr-1" />
                  {formatDate(user.created_at)}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Last Sign In</p>
                <p className="text-sm mt-1 flex items-center">
                  <Clock className="w-3 h-3 mr-1" />
                  {formatDate(user.last_sign_in_at)}
                </p>
              </div>
            </div>

            <Separator />

            {/* Provider Information */}
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Authentication Method</p>
              <div className="flex flex-wrap gap-2">
                {identities.map((identity, index) => (
                  <Badge key={index} variant="outline">
                    <Shield className="w-3 h-3 mr-1" />
                    {identity.provider === 'google' ? 'Google' : identity.provider}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Additional Metadata */}
            {userMetadata.email_verified && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">Email Status</p>
                <Badge variant="default" className="mt-1">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Email Verified
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Session Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Shield className="w-5 h-5 mr-2" />
              Session Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Session Status</p>
                <Badge variant={session ? "default" : "secondary"} className="mt-1">
                  {session ? 'Active Session' : 'No Active Session'}
                </Badge>
              </div>
              {session && (
                <>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Session Expires</p>
                    <p className="text-sm mt-1">
                      {session.expires_at ? formatDate(new Date(session.expires_at * 1000).toISOString()) : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Access Token</p>
                    <p className="text-sm font-mono mt-1 truncate bg-muted p-2 rounded">
                      {session.access_token.substring(0, 30)}...
                    </p>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Developer Info (Optional - Remove in production) */}
        {process.env.NODE_ENV === 'development' && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-sm">Developer Info</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-xs overflow-auto bg-muted p-2 rounded">
                {JSON.stringify({ user: user, session: session }, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}