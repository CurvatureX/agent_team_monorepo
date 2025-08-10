"use client";

import React from 'react';
import { Plus, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { humanizeKey } from '@/utils/nodeHelpers';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

interface ArrayFieldProps {
  name: string;
  value: string[];
  onChange: (value: string[]) => void;
  label?: string;
  required?: boolean;
  error?: string;
  className?: string;
}

export const ArrayField: React.FC<ArrayFieldProps> = ({
  name,
  value = [],
  onChange,
  label,
  required,
  error,
  className,
}) => {
  const displayLabel = label || humanizeKey(name);

  const addItem = () => {
    onChange([...value, '']);
  };

  const removeItem = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const updateItem = (index: number, newValue: string) => {
    const updated = [...value];
    updated[index] = newValue;
    onChange(updated);
  };

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between">
        <Label>
          {displayLabel}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={addItem}
          className="h-8 w-8 p-0"
        >
          <Plus className="w-4 h-4" />
        </Button>
      </div>
      
      <AnimatePresence initial={false}>
        {value.length === 0 ? (
          <p className="text-xs text-muted-foreground py-2">No items added</p>
        ) : (
          <div className="space-y-2">
            {value.map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex gap-2"
              >
                <Input
                  type="text"
                  value={item}
                  onChange={(e) => updateItem(index, e.target.value)}
                  placeholder={`Item ${index + 1}`}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeItem(index)}
                  className="h-10 w-10 p-0 text-muted-foreground hover:text-foreground"
                >
                  <X className="w-4 h-4" />
                </Button>
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>
      
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
};