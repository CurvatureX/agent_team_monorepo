"use client";

import { useState, useEffect } from "react";
import {
  parseNodeKnowledgePreview,
  NODE_KNOWLEDGE_TEXT,
  NodeKnowledge,
} from "@/lib/nodeKnowledgeParser";
import TabNavigation from "@/components/TabNavigation";
import SearchInterface from "@/components/SearchInterface";

interface UploadResult {
  success: boolean;
  message: string;
  inserted?: number;
  errors?: number;
  errorDetails?: Array<{ node: string; error: string }>;
  existingCount?: number;
}

export default function Home() {
  // Tab navigation state
  const [activeTab, setActiveTab] = useState<"upload" | "search">("upload");
  const [searchResultsCount, setSearchResultsCount] = useState<number>(0);

  // Upload interface state
  const [content, setContent] = useState(NODE_KNOWLEDGE_TEXT);
  const [loading, setLoading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [parsedNodes, setParsedNodes] = useState<NodeKnowledge[]>([]);
  const [currentCount, setCurrentCount] = useState<number | null>(null);
  const [uploadMode, setUploadMode] = useState<
    "check" | "overwrite" | "append"
  >("check");
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const [editingNode, setEditingNode] = useState<number | null>(null);
  const [editedNodes, setEditedNodes] = useState<NodeKnowledge[]>([]);
  const [parseMethod, setParseMethod] = useState<"preview" | "openai">(
    "preview"
  );

  // Search interface state preservation
  const [searchQuery] = useState<string>("");

  useEffect(() => {
    // Only auto-parse with preview method on content change
    if (parseMethod === "preview") {
      try {
        const nodes = parseNodeKnowledgePreview(content);
        setParsedNodes(nodes);
        setEditedNodes([...nodes]);
      } catch (error) {
        console.error("Error parsing content:", error);
        setParsedNodes([]);
        setEditedNodes([]);
      }
    }
  }, [content, parseMethod]);

  useEffect(() => {
    // Fetch current count
    fetchCurrentCount();
  }, []);

  const fetchCurrentCount = async () => {
    try {
      const response = await fetch("/api/upload");
      const data = await response.json();
      setCurrentCount(data.currentCount);
    } catch (error) {
      console.error("Error fetching current count:", error);
    }
  };

  const parseWithOpenAI = async () => {
    if (!content.trim()) return;

    setParsing(true);
    setResult(null);

    try {
      const response = await fetch("/api/parse", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content }),
      });

      const data = await response.json();
      console.log("🔍 OpenAI Parse Response:", data);

      if (response.ok) {
        console.log("✅ OpenAI Parse Success - Nodes:", data.nodes);
        console.log("✅ Setting editedNodes to:", data.nodes);
        setParsedNodes(data.nodes);
        setEditedNodes([...data.nodes]);
        setParseMethod("openai");
        setResult({
          success: true,
          message: data.message,
        });
      } else {
        setResult({
          success: false,
          message: data.error || "Failed to parse content",
        });
      }
    } catch (error) {
      console.error("Parse error:", error);
      setResult({
        success: false,
        message: "Network error occurred",
      });
    } finally {
      setParsing(false);
    }
  };

  const toggleNodeExpansion = (index: number) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedNodes(newExpanded);
  };

  const startEditing = (index: number) => {
    setEditingNode(index);
  };

  const saveEdit = () => {
    setEditingNode(null);
    // Update the original parsed nodes if needed
    setParsedNodes([...editedNodes]);
  };

  const cancelEdit = (index: number) => {
    // Revert changes
    const newEditedNodes = [...editedNodes];
    newEditedNodes[index] = parsedNodes[index];
    setEditedNodes(newEditedNodes);
    setEditingNode(null);
  };

  const updateEditedNode = (
    index: number,
    field: keyof NodeKnowledge,
    value: string
  ) => {
    const newEditedNodes = [...editedNodes];
    newEditedNodes[index] = {
      ...newEditedNodes[index],
      [field]: value,
    };
    setEditedNodes(newEditedNodes);
  };

  const handleUpload = async () => {
    setLoading(true);
    setResult(null);

    try {
      // Use edited nodes for upload
      const nodesToUpload = editedNodes.map((node) => ({
        nodeType: node.nodeType,
        nodeSubtype: node.nodeSubtype,
        title: node.title,
        description: node.description,
        content: node.content,
      }));

      const response = await fetch("/api/upload", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: JSON.stringify(nodesToUpload), // Send as structured data
          overwrite: uploadMode === "overwrite",
          append: uploadMode === "append",
          useStructuredData: true,
        }),
      });

      const data = await response.json();
      setResult(data);

      if (data.success) {
        await fetchCurrentCount();
        // Suggest switching to search after successful upload
        if (data.inserted && data.inserted > 0) {
          setTimeout(() => {
            if (
              confirm(
                `Upload successful! ${data.inserted} node${
                  data.inserted > 1 ? "s" : ""
                } added to the knowledge base. Would you like to search the newly added content?`
              )
            ) {
              setActiveTab("search");
            }
          }, 1000);
        }
      }
    } catch {
      setResult({
        success: false,
        message: "Network error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle tab changes with state preservation
  const handleTabChange = (tab: "upload" | "search") => {
    setActiveTab(tab);
    // Refresh database count when switching tabs to ensure accuracy
    fetchCurrentCount();

    // If switching to search tab and database has content, clear any previous search state
    if (tab === "search" && currentCount && currentCount > 0) {
      // Reset search results count to ensure fresh state
      setSearchResultsCount(0);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-6 relative">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">
            Node Knowledge Management System
          </h1>

          {/* Tab Navigation */}
          <TabNavigation
            activeTab={activeTab}
            onTabChange={handleTabChange}
            searchResultsCount={searchResultsCount}
            databaseCount={currentCount}
          />

          {/* Conditional rendering based on active tab */}
          {activeTab === "upload" ? (
            <div>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                {/* Input Section */}
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">
                    Node Knowledge Content
                  </h2>

                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full h-96 p-4 border border-gray-300 rounded-lg font-mono text-sm text-gray-900"
                    placeholder="Paste your node knowledge content here..."
                  />

                  <div className="mt-4">
                    <label className="text-sm font-medium text-gray-800 block mb-2">
                      Upload Mode:
                    </label>
                    <div className="flex flex-col gap-2">
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="uploadMode"
                          value="check"
                          checked={uploadMode === "check"}
                          onChange={(e) =>
                            setUploadMode(e.target.value as "check")
                          }
                          className="rounded"
                        />
                        <span className="text-sm text-gray-800">
                          Check (only upload if database is empty)
                        </span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="uploadMode"
                          value="append"
                          checked={uploadMode === "append"}
                          onChange={(e) =>
                            setUploadMode(e.target.value as "append")
                          }
                          className="rounded"
                        />
                        <span className="text-sm text-gray-800">
                          Append (add new records to existing data)
                        </span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="uploadMode"
                          value="overwrite"
                          checked={uploadMode === "overwrite"}
                          onChange={(e) =>
                            setUploadMode(e.target.value as "overwrite")
                          }
                          className="rounded"
                        />
                        <span className="text-sm text-gray-800">
                          Overwrite (replace all existing data)
                        </span>
                      </label>
                    </div>
                  </div>

                  <div className="mt-4 flex gap-3">
                    <button
                      onClick={parseWithOpenAI}
                      disabled={parsing || !content.trim()}
                      className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {parsing ? (
                        <>
                          <svg
                            className="animate-spin h-4 w-4"
                            viewBox="0 0 24 24"
                          >
                            <circle
                              className="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              strokeWidth="4"
                            ></circle>
                            <path
                              className="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            ></path>
                          </svg>
                          Parsing with OpenAI...
                        </>
                      ) : (
                        <>🤖 Parse with OpenAI</>
                      )}
                    </button>

                    <button
                      onClick={handleUpload}
                      disabled={loading || editedNodes.length === 0}
                      className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    >
                      {loading ? "Uploading..." : "Upload to Supabase"}
                    </button>
                  </div>
                </div>

                {/* Preview Section */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">
                      Parsed Nodes Preview ({editedNodes.length} nodes)
                    </h2>
                    <div className="flex items-center gap-2">
                      {parseMethod === "openai" ? (
                        <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                          🤖 OpenAI Parsed
                        </span>
                      ) : (
                        <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">
                          📄 Basic Preview
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="h-96 overflow-y-auto border border-gray-300 rounded-lg p-4 bg-gray-50">
                    {/* Debug logging */}
                    {(() => {
                      console.log(
                        "🎯 Rendering editedNodes:",
                        editedNodes.length,
                        "nodes"
                      );
                      console.log("🎯 Parse method:", parseMethod);
                      console.log("🎯 First node:", editedNodes[0]);
                      return null;
                    })()}
                    {editedNodes.length > 0 ? (
                      <div className="space-y-3">
                        {editedNodes.map((node, nodeIndex) => (
                          <div
                            key={nodeIndex}
                            className="bg-white p-4 rounded border"
                          >
                            {/* Header */}
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex-1">
                                {editingNode === nodeIndex ? (
                                  <div className="space-y-2">
                                    <input
                                      value={node.nodeType}
                                      onChange={(e) =>
                                        updateEditedNode(
                                          nodeIndex,
                                          "nodeType",
                                          e.target.value
                                        )
                                      }
                                      className="w-full text-sm font-semibold text-blue-700 border rounded px-2 py-1"
                                      placeholder="Node Type"
                                    />
                                    <input
                                      value={node.nodeSubtype || ""}
                                      onChange={(e) =>
                                        updateEditedNode(
                                          nodeIndex,
                                          "nodeSubtype",
                                          e.target.value
                                        )
                                      }
                                      className="w-full text-sm text-gray-800 border rounded px-2 py-1"
                                      placeholder="Node Subtype"
                                    />
                                  </div>
                                ) : (
                                  <div>
                                    <div className="font-semibold text-sm text-blue-700">
                                      {node.nodeType}
                                    </div>
                                    <div className="text-sm text-gray-800">
                                      {node.nodeSubtype}
                                    </div>
                                  </div>
                                )}
                              </div>

                              <div className="flex items-center gap-2">
                                {editingNode === nodeIndex ? (
                                  <>
                                    <button
                                      onClick={() => saveEdit()}
                                      className="text-xs px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600"
                                    >
                                      Save
                                    </button>
                                    <button
                                      onClick={() => cancelEdit(nodeIndex)}
                                      className="text-xs px-2 py-1 bg-gray-500 text-white rounded hover:bg-gray-600"
                                    >
                                      Cancel
                                    </button>
                                  </>
                                ) : (
                                  <button
                                    onClick={() => startEditing(nodeIndex)}
                                    className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                                  >
                                    Edit
                                  </button>
                                )}

                                <button
                                  onClick={() => toggleNodeExpansion(nodeIndex)}
                                  className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                >
                                  {expandedNodes.has(nodeIndex)
                                    ? "Collapse"
                                    : "Expand"}
                                </button>
                              </div>
                            </div>

                            {/* Description */}
                            {editingNode === nodeIndex ? (
                              <textarea
                                value={node.description}
                                onChange={(e) =>
                                  updateEditedNode(
                                    nodeIndex,
                                    "description",
                                    e.target.value
                                  )
                                }
                                className="w-full text-xs text-gray-800 border rounded px-2 py-1 h-16 resize-none"
                                placeholder="Description"
                              />
                            ) : (
                              <div className="text-xs text-gray-700 mb-2">
                                {node.description.substring(
                                  0,
                                  expandedNodes.has(nodeIndex)
                                    ? node.description.length
                                    : 100
                                )}
                                {!expandedNodes.has(nodeIndex) &&
                                  node.description.length > 100 &&
                                  "..."}
                              </div>
                            )}

                            {/* Expanded Content */}
                            {expandedNodes.has(nodeIndex) && (
                              <div className="mt-3 pt-3 border-t border-gray-200">
                                <div className="space-y-2">
                                  <div>
                                    <label className="text-xs font-semibold text-gray-800">
                                      Title:
                                    </label>
                                    {editingNode === nodeIndex ? (
                                      <input
                                        value={node.title}
                                        onChange={(e) =>
                                          updateEditedNode(
                                            nodeIndex,
                                            "title",
                                            e.target.value
                                          )
                                        }
                                        className="w-full text-xs border rounded px-2 py-1 mt-1 text-gray-900"
                                      />
                                    ) : (
                                      <div className="text-xs text-gray-800 mt-1">
                                        {node.title}
                                      </div>
                                    )}
                                  </div>

                                  <div>
                                    <label className="text-xs font-semibold text-gray-800">
                                      Content:
                                    </label>
                                    {editingNode === nodeIndex ? (
                                      <textarea
                                        value={node.content}
                                        onChange={(e) =>
                                          updateEditedNode(
                                            nodeIndex,
                                            "content",
                                            e.target.value
                                          )
                                        }
                                        className="w-full text-xs border rounded px-2 py-1 mt-1 h-32 resize-none text-gray-900"
                                      />
                                    ) : (
                                      <div className="text-xs text-gray-800 mt-1 whitespace-pre-wrap">
                                        {node.content}
                                      </div>
                                    )}
                                  </div>

                                  {node.content.includes("Capabilities:") && (
                                    <div>
                                      <label className="text-xs font-semibold text-green-800">
                                        Has Capabilities
                                      </label>
                                      <div className="text-xs text-green-700 mt-1">
                                        ✓ Capabilities listed in content
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-gray-600 text-center py-8">
                        No nodes parsed. Please check your content format.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Results Section */}
              {result && (
                <div className="mt-6">
                  <div
                    className={`p-4 rounded-lg ${
                      result.success
                        ? "bg-green-50 border border-green-200"
                        : "bg-red-50 border border-red-200"
                    }`}
                  >
                    <h3
                      className={`font-semibold mb-2 ${
                        result.success ? "text-green-900" : "text-red-900"
                      }`}
                    >
                      {result.success ? "Success!" : "Error"}
                    </h3>

                    <p
                      className={
                        result.success ? "text-green-700" : "text-red-700"
                      }
                    >
                      {result.message}
                    </p>

                    {result.success && (
                      <div className="mt-2 text-green-700 text-sm">
                        <p>Inserted: {result.inserted} nodes</p>
                        {result.errors && result.errors > 0 && (
                          <p>Errors: {result.errors} nodes</p>
                        )}
                      </div>
                    )}

                    {result.errorDetails && result.errorDetails.length > 0 && (
                      <div className="mt-3">
                        <h4 className="font-semibold text-red-900 mb-2">
                          Error Details:
                        </h4>
                        <div className="space-y-1">
                          {result.errorDetails.map((error, index) => (
                            <div key={index} className="text-sm text-red-700">
                              <span className="font-medium">{error.node}:</span>{" "}
                              {error.error}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Instructions */}
              <div className="mt-8 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-2">
                  Instructions
                </h3>
                <ol className="list-decimal list-inside space-y-1 text-sm text-gray-800">
                  <li>
                    Make sure your Supabase environment variables are set up
                  </li>
                  <li>
                    Ensure your OpenAI API key is configured for embeddings
                  </li>
                  <li>
                    The content will be parsed into individual node types and
                    subtypes
                  </li>
                  <li>
                    Click &quot;Expand&quot; to see full content and
                    &quot;Edit&quot; to modify nodes
                  </li>
                  <li>
                    Each node will get an embedding generated and stored in the
                    database
                  </li>
                  <li>
                    Choose upload mode: Check (empty database only), Append (add
                    to existing), or Overwrite (replace all)
                  </li>
                </ol>
              </div>
            </div>
          ) : (
            /* Search Interface */
            <div>
              {currentCount === null ? (
                // Loading state while fetching database count
                <div className="text-center py-12">
                  <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                    <div className="animate-spin w-8 h-8 border-2 border-blue-300 border-t-blue-600 rounded-full" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Loading Database Status
                  </h3>
                  <p className="text-gray-600">
                    Checking available knowledge in the database...
                  </p>
                </div>
              ) : currentCount === 0 ? (
                // Empty database state
                <div className="text-center py-12">
                  <div className="mx-auto w-24 h-24 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
                    <svg
                      className="w-12 h-12 text-yellow-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z"
                      />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    No Knowledge Available Yet
                  </h3>
                  <p className="text-gray-600 mb-4 max-w-md mx-auto">
                    The knowledge base is currently empty. Upload some workflow
                    node documentation to start building your searchable
                    knowledge repository.
                  </p>
                  <div className="text-sm text-gray-500 mb-6 max-w-lg mx-auto">
                    <p className="mb-2">
                      Once you upload knowledge, you&apos;ll be able to:
                    </p>
                    <ul className="text-left space-y-1">
                      <li>• Search for specific node types and capabilities</li>
                      <li>• Find relevant workflow components quickly</li>
                      <li>• Explore relationships between different nodes</li>
                      <li>
                        • Get detailed information about node functionality
                      </li>
                    </ul>
                  </div>
                  <button
                    onClick={() => setActiveTab("upload")}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 mx-auto"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    Start by Uploading Knowledge
                  </button>
                </div>
              ) : (
                // Database has content - show search interface
                <SearchInterface
                  initialQuery={searchQuery}
                  onResultsChange={setSearchResultsCount}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
