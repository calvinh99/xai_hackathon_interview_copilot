#!/bin/bash

# XAI Text-to-Speech - Node.js Start Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "XAI Text-to-Speech (Node.js)"
echo "=================================="

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your XAI_API_KEY"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run the example
echo ""
echo "🚀 Running TTS example..."
echo ""
npm start

echo ""
echo "Done! Check the ../audio/ directory for generated files."

