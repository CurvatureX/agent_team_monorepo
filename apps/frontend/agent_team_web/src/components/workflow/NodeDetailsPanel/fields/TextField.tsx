"use client";

import React from 'react';
import { cn } from '@/lib/utils';
import { humanizeKey } from '@/utils/nodeHelpers';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface TextFieldProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
  error?: string;
  className?: string;
}

export const TextField: React.FC<TextFieldProps> = ({
  name,
  value,
  onChange,
  label,
  placeholder,
  required,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);

  return (
    <div className={cn('space-y-2', className)}>
      <Label htmlFor={name}>
        {displayLabel}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <Input
        id={name}
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={error ? 'border-destructive' : ''}
      />
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
};