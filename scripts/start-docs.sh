#!/bin/bash

# Start Internal Documentation Server
# This script starts the Docusaurus documentation server for internal docs

echo "🚀 Starting Internal Documentation Server..."
echo "📍 Location: apps/internal-tools/docusaurus"
echo "🌐 URL: http://localhost:3000"
echo ""

cd "$(dirname "$0")/../apps/internal-tools/docusaurus"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🔄 Starting development server..."
npm start 