"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import sanitizeHtml from "sanitize-html"; // Added for XSS protection

// TypeScript interfaces based on the design document
interface SearchResult {
  id: string;
  node_type: string;
  node_subtype: string | null;
  title: string;
  description: string;
  content: string;
  similarity: number;
  metadata: Record<string, unknown>;
}

interface QueryResponse {
  success: boolean;
  results: SearchResult[];
  query: string;
  processingTime: number;
  totalCount: number;
  error?: string;
}

interface ApiStatus {
  available: boolean;
  openaiAvailable?: boolean;
  databaseAvailable?: boolean;
  totalNodes: number;
  message?: string;
  error?: string;
}

interface ErrorState {
  message: string;
  type:
    | "validation"
    | "network"
    | "server"
    | "rate_limit"
    | "service_unavailable";
  retryable: boolean;
  retryAfter?: number;
  lastRetry?: number;
}

interface SearchInterfaceProps {
  initialQuery?: string;
  onResultsChange?: (count: number) => void;
}

interface QueryHistoryItem {
  query: string;
  timestamp: number;
  resultCount: number;
}

interface SearchState {
  query: string;
  results: SearchResult[];
  filteredResults: SearchResult[];
  loading: boolean;
  filterLoading: boolean; // Added for filter loading state
  error: ErrorState | null;
  recentQueries: QueryHistoryItem[];
  expandedResults: Set<string>;
  apiStatus: ApiStatus | null;
  retryCount: number;
  nodeTypeFilter: string;
  similarityThreshold: number;
  showRefinementSuggestions: boolean;
}

const EXAMPLE_QUERIES = [
  "workflow nodes for data processing",
  "AI agent capabilities",
  "trigger node functionality",
  "memory management nodes",
  "human in the loop processes",
];

const MAX_QUERY_LENGTH = 1000;
const MIN_QUERY_LENGTH = 3;

const NODE_TYPES = [
  { value: "", label: "All Node Types" },
  { value: "TRIGGER", label: "Trigger Nodes" },
  { value: "AI_AGENT", label: "AI Agent Nodes" },
  { value: "EXTERNAL_ACTION", label: "External Action Nodes" },
  { value: "ACTION", label: "Action Nodes" },
  { value: "FLOW", label: "Flow Nodes" },
  { value: "HUMAN_IN_THE_LOOP", label: "Human in the Loop Nodes" },
  { value: "TOOL", label: "Tool Nodes" },
  { value: "MEMORY", label: "Memory Nodes" },
];

const DEFAULT_SIMILARITY_THRESHOLD = 0.3;
const MIN_SIMILARITY_THRESHOLD = 0.1;
const MAX_SIMILARITY_THRESHOLD = 0.9;

