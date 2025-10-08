"use client";

import React from 'react';
import { cn } from '@/lib/utils';
import { humanizeKey } from '@/utils/nodeHelpers';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface TextareaFieldProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  min?: number;
  max?: number;
  error?: string;
  className?: string;
}

export const TextareaField: React.FC<TextareaFieldProps> = ({
  name,
  value,
  onChange,
  label,
  placeholder,
  required,
  readonly,
  min,
  max,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);
  const charCount = value?.length || 0;

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between">
        <Label htmlFor={name}>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        {(min !== undefined || max !== undefined) && (
          <span className={cn(
            'text-xs text-muted-foreground',
            max && charCount > max && 'text-destructive'
          )}>
            {charCount}
            {max !== undefined && ` / ${max}`}
          </span>
        )}
      </div>
      <Textarea
        id={name}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={readonly}
        className={cn(
          'min-h-[100px] resize-y',
          error && 'border-destructive',
          readonly && 'bg-muted cursor-not-allowed'
        )}
        minLength={min}
        maxLength={max}
      />
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
      {min !== undefined && charCount < min && (
        <p className="text-xs text-muted-foreground">
          Minimum {min} characters required
        </p>
      )}
    </div>
  );
};
