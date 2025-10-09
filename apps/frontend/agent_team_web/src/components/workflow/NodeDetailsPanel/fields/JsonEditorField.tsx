"use client";

import React, { useState, useEffect, useMemo } from "react";
import { AlertCircle, Check, Code2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { humanizeKey } from "@/utils/nodeHelpers";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface JsonEditorFieldProps {
  name: string;
  value: Record<string, unknown> | null;
  onChange: (value: Record<string, unknown>) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  error?: string;
  className?: string;
  minHeight?: number;
}

const DEFAULT_MIN_HEIGHT = 125;

export const JsonEditorField: React.FC<JsonEditorFieldProps> = ({
  name,
  value,
  onChange,
  label,
  placeholder,
  required,
  readonly,
  error,
  className,
  minHeight = DEFAULT_MIN_HEIGHT,
}) => {
  const displayLabel = label || humanizeKey(name);

  // Track the text value separately for editing
  const [textValue, setTextValue] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [hasEdited, setHasEdited] = useState(false);

  // Initialize text value from object value
  useEffect(() => {
    if (!hasEdited) {
      try {
        const formatted = JSON.stringify(value || {}, null, 2);
        setTextValue(formatted);
      } catch {
        setTextValue("{}");
      }
    }
  }, [value, hasEdited]);

  // Validate and parse JSON
  const handleChange = (newText: string) => {
    setTextValue(newText);
    setHasEdited(true);

    // Try to parse JSON
    try {
      const parsed = JSON.parse(newText);
      setJsonError(null);
      onChange(parsed);
    } catch (err) {
      // Set error but don't update the value
      setJsonError(err instanceof Error ? err.message : "Invalid JSON");
    }
  };

  // Format JSON button handler
  const handleFormat = () => {
    try {
      const parsed = JSON.parse(textValue);
      const formatted = JSON.stringify(parsed, null, 2);
      setTextValue(formatted);
      setJsonError(null);
      onChange(parsed);
    } catch (err) {
      // If can't parse, don't format
      setJsonError(err instanceof Error ? err.message : "Invalid JSON");
    }
  };

  // Count lines for display
  const lineCount = useMemo(() => {
    return textValue.split("\n").length;
  }, [textValue]);

  // Character count
  const charCount = textValue.length;

  // Validation status
  const isValid = jsonError === null;

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <Label htmlFor={name} className="flex-shrink-0">
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Validation indicator */}
          {hasEdited && (
            <div className="flex items-center gap-1 text-xs whitespace-nowrap">
              {isValid ? (
                <>
                  <Check className="h-3 w-3 text-green-600" />
                  <span className="text-green-600">Valid</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-3 w-3 text-destructive" />
                  <span className="text-destructive">Invalid</span>
                </>
              )}
            </div>
          )}

          {/* Format button */}
          {!readonly && (
            <button
              type="button"
              onClick={handleFormat}
              disabled={!isValid}
              className={cn(
                "flex items-center gap-1 px-2 py-1 text-xs rounded border flex-shrink-0",
                "hover:bg-muted transition-colors",
                !isValid && "opacity-50 cursor-not-allowed"
              )}
            >
              <Code2 className="h-3 w-3" />
              Format
            </button>
          )}
        </div>
      </div>

      {/* JSON Editor */}
      <div className="relative">
        <Textarea
          id={name}
          value={textValue}
          onChange={(e) => handleChange(e.target.value)}
          placeholder={placeholder || '{\n  "key": "value"\n}'}
          disabled={readonly}
          className={cn(
            "font-mono text-xs resize-y !w-full",
            jsonError && "border-destructive",
            readonly && "bg-muted cursor-not-allowed"
          )}
          style={{
            minHeight: `${minHeight}px`,
            maxHeight: "500px",
            overflowX: "auto",
            overflowY: "auto",
            whiteSpace: "pre",
            overflowWrap: "normal",
            wordBreak: "normal",
            wordWrap: "normal",
            paddingRight: "32px",
            paddingLeft: "12px",
            paddingTop: "12px",
            paddingBottom: "12px",
            boxSizing: "border-box"
          }}
          rows={Math.max(10, lineCount)}
        />
      </div>

      {/* Error message */}
      {jsonError && (
        <div className="flex items-start gap-2 p-2 rounded bg-destructive/10 border border-destructive/20">
          <AlertCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-xs font-medium text-destructive">
              JSON Syntax Error
            </p>
            <p className="text-xs text-destructive/80 mt-1">{jsonError}</p>
          </div>
        </div>
      )}

      {/* External error from form validation */}
      {error && !jsonError && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      {/* Info footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {lineCount} lines • {charCount} characters
        </span>
        {placeholder && !hasEdited && (
          <span className="text-muted-foreground/60">
            Press Format to prettify
          </span>
        )}
      </div>
    </div>
  );
};
