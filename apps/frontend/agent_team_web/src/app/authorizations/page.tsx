"use client";

import React, { Suspense } from "react";
import Image from "next/image";
import { useSearchParams } from "next/navigation";
import {
  Shield,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ExternalLink,
  Clock,
  RefreshCw,
} from "lucide-react";
import { useIntegrationsApi } from "@/lib/api/hooks/useIntegrationsApi";
import { useAuth } from "@/contexts/auth-context";
import { useToast } from "@/hooks/use-toast";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// Provider icon mapping
const providerIcons: Record<string, string> = {
  github: "/icons/github.svg",
  slack: "/icons/slack.svg",
  notion: "/icons/notion.svg",
  google: "/icons/google-calendar.svg",
  google_calendar: "/icons/google-calendar.svg",
};

// Separate component that uses useSearchParams
function AuthorizationsContent() {
  const { session, loading: authLoading } = useAuth();
  const { integrations, isLoading, isError, error, mutate } = useIntegrationsApi();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  const handleRefresh = () => {
    mutate();
  };

  const handleConnect = (installUrl: string) => {
    window.location.href = installUrl;
  };

  React.useEffect(() => {
    const provider = searchParams.get("provider");
    const success = searchParams.get("success");

    if (provider && success === "true") {
      toast({
        title: "Connection Successful",
        description: `${provider.charAt(0).toUpperCase() + provider.slice(1)} has been connected successfully.`,
        variant: "default",
      });
      mutate();
      window.history.replaceState({}, "", "/authorizations");
    } else if (provider && success === "false") {
      const errorMsg = searchParams.get("error") || "Unknown error";
      toast({
        title: "Connection Failed",
        description: `Failed to connect ${provider}: ${errorMsg}`,
        variant: "destructive",
      });
      window.history.replaceState({}, "", "/authorizations");
    }
  }, [searchParams, toast, mutate]);

  React.useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        mutate();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [mutate]);

  // Add icon_url to integrations
  const allProviders = React.useMemo(() => {
    return integrations.map((integration) => ({
      ...integration,
      icon_url: providerIcons[integration.provider],
    }));
  }, [integrations]);

  const getTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;

    return date.toLocaleDateString();
  };

  // Skeleton Loading Component
  const SkeletonCard = () => (
    <Card className="overflow-hidden rounded-2xl border bg-card text-card-foreground shadow-sm transition-shadow duration-300 flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="relative h-12 w-12 overflow-hidden rounded-lg bg-white dark:bg-gray-800 p-1">
              <div className="h-full w-full bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            </div>
            <div className="flex-1">
              <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-2" />
              <div className="h-5 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col flex-1">
        <div className="flex-1">
          <div className="h-3 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-1.5" />
          <div className="space-y-1.5">
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-4/5" />
          </div>
        </div>
        <div className="flex justify-end mt-4">
          <div className="h-8 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        </div>
      </CardContent>
    </Card>
  );

  // Loading state
  if (authLoading || (isLoading && allProviders.length === 0)) {
    return (
      <div className="h-full">
        <div className="px-6 pt-16 pb-6">
          {/* Connected Section Skeleton */}
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              <div className="h-5 w-6 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          </div>

          {/* Available Section Skeleton */}
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <XCircle className="w-4 h-4 text-gray-500" />
              <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              <div className="h-5 w-6 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!session) {
    return (
      <div className="h-full flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <Shield className="w-12 h-12 mx-auto mb-4 text-primary" />
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>
              Please sign in to manage your authorizations
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  // Error state
  if (isError && !isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 mx-auto mb-4 text-destructive" />
          <p className="text-destructive mb-2">
            {error?.message || "Failed to load integrations"}
          </p>
          <Button onClick={handleRefresh}>Retry</Button>
        </div>
      </div>
    );
  }

  // Group providers by connection status
  const connectedProviders = allProviders.filter((p) => p.is_connected);
  const availableProviders = allProviders.filter((p) => !p.is_connected);

  return (
    <div className="h-full">
      <div className="px-6 pt-16 pb-6">

        {/* Connected Integrations */}
        {connectedProviders.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <h2 className="text-sm font-medium">Connected</h2>
              <Badge variant="outline" className="text-xs">
                {connectedProviders.length}
              </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {connectedProviders.map((provider) => (
                <Card
                  key={provider.provider}
                  className="overflow-hidden rounded-2xl border bg-card text-card-foreground shadow-sm transition-shadow duration-300 hover:shadow-md relative"
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="relative h-12 w-12 overflow-hidden rounded-lg bg-white p-1">
                          {provider.icon_url ? (
                            <Image
                              src={provider.icon_url}
                              alt={`${provider.name} icon`}
                              fill
                              className="object-contain"
                              loading="lazy"
                            />
                          ) : (
                            <div className="h-full w-full flex items-center justify-center bg-primary/10">
                              <Shield className="w-6 h-6 text-primary" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1">
                          <h3 className="text-sm font-semibold leading-tight text-foreground">
                            {provider.name}
                          </h3>
                          <div className="mt-1.5">
                            <Badge
                              variant="outline"
                              className="font-medium text-[10px] px-1 py-0 text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-950 dark:border-green-800"
                            >
                              Connected
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    <div>
                      <h4 className="text-xs font-medium text-foreground mb-1.5">
                        Description
                      </h4>
                      <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
                        {provider.description || "No description available"}
                      </p>
                    </div>

                    {provider.connection && provider.connection.created_at && (
                      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3 h-3" />
                          <span>{getTimeAgo(provider.connection.created_at)}</span>
                        </div>
                        {provider.connection.updated_at &&
                          provider.connection.updated_at !==
                          provider.connection.created_at && (
                          <>
                            <span className="text-border">•</span>
                            <div className="flex items-center gap-1.5">
                              <RefreshCw className="w-3 h-3" />
                              <span>{getTimeAgo(provider.connection.updated_at)}</span>
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Available Integrations */}
        {availableProviders.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <XCircle className="w-4 h-4 text-gray-500" />
              <h2 className="text-sm font-medium">Available</h2>
              <Badge variant="outline" className="text-xs">
                {availableProviders.length}
              </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {availableProviders.map((provider) => (
                <Card
                  key={provider.provider}
                  className="overflow-hidden rounded-2xl border bg-card text-card-foreground shadow-sm transition-shadow duration-300 hover:shadow-md flex flex-col"
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="relative h-12 w-12 overflow-hidden rounded-lg bg-white p-1">
                          {provider.icon_url ? (
                            <Image
                              src={provider.icon_url}
                              alt={`${provider.name} icon`}
                              fill
                              className="object-contain"
                              loading="lazy"
                            />
                          ) : (
                            <div className="h-full w-full flex items-center justify-center bg-primary/10">
                              <Shield className="w-6 h-6 text-primary" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1">
                          <h3 className="text-sm font-semibold leading-tight text-foreground">
                            {provider.name}
                          </h3>
                          <div className="mt-1.5">
                            <Badge
                              variant="outline"
                              className="font-medium text-[10px] px-1 py-0 text-gray-600 bg-gray-50 border-gray-200 dark:text-gray-400 dark:bg-gray-950 dark:border-gray-800"
                            >
                              Not Connected
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="flex flex-col flex-1">
                    <div className="flex-1">
                      <h4 className="text-xs font-medium text-foreground mb-1.5">
                        Description
                      </h4>
                      <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
                        {provider.description || "No description available"}
                      </p>
                    </div>

                    <div className="flex justify-end mt-4">
                      <Button
                        size="sm"
                        onClick={() => handleConnect(provider.install_url)}
                      >
                        Connect
                        <ExternalLink className="w-3 h-3 ml-2" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

// Main page component with Suspense boundary
function AuthorizationsPage() {
  return (
    <Suspense fallback={
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 mx-auto mb-4 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    }>
      <AuthorizationsContent />
    </Suspense>
  );
}

export default AuthorizationsPage;
