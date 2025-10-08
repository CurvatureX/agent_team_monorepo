"use client";

import React, { useMemo, useState, useCallback, useEffect } from 'react';
import { Loader2, AlertCircle, RefreshCw, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import { humanizeKey } from '@/utils/nodeHelpers';
import { useAuthSWR } from '@/lib/api/fetcher';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import Link from 'next/link';

interface DynamicOption {
  value: string;
  label: string;
  description?: string;
}

interface SlackChannelInfo {
  id: string;
  name: string;
  name_normalized?: string;
  is_private?: boolean;
  is_member?: boolean;
  num_members?: number;
  topic?: { value?: string };
  purpose?: { value?: string };
}

interface NotionDatabaseInfo {
  id: string;
  title: string;
  description?: string;
  url: string;
  icon?: Record<string, any>;
  cover?: Record<string, any>;
  created_time?: string;
  last_edited_time?: string;
}

interface DynamicOptionsResponse {
  options?: DynamicOption[];
  channels?: SlackChannelInfo[]; // Slack-specific response
  databases?: NotionDatabaseInfo[]; // Notion-specific response
  success?: boolean;
  next_cursor?: string;
  has_more?: boolean;
}

interface DynamicSelectFieldProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  apiEndpoint: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  error?: string;
  className?: string;
}

// Debounce utility
function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      const id = setTimeout(() => callback(...args), delay);
      setTimeoutId(id);
    },
    [callback, delay, timeoutId]
  );
}

