'use client'

import { PricingSection } from "@/components/blocks/pricing-section";
import { Zap, Shield, Star } from "lucide-react";
import { SplineScene } from "@/components/ui/splite";

export default function PricingPage() {
  const pricingTiers = [
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
    <main className="min-h-screen">
      {/* Hero section with 3D background */}
      <div className="relative w-full h-[65vh] overflow-hidden mb-12">
        {/* 3D background */}
        <div className="absolute inset-0 z-0">
          <SplineScene 
            scene="https://prod.spline.design/6s4Nl4Xld-jWtN23/scene.splinecode"
            className="w-full h-full"
          />
        </div>
        
        {/* Overlay gradient for better text visibility - now allows pointer events to pass through */}
        <div className="absolute inset-0 bg-gradient-to-b from-background/80 to-transparent z-10 pointer-events-none"></div>
        
        {/* Content overlay - now with limited pointer events area */}
        <div className="relative z-20 container mx-auto px-4 pt-24 pb-16 h-full flex flex-col justify-start items-center">
          <div className="bg-transparent px-6 py-4 rounded-lg">
            <h1 className="text-4xl font-bold text-center mb-6">Pricing Plans</h1>
            <p className="text-lg text-center text-zinc-600 dark:text-zinc-400 mb-12 max-w-2xl mx-auto">
              Come aboard the StarMates flagship. Choose your plan and embark on your AI journey. All plans include core features and can be upgraded anytime.
            </p>
          </div>
        </div>
        
        {/* Watermark cover - positioned at bottom right - now allows pointer events to pass through except where needed */}
        <div className="absolute bottom-0 right-0 w-50 h-20 bg-background z-20 pointer-events-none"></div>
      </div>
      
      {/* Pricing section */}
      <div className="container mx-auto px-4 py-8 relative z-30 -mt-24">
        <PricingSection tiers={pricingTiers} />
      </div>
    </main>
  );
} 