#!/bin/bash

# XAI Speech-to-Text - Python Start Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "XAI Speech-to-Text (Python)"
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
if [ ! -d "$AUDIO_DIR" ] || [ -z "$(ls -A $AUDIO_DIR)" ]; then
    echo "⚠️  No audio files found in $AUDIO_DIR"
    echo "Please add audio files to test transcription."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Use the venv's Python directly
PYTHON="./venv/bin/python"

# Install dependencies
echo "📥 Installing dependencies..."
$PYTHON -m pip install -q --upgrade pip
$PYTHON -m pip install -q -r requirements.txt

# Run the example
echo ""
echo "🚀 Running STT example..."
echo "Testing audio files: mono.mp3, mono.wav, stereo.mp3, stereo.wav"
echo ""
$PYTHON stt.py

echo ""
echo "Done! Transcription complete."

