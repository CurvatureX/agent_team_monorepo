"use client";

import React from 'react';
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

interface SelectFieldProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  label?: string;
  required?: boolean;
  error?: string;
  className?: string;
}

export const SelectField: React.FC<SelectFieldProps> = ({
  name,
  value,
  onChange,
  options,
  label,
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
      <Select value={value || ''} onValueChange={onChange}>
        <SelectTrigger className={error ? 'border-destructive' : ''}>
          <SelectValue placeholder="Select an option" />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {humanizeKey(option)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
};