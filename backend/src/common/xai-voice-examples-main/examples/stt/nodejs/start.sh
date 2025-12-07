#!/bin/bash

# XAI Speech-to-Text - Node.js Start Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "XAI Speech-to-Text (Node.js)"
echo "=================================="

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your XAI_API_KEY"
    exit 1
fi

# Check for audio files
AUDIO_DIR="../audio"
if [ ! -d "$AUDIO_DIR" ] || [ -z "$(ls -A $AUDIO_DIR 2>/dev/null)" ]; then
    echo "⚠️  No audio files found in $AUDIO_DIR"
    echo "Please add audio files to test transcription."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run the example
echo ""
echo "🚀 Running STT example..."
echo "Testing audio files: mono.mp3, mono.wav, stereo.mp3, stereo.wav"
echo ""
npm start

echo ""
echo "Done! Transcription complete."

