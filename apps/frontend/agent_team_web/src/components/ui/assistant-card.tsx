'use client';

import Image from "next/image";
import { Badge } from "./badge";
import { motion } from "framer-motion";
import { GlowCard } from "./spotlight-card";
import { SaveButton } from "./save-button";
import { useState, useEffect } from "react";

interface AssistantCardProps {
  name: string;
  title: string;
  description: string;
  skills: string[];
  imagePath: string;
}

// 状态配置
const statusOptions = [
  { emoji: "😊", color: "bg-gradient-to-br from-green-400/20 to-green-600/30", label: "Happy Working" },
  { emoji: "🤔", color: "bg-gradient-to-br from-blue-400/20 to-blue-600/30", label: "Thinking" },
  { emoji: "💡", color: "bg-gradient-to-br from-yellow-400/20 to-yellow-600/30", label: "Got an Idea" },
  { emoji: "🎯", color: "bg-gradient-to-br from-purple-400/20 to-purple-600/30", label: "Focused" },
  { emoji: "☕", color: "bg-gradient-to-br from-orange-400/20 to-orange-600/30", label: "Coffee Break" },
  { emoji: "🚀", color: "bg-gradient-to-br from-red-400/20 to-red-600/30", label: "High Performance" },
  { emoji: "🎵", color: "bg-gradient-to-br from-pink-400/20 to-pink-600/30", label: "Enjoying Work" },
  { emoji: "⚡", color: "bg-gradient-to-br from-indigo-400/20 to-indigo-600/30", label: "Inspired" },
];

export function AssistantCard({
  name,
  title,
  description,
  skills,
  imagePath,
}: AssistantCardProps) {
  const [currentStatus, setCurrentStatus] = useState(statusOptions[0]);

  // 只在组件初始化时随机选择状态
  useEffect(() => {
    const randomStatus = statusOptions[Math.floor(Math.random() * statusOptions.length)];
    setCurrentStatus(randomStatus);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="group h-full"
    >
      <GlowCard
        glowColor="pink"
        customSize={true}
        className="h-full bg-gradient-to-br from-white/80 via-gray-50/80 to-gray-100/80 dark:from-gray-900/80 dark:via-gray-800/80 dark:to-gray-700/80 backdrop-blur-sm"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center space-x-4 pb-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-full overflow-hidden border-4 border-white dark:border-gray-700 shadow-lg">
                <Image
                  src={imagePath}
                  alt={name}
                  width={64}
                  height={64}
                  className="w-full h-full object-cover"
                />
              </div>
              <div 
                className={`absolute -bottom-1 -right-1 w-8 h-8 ${currentStatus.color} rounded-full border-2 border-white/80 dark:border-gray-700/80 flex items-center justify-center text-sm shadow-lg cursor-pointer hover:scale-110 transition-transform backdrop-blur-sm`}
                title={currentStatus.label}
              >
                <span className="text-lg filter drop-shadow-sm">{currentStatus.emoji}</span>
              </div>
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white group-hover:text-primary transition-colors">
                {name}
              </h3>
              <p className="text-sm text-primary font-medium">{title}</p>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 space-y-4">
            <div className="bg-white/50 dark:bg-gray-800/50 rounded-2xl p-4 border border-gray-200/50 dark:border-gray-700/50 overflow-hidden shadow-sm" style={{ borderRadius: '16px' }}>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {description}
              </p>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 whitespace-nowrap">
                🎯 Professional Skills
              </h4>
              <div className="flex flex-wrap gap-1">
                {skills.map((skill, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="text-xs bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                  >
                    {skill}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="pt-4 border-t border-gray-200/50 dark:border-gray-700/50 mt-auto flex justify-end">
            <SaveButton
              className="text-xs px-4 py-1"
              text={{
                idle: `Hire ${name} 💼`,
                saving: "Processing...",
                saved: `Hired ${name}!`
              }}
            />
          </div>
        </div>
      </GlowCard>
    </motion.div>
  );
}