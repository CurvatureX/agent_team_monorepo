"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ExpandableTabs } from "@/components/ui/expandable-tabs";
import { Home, Bell, User, Settings, Bot, DollarSign, LogIn, LogOut } from "lucide-react";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import Image from "next/image";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";

export const NavigationHeader = () => {
    const router = useRouter();
    const pathname = usePathname();
    const [activeTabIndex, setActiveTabIndex] = useState<number | null>(null);
    const { user, signOut } = useAuth();

    const tabs = [
        { title: "Home", icon: Home },
        { title: "Assistant", icon: Bot },
        { title: "Pricing", icon: DollarSign },
        { title: "Notifications", icon: Bell },
        { type: "separator" as const },
        user ? { title: "Profile", icon: User } : { title: "Login", icon: LogIn },
        { title: "Settings", icon: Settings },
        ...(user ? [{ title: "Logout", icon: LogOut }] : []),
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
            case 'Login':
                router.push('/login');
                break;
            case 'Profile':
                router.push('/profile');
                break;
            case 'Logout':
                await signOut();
                router.push('/');
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

            {/* Theme Toggle - Fixed Position Right */}
            <motion.div
                className="fixed top-4 right-4 z-30"
                initial={{ opacity: 0, x: 20, rotate: 10 }}
                animate={{ opacity: 1, x: 0, rotate: 0 }}
                transition={{ duration: 0.8, delay: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
                whileHover={{ scale: 1.05 }}
            >
                <ThemeToggle />
            </motion.div>
        </>
    );
}; 