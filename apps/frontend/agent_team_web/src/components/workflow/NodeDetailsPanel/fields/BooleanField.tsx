"use client";

import React from 'react';
import { cn } from '@/lib/utils';
import { humanizeKey } from '@/utils/nodeHelpers';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';

interface BooleanFieldProps {
  name: string;
  value: boolean;
  onChange: (value: boolean) => void;
  label?: string;
  required?: boolean;
  error?: string;
  className?: string;
}

export const BooleanField: React.FC<BooleanFieldProps> = ({
  name,
  value,
  onChange,
  label,
  required,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between">
        <Label htmlFor={name}>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <Switch
          id={name}
          checked={value}
          onCheckedChange={onChange}
        />
      </div>
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
};