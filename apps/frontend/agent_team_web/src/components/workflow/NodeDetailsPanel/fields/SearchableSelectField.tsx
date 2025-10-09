"use client";

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { Loader2, AlertCircle, Search, ExternalLink, X, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { humanizeKey } from '@/utils/nodeHelpers';
import { useAuth } from '@/contexts/auth-context';
import { useAuthSWR } from '@/lib/api/fetcher';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import Link from 'next/link';

interface SearchOption {
  value: string;
  label: string;
  description?: string;
  url?: string;
}

interface NotionPageInfo {
  id: string;
  title: string;
  url: string;
  icon?: Record<string, unknown>;
  cover?: Record<string, unknown>;
  created_time?: string;
  last_edited_time?: string;
  parent?: Record<string, unknown>;
}

interface SearchResponse {
  results?: NotionPageInfo[];
  has_more?: boolean;
  next_cursor?: string;
}

interface SearchableSelectFieldProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  searchEndpoint: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  error?: string;
  className?: string;
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export const SearchableSelectField: React.FC<SearchableSelectFieldProps> = ({
  name,
  value,
  onChange,
  searchEndpoint,
  label,
  placeholder,
  required,
  readonly,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);
  const { session } = useAuth();
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [options, setOptions] = useState<SearchOption[]>([]);
  const [selectedOption, setSelectedOption] = useState<SearchOption | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Debounce search query
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // Build initial fetch URL (empty query to detect OAuth errors immediately)
  const initialFetchUrl = useMemo(() => {
    if (!searchEndpoint) return null;
    return `${searchEndpoint}?limit=30`;
  }, [searchEndpoint]);

  // Use SWR for initial fetch to detect OAuth errors immediately
  const { data: initialData, error: swrError, isLoading: swrLoading } = useAuthSWR<SearchResponse>(
    initialFetchUrl,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      shouldRetryOnError: false,
    }
  );

  // Parse Notion page results to options
  const parseNotionPages = useCallback((pages: NotionPageInfo[]): SearchOption[] => {
    return pages.map((page) => ({
      value: page.id,
      label: page.title || 'Untitled',
      description: page.url ? `Last edited: ${page.last_edited_time ? new Date(page.last_edited_time).toLocaleDateString() : 'Unknown'}` : undefined,
      url: page.url,
    }));
  }, []);

  // Load initial data from SWR
  useEffect(() => {
    if (initialData?.results) {
      const parsedOptions = parseNotionPages(initialData.results);
      setOptions(parsedOptions);
    }
  }, [initialData, parseNotionPages]);

  // Manual fetch for search (when user types)
  const [isSearching, setIsSearching] = useState(false);
  const fetchSearchResults = useCallback(async (query: string) => {
    if (!session?.access_token || !query) return;

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsSearching(true);

    try {
      const searchParams = new URLSearchParams();
      searchParams.set('query', query);
      searchParams.set('limit', '30');

      const url = `${searchEndpoint}?${searchParams.toString()}`;

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      if (response.ok) {
        const data: SearchResponse = await response.json();
        if (data.results) {
          const parsedOptions = parseNotionPages(data.results);
          setOptions(parsedOptions);
        } else {
          setOptions([]);
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        console.error('Search failed:', err);
      }
    } finally {
      setIsSearching(false);
      abortControllerRef.current = null;
    }
  }, [session?.access_token, searchEndpoint, parseNotionPages]);

  // Fetch results when search query changes
  useEffect(() => {
    if (open && debouncedSearchQuery) {
      fetchSearchResults(debouncedSearchQuery);
    } else if (open && !debouncedSearchQuery && initialData) {
      // Reset to initial results when search is cleared
      if (initialData.results) {
        setOptions(parseNotionPages(initialData.results));
      }
    }
  }, [debouncedSearchQuery, open, fetchSearchResults, initialData, parseNotionPages]);

  // Load selected option details if we have a value
  useEffect(() => {
    if (value && !selectedOption) {
      const existingOption = options.find(opt => opt.value === value);
      if (existingOption) {
        setSelectedOption(existingOption);
      } else if (value) {
        // Value exists but not in options - create placeholder
        setSelectedOption({
          value,
          label: `Page: ${value.substring(0, 8)}...`,
        });
      }
    }
  }, [value, selectedOption, options]);

  const handleSelect = (selectedValue: string) => {
    const selected = options.find(opt => opt.value === selectedValue);
    if (selected) {
      setSelectedOption(selected);
      onChange(selectedValue);
      console.log('SearchableSelectField: Selected value:', selectedValue, 'Option:', selected);
    }
    setOpen(false);
    setSearchQuery('');
  };

  const handleClear = () => {
    setSelectedOption(null);
    onChange('');
  };

  // Check for OAuth errors (from SWR)
  const errorWithStatus = swrError as Error & { status?: number };
  const errorStatus = errorWithStatus?.status;
  const isOAuthError = errorStatus === 412;
  const isAuthExpired = errorStatus === 401;

  // OAuth not connected error
  if (isOAuthError) {
    const provider = searchEndpoint.includes('/notion/') ? 'Notion' :
                     searchEndpoint.includes('/slack/') ? 'Slack' : 'Integration';

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
            <Link href="/authorizations" className="flex items-center gap-1 text-sm underline">
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

  return (
    <div className={cn('space-y-2', className)}>
      <Label htmlFor={name}>
        {displayLabel}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <div className="relative">
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={open}
              className={cn(
                "w-full justify-between",
                !selectedOption && "text-muted-foreground",
                error && "border-destructive"
              )}
              disabled={readonly}
            >
              <div className="flex items-center gap-2 flex-1 overflow-hidden">
                <Search className="h-4 w-4 flex-shrink-0" />
                <span className="truncate">
                  {selectedOption ? selectedOption.label : (placeholder || "Search pages...")}
                </span>
              </div>
              <ChevronDown className="h-4 w-4 opacity-50" />
            </Button>
            {selectedOption && !readonly && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-10 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClear();
                }}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          className="w-[400px] p-0"
          align="start"
          onCloseAutoFocus={(e) => e.preventDefault()}
        >
          <div className="flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Search input */}
            <div className="p-3 border-b" onClick={(e) => e.stopPropagation()}>
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search pages..."
                  value={searchQuery}
                  onChange={(e) => {
                    e.stopPropagation();
                    setSearchQuery(e.target.value);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  onKeyDown={(e) => e.stopPropagation()}
                  className="pl-8"
                  autoFocus
                />
              </div>
            </div>

            {/* Results */}
            <ScrollArea className="h-[300px]">
              {(swrLoading || isSearching) && (
                <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Searching...</span>
                </div>
              )}

              {!swrLoading && !isSearching && swrError && !isOAuthError && !isAuthExpired && (
                <div className="flex items-center gap-2 p-4 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  <span>Failed to search: {swrError.message}</span>
                </div>
              )}

              {!swrLoading && !isSearching && !swrError && options.length === 0 && (
                <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
                  {searchQuery ? 'No pages found.' : 'No pages available.'}
                </div>
              )}

              {!swrLoading && !isSearching && options.length > 0 && (
                <div className="py-1">
                  {options.map((option) => (
                    <DropdownMenuItem
                      key={option.value}
                      onSelect={(e) => {
                        e.preventDefault();
                        handleSelect(option.value);
                      }}
                      className="cursor-pointer"
                    >
                      <div className="flex flex-col gap-1 flex-1">
                        <span className="font-medium text-sm">{option.label}</span>
                        {option.description && (
                          <span className="text-xs text-muted-foreground">
                            {option.description}
                          </span>
                        )}
                      </div>
                    </DropdownMenuItem>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
      {selectedOption && (
        <div className="text-xs text-muted-foreground">
          Selected: {selectedOption.label}
        </div>
      )}
    </div>
  );
};
