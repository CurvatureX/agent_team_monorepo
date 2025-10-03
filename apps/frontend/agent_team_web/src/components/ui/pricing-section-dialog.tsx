"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Check, Zap, Shield, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogTitle,
  DialogPortal,
  DialogOverlay,
} from "@/components/ui/dialog";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";

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

interface PricingSectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PricingSectionDialog({ open, onOpenChange }: PricingSectionDialogProps) {
  const [isYearly, setIsYearly] = useState(false);

  const pricingTiers: PricingTier[] = [
    {
      name: "Basic",
      price: {
        monthly: 0,
        yearly: 0,
      },
      description: "Essential features for individuals and small teams",
      features: [
        {
          name: "Basic Workflows",
          description: "Create and run simple automation workflows",
          included: true,
        },
        {
          name: "Limited Executions",
          description: "Up to 100 workflow executions per month",
          included: true,
        },
        {
          name: "Community Support",
          description: "Get help through our community forums",
          included: true,
        },
        {
          name: "Standard Integrations",
          description: "Connect with common apps and services",
          included: true,
        },
        {
          name: "Advanced Features",
          description: "Access to advanced automation features",
          included: false,
        },
      ],
      icon: <Zap className="w-6 h-6" />,
    },
    {
      name: "Professional",
      price: {
        monthly: 29,
        yearly: 290,
      },
      description: "Advanced features and more executions for professional teams",
      features: [
        {
          name: "Advanced Workflows",
          description: "Create and run complex automation workflows",
          included: true,
        },
        {
          name: "Unlimited Executions",
          description: "Run your workflows without limits",
          included: true,
        },
        {
          name: "Priority Support",
          description: "Get fast email support responses",
          included: true,
        },
        {
          name: "All Integrations",
          description: "Connect with all available apps and services",
          included: true,
        },
        {
          name: "Advanced Features",
          description: "Access to all advanced automation features",
          included: true,
        },
      ],
      highlight: true,
      badge: "Popular",
      icon: <Star className="w-6 h-6" />,
    },
    {
      name: "Enterprise",
      price: {
        monthly: 99,
        yearly: 990,
      },
      description: "Custom solutions and dedicated support for large organizations",
      features: [
        {
          name: "Custom Workflows",
          description: "Create and run highly customized workflows",
          included: true,
        },
        {
          name: "Unlimited Executions",
          description: "Run your workflows without limits",
          included: true,
        },
        {
          name: "Dedicated Support",
          description: "Get dedicated account and technical support",
          included: true,
        },
        {
          name: "Enterprise Integrations",
          description: "Connect with enterprise-grade apps and services",
          included: true,
        },
        {
          name: "Advanced Security",
          description: "Enterprise-grade security and compliance features",
          included: true,
        },
      ],
      icon: <Shield className="w-6 h-6" />,
    },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogPortal>
        <DialogOverlay />
        <DialogPrimitive.Close className="fixed top-8 right-8 z-[100] w-10 h-10 rounded-full shadow-lg flex items-center justify-center text-zinc-900 hover:opacity-80 transition-opacity" style={{ backgroundColor: '#F1F1F1' }}>
          <X className="w-4 h-4" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
        <DialogPrimitive.Content className="w-[85vw] !max-w-[1100px] sm:!max-w-[1100px] fixed top-[50%] left-[50%] translate-x-[-50%] translate-y-[-50%] z-50 max-h-[90vh] overflow-y-auto bg-transparent border-none shadow-none p-6">
          <DialogTitle className="sr-only">Pricing Plans</DialogTitle>
        <div className="flex flex-col gap-4">
          {/* Billing Toggle */}
          <div className="flex justify-center">
            <div className="inline-flex items-center p-1 bg-white dark:bg-zinc-800/50 rounded-full border border-zinc-200 dark:border-zinc-700 shadow-sm">
              {["Monthly", "Yearly"].map((period) => (
                <button
                  key={period}
                  onClick={() => setIsYearly(period === "Yearly")}
                  className={cn(
                    "px-5 py-1.5 text-xs font-medium rounded-full transition-all duration-300",
                    (period === "Yearly") === isYearly
                      ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-lg"
                      : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100",
                  )}
                >
                  {period}
                </button>
              ))}
            </div>
          </div>

          {/* Pricing Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {pricingTiers.map((tier) => (
              <div
                key={tier.name}
                className={cn(
                  "relative group backdrop-blur-sm",
                  "rounded-2xl transition-all duration-300",
                  "flex flex-col border",
                  tier.highlight
                    ? "bg-gradient-to-b from-zinc-100/80 to-zinc-50/50 dark:from-zinc-400/[0.15] dark:to-zinc-800/10 shadow-xl border-zinc-300/50 dark:border-zinc-500/30"
                    : "bg-white dark:bg-zinc-800/50 shadow-md border-zinc-200 dark:border-zinc-700",
                )}
              >
                <div className="p-6 flex-1 flex flex-col">
                  <div className="mb-4">
                    <div className="flex items-center gap-2 mb-3">
                      <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                        {tier.name}
                      </h3>
                      {tier.badge && tier.highlight && (
                        <Badge className="px-2 py-0.5 text-xs font-medium text-white border-none" style={{ backgroundColor: '#5780BD' }}>
                          {tier.badge}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                      {tier.description}
                    </p>
                  </div>

                  <div className="mb-6">
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-bold text-zinc-900 dark:text-zinc-100">
                        ${isYearly ? tier.price.yearly : tier.price.monthly}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                      per month billed {isYearly ? "yearly" : "yearly"}
                    </p>
                  </div>

                  <div className="space-y-3 flex-1">
                    {tier.features.map((feature) => (
                      <div key={feature.name} className="flex gap-3">
                        <div
                          className={cn(
                            "mt-0.5 flex-shrink-0",
                            feature.included
                              ? "text-zinc-900 dark:text-zinc-100"
                              : "text-zinc-400 dark:text-zinc-600",
                          )}
                        >
                          <Check className="w-4 h-4" />
                        </div>
                        <div className="text-sm text-zinc-900 dark:text-zinc-100">
                          {feature.name}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="p-6 pt-0 mt-auto">
                  <Button
                    className={cn(
                      "w-full relative transition-all duration-300 h-11 text-sm font-medium",
                      tier.highlight
                        ? "text-white hover:opacity-90"
                        : "bg-zinc-100 hover:bg-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-100",
                    )}
                    style={tier.highlight ? { backgroundColor: '#5780BD' } : undefined}
                  >
                    {tier.price.monthly === 0 ? "Current Plan" : tier.highlight ? "Upgrade" : "Upgrade"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  );
}