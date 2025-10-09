"use client";

import React, { useEffect } from "react";
import { Globe, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { humanizeKey } from "@/utils/nodeHelpers";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getUserTimezone, getTimezoneWithOffset, TIMEZONE_OPTIONS } from "@/utils/timezone";

interface TimezoneFieldProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  error?: string;
  className?: string;
}

export const TimezoneField: React.FC<TimezoneFieldProps> = ({
  name,
  value,
  onChange,
  label,
  placeholder: _placeholder,
  required,
  readonly,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);
  const [hasInitialized, setHasInitialized] = React.useState(false);

  // Auto-detect timezone only once when component first mounts and value is empty
  useEffect(() => {
    if (!hasInitialized && !value) {
      const detectedTz = getUserTimezone();
      onChange(detectedTz);
      setHasInitialized(true);
    } else if (!hasInitialized) {
      setHasInitialized(true);
    }
  }, [hasInitialized, value, onChange]);

  const currentTimezone = value || getUserTimezone();
  const timezoneDisplay = getTimezoneWithOffset(currentTimezone);

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={name}>
        {displayLabel}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>

      {/* Display current timezone */}
      <div className="flex items-center gap-2 p-3 rounded-md border bg-muted/30">
        <Globe className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium">{timezoneDisplay}</p>
          <p className="text-xs text-muted-foreground">
            Auto-detected from your browser
          </p>
        </div>
      </div>

      {/* Dropdown for manual override (advanced users) */}
      <details className="text-xs">
        <summary className="cursor-pointer text-muted-foreground hover:text-foreground flex items-center gap-1">
          <Info className="h-3 w-3" />
          Advanced: Change timezone
        </summary>
        <div className="mt-2">
          <Select
            value={currentTimezone}
            onValueChange={onChange}
            disabled={readonly}
          >
            <SelectTrigger className={cn("w-full", error && "border-destructive")}>
              <SelectValue placeholder="Select a timezone..." />
            </SelectTrigger>
            <SelectContent className="max-h-[300px]">
              {TIMEZONE_OPTIONS.map((tz) => (
                <SelectItem key={tz.value} value={tz.value}>
                  <div className="flex items-center justify-between gap-2">
                    <span>{tz.label}</span>
                    <span className="text-xs text-muted-foreground">
                      UTC{tz.offset}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground mt-1">
            Select a timezone from the list of common options
          </p>
        </div>
      </details>

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
};
