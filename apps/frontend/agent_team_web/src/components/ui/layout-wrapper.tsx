"use client";

import React, { createContext, useContext, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { PanelLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePageTitle } from "@/contexts/page-title-context";

interface LayoutContextType {
  isCollapsed: boolean;
  setIsCollapsed: (value: boolean) => void;
  isHovered: boolean;
  setIsHovered: (value: boolean) => void;
}

const LayoutContext = createContext<LayoutContextType>({
  isCollapsed: false,
  setIsCollapsed: () => {},
  isHovered: false,
  setIsHovered: () => {},
});

export const useLayout = () => useContext(LayoutContext);

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  // Auto-collapse sidebar for workflow pages
  const [isCollapsed, setIsCollapsed] = useState(pathname.startsWith('/workflow/'));
  const [isHovered, setIsHovered] = useState(false);
  const { customTitle } = usePageTitle();

  // Update sidebar state when pathname changes
  React.useEffect(() => {
    setIsCollapsed(pathname.startsWith('/workflow/'));
  }, [pathname]);

  // Get page title based on pathname
  const getPageTitle = () => {
    if (pathname === "/") return "Recent";
    if (pathname === "/canvas") return "Assistants";
    if (pathname === "/components") return "Authorizations";
    if (pathname === "/themes") return "Themes";
    if (pathname === "/bookmarks") return "Bookmarks";
    if (pathname === "/pricing") return "Pricing";
    // For workflow pages, show "Assistants / Loading..."
    if (pathname.startsWith("/workflow/")) {
      return (
        <div className="flex items-center gap-1 text-sm font-bold">
          <button
            onClick={() => router.push('/canvas')}
            className="text-black dark:text-white hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            Assistants
          </button>
          <span className="text-black/50 dark:text-white/50 px-1">/</span>
          <span className="text-black dark:text-white">Loading...</span>
        </div>
      );
    }
    // Capitalize first letter of pathname
    return pathname.slice(1).charAt(0).toUpperCase() + pathname.slice(2);
  };

  return (
    <LayoutContext.Provider value={{ isCollapsed, setIsCollapsed, isHovered, setIsHovered }}>
      <div className="fixed inset-0 bg-white dark:bg-background">
        <div
          className={cn(
            "fixed transition-all duration-300 ease-in-out",
            "lg:left-56 lg:right-2 lg:top-2 lg:bottom-2",
            "left-0 right-0 top-0 bottom-0",
            isCollapsed && !isHovered && "lg:left-2"
          )}
        >
          <div className="h-full bg-[#F8F8F8] dark:bg-background lg:rounded-xl lg:border lg:border-border/40 flex flex-col overflow-hidden relative">
            {/* Fixed Title in Top Left Corner */}
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
              {isCollapsed && (
                <button
                  className="lg:flex hidden p-1 hover:bg-gray-100 dark:hover:bg-muted/50 rounded transition-colors bg-white dark:bg-background"
                  onClick={() => setIsCollapsed(false)}
                >
                  <PanelLeft className="h-3.5 w-3.5" />
                </button>
              )}
              {customTitle ? (
                customTitle
              ) : (
                <span className="text-sm font-bold text-black dark:text-white bg-[#F8F8F8] dark:bg-background px-2 py-1 rounded">
                  {getPageTitle()}
                </span>
              )}
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto">
              {children}
            </div>
          </div>
        </div>
      </div>
    </LayoutContext.Provider>
  );
}