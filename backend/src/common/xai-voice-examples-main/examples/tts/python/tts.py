#!/usr/bin/env python3
"""
XAI Text-to-Speech (TTS) Example - Python

Converts text to speech using XAI's audio API.
"""

import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
XAI_API_KEY = os.getenv("XAI_API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://api.x.ai/v1")
API_URL = f"{BASE_URL}/audio/speech"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def text_to_speech(
    text: str,
    voice: str = "Ara",
    response_format: str = "mp3",
    output_file: str = None
) -> str:
    """
    Convert text to speech using XAI API.
    
    Args:
        text: The text to convert to speech
        voice: Voice to use (default: "Ara")
        response_format: Audio format (mp3, wav, opus, flac, pcm)
        output_file: Output filename (auto-generated if None)
    
    Returns:
        Path to the generated audio file
    """
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY not found in environment variables")
    
    # Generate output filename if not provided
    if not output_file:
        output_file = f"speech_{voice.lower()}.{response_format}"
    
    output_path = OUTPUT_DIR / output_file
    
    print(f"Converting text to speech...")
    print(f"  Text: {text[:50]}{'...' if len(text) > 50 else ''}")
    print(f"  Voice: {voice}")
    print(f"  Format: {response_format}")
    
    # Make API request
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "input": text,
        "voice": voice,
        "response_format": response_format,
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        # Save audio file
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        print(f"Audio saved to: {output_path}")
        print(f"   Size: {len(response.content)} bytes")
        return str(output_path)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        raise


def main():
    """Main function with examples"""
    print("=" * 60)
    print("XAI Text-to-Speech Example")
    print("=" * 60)
    
    # Test text for all voices
    test_text = "Hello! This is a test of the XAI text-to-speech API. I hope you enjoy listening to my voice."
    
    # Available voices
    voices = [
        ("Ara", "Female"),
        ("Rex", "Male"),
        ("Sal", "Voice"),
        ("Eve", "Female"),
        ("Una", "Female"),
        ("Leo", "Male"),
    ]
    
    print(f"\nTesting all {len(voices)} voices...")
    print()
    
    # Test each voice
    for voice_name, voice_type in voices:
        print(f"Voice: {voice_name} ({voice_type})")
        text_to_speech(
            test_text,
            voice=voice_name,
            response_format="mp3",
            output_file=f"{voice_name.lower()}_sample.mp3",
        )
        print()
    
    print("=" * 60)
    print(f"All audio files saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

