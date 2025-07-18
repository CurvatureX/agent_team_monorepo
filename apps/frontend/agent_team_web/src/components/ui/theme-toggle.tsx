"use client"

import { useState, useEffect } from "react"
import { Moon, Sun } from "lucide-react"
import { cn } from "@/lib/utils"

interface ThemeToggleProps {
  className?: string
}

export function ThemeToggle({ className }: ThemeToggleProps) {
  const [isDark, setIsDark] = useState(false)

  // 初始化主题
  useEffect(() => {
    // 检查localStorage中的主题设置
    const savedTheme = localStorage.getItem("theme")
    // 检查系统偏好
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
    
    // 确定初始主题
    const shouldBeDark = savedTheme === "dark" || (!savedTheme && systemPrefersDark)
    
    setIsDark(shouldBeDark)
    applyTheme(shouldBeDark)
  }, [])

  // 应用主题到DOM
  const applyTheme = (dark: boolean) => {
    const root = document.documentElement
    
    if (dark) {
      root.classList.add("dark")
    } else {
      root.classList.remove("dark")
    }
  }

  // 切换主题
  const toggleTheme = () => {
    const newTheme = !isDark
    setIsDark(newTheme)
    applyTheme(newTheme)
    
    // 保存到localStorage
    localStorage.setItem("theme", newTheme ? "dark" : "light")
  }

  return (
    <div
      className={cn(
        "flex w-16 h-8 p-1 rounded-full cursor-pointer transition-all duration-300",
        isDark 
          ? "bg-zinc-950 border border-zinc-800" 
          : "bg-white border border-zinc-200",
        className
      )}
      onClick={toggleTheme}
      role="button"
      tabIndex={0}
    >
      <div className="flex justify-between items-center w-full">
        <div
          className={cn(
            "flex justify-center items-center w-6 h-6 rounded-full transition-transform duration-300",
            isDark 
              ? "transform translate-x-0 bg-zinc-800" 
              : "transform translate-x-8 bg-gray-200"
          )}
        >
          {isDark ? (
            <Moon 
              className="w-4 h-4 text-white" 
              strokeWidth={1.5}
            />
          ) : (
            <Sun 
              className="w-4 h-4 text-gray-700" 
              strokeWidth={1.5}
            />
          )}
        </div>
        <div
          className={cn(
            "flex justify-center items-center w-6 h-6 rounded-full transition-transform duration-300",
            isDark 
              ? "bg-transparent" 
              : "transform -translate-x-8"
          )}
        >
          {isDark ? (
            <Sun 
              className="w-4 h-4 text-gray-500" 
              strokeWidth={1.5}
            />
          ) : (
            <Moon 
              className="w-4 h-4 text-black" 
              strokeWidth={1.5}
            />
          )}
        </div>
      </div>
    </div>
  )
}