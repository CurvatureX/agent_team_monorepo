"use client";

import { useState, useEffect } from "react";
import {
  parseNodeKnowledgePreview,
  NODE_KNOWLEDGE_TEXT,
  NodeKnowledge,
} from "@/lib/nodeKnowledgeParser";

interface UploadResult {
  success: boolean;
  message: string;
  inserted?: number;
  errors?: number;
  errorDetails?: Array<{ node: string; error: string }>;
  existingCount?: number;
}

export default function Home() {
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

  const saveEdit = (index: number) => {
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
      }
    } catch (error) {
      setResult({
        success: false,
        message: "Network error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">
            Node Knowledge Uploader
          </h1>

          <div className="mb-6 p-4 bg-blue-50 rounded-lg">
            <h2 className="text-lg font-semibold text-blue-900 mb-2">
              Database Status
            </h2>
            <p className="text-blue-800">
              Current records in database:{" "}
              {currentCount !== null ? currentCount : "Loading..."}
            </p>
          </div>

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
                      onChange={(e) => setUploadMode(e.target.value as "check")}
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
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
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
                    {editedNodes.map((node, index) => (
                      <div key={index} className="bg-white p-4 rounded border">
                        {/* Header */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex-1">
                            {editingNode === index ? (
                              <div className="space-y-2">
                                <input
                                  value={node.nodeType}
                                  onChange={(e) =>
                                    updateEditedNode(
                                      index,
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
                                      index,
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
                            {editingNode === index ? (
                              <>
                                <button
                                  onClick={() => saveEdit(index)}
                                  className="text-xs px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600"
                                >
                                  Save
                                </button>
                                <button
                                  onClick={() => cancelEdit(index)}
                                  className="text-xs px-2 py-1 bg-gray-500 text-white rounded hover:bg-gray-600"
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => startEditing(index)}
                                className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                              >
                                Edit
                              </button>
                            )}

                            <button
                              onClick={() => toggleNodeExpansion(index)}
                              className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                            >
                              {expandedNodes.has(index) ? "Collapse" : "Expand"}
                            </button>
                          </div>
                        </div>

                        {/* Description */}
                        {editingNode === index ? (
                          <textarea
                            value={node.description}
                            onChange={(e) =>
                              updateEditedNode(
                                index,
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
                              expandedNodes.has(index)
                                ? node.description.length
                                : 100
                            )}
                            {!expandedNodes.has(index) &&
                              node.description.length > 100 &&
                              "..."}
                          </div>
                        )}

                        {/* Expanded Content */}
                        {expandedNodes.has(index) && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <div className="space-y-2">
                              <div>
                                <label className="text-xs font-semibold text-gray-800">
                                  Title:
                                </label>
                                {editingNode === index ? (
                                  <input
                                    value={node.title}
                                    onChange={(e) =>
                                      updateEditedNode(
                                        index,
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
                                {editingNode === index ? (
                                  <textarea
                                    value={node.content}
                                    onChange={(e) =>
                                      updateEditedNode(
                                        index,
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
                  className={result.success ? "text-green-700" : "text-red-700"}
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
            <h3 className="font-semibold text-gray-900 mb-2">Instructions</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm text-gray-800">
              <li>Make sure your Supabase environment variables are set up</li>
              <li>Ensure your OpenAI API key is configured for embeddings</li>
              <li>
                The content will be parsed into individual node types and
                subtypes
              </li>
              <li>
                Click "Expand" to see full content and "Edit" to modify nodes
              </li>
              <li>
                Each node will get an embedding generated and stored in the
                database
              </li>
              <li>
                Choose upload mode: Check (empty database only), Append (add to
                existing), or Overwrite (replace all)
              </li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