export const DynamicSelectField: React.FC<DynamicSelectFieldProps> = ({
  name,
  value,
  onChange,
  apiEndpoint,
  label,
  placeholder,
  required,
  readonly,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);
  const [allOptions, setAllOptions] = useState<DynamicOption[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Build URL with cursor for pagination
  const fetchUrl = useMemo(() => {
    if (!apiEndpoint) return null;
    return apiEndpoint;
  }, [apiEndpoint]);

  // Fetch options from API using SWR with retry logic
  const { data, error: fetchError, isLoading, mutate } = useAuthSWR<DynamicOptionsResponse>(
    fetchUrl,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      shouldRetryOnError: true,
      errorRetryCount: 3,
      errorRetryInterval: 5000,
      onSuccess: (responseData) => {
        if (responseData) {
          setNextCursor(responseData.next_cursor || null);
        }
      },
    }
  );

  // Parse options from response
  const parseOptions = useCallback((responseData: DynamicOptionsResponse): DynamicOption[] => {
    if (!responseData) return [];

    // Handle standard "options" format
    if (responseData.options) {
      return responseData.options.map((opt) => {
        if (typeof opt === 'string') {
          return { value: opt, label: opt };
        }
        return opt;
      });
    }

    // Handle Slack "channels" format
    if (responseData.channels) {
      return responseData.channels.map((channel: SlackChannelInfo) => {
        // Build description from channel metadata
        const descParts: string[] = [];
        if (channel.is_private) descParts.push('Private');
        if (channel.is_member) descParts.push('Member');
        if (channel.num_members) descParts.push(`${channel.num_members} members`);

        const description = descParts.length > 0 ? descParts.join(' • ') : undefined;

        return {
          value: channel.name,  // Use channel name as value (backend stores names, not IDs)
          label: channel.name,  // Show channel name without prefix
          description,
        };
      });
    }

    // Handle Notion "databases" format
    if (responseData.databases) {
      return responseData.databases.map((database: NotionDatabaseInfo) => {
        // Use database description or truncated description as secondary info
        const description = database.description
          ? (database.description.length > 60
              ? database.description.substring(0, 60) + '...'
              : database.description)
          : undefined;

        return {
          value: database.id,  // Use database ID as value
          label: database.title || 'Untitled Database',  // Show database title
          description,
        };
      });
    }

    return [];
  }, []);

  // Update all options when data changes
  useEffect(() => {
    if (data) {
      const newOptions = parseOptions(data);
      setAllOptions(newOptions);
    }
  }, [data, parseOptions]);

  // Load more options (pagination)
  const handleLoadMore = useCallback(async () => {
    if (!nextCursor || isLoadingMore) return;

    setIsLoadingMore(true);
    try {
      const cursorParam = nextCursor ? `${apiEndpoint.includes('?') ? '&' : '?'}cursor=${nextCursor}` : '';
      const response = await fetch(`${apiEndpoint}${cursorParam}`, {
        headers: {
          'Authorization': `Bearer ${(window as any).authToken || ''}`,
        },
      });

      if (response.ok) {
        const moreData: DynamicOptionsResponse = await response.json();
        const moreOptions = parseOptions(moreData);
        setAllOptions(prev => [...prev, ...moreOptions]);
        setNextCursor(moreData.next_cursor || null);
      }
    } catch (err) {
      console.error('Failed to load more options:', err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [nextCursor, apiEndpoint, parseOptions, isLoadingMore]);

  // Debounced refresh handler
  const debouncedRefresh = useDebouncedCallback(() => {
    setRefreshing(true);
    setAllOptions([]);
    setNextCursor(null);
    mutate().finally(() => {
      setTimeout(() => setRefreshing(false), 500);
    });
  }, 300);

  const handleRefresh = () => {
    if (!refreshing) {
      debouncedRefresh();
    }
  };

  // Find display label for current value
  const currentValueLabel = useMemo(() => {
    if (!value) return null;

    const option = allOptions.find(opt => opt.value === value);
    if (option) return option.label;

    // Fallback for deleted/unknown options
    return `(Unknown: ${value})`;
  }, [value, allOptions]);

  // Check for specific error types
  const errorStatus = (fetchError as any)?.status;
  const isOAuthError = errorStatus === 412;
  const isAuthExpired = errorStatus === 401;

  // Initial loading state (only show on first load, not during refresh)
  if (isLoading && !refreshing && allOptions.length === 0) {
    return (
      <div className={cn('space-y-2', className)}>
        <Label htmlFor={name}>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <div className="flex items-center gap-2 p-3 border rounded-md bg-muted/50">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Loading options...</span>
        </div>
      </div>
    );
  }

  // OAuth not connected error
  if (isOAuthError) {
    const provider = apiEndpoint.includes('/slack/') ? 'Slack' :
                     apiEndpoint.includes('/notion/') ? 'Notion' :
                     apiEndpoint.includes('/github/') ? 'GitHub' : 'Integration';

    return (
      <div className={cn('space-y-2', className)}>
        <Label htmlFor={name}>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{provider} not connected. Please connect your account first.</span>
            <Link href="/integrations" className="flex items-center gap-1 text-sm underline">
              Connect <ExternalLink className="h-3 w-3" />
            </Link>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Auth expired error
  if (isAuthExpired) {
    return (
      <div className={cn('space-y-2', className)}>
        <Label htmlFor={name}>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Your session has expired. Please refresh the page and sign in again.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Other error states
  if (fetchError && !refreshing) {
    return (
      <div className={cn('space-y-2', className)}>
        <Label htmlFor={name}>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <div className="flex items-center justify-between gap-2 p-3 border border-destructive rounded-md bg-destructive/10">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-destructive" />
            <span className="text-sm text-destructive">
              Failed to load options: {fetchError.message}
            </span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={cn("h-3 w-3 mr-1", refreshing && "animate-spin")} />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  // Empty options state (but don't show if we have a value - might be loading)
  if (allOptions.length === 0 && !isLoading && !value) {
    return (
      <div className={cn('space-y-2', className)}>
        <Label htmlFor={name}>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <div className="flex items-center justify-between gap-2 p-3 border rounded-md bg-muted/50">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">No options available</span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={cn("h-3 w-3 mr-1", refreshing && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>
    );
  }

  // Success state - render select (show even during refresh/loading more)
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between">
        <Label htmlFor={name}>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          className="h-6 px-2"
          disabled={readonly || refreshing}
        >
          <RefreshCw className={cn("h-3 w-3", refreshing && "animate-spin")} />
        </Button>
      </div>
      <Select
        value={value || ''}
        onValueChange={onChange}
        disabled={readonly || isLoading}
      >
        <SelectTrigger className={cn(error ? 'border-destructive' : '', isLoading && 'opacity-70')}>
          <SelectValue placeholder={placeholder || "Select an option..."}>
            {value && currentValueLabel ? currentValueLabel : placeholder || "Select an option..."}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {/* Show loading indicator if refreshing */}
          {refreshing && (
            <div className="flex items-center justify-center gap-2 py-2 text-sm text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Refreshing...</span>
            </div>
          )}

          {/* Show current value if it's not in options (deleted channel) */}
          {value && !allOptions.some(opt => opt.value === value) && (
            <SelectItem value={value} disabled>
              <div className="flex items-center gap-2">
                <AlertCircle className="h-3 w-3 text-amber-500" />
                <span className="text-amber-600">{currentValueLabel}</span>
              </div>
            </SelectItem>
          )}

          {/* Regular options */}
          {allOptions.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              <div className="flex flex-col">
                <span>{option.label}</span>
                {option.description && (
                  <span className="text-xs text-muted-foreground">
                    {option.description}
                  </span>
                )}
              </div>
            </SelectItem>
          ))}

          {/* Load more button for pagination */}
          {nextCursor && (
            <div className="p-2 border-t">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleLoadMore}
                disabled={isLoadingMore}
                className="w-full"
              >
                {isLoadingMore ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                    Loading more...
                  </>
                ) : (
                  <>Load more options</>
                )}
              </Button>
            </div>
          )}
        </SelectContent>
      </Select>
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Loaded {allOptions.length} option{allOptions.length !== 1 ? 's' : ''}
          {nextCursor && ' (more available)'}
        </span>
        {value && !allOptions.some(opt => opt.value === value) && (
          <span className="text-amber-600">⚠️ Selected option may no longer exist</span>
        )}
      </div>
    </div>
  );
};
