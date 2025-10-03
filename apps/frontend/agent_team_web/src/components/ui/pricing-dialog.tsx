"use client";

import { Button } from "@/components/ui/button";
import { Check, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Feature {
  name: string;
  description: string;
  included: boolean;
}

interface PricingTier {
  name: string;
  price: {
    monthly: number;
    yearly: number;
  };
  description: string;
  features: Feature[];
  highlight?: boolean;
  badge?: string;
  icon: React.ReactNode;
}

interface PricingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tier: PricingTier | null;
  isYearly: boolean;
}

export function PricingDialog({ open, onOpenChange, tier, isYearly }: PricingDialogProps) {
  if (!tier) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg !top-[40%]">
        <DialogHeader>
          <DialogTitle className="text-center text-2xl font-semibold flex items-center justify-center gap-3">
            <div
              className={cn(
                "p-3 rounded-xl",
                tier.highlight
                  ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                  : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
              )}
            >
              {tier.icon}
            </div>
            <span>{tier.name} Plan</span>
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-6 py-4">
          {/* Price section */}
          <div className="text-center">
            <div className="flex items-baseline justify-center gap-2 mb-2">
              <span className="text-5xl font-bold text-zinc-900 dark:text-zinc-100">
                ${isYearly ? tier.price.yearly : tier.price.monthly}
              </span>
              <span className="text-lg text-zinc-500 dark:text-zinc-400">
                /{isYearly ? "year" : "month"}
              </span>
            </div>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {tier.description}
            </p>
            {isYearly && tier.price.yearly < tier.price.monthly * 12 && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2">
                Save ${tier.price.monthly * 12 - tier.price.yearly} with yearly billing
              </p>
            )}
          </div>

          {/* Features list */}
          <div className="space-y-3 max-h-[300px] overflow-y-auto">
            {tier.features.map((feature) => (
              <div key={feature.name} className="flex gap-3">
                <div
                  className={cn(
                    "mt-0.5 p-0.5 rounded-full transition-colors duration-200 flex-shrink-0",
                    feature.included
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-zinc-400 dark:text-zinc-600"
                  )}
                >
                  <Check className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                    {feature.name}
                  </div>
                  <div className="text-xs text-zinc-500 dark:text-zinc-400">
                    {feature.description}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              className={cn(
                "flex-1 gap-2",
                tier.highlight
                  ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900"
                  : "bg-zinc-800 dark:bg-zinc-200 text-white dark:text-zinc-900"
              )}
            >
              {tier.price.monthly === 0 ? "Get Started" : "Subscribe"}
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}