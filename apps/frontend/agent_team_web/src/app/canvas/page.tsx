"use client";

import React, { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { ExpandableTabs } from "@/components/ui/expandable-tabs";
import { PanelResizer } from "@/components/ui/panel-resizer";
import AssistantList from "@/components/ui/assistant-list";
import { User, Bot, Home, Bell, Settings } from "lucide-react";
import { useResizablePanel } from "@/hooks";
import { assistants } from "@/lib/assistant-data";

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

const CanvasPage = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // Use the custom hook for resizable panels
  const { width: rightPanelWidth, isResizing, resizerProps, overlayProps } = useResizablePanel({
    initialWidth: 384,
    minWidth: 300,
    maxWidthRatio: 0.6
  });

  const tabs = [
    { title: "Home", icon: Home },
    { title: "Assistant", icon: Bot },
    { title: "Notifications", icon: Bell },
    { type: "separator" as const },
    { title: "Profile", icon: User },
    { title: "Settings", icon: Settings },
  ];

  // Get initial message from ai-prompt page
  useEffect(() => {
    const initialMessage = sessionStorage.getItem('initialMessage');
    if (initialMessage) {
      const userMessage: Message = {
        id: Date.now().toString(),
        content: initialMessage,
        sender: 'user',
        timestamp: new Date()
      };
      setMessages([userMessage]);
      sessionStorage.removeItem('initialMessage');
      
      // Simulate AI response
      setTimeout(() => {
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: "I understand your requirements. Let me create a solution for you.",
          sender: 'assistant',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
      }, 1000);
    }
  }, []);

  const handleSendMessage = useCallback((message: string, files?: File[]) => {
    if (!message.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: message,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Handle file uploads if any
    if (files && files.length > 0) {
      console.log('Processing uploaded files:', files);
    }

    // Simulate AI response
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `I received your message: "${message}". Let me process this request for you.`,
        sender: 'assistant',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1500);
  }, []);

  const leftPanelWidth = `calc(100% - ${rightPanelWidth}px)`;

  return (
    <div className="min-h-screen bg-background transition-colors duration-300">
      {/* Background Gradient Overlay */}
      {/* <div className="fixed inset-0 bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,0.1)_10.5%,rgba(245,120,2,0.08)_16%,rgba(245,140,2,0.06)_17.5%,rgba(245,170,100,0.04)_25%,rgba(238,174,202,0.02)_40%,rgba(202,179,214,0.01)_65%,rgba(148,201,233,0.005)_100%)] dark:bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,0.05)_10.5%,rgba(245,120,2,0.04)_16%,rgba(245,140,2,0.03)_17.5%,rgba(245,170,100,0.02)_25%,rgba(238,174,202,0.01)_40%,rgba(202,179,214,0.005)_65%,rgba(148,201,233,0.002)_100%)] pointer-events-none" /> */}

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
            onChange={(index) => {
              if (index !== null) {
                console.log("Selected tab:", tabs[index]);
              }
            }}
          />
        </div>
      </motion.div>

      {/* Assistant Icon - Fixed Position Left */}
      <motion.div
        className="fixed top-4 left-4 z-30"
        initial={{ opacity: 0, x: -20, rotate: -10 }}
        animate={{ opacity: 1, x: 0, rotate: 0 }}
        transition={{ duration: 0.8, delay: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
        whileHover={{ scale: 1.1, rotate: 5 }}
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

      {/* Main Content */}
      <motion.div 
        className="flex fixed inset-0 pt-[80px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        {/* Left Side - Canvas Area */}
        <motion.div
          className="pb-6 px-6 h-full"
          style={{ width: leftPanelWidth }}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <AssistantList assistants={assistants} />
        </motion.div>

        {/* Resize Handle */}
        <PanelResizer isResizing={isResizing} resizerProps={resizerProps} overlayProps={overlayProps} />

        {/* Right Side - Chat Area */}
        <motion.div
          className="flex flex-col bg-background/95 backdrop-blur-sm h-full border-l border-t border-border/30 rounded-tl-lg"
          style={{ width: `${rightPanelWidth}px` }}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          {/* Chat Messages */}
          <div className="flex-1 p-4 overflow-y-auto pt-2">
            <div className="space-y-4">
              <AnimatePresence>
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                    className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] p-3 rounded-2xl ${
                        message.sender === 'user'
                          ? 'bg-primary text-primary-foreground ml-4'
                          : 'bg-muted text-muted-foreground mr-4'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {message.sender === 'assistant' && (
                          <Bot className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        )}
                        {message.sender === 'user' && (
                          <User className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        )}
                        <div>
                          <p className="text-sm">{message.content}</p>
                          <p className="text-xs opacity-70 mt-1">
                            {message.timestamp.toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start"
                >
                  <div className="bg-muted text-muted-foreground p-3 rounded-2xl mr-4">
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4" />
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>
          </div>

          {/* Input Area */}
          <motion.div
            className="p-4 bg-background/95 backdrop-blur-sm flex-shrink-0"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <PromptInputBox
              onSend={handleSendMessage}
              isLoading={isLoading}
              placeholder="Continue conversation..."
              className="shadow-sm"
            />
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default CanvasPage;
