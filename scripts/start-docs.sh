#!/bin/bash

echo "🚀 Starting Starmates Documentation Website..."
echo "📍 Location: apps/internal-tools/docusaurus-doc"
echo ""

# 检查是否在正确的目录
if [ ! -d "apps/internal-tools/docusaurus-doc" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# 进入文档目录
cd apps/internal-tools/docusaurus-doc

# 检查依赖是否已安装
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# 启动开发服务器
echo "🌟 Starting development server..."
echo "🎯 The documentation will be available at: http://localhost:3000"
echo "🔧 Features: Cyber-tech theme with pixel-style neon colors"
echo ""

npm start
