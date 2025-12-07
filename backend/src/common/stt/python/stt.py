#!/usr/bin/env python3
"""
XAI Speech-to-Text (STT) Example - Python

Converts audio files to text using XAI's transcription API.
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
API_URL = f"{BASE_URL}/audio/transcriptions"

# Audio directory
AUDIO_DIR = Path(__file__).parent.parent / "audio"


def transcribe_audio(audio_file_path: str) -> dict:
    """
    Transcribe an audio file using XAI API.
    
    Args:
        audio_file_path: Path to the audio file
    
    Returns:
        Dictionary with transcription results
    """
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY not found in environment variables")
    
    audio_path = Path(audio_file_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    print(f"Transcribing audio file: {audio_path.name}")
    print(f"  Size: {audio_path.stat().st_size} bytes")
    
    # Make API request
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
    }
    
    try:
        with open(audio_path, "rb") as f:
            files = {
                "file": (audio_path.name, f, "audio/mpeg" if audio_path.suffix == ".mp3" else "audio/wav")
            }
            response = requests.post(API_URL, headers=headers, files=files)
            response.raise_for_status()
        
        result = response.json()
        
        print(f"Transcription complete")
        print(f"   Text: {result.get('text', 'N/A')}")
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        raise


def main():
    """Main function with examples"""
    print("=" * 60)
    print("XAI Speech-to-Text Example")
    print("=" * 60)
    
    # Test all audio files
    audio_files = [
        "mono.mp3",
        "mono.wav",
        "stereo.mp3",
        "stereo.wav",
    ]
    
    results = []
    
    for audio_file in audio_files:
        audio_path = AUDIO_DIR / audio_file
        if audio_path.exists():
            print()
            try:
                result = transcribe_audio(audio_path)
                results.append({
                    "file": audio_file,
                    "success": True,
                    "text": result.get("text", ""),
                })
            except Exception as e:
                print(f"Failed to transcribe {audio_file}: {e}")
                results.append({
                    "file": audio_file,
                    "success": False,
                    "error": str(e),
                })
        else:
            print(f"\n⚠️  Audio file not found: {audio_file}")
    
    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    for result in results:
        status = "✅" if result.get("success") else "❌"
        print(f"{status} {result['file']}")
        if result.get("success"):
            print(f"   {result['text'][:80]}{'...' if len(result['text']) > 80 else ''}")
    print("=" * 60)


if __name__ == "__main__":
    main()

