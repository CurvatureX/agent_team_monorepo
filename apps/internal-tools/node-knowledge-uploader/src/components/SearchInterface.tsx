"use client";

import { useState, useEffect, useCallback } from "react";

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

// Available node types for filtering (from database schema)
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
      // Network errors
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

      // HTTP status-based errors
      if (response) {
        const retryAfter = response.headers.get("Retry-After");
        const retryAfterSeconds = retryAfter ? parseInt(retryAfter) : undefined;

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
              retryAfter: retryAfterSeconds || 60,
            };
          case 503:
            return {
              message:
                "Search service is temporarily unavailable. Please try again in a few minutes.",
              type: "service_unavailable",
              retryable: true,
              retryAfter: retryAfterSeconds || 300,
            };
          case 500:
          case 502:
          case 504:
            return {
              message: "Server error occurred. Please try again in a moment.",
              type: "server",
              retryable: true,
              retryAfter: retryAfterSeconds || 30,
            };
          default:
            return {
              message: "An unexpected error occurred. Please try again.",
              type: "server",
              retryable: true,
            };
        }
      }

      // Default error
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
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

        const response = await fetch("/api/query", {
          method: "GET",
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        const status: ApiStatus = await response.json();
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

    // Initial check
    checkApiStatus();

    // Listen for online/offline events
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
        // Sort by timestamp (most recent first) and ensure we have valid data
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

  // Save recent queries to localStorage with timestamp and result count
  const saveRecentQuery = useCallback(
    (query: string, resultCount: number) => {
      try {
        const newQueryItem: QueryHistoryItem = {
          query,
          timestamp: Date.now(),
          resultCount,
        };

        // Remove any existing query with the same text and add the new one at the front
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

  // Enhanced query validation with real-time feedback
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

      // Check for potentially problematic characters
      if (/[<>{}[\\]/.test(trimmedQuery)) {
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

  // Enhanced search with retry logic and comprehensive error handling
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

      // Check if we should wait before retrying
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
              ?
              {
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
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

        // Include filtering parameters in the request
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
            ?
            {
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
      searchState.error,
      searchState.nodeTypeFilter,
      searchState.similarityThreshold,
    ]
  );

  // Handle search form submission
  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (searchState.query.trim()) {
        performSearch(searchState.query);
      }
    },
    [searchState.query, performSearch]
  );

  // Retry search with exponential backoff
  const retrySearch = useCallback(() => {
    if (searchState.query.trim()) {
      performSearch(searchState.query, true);
    }
  },
  [searchState.query, performSearch]);

  // Handle query input change with real-time validation
  const handleQueryChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newQuery = e.target.value;

      // Real-time validation for immediate feedback
      const validation = validateQuery(newQuery);

      setSearchState((prev) => ({
        ...prev,
        query: newQuery,
        error: !validation.isValid ? validation.error || null : null,
      }));
    },
    [validateQuery]
  );

  // Handle recent query click
  const handleRecentQueryClick = useCallback(
    (query: string) => {
      setSearchState((prev) => ({ ...prev, query }));
      performSearch(query);
    },
    [performSearch]
  );

  // Remove individual query from history
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

  // Clear all recent queries
  const clearRecentQueries = useCallback(() => {
    try {
      localStorage.removeItem("nodeKnowledgeRecentQueries");
      setSearchState((prev) => ({ ...prev, recentQueries: [] }));
    } catch (error) {
      console.error("Error clearing recent queries:", error);
    }
  },
  []);

  // Toggle result expansion
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
  },
  []);

  // Apply client-side filters to search results
  const applyClientSideFilters = useCallback(
    (results: SearchResult[]) => {
      let filtered = results;

      // Apply similarity threshold filter
      filtered = filtered.filter(
        (result) => result.similarity >= searchState.similarityThreshold
      );

      // Apply node type filter (if not already applied server-side)
      if (searchState.nodeTypeFilter && searchState.nodeTypeFilter !== "") {
        filtered = filtered.filter(
          (result) => result.node_type === searchState.nodeTypeFilter
        );
      }

      return filtered;
    },
    [searchState.similarityThreshold, searchState.nodeTypeFilter]
  );

  // Update filtered results when filters change
  useEffect(() => {
    if (searchState.results.length > 0) {
      const filtered = applyClientSideFilters(searchState.results);
      setSearchState((prev) => ({
        ...prev,
        filteredResults: filtered,
      }));
      onResultsChange?.(filtered.length);
    }
  },
  [
    searchState.results,
    searchState.similarityThreshold,
    searchState.nodeTypeFilter,
    applyClientSideFilters,
    onResultsChange,
  ]);

  // Handle node type filter change
  const handleNodeTypeFilterChange = useCallback((nodeType: string) => {
    setSearchState((prev) => ({
      ...prev,
      nodeTypeFilter: nodeType,
    }));
  },
  []);

  // Handle similarity threshold change
  const handleSimilarityThresholdChange = useCallback((threshold: number) => {
    setSearchState((prev) => ({
      ...prev,
      similarityThreshold: threshold,
    }));
  },
  []);

  // Clear results and reset filters
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
  },
  [onResultsChange]);

  // Dismiss error
  const dismissError = useCallback(() => {
    setSearchState((prev) => ({
      ...prev,
      error: null,
    }));
  },
  []);

  // Format timestamp for display
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
  },
  []);

  // Format similarity score as percentage
  const formatSimilarityScore = useCallback((similarity: number): string => {
    return `${Math.round(similarity * 100)}%`;
  },
  []);

  // Enhanced keyword highlighting with better word boundary detection
  const highlightKeywords = useCallback(
    (text: string, query: string): string => {
      if (!query.trim()) return text;

      const keywords = query.trim().toLowerCase().split(/\s+/);
      let highlightedText = text;

      keywords.forEach((keyword) => {
        if (keyword.length > 2) {
          // Use word boundaries for more accurate highlighting
          const regex = new RegExp(
            `\\b(${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\"use client";

import { useState, useEffect, useCallback } from "react";

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

// Available node types for filtering (from database schema)
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
      // Network errors
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

      // HTTP status-based errors
      if (response) {
        const retryAfter = response.headers.get("Retry-After");
        const retryAfterSeconds = retryAfter ? parseInt(retryAfter) : undefined;

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
              retryAfter: retryAfterSeconds || 60,
            };
          case 503:
            return {
              message:
                "Search service is temporarily unavailable. Please try again in a few minutes.",
              type: "service_unavailable",
              retryable: true,
              retryAfter: retryAfterSeconds || 300,
            };
          case 500:
          case 502:
          case 504:
            return {
              message: "Server error occurred. Please try again in a moment.",
              type: "server",
              retryable: true,
              retryAfter: retryAfterSeconds || 30,
            };
          default:
            return {
              message: "An unexpected error occurred. Please try again.",
              type: "server",
              retryable: true,
            };
        }
      }

      // Default error
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
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

        const response = await fetch("/api/query", {
          method: "GET",
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        const status: ApiStatus = await response.json();
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

    // Initial check
    checkApiStatus();

    // Listen for online/offline events
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
        // Sort by timestamp (most recent first) and ensure we have valid data
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

  // Save recent queries to localStorage with timestamp and result count
  const saveRecentQuery = useCallback(
    (query: string, resultCount: number) => {
      try {
        const newQueryItem: QueryHistoryItem = {
          query,
          timestamp: Date.now(),
          resultCount,
        };

        // Remove any existing query with the same text and add the new one at the front
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

  // Enhanced query validation with real-time feedback
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

      // Check for potentially problematic characters
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

  // Enhanced search with retry logic and comprehensive error handling
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

      // Check if we should wait before retrying
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
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

        // Include filtering parameters in the request
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
      searchState.error,
      searchState.nodeTypeFilter,
      searchState.similarityThreshold,
    ]
  );

  // Handle search form submission
  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (searchState.query.trim()) {
        performSearch(searchState.query);
      }
    },
    [searchState.query, performSearch]
  );

  // Retry search with exponential backoff
  const retrySearch = useCallback(() => {
    if (searchState.query.trim()) {
      performSearch(searchState.query, true);
    }
  }, [searchState.query, performSearch]);

  // Handle query input change with real-time validation
  const handleQueryChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newQuery = e.target.value;

      // Real-time validation for immediate feedback
      const validation = validateQuery(newQuery);

      setSearchState((prev) => ({
        ...prev,
        query: newQuery,
        error: !validation.isValid ? validation.error || null : null,
      }));
    },
    [validateQuery]
  );

  // Handle recent query click
  const handleRecentQueryClick = useCallback(
    (query: string) => {
      setSearchState((prev) => ({ ...prev, query }));
      performSearch(query);
    },
    [performSearch]
  );

  // Remove individual query from history
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

  // Clear all recent queries
  const clearRecentQueries = useCallback(() => {
    try {
      localStorage.removeItem("nodeKnowledgeRecentQueries");
      setSearchState((prev) => ({ ...prev, recentQueries: [] }));
    } catch (error) {
      console.error("Error clearing recent queries:", error);
    }
  }, []);

  // Toggle result expansion
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

  // Apply client-side filters to search results
  const applyClientSideFilters = useCallback(
    (results: SearchResult[]) => {
      let filtered = results;

      // Apply similarity threshold filter
      filtered = filtered.filter(
        (result) => result.similarity >= searchState.similarityThreshold
      );

      // Apply node type filter (if not already applied server-side)
      if (searchState.nodeTypeFilter && searchState.nodeTypeFilter !== "") {
        filtered = filtered.filter(
          (result) => result.node_type === searchState.nodeTypeFilter
        );
      }

      return filtered;
    },
    [searchState.similarityThreshold, searchState.nodeTypeFilter]
  );

  // Update filtered results when filters change
  useEffect(() => {
    if (searchState.results.length > 0) {
      const filtered = applyClientSideFilters(searchState.results);
      setSearchState((prev) => ({
        ...prev,
        filteredResults: filtered,
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

  // Handle node type filter change
  const handleNodeTypeFilterChange = useCallback((nodeType: string) => {
    setSearchState((prev) => ({
      ...prev,
      nodeTypeFilter: nodeType,
    }));
  }, []);

  // Handle similarity threshold change
  const handleSimilarityThresholdChange = useCallback((threshold: number) => {
    setSearchState((prev) => ({
      ...prev,
      similarityThreshold: threshold,
    }));
  }, []);

  // Clear results and reset filters
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

  // Dismiss error
  const dismissError = useCallback(() => {
    setSearchState((prev) => ({
      ...prev,
      error: null,
    }));
  }, []);

  // Format timestamp for display
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

  // Format similarity score as percentage
  const formatSimilarityScore = useCallback((similarity: number): string => {
    return `${Math.round(similarity * 100)}%`;
  }, []);

  // Enhanced keyword highlighting with better word boundary detection
  const highlightKeywords = useCallback(
    (text: string, query: string): string => {
      if (!query.trim()) return text;

      const keywords = query.trim().toLowerCase().split(/\s+/);
      let highlightedText = text;

      keywords.forEach((keyword) => {
        if (keyword.length > 2) {
          // Use word boundaries for more accurate highlighting
          const regex = new RegExp(
            `\\b(${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})\\b`,
            "gi"
          );
          highlightedText = highlightedText.replace(
            regex,
            '<mark class="bg-yellow-200 px-1 rounded font-medium">$1</mark>'
          );
        }
      });

      return highlightedText;
    },
    []
  );

  // Group results by node type for visual organization
  const groupResultsByType = useCallback((results: SearchResult[]) => {
    const grouped = results.reduce((acc, result) => {
      const key = result.node_type;
      if (!acc[key]) {
        acc[key] = [];
      }
      acc[key].push(result);
      return acc;
    }, {} as Record<string, SearchResult[]>);

    // Sort groups by the highest similarity score in each group
    return Object.entries(grouped).sort(([, a], [, b]) => {
      const maxA = Math.max(...a.map((r) => r.similarity));
      const maxB = Math.max(...b.map((r) => r.similarity));
      return maxB - maxA;
    });
  }, []);

  // Parse and format metadata for better display
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

  // Generate search refinement suggestions based on current results
  const generateRefinementSuggestions = useCallback(() => {
    if (searchState.filteredResults.length === 0) return [];

    const suggestions: string[] = [];
    const nodeTypes = [
      ...new Set(searchState.filteredResults.map((r) => r.node_type)),
    ];
    const avgSimilarity =
      searchState.filteredResults.reduce((sum, r) => sum + r.similarity, 0) /
      searchState.filteredResults.length;

    // Suggest more specific queries if results are too broad
    if (searchState.filteredResults.length > 10) {
      if (nodeTypes.length > 1) {
        suggestions.push(
          `Try filtering by a specific node type like "${nodeTypes[0]}"`
        );
      }
      suggestions.push("Try a more specific query to narrow down results");
    }

    // Suggest broader queries if results are too few
    if (
      searchState.filteredResults.length < 3 &&
      searchState.results.length > searchState.filteredResults.length
    ) {
      suggestions.push(
        "Try lowering the similarity threshold to see more results"
      );
    }

    // Suggest related searches based on common node types
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

    // Suggest quality improvements
    if (avgSimilarity < 0.6) {
      suggestions.push("Try using different keywords or more specific terms");
    }

    return suggestions.slice(0, 3); // Limit to 3 suggestions
  }, [searchState.filteredResults, searchState.results]);

  // Get available node types from current results for filter dropdown
  const getAvailableNodeTypes = useCallback(() => {
    const typesInResults = [
      ...new Set(searchState.results.map((r) => r.node_type)),
    ];
    return NODE_TYPES.filter(
      (type) => type.value === "" || typesInResults.includes(type.value)
    );
  }, [searchState.results]);

  return (
    <div className="space-y-6">
      {/* Search Header with Service Status */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Search Node Knowledge
          </h2>

          {/* Service Status Indicator */}
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

        {/* Service degradation warning */}
        {searchState.apiStatus && !searchState.apiStatus.available && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
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

        {/* Search Form */}
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

              {/* Real-time validation indicator */}
              {searchState.query.length > 0 && (
                <div
                  className={`w-2 h-2 rounded-full ${
                    validateQuery(searchState.query).isValid
                      ? "bg-green-500"
                      : "bg-red-500"
                  }`}
                />
              )}
            </div>
          </div>

          {/* Enhanced error display with recovery options */}
          {searchState.error && (
            <div
              className={`text-sm p-3 rounded-lg border ${
                searchState.error.type === "validation"
                  ? "text-amber-700 bg-amber-50 border-amber-200"
                  : "text-red-700 bg-red-50 border-red-200"
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {searchState.error.type === "validation" ? (
                    <svg
                      className="w-4 h-4 text-amber-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
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

                  {/* Retry information */}
                  {searchState.error.retryAfter && (
                    <p className="text-xs mt-1 opacity-75">
                      You can retry in {searchState.error.retryAfter} seconds.
                    </p>
                  )}

                  {/* Retry count */}
                  {searchState.retryCount > 0 && (
                    <p className="text-xs mt-1 opacity-75">
                      Retry attempt: {searchState.retryCount}
                    </p>
                  )}
                </div>

                <div className="flex-shrink-0 flex gap-2">
                  {/* Retry button for retryable errors */}
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
                    >
                      Retry
                    </button>
                  )}

                  {/* Dismiss button */}
                  <button
                    onClick={dismissError}
                    className="px-2 py-1 text-xs hover:bg-white hover:bg-opacity-50 rounded transition-colors"
                    title="Dismiss error"
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

            {/* Retry button for failed searches */}
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
              >
                Clear Results
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Recent Queries */}
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
                    title="Remove from history"
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

      {/* Example Queries */}
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
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

      {/* Search Results with Visual Grouping */}
      {searchState.results.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Search Results ({searchState.results.length} found)
            </h3>
          </div>

          <div className="space-y-6">
            {groupResultsByType(searchState.results).map(
              ([nodeType, results]) => (
                <div key={nodeType} className="space-y-3">
                  {/* Node Type Group Header */}
                  {groupResultsByType(searchState.results).length > 1 && (
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

                  {/* Results in this group */}
                  <div className="space-y-3">
                    {results.map((result) => (
                      <div
                        key={result.id}
                        className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
                      >
                        {/* Result Header */}
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <div className="flex items-center gap-2">
                                {groupResultsByType(searchState.results)
                                  .length === 1 && (
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

                              {/* Similarity Score */}
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
                                      : `${result.description.substring(
                                          0,
                                          150
                                        )}${
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
                          >
                            {searchState.expandedResults.has(result.id) ? (
                              <>
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

                        {/* Expanded Content */}
                        {searchState.expandedResults.has(result.id) && (
                          <div className="mt-4 pt-4 border-t border-gray-200">
                            <div className="space-y-4">
                              {/* Full Content Section */}
                              <div>
                                <h5 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
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

                              {/* Enhanced Metadata Display */}
                              {result.metadata &&
                                Object.keys(result.metadata).length > 0 && (
                                  <div>
                                    <h5 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
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
                                          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        />
                                      </svg>
                                      Additional Information
                                    </h5>
                                    <div className="bg-gray-50 p-3 rounded-md">
                                      {Object.entries(
                                        formatMetadata(result.metadata)
                                      ).map(([key, value]) => (
                                        <div
                                          key={key}
                                          className="mb-3 last:mb-0"
                                        >
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
              )
            )}
          </div>
        </div>
      )}

      {/* No Results Message */}
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
                  Try searching for node types like &quot;AI Agent&quot; or
                  &quot;Workflow&quot;
                </li>
              </ul>
            </div>
          </div>
        )}
    </div>
  );
}")})\\b`,
            "gi"
          );
          highlightedText = highlightedText.replace(
            regex,
            '<mark class="bg-yellow-200 px-1 rounded font-medium">$1</mark>'
          );
        }
      });

      return highlightedText;
    },
    []
  );

  // Group results by node type for visual organization
  const groupResultsByType = useCallback((results: SearchResult[]) => {
    const grouped = results.reduce((acc, result) => {
      const key = result.node_type;
      if (!acc[key]) {
        acc[key] = [];
      }
      acc[key].push(result);
      return acc;
    }, {} as Record<string, SearchResult[]>);

    // Sort groups by the highest similarity score in each group
    return Object.entries(grouped).sort(([, a], [, b]) => {
      const maxA = Math.max(...a.map((r) => r.similarity));
      const maxB = Math.max(...b.map((r) => r.similarity));
      return maxB - maxA;
    });
  },
  []);

  // Parse and format metadata for better display
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
  },
  []);

  // Generate search refinement suggestions based on current results
  const generateRefinementSuggestions = useCallback(() => {
    if (searchState.filteredResults.length === 0) return [];

    const suggestions: string[] = [];
    const nodeTypes = [
      ...new Set(searchState.filteredResults.map((r) => r.node_type)),
    ];
    const avgSimilarity =
      searchState.filteredResults.reduce((sum, r) => sum + r.similarity, 0) /
      searchState.filteredResults.length;

    // Suggest more specific queries if results are too broad
    if (searchState.filteredResults.length > 10) {
      if (nodeTypes.length > 1) {
        suggestions.push(
          `Try filtering by a specific node type like "${nodeTypes[0]}"`
        );
      }
      suggestions.push("Try a more specific query to narrow down results");
    }

    // Suggest broader queries if results are too few
    if (
      searchState.filteredResults.length < 3 &&
      searchState.results.length > searchState.filteredResults.length
    ) {
      suggestions.push(
        "Try lowering the similarity threshold to see more results"
      );
    }

    // Suggest related searches based on common node types
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

    // Suggest quality improvements
    if (avgSimilarity < 0.6) {
      suggestions.push("Try using different keywords or more specific terms");
    }

    return suggestions.slice(0, 3); // Limit to 3 suggestions
  },
  [searchState.filteredResults, searchState.results]);

  // Get available node types from current results for filter dropdown
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
  },
  [searchState.results]);

  return (
    <div className="space-y-6">
      {/* Search Header with Service Status */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Search Node Knowledge
          </h2>

          {/* Service Status Indicator */}
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

        {/* Service degradation warning */}
        {searchState.apiStatus && !searchState.apiStatus.available && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
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

        {/* Search Form */}
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

              {/* Real-time validation indicator */}
              {searchState.query.length > 0 && (
                <div
                  className={`w-2 h-2 rounded-full ${
                    validateQuery(searchState.query).isValid
                      ? "bg-green-500"
                      : "bg-red-500"
                  }`}
                />
              )}
            </div>
          </div>

          {/* Enhanced error display with recovery options */}
          {searchState.error && (
            <div
              className={`text-sm p-3 rounded-lg border ${
                searchState.error.type === "validation"
                  ? "text-amber-700 bg-amber-50 border-amber-200"
                  : "text-red-700 bg-red-50 border-red-200"
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {searchState.error.type === "validation" ? (
                    <svg
                      className="w-4 h-4 text-amber-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
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

                  {/* Retry information */}
                  {searchState.error.retryAfter && (
                    <p className="text-xs mt-1 opacity-75">
                      You can retry in {searchState.error.retryAfter} seconds.
                    </p>
                  )}

                  {/* Retry count */}
                  {searchState.retryCount > 0 && (
                    <p className="text-xs mt-1 opacity-75">
                      Retry attempt: {searchState.retryCount}
                    </p>
                  )}
                </div>

                <div className="flex-shrink-0 flex gap-2">
                  {/* Retry button for retryable errors */}
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
                    >
                      Retry
                    </button>
                  )}

                  {/* Dismiss button */}
                  <button
                    onClick={dismissError}
                    className="px-2 py-1 text-xs hover:bg-white hover:bg-opacity-50 rounded transition-colors"
                    title="Dismiss error"
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

            {/* Retry button for failed searches */}
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
              >
                Clear Results
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Recent Queries */}
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
                    title="Remove from history"
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

      {/* Example Queries */}
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
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

      {/* Search Results with Visual Grouping */}
      {searchState.results.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Search Results ({searchState.filteredResults.length} of{" "}
              {searchState.results.length} found)
            </h3>
          </div>

          {/* Filter and Refinement Section */}
          <div className="bg-gray-50 p-4 rounded-lg mb-4 border border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
              {/* Node Type Filter */}
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
                >
                  {getAvailableNodeTypes().map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Similarity Threshold Slider */}
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
                />
              </div>
            </div>

            {/* Refinement Suggestions */}
            {searchState.showRefinementSuggestions &&
              generateRefinementSuggestions().length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Refinement Suggestions:
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {generateRefinementSuggestions().map(
                      (suggestion, index) => (
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
                        >
                          {suggestion}
                        </button>
                      )
                    )}
                  </div>
                </div>
              )}
          </div>

          <div className="space-y-6">
            {groupResultsByType(searchState.filteredResults).map(
              ([nodeType, results]) => (
                <div key={nodeType} className="space-y-3">
                  {/* Node Type Group Header */}
                  {groupResultsByType(searchState.filteredResults).length >
                    1 && (
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

                  {/* Results in this group */}
                  <div className="space-y-3">
                    {results.map((result) => (
                      <div
                        key={result.id}
                        className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
                      >
                        {/* Result Header */}
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <div className="flex items-center gap-2">
                                {groupResultsByType(searchState.filteredResults)
                                  .length === 1 && (
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

                              {/* Similarity Score */}
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
                                      : `${result.description.substring(
                                          0,
                                          150
                                        )}${
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
                          >
                            {searchState.expandedResults.has(result.id) ? (
                              <>
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

                        {/* Expanded Content */}
                        {searchState.expandedResults.has(result.id) && (
                          <div className="mt-4 pt-4 border-t border-gray-200">
                            <div className="space-y-4">
                              {/* Full Content Section */}
                              <div>
                                <h5 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
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

                              {/* Enhanced Metadata Display */}
                              {result.metadata &&
                                Object.keys(result.metadata).length > 0 && (
                                  <div>
                                    <h5 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
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
                                          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        />
                                      </svg>
                                      Additional Information
                                    </h5>
                                    <div className="bg-gray-50 p-3 rounded-md">
                                      {Object.entries(
                                        formatMetadata(result.metadata)
                                      ).map(([key, value]) => (
                                        <div
                                          key={key}
                                          className="mb-3 last:mb-0"
                                        >
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
              )
            )}
          </div>
        </div>
      )}

      {/* No Results Message */}
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
                  Try searching for node types like &quot;AI Agent&quot; or
                  &quot;Workflow&quot;
                </li>
              </ul>
            </div>
          </div>
        )}
    </div>
  );
}