export default function SearchInterface({
  initialQuery = "",
  onResultsChange,
}: SearchInterfaceProps) {
  const [searchState, setSearchState] = useState<SearchState>({
    query: initialQuery,
    results: [],
    filteredResults: [],
    loading: false,
    filterLoading: false,
    error: null,
    recentQueries: [],
    expandedResults: new Set(),
    apiStatus: null,
    retryCount: 0,
    nodeTypeFilter: "",
    similarityThreshold: DEFAULT_SIMILARITY_THRESHOLD,
    showRefinementSuggestions: false,
  });

  // Enhanced error classification
  const classifyError = useCallback(
    (error: any, response?: Response): ErrorState => {
      if (!navigator.onLine) {
        return {
          message:
            "You're currently offline. Please check your internet connection and try again.",
          type: "network",
          retryable: true,
        };
      }

      if (error.name === "TypeError" && error.message.includes("fetch")) {
        return {
          message:
            "Network connection failed. Please check your internet connection and try again.",
          type: "network",
          retryable: true,
        };
      }

      if (response) {
        const retryAfterHeader = response.headers.get("Retry-After");
        const retryAfterSeconds = retryAfterHeader
          ? Number(retryAfterHeader)
          : undefined;

        switch (response.status) {
          case 400:
            return {
              message:
                "Invalid search query. Please check your input and try again.",
              type: "validation",
              retryable: false,
            };
          case 429:
            return {
              message:
                "Too many requests. Please wait a moment before searching again.",
              type: "rate_limit",
              retryable: true,
              retryAfter: Number.isFinite(retryAfterSeconds)
                ? retryAfterSeconds
                : 60,
            };
          case 503:
            return {
              message:
                "Search service is temporarily unavailable. Please try again in a few minutes.",
              type: "service_unavailable",
              retryable: true,
              retryAfter: Number.isFinite(retryAfterSeconds)
                ? retryAfterSeconds
                : 300,
            };
          case 500:
          case 502:
          case 504:
            return {
              message: "Server error occurred. Please try again in a moment.",
              type: "server",
              retryable: true,
              retryAfter: Number.isFinite(retryAfterSeconds)
                ? retryAfterSeconds
                : 30,
            };
          default:
            return {
              message: "An unexpected error occurred. Please try again.",
              type: "server",
              retryable: true,
            };
        }
      }

      return {
        message: "An unexpected error occurred. Please try again.",
        type: "server",
        retryable: true,
      };
    },
    []
  );

  // Check API status on component mount and handle online/offline events
  useEffect(() => {
    const checkApiStatus = async () => {
      if (!navigator.onLine) {
        setSearchState((prev) => ({
          ...prev,
          apiStatus: {
            available: false,
            totalNodes: 0,
            error: "You are currently offline",
          },
        }));
        return;
      }

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch("/api/query", {
          method: "GET",
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        let status: ApiStatus;
        try {
          status = await response.json();
        } catch {
          throw new Error("Invalid API status response");
        }
        setSearchState((prev) => ({ ...prev, apiStatus: status }));
      } catch (error) {
        console.error("Failed to check API status:", error);
        setSearchState((prev) => ({
          ...prev,
          apiStatus: {
            available: false,
            totalNodes: 0,
            error: "Failed to check service status",
          },
        }));
      }
    };

    checkApiStatus();

    const handleOnline = () => {
      console.log("Connection restored, checking API status...");
      checkApiStatus();
    };

    const handleOffline = () => {
      console.log("Connection lost");
      setSearchState((prev) => ({
        ...prev,
        apiStatus: {
          available: false,
          totalNodes: prev.apiStatus?.totalNodes || 0,
          error: "You are currently offline",
        },
        error: prev.loading
          ? {
              message:
                "Connection lost. Please check your internet connection and try again.",
              type: "network",
              retryable: true,
            }
          : prev.error,
      }));
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // Load recent queries from localStorage on component mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem("nodeKnowledgeRecentQueries");
      if (stored) {
        const recentQueries: QueryHistoryItem[] = JSON.parse(stored);
        const validQueries = recentQueries
          .filter((item) => item.query && typeof item.timestamp === "number")
          .sort((a, b) => b.timestamp - a.timestamp)
          .slice(0, 5);
        setSearchState((prev) => ({ ...prev, recentQueries: validQueries }));
      }
    } catch (error) {
      console.error("Error loading recent queries:", error);
    }
  }, []);

  const saveRecentQuery = useCallback(
    (query: string, resultCount: number) => {
      try {
        const newQueryItem: QueryHistoryItem = {
          query,
          timestamp: Date.now(),
          resultCount,
        };

        const updatedQueries = [
          newQueryItem,
          ...searchState.recentQueries.filter((q) => q.query !== query),
        ].slice(0, 5);

        localStorage.setItem(
          "nodeKnowledgeRecentQueries",
          JSON.stringify(updatedQueries)
        );
        setSearchState((prev) => ({ ...prev, recentQueries: updatedQueries }));
      } catch (error) {
        console.error("Error saving recent query:", error);
      }
    },
    [searchState.recentQueries]
  );

  const validateQuery = useCallback(
    (query: string): { isValid: boolean; error?: ErrorState } => {
      const trimmedQuery = query.trim();

      if (trimmedQuery.length === 0) {
        return {
          isValid: false,
          error: {
            message: "Please enter a search query",
            type: "validation",
            retryable: false,
          },
        };
      }

      if (trimmedQuery.length < MIN_QUERY_LENGTH) {
        return {
          isValid: false,
          error: {
            message: `Query must be at least ${MIN_QUERY_LENGTH} characters long`,
            type: "validation",
            retryable: false,
          },
        };
      }

      if (trimmedQuery.length > MAX_QUERY_LENGTH) {
        return {
          isValid: false,
          error: {
            message: `Query must be less than ${MAX_QUERY_LENGTH} characters`,
            type: "validation",
            retryable: false,
          },
        };
      }

      if (/[<>{}[\]\\]/.test(trimmedQuery)) {
        return {
          isValid: false,
          error: {
            message:
              "Query contains invalid characters. Please use only letters, numbers, and basic punctuation.",
            type: "validation",
            retryable: false,
          },
        };
      }

      return { isValid: true };
    },
    []
  );

  const performSearch = useCallback(
    async (query: string, isRetry = false) => {
      const validation = validateQuery(query);
      if (!validation.isValid) {
        setSearchState((prev) => ({
          ...prev,
          error: validation.error || null,
        }));
        return;
      }

      if (
        isRetry &&
        searchState.error?.retryAfter &&
        searchState.error.lastRetry
      ) {
        const timeSinceLastRetry = Date.now() - searchState.error.lastRetry;
        const waitTime =
          searchState.error.retryAfter * 1000 - timeSinceLastRetry;

        if (waitTime > 0) {
          setSearchState((prev) => ({
            ...prev,
            error: prev.error
              ? {
                  ...prev.error,
                  message: `Please wait ${Math.ceil(
                    waitTime / 1000
                  )} more seconds before retrying.`,
                }
              : null,
          }));
          return;
        }
      }

      setSearchState((prev) => ({
        ...prev,
        loading: true,
        error: null,
        results: [],
        filteredResults: [],
        retryCount: isRetry ? prev.retryCount + 1 : 0,
        showRefinementSuggestions: false,
      }));

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);

        const requestBody = {
          query: query.trim(),
          nodeTypeFilter: searchState.nodeTypeFilter || undefined,
          threshold: searchState.similarityThreshold,
        };

        const response = await fetch("/api/query", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        let data: QueryResponse;
        try {
          data = await response.json();
        } catch (parseError) {
          throw new Error("Invalid response from server");
        }

        if (response.ok && data.success) {
          const filteredResults = applyClientSideFilters(data.results);
          setSearchState((prev) => ({
            ...prev,
            results: data.results,
            filteredResults,
            loading: false,
            expandedResults: new Set(),
            retryCount: 0,
            showRefinementSuggestions: data.results.length > 0,
          }));
          saveRecentQuery(query.trim(), filteredResults.length);
          onResultsChange?.(filteredResults.length);
        } else {
          const errorState = data.error
            ? {
                message: data.error,
                type: "server" as const,
                retryable: true,
                lastRetry: Date.now(),
              }
            : classifyError(new Error("Search failed"), response);

          setSearchState((prev) => ({
            ...prev,
            error: errorState,
            loading: false,
            results: [],
            filteredResults: [],
          }));
        }
      } catch (error) {
        console.error("Search error:", error);

        let errorState: ErrorState;

        if (error instanceof Error && error.name === "AbortError") {
          errorState = {
            message:
              "Search request timed out. Please try again with a shorter query.",
            type: "network",
            retryable: true,
          };
        } else {
          errorState = classifyError(error);
          errorState.lastRetry = Date.now();
        }

        setSearchState((prev) => ({
          ...prev,
          error: errorState,
          loading: false,
          results: [],
          filteredResults: [],
        }));
      }
    },
    [
      validateQuery,
      saveRecentQuery,
      onResultsChange,
      classifyError,
      searchState.nodeTypeFilter,
      searchState.similarityThreshold,
      searchState.error?.retryAfter,
      searchState.error?.lastRetry,
    ]
  );

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (searchState.query.trim()) {
        performSearch(searchState.query);
      }
    },
    [searchState.query, performSearch]
  );

  const retrySearch = useCallback(() => {
    if (searchState.query.trim()) {
      performSearch(searchState.query, true);
    }
  }, [searchState.query, performSearch]);

  const handleQueryChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newQuery = e.target.value;
      const validation = validateQuery(newQuery);
      setSearchState((prev) => ({
        ...prev,
        query: newQuery,
        error: !validation.isValid ? validation.error || null : null,
      }));
    },
    [validateQuery]
  );

  const handleRecentQueryClick = useCallback(
    (query: string) => {
      setSearchState((prev) => ({ ...prev, query }));
      performSearch(query);
    },
    [performSearch]
  );

  const removeRecentQuery = useCallback(
    (queryToRemove: string) => {
      try {
        const updatedQueries = searchState.recentQueries.filter(
          (q) => q.query !== queryToRemove
        );
        localStorage.setItem(
          "nodeKnowledgeRecentQueries",
          JSON.stringify(updatedQueries)
        );
        setSearchState((prev) => ({ ...prev, recentQueries: updatedQueries }));
      } catch (error) {
        console.error("Error removing recent query:", error);
      }
    },
    [searchState.recentQueries]
  );

  const clearRecentQueries = useCallback(() => {
    try {
      localStorage.removeItem("nodeKnowledgeRecentQueries");
      setSearchState((prev) => ({ ...prev, recentQueries: [] }));
    } catch (error) {
      console.error("Error clearing recent queries:", error);
    }
  }, []);

  const toggleResultExpansion = useCallback((resultId: string) => {
    setSearchState((prev) => {
      const newExpanded = new Set(prev.expandedResults);
      if (newExpanded.has(resultId)) {
        newExpanded.delete(resultId);
      } else {
        newExpanded.add(resultId);
      }
      return { ...prev, expandedResults: newExpanded };
    });
  }, []);

  const applyClientSideFilters = useCallback(
    (results: SearchResult[]) => {
      let filtered = results;

      filtered = filtered.filter(
        (result) => result.similarity >= searchState.similarityThreshold
      );

      if (searchState.nodeTypeFilter && searchState.nodeTypeFilter !== "") {
        filtered = filtered.filter(
          (result) => result.node_type === searchState.nodeTypeFilter
        );
      }

      return filtered;
    },
    [searchState.similarityThreshold, searchState.nodeTypeFilter]
  );

  useEffect(() => {
    if (searchState.results.length > 0) {
      setSearchState((prev) => ({ ...prev, filterLoading: true }));
      const filtered = applyClientSideFilters(searchState.results);
      setSearchState((prev) => ({
        ...prev,
        filteredResults: filtered,
        filterLoading: false,
      }));
      onResultsChange?.(filtered.length);
    }
  }, [
    searchState.results,
    searchState.similarityThreshold,
    searchState.nodeTypeFilter,
    applyClientSideFilters,
    onResultsChange,
  ]);

  const handleNodeTypeFilterChange = useCallback((nodeType: string) => {
    setSearchState((prev) => ({
      ...prev,
      nodeTypeFilter: nodeType,
    }));
  }, []);

  const handleSimilarityThresholdChange = useCallback((threshold: number) => {
    setSearchState((prev) => ({
      ...prev,
      similarityThreshold: threshold,
    }));
  }, []);

  const clearResults = useCallback(() => {
    setSearchState((prev) => ({
      ...prev,
      query: "",
      results: [],
      filteredResults: [],
      error: null,
      expandedResults: new Set(),
      retryCount: 0,
      nodeTypeFilter: "",
      similarityThreshold: DEFAULT_SIMILARITY_THRESHOLD,
      showRefinementSuggestions: false,
    }));
    onResultsChange?.(0);
  }, [onResultsChange]);

  const dismissError = useCallback(() => {
    setSearchState((prev) => ({
      ...prev,
      error: null,
    }));
  }, []);

  const formatTimestamp = useCallback((timestamp: number): string => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(timestamp).toLocaleDateString();
  }, []);

  const formatSimilarityScore = useCallback((similarity: number): string => {
    return `${Math.round(similarity * 100)}%`;
  }, []);

  const highlightKeywords = useCallback(
    (text: string, query: string): string => {
      if (!query.trim()) return sanitizeHtml(text);

      const keywords = query.trim().toLowerCase().split(/\s+/);
      let highlightedText = sanitizeHtml(text);

      keywords.forEach((keyword) => {
        if (keyword.length > 2) {
          const regex = new RegExp(
            `\\b(${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})\\b`,
            "gi"
          );
          highlightedText = highlightedText.replace(
            regex,
            '<mark class="bg-yellow-200 dark:bg-yellow-800 px-1 rounded font-medium">$1</mark>'
          );
        }
      });

      return highlightedText;
    },
    []
  );

  const groupResultsByType = useCallback((results: SearchResult[]) => {
    const grouped = results.reduce<Record<string, SearchResult[]>>((acc, result) => {
      const nodeType = result.node_type || 'Unknown';
      if (!acc[nodeType]) {
        acc[nodeType] = [];
      }
      acc[nodeType].push(result);
      return acc;
    }, {});

    return Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b));
  }, []);

  const groupedResults = useMemo(
    () => groupResultsByType(searchState.filteredResults),
    [searchState.filteredResults, groupResultsByType]
  );

  const formatMetadata = useCallback((metadata: Record<string, unknown>) => {
    const formatted: Record<string, string | string[]> = {};

    Object.entries(metadata).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        formatted[key] = value.map(String);
      } else if (typeof value === "object" && value !== null) {
        formatted[key] = JSON.stringify(value, null, 2);
      } else {
        formatted[key] = String(value);
      }
    });

    return formatted;
  }, []);

  const generateRefinementSuggestions = useCallback(() => {
    if (searchState.filteredResults.length === 0) return [];

    const suggestions: string[] = [];
    const nodeTypes = [
      ...new Set(searchState.filteredResults.map((r) => r.node_type)),
    ];
    const avgSimilarity =
      searchState.filteredResults.reduce((sum, r) => sum + r.similarity, 0) /
      searchState.filteredResults.length;

    if (searchState.filteredResults.length > 10) {
      if (nodeTypes.length > 1) {
        suggestions.push(
          `Try filtering by a specific node type like "${nodeTypes[0]}"`
        );
      }
      suggestions.push("Try a more specific query to narrow down results");
    }

    if (
      searchState.filteredResults.length < 3 &&
      searchState.results.length > searchState.filteredResults.length
    ) {
      suggestions.push(
        "Try lowering the similarity threshold to see more results"
      );
    }

    if (nodeTypes.includes("AI_AGENT")) {
      suggestions.push(
        "Try searching for 'AI agent workflows' or 'intelligent automation'"
      );
    }
    if (nodeTypes.includes("TRIGGER")) {
      suggestions.push(
        "Try searching for 'workflow triggers' or 'event-driven automation'"
      );
    }
    if (nodeTypes.includes("MEMORY")) {
      suggestions.push(
        "Try searching for 'data persistence' or 'workflow state management'"
      );
    }

    if (avgSimilarity < 0.6) {
      suggestions.push("Try using different keywords or more specific terms");
    }

    return suggestions.slice(0, 3);
  }, [searchState.filteredResults, searchState.results]);

  const getAvailableNodeTypes = useCallback(() => {
    const typesInResults = new Set(searchState.results.map((r) => r.node_type));

    const availableNodeTypes = NODE_TYPES.filter(
      (type) => type.value === "" || typesInResults.has(type.value)
    );

    return availableNodeTypes.map((type) => {
      const count =
        type.value === ""
          ? searchState.results.length
          : searchState.results.filter((r) => r.node_type === type.value)
              .length;
      return { ...type, label: `${type.label} (${count})` };
    });
  }, [searchState.results]);

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Search Node Knowledge
          </h2>

          {searchState.apiStatus && (
            <div className="flex items-center gap-2 text-sm">
              <div
                className={`w-2 h-2 rounded-full ${
                  searchState.apiStatus.available
                    ? "bg-green-500"
                    : "bg-red-500"
                }`}
              />
              <span
                className={`${
                  searchState.apiStatus.available
                    ? "text-green-700"
                    : "text-red-700"
                }`}
              >
                {searchState.apiStatus.available
                  ? `Service Online (${searchState.apiStatus.totalNodes} nodes)`
                  : "Service Issues"}
              </span>
            </div>
          )}
        </div>

        {searchState.apiStatus && !searchState.apiStatus.available && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 15.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
              <div>
                <h3 className="font-medium text-yellow-800 mb-1">
                  Service Partially Available
                </h3>
                <p className="text-sm text-yellow-700">
                  {!searchState.apiStatus.openaiAvailable &&
                  !searchState.apiStatus.databaseAvailable
                    ? "Both search and database services are currently unavailable. Please try again later."
                    : !searchState.apiStatus.openaiAvailable
                    ? "AI search processing is currently unavailable. Please try again later."
                    : !searchState.apiStatus.databaseAvailable
                    ? "Database is currently unavailable. Please try again later."
                    : "Some features may be limited. Please try again if you experience issues."}
                </p>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSearch} className="space-y-4">
          <div className="relative">
            <input
              type="text"
              value={searchState.query}
              onChange={handleQueryChange}
              placeholder="Enter your search query (e.g., 'workflow nodes for data processing')"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={searchState.loading}
              maxLength={MAX_QUERY_LENGTH}
              aria-describedby={searchState.error ? "search-error" : undefined}
            />
            <div className="absolute right-3 top-3 flex items-center gap-2">
              <span
                className={`text-sm ${
                  searchState.query.length > MAX_QUERY_LENGTH * 0.9
                    ? "text-red-500"
                    : searchState.query.length > MAX_QUERY_LENGTH * 0.7
                    ? "text-yellow-500"
                    : "text-gray-400"
                }`}
              >
                {searchState.query.length}/{MAX_QUERY_LENGTH}
              </span>

              {searchState.query.length > 0 && (
                <div
                  className={`w-2 h-2 rounded-full ${
                    validateQuery(searchState.query).isValid
                      ? "bg-green-500"
                      : "bg-red-500"
                  }`}
                  aria-label={
                    validateQuery(searchState.query).isValid
                      ? "Valid query"
                      : "Invalid query"
                  }
                />
              )}
            </div>
          </div>

          {searchState.error && (
            <div
              id="search-error"
              className={`text-sm p-3 rounded-lg border ${
                searchState.error.type === "validation"
                  ? "text-amber-700 bg-amber-50 border-amber-200"
                  : "text-red-700 bg-red-50 border-red-200"
              }`}
              role="alert"
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {searchState.error.type === "validation" ? (
                    <svg
                      className="w-4 h-4 text-amber-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 15.5c-.77.833.192 2.5 1.732 2.5z"
                      />
                    </svg>
                  ) : searchState.error.type === "network" ? (
                    <svg
                      className="w-4 h-4 text-red-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="w-4 h-4 text-red-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 15.5c-.77.833.192 2.5 1.732 2.5z"
                      />
                    </svg>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-medium mb-1">
                    {searchState.error.type === "validation"
                      ? "Input Error"
                      : searchState.error.type === "network"
                      ? "Connection Error"
                      : searchState.error.type === "rate_limit"
                      ? "Rate Limited"
                      : searchState.error.type === "service_unavailable"
                      ? "Service Unavailable"
                      : "Search Error"}
                  </p>
                  <p className="text-sm">{searchState.error.message}</p>

                  {searchState.error.retryAfter && (
                    <p className="text-xs mt-1 opacity-75">
                      You can retry in {searchState.error.retryAfter} seconds.
                    </p>
                  )}

                  {searchState.retryCount > 0 && (
                    <p className="text-xs mt-1 opacity-75">
                      Retry attempt: {searchState.retryCount}
                    </p>
                  )}
                </div>

                <div className="flex-shrink-0 flex gap-2">
                  {searchState.error.retryable && !searchState.loading && (
                    <button
                      onClick={retrySearch}
                      className="px-3 py-1 text-xs bg-white border border-current rounded hover:bg-gray-50 transition-colors"
                      disabled={
                        searchState.error.retryAfter &&
                        searchState.error.lastRetry &&
                        Date.now() - searchState.error.lastRetry <
                          searchState.error.retryAfter * 1000
                      }
                      aria-label="Retry search"
                    >
                      Retry
                    </button>
                  )}

                  <button
                    onClick={dismissError}
                    className="px-2 py-1 text-xs hover:bg-white hover:bg-opacity-50 rounded transition-colors"
                    aria-label="Dismiss error"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={
                searchState.loading ||
                !searchState.query.trim() ||
                !validateQuery(searchState.query).isValid ||
                (searchState.apiStatus && !searchState.apiStatus.available)
              }
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
              aria-label="Submit search"
            >
              {searchState.loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Searching...
                </>
              ) : (
                <>
                  🔍 Search
                  {searchState.retryCount > 0 && (
                    <span className="text-xs bg-blue-500 px-1 rounded">
                      Retry {searchState.retryCount}
                    </span>
                  )}
                </>
              )}
            </button>

            {searchState.error?.retryable && !searchState.loading && (
              <button
                type="button"
                onClick={retrySearch}
                disabled={
                  searchState.error.retryAfter &&
                  searchState.error.lastRetry &&
                  Date.now() - searchState.error.lastRetry <
                    searchState.error.retryAfter * 1000
                }
                className="px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
                aria-label="Retry search"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Retry Search
              </button>
            )}

            {searchState.filteredResults.length > 0 && (
              <button
                type="button"
                onClick={clearResults}
                className="px-4 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                aria-label="Clear results"
              >
                Clear Results
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="bg-gray-50 p-4 rounded-lg mb-4 border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
          <div>
            <label
              htmlFor="nodeTypeFilter"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Filter by Node Type
            </label>
            <select
              id="nodeTypeFilter"
              value={searchState.nodeTypeFilter}
              onChange={(e) => handleNodeTypeFilterChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
              disabled={searchState.filterLoading}
              aria-label="Select node type filter"
            >
              {getAvailableNodeTypes().map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="similarityThreshold"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Minimum Similarity:{" "}
              {formatSimilarityScore(searchState.similarityThreshold)}
            </label>
            <input
              id="similarityThreshold"
              type="range"
              min={MIN_SIMILARITY_THRESHOLD}
              max={MAX_SIMILARITY_THRESHOLD}
              step="0.01"
              value={searchState.similarityThreshold}
              onChange={(e) =>
                handleSimilarityThresholdChange(parseFloat(e.target.value))
              }
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              disabled={searchState.filterLoading}
              aria-label={`Set minimum similarity to ${formatSimilarityScore(
                searchState.similarityThreshold
              )}`}
            />
          </div>
        </div>

        {searchState.showRefinementSuggestions &&
          generateRefinementSuggestions().length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                Refinement Suggestions:
              </h4>
              <div className="flex flex-wrap gap-2">
                {generateRefinementSuggestions().map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      if (suggestion.includes("Try filtering by")) {
                        const nodeType = suggestion.match(/"(.*?)"/)?.[1];
                        if (nodeType) handleNodeTypeFilterChange(nodeType);
                      } else if (
                        suggestion.includes("lowering the similarity")
                      ) {
                        handleSimilarityThresholdChange(
                          Math.max(
                            MIN_SIMILARITY_THRESHOLD,
                            searchState.similarityThreshold - 0.1
                          )
                        );
                      } else {
                        const newQuery = suggestion.match(/'(.*?)'/)?.[1];
                        if (newQuery) {
                          setSearchState((prev) => ({
                            ...prev,
                            query: newQuery,
                          }));
                          performSearch(newQuery);
                        }
                      }
                    }}
                    className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs hover:bg-blue-100 transition-colors"
                    aria-label={`Apply suggestion: ${suggestion}`}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}
      </div>

      {searchState.recentQueries.length > 0 &&
        searchState.results.length === 0 &&
        !searchState.loading && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-700">
                Recent Queries:
              </h3>
              <button
                onClick={clearRecentQueries}
                className="text-xs text-gray-500 hover:text-gray-700 underline"
                aria-label="Clear all recent queries"
              >
                Clear all
              </button>
            </div>
            <div className="space-y-2">
              {searchState.recentQueries.map((queryItem, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between bg-gray-50 rounded-lg p-3 hover:bg-gray-100 transition-colors"
                >
                  <button
                    onClick={() => handleRecentQueryClick(queryItem.query)}
                    className="flex-1 text-left"
                    aria-label={`Search for "${queryItem.query}"`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="text-sm text-gray-900 font-medium">
                          {queryItem.query}
                        </div>
                        <div className="text-xs text-gray-500 mt-1 flex items-center gap-3">
                          <span>{formatTimestamp(queryItem.timestamp)}</span>
                          <span>•</span>
                          <span>
                            {queryItem.resultCount} result
                            {queryItem.resultCount !== 1 ? "s" : ""}
                          </span>
                        </div>
                      </div>
                      <svg
                        className="w-4 h-4 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                        />
                      </svg>
                    </div>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeRecentQuery(queryItem.query);
                    }}
                    className="ml-3 p-1 text-gray-400 hover:text-red-500 transition-colors"
                    aria-label={`Remove "${queryItem.query}" from history`}
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

      {searchState.results.length === 0 &&
        !searchState.loading &&
        searchState.recentQueries.length === 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              Example Queries:
            </h3>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((example, index) => (
                <button
                  key={index}
                  onClick={() => handleRecentQueryClick(example)}
                  className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm hover:bg-blue-100 transition-colors"
                  aria-label={`Try example query: ${example}`}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

      {searchState.results.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Search Results ({searchState.filteredResults.length} of{" "}
              {searchState.results.length} found)
            </h3>
            {searchState.filterLoading && (
              <span className="text-sm text-gray-500 flex items-center gap-2">
                <svg
                  className="animate-spin h-4 w-4"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Filtering...
              </span>
            )}
          </div>

          <div className="space-y-6">
            {groupedResults.map(([nodeType, results]) => (
              <div key={nodeType} className="space-y-3">
                {groupedResults.length > 1 && (
                  <div className="flex items-center gap-3 pb-2 border-b border-gray-200">
                    <h4 className="text-md font-semibold text-gray-800 flex items-center gap-2">
                      <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-md text-sm font-medium">
                        {nodeType}
                      </span>
                      <span className="text-sm text-gray-500">
                        ({results.length} result
                        {results.length !== 1 ? "s" : ""})
                      </span>
                    </h4>
                  </div>
                )}

                <div className="space-y-3">
                  {results.map((result) => (
                    <div
                      key={result.id}
                      className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <div className="flex items-center gap-2">
                              {groupedResults.length === 1 && (
                                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-medium">
                                  {result.node_type}
                                </span>
                              )}
                              {result.node_subtype && (
                                <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-sm">
                                  {result.node_subtype}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-2">
                              <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-green-400 to-green-600 transition-all duration-300"
                                  style={{
                                    width: `${result.similarity * 100}%`,
                                  }}
                                />
                              </div>
                              <span className="text-sm font-medium text-green-600 min-w-[3rem]">
                                {formatSimilarityScore(result.similarity)}
                              </span>
                            </div>
                          </div>

                          <h4 className="font-semibold text-gray-900 mb-2">
                            <span
                              dangerouslySetInnerHTML={{
                                __html: highlightKeywords(
                                  result.title,
                                  searchState.query
                                ),
                              }}
                            />
                          </h4>

                          <p className="text-gray-700 text-sm leading-relaxed">
                            <span
                              dangerouslySetInnerHTML={{
                                __html: highlightKeywords(
                                  searchState.expandedResults.has(result.id)
                                    ? result.description
                                    : `${result.description.substring(0, 150)}${
                                        result.description.length > 150
                                          ? "..."
                                          : ""
                                      }`,
                                  searchState.query
                                ),
                              }}
                            />
                          </p>
                        </div>

                        <button
                          onClick={() => toggleResultExpansion(result.id)}
                          className="ml-4 px-3 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 transition-colors flex items-center gap-1"
                          aria-label={
                            searchState.expandedResults.has(result.id)
                              ? "Collapse result"
                              : "Expand result"
                          }
                        >
                          {searchState.expandedResults.has(result.id) ? (
                            <>
                              <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                aria-hidden="true"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M5 15l7-7 7 7"
                                />
                              </svg>
                              Collapse
                            </>
                          ) : (
                            <>
                              <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                aria-hidden="true"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M19 9l-7 7-7-7"
                                />
                              </svg>
                              Expand
                            </>
                          )}
                        </button>
                      </div>

                      {searchState.expandedResults.has(result.id) && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <div className="space-y-4">
                            <div>
                              <h5 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                                <svg
                                  className="w-4 h-4"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                  aria-hidden="true"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                  />
                                </svg>
                                Detailed Content
                              </h5>
                              <div
                                className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap bg-gray-50 p-3 rounded-md"
                                dangerouslySetInnerHTML={{
                                  __html: highlightKeywords(
                                    result.content,
                                    searchState.query
                                  ),
                                }}
                              />
                            </div>

                            {result.metadata &&
                              Object.keys(result.metadata).length > 0 && (
                                <div>
                                  <h5 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                                    <svg
                                      className="w-4 h-4"
                                      fill="none"
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                      aria-hidden="true"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                      />
                                    </svg>
                                    Additional Information
                                  </h5>
                                  <div className="bg-gray-50 p-3 rounded-md">
                                    {Object.entries(
                                      formatMetadata(result.metadata)
                                    ).map(([key, value]) => (
                                      <div key={key} className="mb-3 last:mb-0">
                                        <div className="font-medium text-gray-800 text-sm mb-1 capitalize">
                                          {key.replace(/_/g, " ")}:
                                        </div>
                                        {Array.isArray(value) ? (
                                          <ul className="text-sm text-gray-600 ml-4 space-y-1">
                                            {value.map((item, index) => (
                                              <li
                                                key={index}
                                                className="flex items-start gap-2"
                                              >
                                                <span className="text-gray-400 mt-1">
                                                  •
                                                </span>
                                                <span
                                                  dangerouslySetInnerHTML={{
                                                    __html: highlightKeywords(
                                                      item,
                                                      searchState.query
                                                    ),
                                                  }}
                                                />
                                              </li>
                                            ))}
                                          </ul>
                                        ) : (
                                          <div
                                            className="text-sm text-gray-600 ml-4"
                                            dangerouslySetInnerHTML={{
                                              __html: highlightKeywords(
                                                value,
                                                searchState.query
                                              ),
                                            }}
                                          />
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!searchState.loading &&
        searchState.results.length === 0 &&
        searchState.query.trim() &&
        !searchState.error && (
          <div className="text-center py-8">
            <div className="text-gray-500 mb-4">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No results found
            </h3>
            <p className="text-gray-500 mb-4">
              Try adjusting your search query or using different keywords.
            </p>
            <div className="text-sm text-gray-600">
              <p>Suggestions:</p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Use more general terms</li>
                <li>Check for typos</li>
                <li>
                  Try searching for node types like "AI Agent" or "Workflow"
                </li>
              </ul>
            </div>
          </div>
        )}
    </div>
  );
}
