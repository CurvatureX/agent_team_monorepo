import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import SearchInterface from "../SearchInterface";

// Mock fetch globally
global.fetch = jest.fn();

describe("SearchInterface", () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    // Clear localStorage
    localStorage.clear();

    // Mock the API status check and search requests
    (global.fetch as jest.Mock).mockImplementation(
      (url: string, options?: any) => {
        if (url === "/api/query" && options?.method === "GET") {
          // Mock API status check
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                available: true,
                openaiAvailable: true,
                databaseAvailable: true,
                totalNodes: 10,
                message: "Query API is ready",
              }),
          });
        }

        if (url === "/api/query" && options?.method === "POST") {
          // Mock search request - return success by default
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                results: [
                  {
                    id: "1",
                    node_type: "ACTION",
                    node_subtype: "data_processing",
                    title: "Test Node",
                    description: "Test description",
                    content: "Test content",
                    similarity: 0.85,
                    metadata: {},
                  },
                ],
                query: "test query",
                processingTime: 100,
                totalCount: 1,
              }),
          });
        }

        // Default fallback
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        });
      }
    );
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("renders search interface with initial elements", () => {
    render(<SearchInterface />);

    // Check for main heading
    expect(screen.getByText("Search Node Knowledge")).toBeInTheDocument();

    // Check for search input
    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    expect(searchInput).toBeInTheDocument();

    // Check for search button
    expect(
      screen.getByRole("button", { name: /🔍 Search/ })
    ).toBeInTheDocument();

    // Check for example queries
    expect(screen.getByText("Example Queries:")).toBeInTheDocument();
    expect(
      screen.getByText("workflow nodes for data processing")
    ).toBeInTheDocument();
  });

  it("shows character count and validates query length", () => {
    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);

    // Initially should show 0/1000
    expect(screen.getByText("0/1000")).toBeInTheDocument();

    // Type a short query
    fireEvent.change(searchInput, { target: { value: "ab" } });
    expect(screen.getByText("2/1000")).toBeInTheDocument();

    // Try to submit short query - should show validation error
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });
    fireEvent.click(searchButton);

    expect(
      screen.getByText("Query must be at least 3 characters long")
    ).toBeInTheDocument();
  });

  it("disables search button when loading", async () => {
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        results: [],
        query: "test query",
        processingTime: 100,
        totalCount: 0,
      }),
    });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    // Enter valid query
    fireEvent.change(searchInput, { target: { value: "test query" } });

    // Click search
    fireEvent.click(searchButton);

    // Button should show loading state
    expect(screen.getByText("Searching...")).toBeInTheDocument();

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /🔍 Search/})).toBeInTheDocument();
    });
  });

  it("displays search results correctly", async () => {
    const mockResults = [
      {
        id: "1",
        node_type: "AI_AGENT",
        node_subtype: "Workflow",
        title: "Test Node",
        description: "This is a test node description",
        content: "Full content of the test node",
        similarity: 0.85,
        metadata: { capabilities: ["test1", "test2"] },
      },
    ];

    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        results: mockResults,
        query: "test query",
        processingTime: 100,
        totalCount: 1,
      }),
    });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    // Enter valid query and search
    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    // Wait for results
    await waitFor(() => {
      expect(screen.getByText(/Search Results \(1 of 1 found\)/)).toBeInTheDocument();
    });

    // Check result content
    expect(screen.getByText("AI_AGENT")).toBeInTheDocument();
    expect(screen.getByText("Workflow")).toBeInTheDocument();
    // Check for highlighted "Test" in the title
    expect(screen.getByText("Test")).toBeInTheDocument();
    expect(screen.getByText("Node")).toBeInTheDocument();
    // Check for highlighted "test" in the description (case-insensitive highlighting)
    expect(screen.getByText("test")).toBeInTheDocument();
    // Check that the description contains the expected text (using partial match)
    expect(screen.getByText(/This is a.*node description/)).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument(); // Similarity score
  });

  it("handles API errors gracefully", async () => {
    // Mock API error
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error("Network error")
    );

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    // Enter valid query and search
    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    // Wait for error message
    await waitFor(() => {
      expect(
        screen.getByText("Network connection failed. Please check your internet connection and try again.")
      ).toBeInTheDocument();
    });
  });

  it("expands and collapses search results", async () => {
    const mockResults = [
      {
        id: "1",
        node_type: "AI_AGENT",
        node_subtype: "Workflow",
        title: "Test Node",
        description: "This is a test node description",
        content: "Full content of the test node with more details",
        similarity: 0.85,
        metadata: { capabilities: ["test1", "test2"] },
      },
    ];

    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        results: mockResults,
        query: "test query",
        processingTime: 100,
        totalCount: 1,
      }),
    });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    // Enter valid query and search
    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    // Wait for results
    await waitFor(() => {
      expect(screen.getByText(/Search Results \(1 of 1 found\)/)).toBeInTheDocument();
    });

    // Initially should show Expand button
    const expandButton = screen.getByRole("button", { name: /Expand/ });
    expect(expandButton).toBeInTheDocument();

    // Click expand
    fireEvent.click(expandButton);

    // Should now show full content and Collapse button
    expect(
      screen.getByText((content, element) => {
        return (
          element?.textContent ===
          "Full content of the test node with more details"
        );
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Collapse/ })
    ).toBeInTheDocument();
  });

  it("handles recent queries with timestamps correctly", async () => {
    // Mock localStorage with recent queries in new format
    const recentQueries = [
      {
        query: "previous query",
        timestamp: Date.now() - 60000, // 1 minute ago
        resultCount: 5,
      },
      {
        query: "another query",
        timestamp: Date.now() - 3600000, // 1 hour ago
        resultCount: 2,
      },
    ];
    localStorage.setItem(
      "nodeKnowledgeRecentQueries",
      JSON.stringify(recentQueries)
    );

    render(<SearchInterface />);

    // Should show recent queries
    expect(screen.getByText("Recent Queries:")).toBeInTheDocument();
    expect(screen.getByText("previous query")).toBeInTheDocument();
    expect(screen.getByText("another query")).toBeInTheDocument();

    // Should show timestamps and result counts
    expect(screen.getByText("1m ago")).toBeInTheDocument();
    expect(screen.getByText("1h ago")).toBeInTheDocument();
    expect(screen.getByText("5 results")).toBeInTheDocument();
    expect(screen.getByText("2 results")).toBeInTheDocument();
  });

  it("allows removing individual recent queries", async () => {
    const recentQueries = [
      {
        query: "query to remove",
        timestamp: Date.now() - 60000,
        resultCount: 3,
      },
      {
        query: "query to keep",
        timestamp: Date.now() - 120000,
        resultCount: 1,
      },
    ];
    localStorage.setItem(
      "nodeKnowledgeRecentQueries",
      JSON.stringify(recentQueries)
    );

    render(<SearchInterface />);

    // Should show both queries initially
    expect(screen.getByText("query to remove")).toBeInTheDocument();
    expect(screen.getByText("query to keep")).toBeInTheDocument();

    // Find and click the remove button for the first query
    const removeButtons = screen.getAllByTitle("Remove from history");
    fireEvent.click(removeButtons[0]);

    // Should only show the second query now
    expect(screen.queryByText("query to remove")).not.toBeInTheDocument();
    expect(screen.getByText("query to keep")).toBeInTheDocument();
  });

  it("allows clearing all recent queries", async () => {
    const recentQueries = [
      {
        query: "query 1",
        timestamp: Date.now() - 60000,
        resultCount: 3,
      },
      {
        query: "query 2",
        timestamp: Date.now() - 120000,
        resultCount: 1,
      },
    ];
    localStorage.setItem(
      "nodeKnowledgeRecentQueries",
      JSON.stringify(recentQueries)
    );

    render(<SearchInterface />);

    // Should show recent queries initially
    expect(screen.getByText("Recent Queries:")).toBeInTheDocument();
    expect(screen.getByText("query 1")).toBeInTheDocument();
    expect(screen.getByText("query 2")).toBeInTheDocument();

    // Click clear all button
    const clearAllButton = screen.getByText("Clear all");
    fireEvent.click(clearAllButton);

    // Should show example queries instead
    expect(screen.queryByText("Recent Queries:")).not.toBeInTheDocument();
    expect(screen.getByText("Example Queries:")).toBeInTheDocument();
    expect(screen.queryByText("query 1")).not.toBeInTheDocument();
    expect(screen.queryByText("query 2")).not.toBeInTheDocument();
  });

  it("saves queries to history with timestamps and result counts", async () => {
    const mockResults = [
      {
        id: "1",
        node_type: "AI_AGENT",
        node_subtype: "Workflow",
        title: "Test Node",
        description: "This is a test node description",
        content: "Full content of the test node",
        similarity: 0.85,
        metadata: {},
      },
    ];

    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        results: mockResults,
        query: "test query",
        processingTime: 100,
        totalCount: 1,
      }),
    });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    // Enter valid query and search
    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    // Wait for results
    await waitFor(() => {
      expect(screen.getByText(/Search Results \(1 of 1 found\)/)).toBeInTheDocument();
    });

    // Check that query was saved to localStorage with proper format
    const savedQueries = JSON.parse(
      localStorage.getItem("nodeKnowledgeRecentQueries") || "[]"
    );
    expect(savedQueries).toHaveLength(1);
    expect(savedQueries[0]).toMatchObject({
      query: "test query",
      resultCount: 1,
    });
    expect(savedQueries[0].timestamp).toBeGreaterThan(Date.now() - 1000);
  });

  it("clears results when clear button is clicked but keeps recent queries", async () => {
    const mockResults = [
      {
        id: "1",
        node_type: "AI_AGENT",
        node_subtype: "Workflow",
        title: "Test Node",
        description: "This is a test node description",
        content: "Full content of the test node",
        similarity: 0.85,
        metadata: {},
      },
    ];

    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        results: mockResults,
        query: "test query",
        processingTime: 100,
        totalCount: 1,
      }),
    });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    // Enter valid query and search
    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    // Wait for results
    await waitFor(() => {
      expect(screen.getByText(/Search Results \(1 of 1 found\)/)).toBeInTheDocument();
    });

    // Click clear results
    const clearButton = screen.getByRole("button", { name: "Clear Results" });
    fireEvent.click(clearButton);

    // Results should be cleared
    expect(
      screen.queryByText(/Search Results \(1 of 1 found\)/)
    ).not.toBeInTheDocument();

    // Should show recent queries (not example queries) since we just performed a search
    expect(screen.getByText("Recent Queries:")).toBeInTheDocument();
    expect(screen.getByText("test query")).toBeInTheDocument();
  });

  it("shows no results message when search returns empty", async () => {
    // Mock API responses - status check first, then search with no results
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          available: true,
          openaiAvailable: true,
          databaseAvailable: true,
          totalNodes: 10,
          message: "Query API is ready",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          results: [],
          query: "test query",
          processingTime: 100,
          totalCount: 0,
        }),
      });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    // Enter valid query and search
    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    // Wait for no results message
    await waitFor(() => {
      expect(screen.getByText("No results found")).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        "Try adjusting your search query or using different keywords."
      )
    ).toBeInTheDocument();
  });

  // Additional tests for Task 3 functionality
  it("displays detailed content and metadata when result is expanded", async () => {
    const mockResults = [
      {
        id: "1",
        node_type: "AI_AGENT",
        node_subtype: "Workflow",
        title: "Test Node",
        description: "This is a test node description",
        content: "Full detailed content with capabilities and examples",
        similarity: 0.85,
        metadata: {
          capabilities: ["capability1", "capability2"],
          examples: ["example1", "example2"],
          custom_field: "custom value",
        },
      },
    ];

    // Mock API responses - status check first, then search
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          available: true,
          openaiAvailable: true,
          databaseAvailable: true,
          totalNodes: 10,
          message: "Query API is ready",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          results: mockResults,
          query: "test query",
          processingTime: 100,
          totalCount: 1,
        }),
      });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText(/Search Results \(1 of 1 found\)/)).toBeInTheDocument();
    });

    // Expand the result
    const expandButton = screen.getByRole("button", { name: /Expand/ });
    fireEvent.click(expandButton);

    // Check for detailed content section
    expect(screen.getByText("Detailed Content")).toBeInTheDocument();
    expect(
      screen.getByText("Full detailed content with capabilities and examples")
    ).toBeInTheDocument();

    // Check for metadata section
    expect(screen.getByText("Additional Information")).toBeInTheDocument();
    expect(screen.getByText("capabilities:")).toBeInTheDocument();
    expect(screen.getByText("capability1")).toBeInTheDocument();
    expect(screen.getByText("capability2")).toBeInTheDocument();
    expect(screen.getByText("examples:")).toBeInTheDocument();
    expect(screen.getByText("example1")).toBeInTheDocument();
    expect(screen.getByText("example2")).toBeInTheDocument();
    expect(screen.getByText("custom field:")).toBeInTheDocument();
    expect(screen.getByText("custom value")).toBeInTheDocument();
  });

  it("groups results by node type with proper headers", async () => {
    const mockResults = [
      {
        id: "1",
        node_type: "AI_AGENT",
        node_subtype: "Workflow",
        title: "AI Agent Node 1",
        description: "First AI agent description",
        content: "AI agent content",
        similarity: 0.85,
        metadata: {},
      },
      {
        id: "2",
        node_type: "TOOL",
        node_subtype: "API",
        title: "Tool Node 1",
        description: "Tool node description",
        content: "Tool node content",
        similarity: 0.75,
        metadata: {},
      },
      {
        id: "3",
        node_type: "AI_AGENT",
        node_subtype: "Assistant",
        title: "AI Agent Node 2",
        description: "Second AI agent description",
        content: "Second AI agent content",
        similarity: 0.8,
        metadata: {},
      },
    ];

    // Mock API responses - status check first, then search
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          available: true,
          openaiAvailable: true,
          databaseAvailable: true,
          totalNodes: 10,
          message: "Query API is ready",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          results: mockResults,
          query: "test query",
          processingTime: 100,
          totalCount: 3,
        }),
      });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText(/Search Results \(3 of 3 found\)/)).toBeInTheDocument();
    });

    // Check for group headers (AI Agent should appear first due to higher max similarity)
    expect(screen.getByText("AI_AGENT")).toBeInTheDocument();
    expect(screen.getByText("TOOL")).toBeInTheDocument();

    // Check for result counts in group headers
    expect(screen.getByText("(2 results)")).toBeInTheDocument(); // AI Agent group
    expect(screen.getByText("(1 result)")).toBeInTheDocument(); // Tool Node group

    // Check that all results are displayed
    expect(screen.getByText("AI Agent Node 1")).toBeInTheDocument();
    expect(screen.getByText("AI Agent Node 2")).toBeInTheDocument();
    expect(screen.getByText("Tool Node 1")).toBeInTheDocument();
  });

  it("highlights keywords in both title and content when expanded", async () => {
    const mockResults = [
      {
        id: "1",
        node_type: "AI_AGENT",
        node_subtype: "Workflow",
        title: "Workflow Processing Node",
        description: "This node handles workflow processing tasks",
        content:
          "The workflow processing capabilities include data transformation and workflow orchestration",
        similarity: 0.85,
        metadata: { capabilities: ["workflow management", "data processing"] },
      },
    ];

    // Mock API responses - status check first, then search
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          available: true,
          openaiAvailable: true,
          databaseAvailable: true,
          totalNodes: 10,
          message: "Query API is ready",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          results: mockResults,
          query: "workflow processing",
          processingTime: 100,
          totalCount: 1,
        }),
      });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    fireEvent.change(searchInput, { target: { value: "workflow processing" } });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText(/Search Results \(1 of 1 found\)/)).toBeInTheDocument();
    });

    // Check that keywords are highlighted in title and description (using getAllByText for multiple occurrences)
    expect(screen.getAllByText("Workflow")).toHaveLength(2); // One in subtype, one highlighted in title
    expect(screen.getByText("Processing")).toBeInTheDocument(); // Highlighted in title
    expect(screen.getAllByText("workflow")).toHaveLength(1); // Highlighted in description

    // Expand the result
    const expandButton = screen.getByRole("button", { name: /Expand/ });
    fireEvent.click(expandButton);

    // Check that keywords are highlighted in expanded content and metadata
    expect(screen.getAllByText("workflow")).toHaveLength(4); // Should appear multiple times (title, description, content, metadata)
    expect(screen.getAllByText("processing")).toHaveLength(3); // Should appear multiple times (title, description, content, metadata)
  });

  it("displays similarity scores as visual progress bars", async () => {
    const mockResults = [
      {
        id: "1",
        node_type: "AI_AGENT",
        node_subtype: "Workflow",
        title: "High Similarity Node",
        description: "Node with high similarity",
        content: "Content",
        similarity: 0.95,
        metadata: {},
      },
      {
        id: "2",
        node_type: "TOOL",
        node_subtype: "API",
        title: "Medium Similarity Node",
        description: "Node with medium similarity",
        content: "Content",
        similarity: 0.65,
        metadata: {},
      },
    ];

    // Mock API responses - status check first, then search
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          available: true,
          openaiAvailable: true,
          databaseAvailable: true,
          totalNodes: 10,
          message: "Query API is ready",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          results: mockResults,
          query: "test query",
          processingTime: 100,
          totalCount: 2,
        }),
      });

    render(<SearchInterface />);

    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    const searchButton = screen.getByRole("button", { name: /🔍 Search/ });

    fireEvent.change(searchInput, { target: { value: "test query" } });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText(/Search Results \(2 of 2 found\)/)).toBeInTheDocument();
    });

    // Check for percentage displays
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText("65%")).toBeInTheDocument();

    // Check for progress bar elements (they should have the correct width styles)
    const progressBars = document.querySelectorAll(".bg-gradient-to-r");
    expect(progressBars).toHaveLength(2);

    // Check that the progress bars have the correct width styles
    expect(progressBars[0]).toHaveStyle("width: 95%");
    expect(progressBars[1]).toHaveStyle("width: 65%");
  });

  it('filters results by node type', async () => {
    const mockResults = [
      { id: '1', node_type: 'AI_AGENT', title: 'AI Node', similarity: 0.9, description: 'd', content: 'c' },
      { id: '2', node_type: 'TOOL', title: 'Tool Node', similarity: 0.8, description: 'd', content: 'c' },
    ];

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ available: true, totalNodes: 2 }),
    }).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, results: mockResults, totalCount: 2 }),
    });

    render(<SearchInterface />);
    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    fireEvent.change(searchInput, { target: { value: 'test' } });
    fireEvent.click(screen.getByRole('button', { name: /🔍 Search/ }));

    await waitFor(() => {
      expect(screen.getByText('AI Node')).toBeInTheDocument();
      expect(screen.getByText('Tool Node')).toBeInTheDocument();
    });

    const filterSelect = screen.getByLabelText('Filter by Node Type');
    fireEvent.change(filterSelect, { target: { value: 'AI_AGENT' } });

    expect(screen.getByText('AI Node')).toBeInTheDocument();
    expect(screen.queryByText('Tool Node')).not.toBeInTheDocument();
  });

  it('filters results by similarity threshold', async () => {
    const mockResults = [
      { id: '1', node_type: 'AI_AGENT', title: 'High Similarity', similarity: 0.95, description: 'd', content: 'c' },
      { id: '2', node_type: 'TOOL', title: 'Low Similarity', similarity: 0.5, description: 'd', content: 'c' },
    ];

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ available: true, totalNodes: 2 }),
    }).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, results: mockResults, totalCount: 2 }),
    });

    render(<SearchInterface />);
    const searchInput = screen.getByPlaceholderText(/Enter your search query/);
    fireEvent.change(searchInput, { target: { value: 'test' } });
    fireEvent.click(screen.getByRole('button', { name: /🔍 Search/ }));

    await waitFor(() => {
      expect(screen.getByText('High Similarity')).toBeInTheDocument();
      expect(screen.getByText('Low Similarity')).toBeInTheDocument();
    });

    const similaritySlider = screen.getByLabelText(/Minimum Similarity/);
    fireEvent.change(similaritySlider, { target: { value: '0.7' } });

    expect(screen.getByText('High Similarity')).toBeInTheDocument();
    expect(screen.queryByText('Low Similarity')).not.toBeInTheDocument();
  });
});
