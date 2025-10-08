"use client";

import React from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { humanizeKey } from '@/utils/nodeHelpers';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface MultiSelectFieldProps {
  name: string;
  value: string[];
  onChange: (value: string[]) => void;
  options: string[];
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  error?: string;
  className?: string;
}

export const MultiSelectField: React.FC<MultiSelectFieldProps> = ({
  name,
  value,
  onChange,
  options,
  label,
  placeholder,
  required,
  readonly,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);
  const selectedValues = Array.isArray(value) ? value : [];

  const handleAdd = (newValue: string) => {
    if (!selectedValues.includes(newValue)) {
      onChange([...selectedValues, newValue]);
    }
  };

  const handleRemove = (removeValue: string) => {
    onChange(selectedValues.filter((v) => v !== removeValue));
  };

  const availableOptions = options.filter((opt) => !selectedValues.includes(opt));

  return (
    <div className={cn('space-y-2', className)}>
      <Label htmlFor={name}>
        {displayLabel}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>

      {/* Selected values as badges */}
      {selectedValues.length > 0 && (
        <div className="flex flex-wrap gap-2 p-2 border rounded-md min-h-[42px]">
          {selectedValues.map((val) => (
            <Badge
              key={val}
              variant="secondary"
              className="flex items-center gap-1"
            >
              {humanizeKey(val)}
              {!readonly && (
                <button
                  type="button"
                  onClick={() => handleRemove(val)}
                  className="ml-1 hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </Badge>
          ))}
        </div>
      )}

      {/* Dropdown to add more values */}
      {!readonly && availableOptions.length > 0 && (
        <Select value="" onValueChange={handleAdd}>
          <SelectTrigger className={error ? 'border-destructive' : ''}>
            <SelectValue placeholder={placeholder || "Select options..."} />
          </SelectTrigger>
          <SelectContent>
            {availableOptions.map((option) => (
              <SelectItem key={option} value={option}>
                {humanizeKey(option)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      {selectedValues.length === 0 && required && (
        <p className="text-xs text-muted-foreground">
          At least one option must be selected
        </p>
      )}
    </div>
  );
};
