"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface JsonViewerProps {
  data: Record<string, unknown>;
  className?: string;
  initialExpanded?: boolean;
  currentDepth?: number;
}

// Component for nested object/array rendering
const NestedObjectViewer: React.FC<{
  value: Record<string, unknown>;
  depth: number;
}> = ({ value, depth }) => {
  // Auto-collapse deeply nested objects (depth > 2), but keep them expandable
  const [expanded, setExpanded] = useState(depth <= 2);
  const entries = Object.entries(value);

  if (entries.length === 0) {
    return <span className="text-muted-foreground">{"{}"}</span>;
  }

  return (
    <div className="inline-block">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
        className="inline-flex items-center gap-1 hover:bg-accent/30 rounded px-1 py-0.5 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 flex-shrink-0" />
        )}
        <span className="text-muted-foreground">
          {expanded ? "{" : `{${entries.length} ${entries.length === 1 ? "field" : "fields"}}`}
        </span>
      </button>

      {expanded && (
        <>
          <div className="ml-4 border-l border-border/50 pl-2 space-y-1 mt-1">
            {entries.map(([key, val]) => (
              <div key={key} className="flex items-start gap-2">
                <span className="text-orange-600 dark:text-orange-400 whitespace-nowrap">
                  {key}:
                </span>
                <span className="flex-1">
                  {renderJsonValue(val, depth + 1)}
                </span>
              </div>
            ))}
          </div>
          <div className="text-muted-foreground">{"}"}</div>
        </>
      )}
    </div>
  );
};

// Component for nested array rendering
const NestedArrayViewer: React.FC<{
  value: unknown[];
  depth: number;
}> = ({ value, depth }) => {
  // Auto-collapse deeply nested arrays (depth > 2), but keep them expandable
  const [expanded, setExpanded] = useState(depth <= 2);

  if (value.length === 0) {
    return <span className="text-muted-foreground">[]</span>;
  }

  return (
    <div className="inline-block">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
        className="inline-flex items-center gap-1 hover:bg-accent/30 rounded px-1 py-0.5 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 flex-shrink-0" />
        )}
        <span className="text-muted-foreground">
          {expanded ? "[" : `[${value.length} items]`}
        </span>
      </button>

      {expanded && (
        <>
          <div className="ml-4 border-l border-border/50 pl-2 space-y-1 mt-1">
            {value.map((item, index) => (
              <div key={index} className="flex items-start gap-2">
                <span className="text-orange-600 dark:text-orange-400 whitespace-nowrap">
                  {index}:
                </span>
                <span className="flex-1">
                  {renderJsonValue(item, depth + 1)}
                </span>
              </div>
            ))}
          </div>
          <div className="text-muted-foreground">{"]"}</div>
        </>
      )}
    </div>
  );
};

// Helper function to render any JSON value
const renderJsonValue = (value: unknown, depth: number): React.ReactNode => {
  if (value === null) {
    return <span className="text-gray-500">null</span>;
  }

  if (value === undefined) {
    return <span className="text-gray-500">undefined</span>;
  }

  if (typeof value === "boolean") {
    return <span className="text-purple-600 dark:text-purple-400">{String(value)}</span>;
  }

  if (typeof value === "number") {
    return <span className="text-blue-600 dark:text-blue-400">{value}</span>;
  }

  if (typeof value === "string") {
    // Truncate very long strings
    const displayValue = value.length > 100 ? value.substring(0, 100) + "..." : value;
    return <span className="text-green-600 dark:text-green-400">&quot;{displayValue}&quot;</span>;
  }

  if (Array.isArray(value)) {
    return <NestedArrayViewer value={value} depth={depth} />;
  }

  if (typeof value === "object" && value !== null) {
    return <NestedObjectViewer value={value as Record<string, unknown>} depth={depth} />;
  }

  return <span className="text-muted-foreground">{String(value)}</span>;
};

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  className,
  initialExpanded = false,
  currentDepth = 0,
}) => {
  const [expanded, setExpanded] = useState(initialExpanded || currentDepth < 1);

  if (!data || typeof data !== "object" || Object.keys(data).length === 0) {
    return null;
  }

  const entries = Object.entries(data);

  return (
    <div className={cn("font-mono text-xs", className)}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 hover:bg-accent/30 rounded px-1 py-0.5 transition-colors w-full text-left"
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 flex-shrink-0" />
        )}
        <span className="text-muted-foreground">
          {expanded ? "{" : `{${entries.length} ${entries.length === 1 ? "field" : "fields"}}`}
        </span>
      </button>

      {expanded && (
        <div className="ml-4 border-l border-border/50 pl-2 space-y-1">
          {entries.map(([key, value]) => (
            <div key={key} className="flex items-start gap-2">
              <span className="text-orange-600 dark:text-orange-400 whitespace-nowrap">
                {key}:
              </span>
              <span className="flex-1">
                {renderJsonValue(value, currentDepth + 1)}
              </span>
            </div>
          ))}
        </div>
      )}

      {expanded && <span className="text-muted-foreground">{"}"}</span>}
    </div>
  );
};
