"use client";

import React, { useState } from "react";
import { Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import { humanizeKey } from "@/utils/nodeHelpers";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { CronBuilderDialog } from "./CronBuilderDialog";

interface CronExpressionFieldProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
  error?: string;
  className?: string;
}

export const CronExpressionField: React.FC<CronExpressionFieldProps> = ({
  name,
  value,
  onChange,
  label,
  placeholder,
  required,
  error,
  className,
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const displayLabel = label || humanizeKey(name);

  const handleConfirm = (cronExpression: string) => {
    onChange(cronExpression);
  };

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={name}>
        {displayLabel}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <div className="flex gap-2">
        <Input
          id={name}
          type="text"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || "0 9 * * *"}
          className={cn("flex-1 font-mono text-sm", error && "border-destructive")}
        />
        <Button
          type="button"
          variant="outline"
          size="default"
          onClick={() => setDialogOpen(true)}
          className="flex-shrink-0"
        >
          <Calendar className="h-4 w-4 mr-2" />
          Build
        </Button>
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
      <p className="text-xs text-muted-foreground">
        Use the builder to create a schedule or enter a cron expression manually
      </p>

      <CronBuilderDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        initialValue={value}
        onConfirm={handleConfirm}
      />
    </div>
  );
};
