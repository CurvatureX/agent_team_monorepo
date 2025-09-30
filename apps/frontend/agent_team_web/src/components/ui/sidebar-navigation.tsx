"use client";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { useLayout } from "./layout-wrapper";
import {
  Bot,
  User,
  Settings,
  LogOut,
  Moon,
  Sun,
  Menu,
  X,
  ChevronUp,
  FileText,
  Workflow,
  Clock,
  Zap,
  PanelLeftClose,
  Shield,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { LoginDialog } from "@/components/ui/login-dialog";

interface NavigationItem {
  title: string;
  href: string;
  icon: React.ElementType;
  badge?: string | number;
}

interface NavigationGroup {
  title?: string;
  items: NavigationItem[];
}

export const SidebarNavigation = () => {
  const router = useRouter();
  const pathname = usePathname();
  const { user, signOut, loading } = useAuth();
  const { theme, setTheme } = useTheme();
  const { isCollapsed, setIsCollapsed, isHovered, setIsHovered } = useLayout();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [showContent, setShowContent] = useState(!isCollapsed);
  const [isLoginDialogOpen, setIsLoginDialogOpen] = useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  React.useEffect(() => {
    if (!isCollapsed || isHovered) {
      // Delay showing content to allow sidebar animation to complete
      const timer = setTimeout(() => {
        setShowContent(true);
      }, 100);
      return () => clearTimeout(timer);
    } else {
      // Immediate hide when collapsing
      setShowContent(false);
    }
  }, [isCollapsed, isHovered]);

  const navigationGroups: NavigationGroup[] = [
    {
      items: [
        { title: "Recent", href: "/", icon: Clock },
        { title: "Assistants", href: "/canvas", icon: Bot },
        { title: "Authorizations", href: "/components", icon: Shield },
        { title: "Mock", href: "/themes", icon: Workflow },
        { title: "Mock", href: "/bookmarks", icon: FileText },
      ],
    },
    {
      title: "Tools",
      items: [
        { title: "Mock", href: "/magic-mcp", icon: Zap },
        { title: "Mock", href: "/vscode", icon: Bot },
      ],
    },
  ];

  const handleNavigation = (href: string) => {
    router.push(href);
    setIsMobileOpen(false);
  };

  const getUserInitials = () => {
    if (!user) return "U";
    const name = user.user_metadata?.full_name ||
      user.user_metadata?.name ||
      user.email ||
      'User';
    const parts = name.split('@')[0].split(' ');
    if (parts.length > 1) {
      return parts.map((p: string) => p[0]).join('').toUpperCase().slice(0, 2);
    } else {
      return parts[0].slice(0, 2).toUpperCase();
    }
  };

  const sidebarContent = (
    <>
      {/* User Section at Top */}
      <div className="px-4 py-3">
        {loading ? (
          <div className={cn(
            "flex items-center gap-2 w-full rounded-lg p-2",
            isCollapsed && !isHovered && "justify-center p-1"
          )}>
            <Avatar className="h-7 w-7 flex-shrink-0 rounded-lg">
              <AvatarFallback className="bg-primary/10 text-primary font-medium text-xs flex items-center justify-center rounded-lg">
                U
              </AvatarFallback>
            </Avatar>
            <div className={cn(
              "text-left min-w-0 flex-1 transition-all duration-300",
              showContent ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2 w-0"
            )}>
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-20"></div>
            </div>
          </div>
        ) : user ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className={cn(
                "flex items-center gap-2 w-full hover:bg-muted/30 rounded-lg p-2 transition-colors",
                isCollapsed && !isHovered && "justify-center p-1"
              )}>
                <Avatar className="h-7 w-7 flex-shrink-0 rounded-lg">
                  <AvatarFallback className="bg-primary/10 text-primary font-medium text-xs flex items-center justify-center rounded-lg">
                    {getUserInitials()}
                  </AvatarFallback>
                </Avatar>
                <div className={cn(
                  "text-left min-w-0 flex-1 transition-all duration-300",
                  showContent ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2 w-0"
                )}>
                  <p className="text-sm font-medium truncate">
                    {user.user_metadata?.full_name || user.user_metadata?.name || user.email?.split('@')[0] || 'User'}
                  </p>
                </div>
              </button>
            </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuLabel>My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => handleNavigation('/profile')}>
                  <User className="mr-2 h-4 w-4" />
                  Profile
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleNavigation('/settings')}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={async () => {
                    await signOut();
                    router.push('/');
                  }}
                  className="text-red-600 focus:text-red-600"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className={cn("justify-start", isCollapsed && !isHovered && "px-2")}
            onClick={() => setIsLoginDialogOpen(true)}
          >
            {!showContent ? <User className="h-4 w-4" /> : (
              <>
                <User className="h-4 w-4 mr-2" />
                Sign In
              </>
            )}
          </Button>
        )}
      </div>

      {/* Create New Button */}
      <div className="px-3 pb-4">
        <button
          className={cn(
            "w-full flex items-center justify-center px-3 py-1.5 rounded-lg text-sm transition-colors text-white h-8",
            isCollapsed && !isHovered && "px-2"
          )}
          style={{ backgroundColor: "#5780BD" }}
          onClick={() => console.log("Create new")}
        >
          <span className={cn(
            "transition-all duration-300 whitespace-nowrap",
            showContent ? "opacity-100 scale-100" : "opacity-0 scale-95 w-0"
          )}>
            Create new
          </span>
        </button>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 overflow-y-auto px-3">
        {navigationGroups.map((group, groupIndex) => (
          <div key={groupIndex} className="mb-4">
            {group.title && showContent && (
              <div className="px-2 pb-2">
                <p className="text-xs font-medium text-muted-foreground">
                  {group.title}
                </p>
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <button
                  key={item.href}
                  onClick={() => handleNavigation(item.href)}
                  className={cn(
                    "w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-sm transition-colors h-8",
                    "hover:bg-gray-100 dark:hover:bg-muted/50",
                    pathname === item.href
                      ? "bg-gray-100 dark:bg-muted font-medium text-foreground"
                      : "text-muted-foreground hover:text-foreground",
                    isCollapsed && !isHovered && "justify-center px-2"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <item.icon className="h-4 w-4 flex-shrink-0" />
                    <span className={cn(
                      "transition-all duration-300",
                      showContent ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2 absolute"
                    )}>
                      {item.title}
                    </span>
                  </div>
                  {showContent && item.badge && (
                    <span className="bg-primary text-primary-foreground text-xs px-1.5 py-0.5 rounded-full font-medium">
                      {item.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom Section */}
      <div className="px-4 py-3 mb-2">
        <div className={cn(
          "flex items-center justify-between",
          isCollapsed && !isHovered && "flex-col gap-1"
        )}>
          {/* Plan Button - Left Side */}
          {showContent ? (
            <button
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-gray-100 dark:bg-muted hover:bg-gray-200 dark:hover:bg-muted/80 transition-colors"
              onClick={() => handleNavigation('/pricing')}
            >
              <div className="w-4 h-4 rounded-full bg-foreground flex items-center justify-center">
                <ChevronUp className="w-2.5 h-2.5 text-background" />
              </div>
              <span className="text-xs font-medium">Free plan</span>
            </button>
          ) : (
            <button
              className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-muted hover:bg-gray-200 dark:hover:bg-muted/80 transition-colors flex items-center justify-center"
              onClick={() => handleNavigation('/pricing')}
            >
              <div className="w-4 h-4 rounded-full bg-foreground flex items-center justify-center">
                <ChevronUp className="w-2.5 h-2.5 text-background" />
              </div>
            </button>
          )}

          {/* Right Side Buttons */}
          <div className={cn(
            "flex items-center gap-1",
            isCollapsed && !isHovered && "flex-col gap-1"
          )}>
            {/* Collapse Button */}
            <button
              className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-muted hover:bg-gray-200 dark:hover:bg-muted/80 transition-colors flex items-center justify-center"
              onClick={() => setIsCollapsed(!isCollapsed)}
            >
              <PanelLeftClose className="w-3.5 h-3.5" />
            </button>

            {/* Theme Toggle */}
            {showContent ? (
              <button
                className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-muted hover:bg-gray-200 dark:hover:bg-muted/80 transition-colors flex items-center justify-center"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              >
                {mounted ? (
                  theme === 'dark' ? (
                    <Moon className="w-3.5 h-3.5" />
                  ) : (
                    <Sun className="w-3.5 h-3.5" />
                  )
                ) : (
                  <div className="w-3.5 h-3.5" />
                )}
              </button>
            ) : (
              <button
                className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-muted hover:bg-gray-200 dark:hover:bg-muted/80 transition-colors flex items-center justify-center"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              >
                {mounted ? (
                  theme === 'dark' ? (
                    <Moon className="w-3.5 h-3.5" />
                  ) : (
                    <Sun className="w-3.5 h-3.5" />
                  )
                ) : (
                  <div className="w-3.5 h-3.5" />
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden bg-background border rounded-md p-2"
      >
        {isMobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Mobile Sidebar Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-64 bg-white dark:bg-background transition-transform duration-200 lg:hidden",
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="h-full flex flex-col">
          {sidebarContent}
        </div>
      </div>

      {/* Desktop Sidebar */}
      <aside
        className={cn(
          "hidden lg:flex fixed inset-y-0 left-0 z-30 bg-white dark:bg-background transition-all duration-300 ease-in-out",
          isCollapsed && !isHovered ? "w-0 overflow-hidden" : "w-56"
        )}
        onMouseEnter={() => isCollapsed && setIsHovered(true)}
        onMouseLeave={() => isCollapsed && setIsHovered(false)}
      >
        <div className="h-full w-full flex flex-col">
          {sidebarContent}
        </div>
      </aside>

      {/* Hover Trigger Zone - only visible when collapsed */}
      {isCollapsed && !isHovered && (
        <div
          className="hidden lg:block fixed left-0 inset-y-0 w-1 z-30 hover:bg-gradient-to-r hover:from-gray-200/30 hover:to-transparent dark:hover:from-gray-700/30 transition-all duration-200"
          onMouseEnter={() => setIsHovered(true)}
        />
      )}

      {/* Login Dialog */}
      <LoginDialog
        open={isLoginDialogOpen}
        onOpenChange={setIsLoginDialogOpen}
        defaultMode="signin"
      />
    </>
  );
};