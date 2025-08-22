"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ExpandableTabs } from "@/components/ui/expandable-tabs";
import { Home, Bell, User, Settings, Bot, DollarSign, LogOut, Moon, Sun } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "next-themes";
import Image from "next/image";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { GlowButton } from "@/components/ui/shiny-button-1";

export const NavigationHeader = () => {
    const router = useRouter();
    const pathname = usePathname();
    const [activeTabIndex, setActiveTabIndex] = useState<number | null>(null);
    const { user, signOut } = useAuth();
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    const tabs = [
        { title: "Home", icon: Home },
        { title: "Assistant", icon: Bot },
        { title: "Pricing", icon: DollarSign },
        { title: "Notifications", icon: Bell },
        { type: "separator" as const },
        { title: "Profile", icon: User },
        { title: "Settings", icon: Settings },
    ];

    // Set active tab based on current path
    useEffect(() => {
        if (pathname === "/") {
            setActiveTabIndex(0); // Home
        } else if (pathname.includes("/canvas")) {
            setActiveTabIndex(1); // Assistant/Canvas page
        } else if (pathname.includes("/pricing")) {
            setActiveTabIndex(2); // Pricing page
        } else {
            // Keep current selection, don't set to null
        }
    }, [pathname]);

    // Handle tab click events
    const handleTabChange = async (index: number | null) => {
        if (index === null) return;

        setActiveTabIndex(index); // Update selected state first

        const tab = tabs[index];

        // Navigate to corresponding page based on selected tab
        switch (tab.title) {
            case 'Home':
                router.push('/');
                break;
            case 'Assistant':
                router.push('/canvas');
                break;
            case 'Pricing':
                router.push('/pricing');
                break;
            case 'Profile':
                router.push('/profile');
                break;
            default:
                console.log("Selected tab:", tab);
                break;
        }
    };

    // Handle logo click event, navigate to home page
    const handleLogoClick = () => {
        router.push('/');
        setActiveTabIndex(0);
    };

    return (
        <>
            {/* Top navigation tabs */}
            <motion.div
                className="w-full pt-4 pb-4 px-4 relative z-20 bg-background/90 backdrop-blur-sm"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
            >
                <div className="flex justify-center">
                    <ExpandableTabs
                        tabs={tabs}
                        onChange={handleTabChange}
                        initialSelectedIndex={activeTabIndex}
                    />
                </div>
            </motion.div>

            {/* Assistant Icon - Fixed Position Left */}
            <motion.div
                className="fixed top-4 left-4 z-30 cursor-pointer"
                initial={{ opacity: 0, x: -20, rotate: -10 }}
                animate={{ opacity: 1, x: 0, rotate: 0 }}
                transition={{ duration: 0.8, delay: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
                whileHover={{ scale: 1.1, rotate: 5 }}
                onClick={handleLogoClick}
                title="Go to Home"
            >
                <Image
                    src="/assistant/AlfieKnowledgeBaseQueryAssistantIcon.png"
                    alt="Alfie Knowledge Base Query Assistant"
                    width={40}
                    height={40}
                    className="w-10 h-10"
                />
            </motion.div>

            {/* User Avatar with Dropdown - Fixed Position Right */}
            <motion.div
                className="fixed top-4 right-4 z-30"
                initial={{ opacity: 0, x: 20, rotate: 10 }}
                animate={{ opacity: 1, x: 0, rotate: 0 }}
                transition={{ duration: 0.8, delay: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
            >
                {user ? (
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <div className="cursor-pointer">
                                <Avatar className="h-8 w-8 bg-primary/10 border border-primary/20 hover:scale-105 transition-transform">
                                    <AvatarFallback className="bg-gradient-to-br from-primary/20 to-primary/10 text-primary font-semibold text-sm">
                                        {(() => {
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
                                        })()}
                                    </AvatarFallback>
                                </Avatar>
                            </div>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-56">
                            <DropdownMenuLabel>
                                <div className="flex flex-col space-y-1">
                                    <p className="text-sm font-medium leading-none">
                                        {user.user_metadata?.full_name || user.user_metadata?.name || 'User'}
                                    </p>
                                    <p className="text-xs leading-none text-muted-foreground">
                                        {user.email}
                                    </p>
                                </div>
                            </DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => router.push('/profile')}>
                                <User className="mr-2 h-4 w-4" />
                                <span>Profile</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => router.push('/settings')}>
                                <Settings className="mr-2 h-4 w-4" />
                                <span>Settings</span>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            {mounted && (
                                <DropdownMenuItem onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
                                    {theme === 'dark' ? (
                                        <>
                                            <Sun className="mr-2 h-4 w-4" />
                                            <span>Light Mode</span>
                                        </>
                                    ) : (
                                        <>
                                            <Moon className="mr-2 h-4 w-4" />
                                            <span>Dark Mode</span>
                                        </>
                                    )}
                                </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={async () => {
                                await signOut();
                                router.push('/');
                            }} className="text-red-600 focus:text-red-600">
                                <LogOut className="mr-2 h-4 w-4" />
                                <span>Log out</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                ) : (
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => router.push('/login?mode=signin')}
                            className="px-4 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                        >
                            Sign In
                        </button>
                        <button
                            onClick={() => router.push('/login?mode=signup')}
                            className="px-4 py-1.5 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                        >
                            Sign Up
                        </button>
                    </div>
                )}
            </motion.div>
        </>
    );
}; 