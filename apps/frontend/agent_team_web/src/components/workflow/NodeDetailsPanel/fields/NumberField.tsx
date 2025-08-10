"use client";

import React from 'react';
import { cn } from '@/lib/utils';
import { humanizeKey } from '@/utils/nodeHelpers';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface NumberFieldProps {
  name: string;
  value: number;
  onChange: (value: number) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
  min?: number;
  max?: number;
  step?: number;
  error?: string;
  className?: string;
}

export const NumberField: React.FC<NumberFieldProps> = ({
  name,
  value,
  onChange,
  label,
  placeholder,
  required,
  min,
  max,
  step = 1,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.valueAsNumber;
    if (!isNaN(newValue)) {
      onChange(newValue);
    }
  };

  return (
    <div className={cn('space-y-2', className)}>
      <Label htmlFor={name}>
        {displayLabel}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <Input
        id={name}
        type="number"
        value={value || 0}
        onChange={handleChange}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step}
        className={error ? 'border-destructive' : ''}
      />
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
};