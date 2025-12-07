#!/usr/bin/env python3
"""
Streaming Text-to-Speech Example

This example demonstrates how to use XAI's streaming TTS API to convert text to speech
in real-time using WebSocket connections. The audio is played as it's received and
optionally saved to a file.

API: wss://api.x.ai/v1/realtime/audio/speech
Audio format: PCM linear16, 24kHz, mono
"""

import argparse
import asyncio
import base64
import json
import os
import sys
import time
import wave
from pathlib import Path

import websockets
from dotenv import load_dotenv

# PyAudio is optional - only needed for playback
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    pyaudio = None


async def streaming_tts(
    text: str,
    voice: str = "ara",
    output_file: str = None,
    play_audio: bool = True,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
):
    """
    Stream text-to-speech from XAI API.

    Args:
        text: Text to convert to speech
        voice: Voice ID (ara, rex, sal, eve, una, leo)
        output_file: Optional path to save audio
        play_audio: Whether to play audio in real-time
        sample_rate: Audio sample rate (24000 Hz)
        channels: Number of audio channels (1 for mono)
        sample_width: Sample width in bytes (2 for 16-bit)
    """
    # Get API key
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY not found in environment variables")

    # Get base URL
    base_url = os.getenv("BASE_URL", "https://api.x.ai/v1")
    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
    uri = f"{ws_url}/realtime/audio/speech"

    print(f"🎤 Connecting to {uri}")
    print(f"📝 Voice: {voice}")
    print(f"📄 Text: {text[:50]}{'...' if len(text) > 50 else ''}")

    # Set up headers
    headers = {"Authorization": f"Bearer {api_key}"}

    # Initialize audio playback if needed
    audio_stream = None
    p = None
    if play_audio:
        if not PYAUDIO_AVAILABLE:
            print("⚠️  PyAudio not available - skipping playback")
            print("   Install with: pip install pyaudio")
            play_audio = False
        else:
            p = pyaudio.PyAudio()
            audio_stream = p.open(
                format=pyaudio.paInt16 if sample_width == 2 else pyaudio.paInt32,
                channels=channels,
                rate=sample_rate,
                output=True,
            )

    audio_bytes = b""
    chunk_count = 0
    
    # Timing metrics
    start_time = time.time()
    first_chunk_time = None
    last_chunk_time = None

    try:
        async with websockets.connect(uri, additional_headers=headers) as websocket:
            print("✅ Connected to XAI streaming TTS API")

            # Send config message
            config_message = {"type": "config", "data": {"voice_id": voice}}
            await websocket.send(json.dumps(config_message))
            print(f"📤 Sent config: {config_message}")

            # Send text chunk
            text_message = {
                "type": "text_chunk",
                "data": {"text": text, "is_last": True},
            }
            await websocket.send(json.dumps(text_message))
            request_sent_time = time.time()
            print(f"📤 Sent text chunk")

            # Receive audio chunks
            print("🎵 Receiving and playing audio in real-time...")
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)

                    # Extract audio data
                    audio_b64 = data["data"]["data"]["audio"]
                    is_last = data["data"]["data"].get("is_last", False)

                    # Decode audio
                    chunk_bytes = base64.b64decode(audio_b64)
                    audio_bytes += chunk_bytes
                    chunk_count += 1
                    
                    # Track timing
                    current_time = time.time()
                    if first_chunk_time is None and len(chunk_bytes) > 0:
                        first_chunk_time = current_time
                        time_to_first_audio = (first_chunk_time - request_sent_time) * 1000
                        print(f"  ⚡ First audio chunk received in {time_to_first_audio:.0f}ms")

                    # Play audio in real-time (streaming playback!)
                    if play_audio and audio_stream and len(chunk_bytes) > 0:
                        await asyncio.to_thread(audio_stream.write, chunk_bytes)

                    print(f"  📦 Chunk {chunk_count}: {len(chunk_bytes)} bytes", end="")
                    if is_last:
                        last_chunk_time = current_time
                        print(" (last)")
                        break
                    else:
                        print()

                except websockets.exceptions.ConnectionClosedOK:
                    print("✅ Connection closed normally")
                    break
                except websockets.exceptions.ConnectionClosedError as e:
                    print(f"❌ Connection closed with error: {e}")
                    break

    finally:
        # Clean up audio playback
        if audio_stream:
            audio_stream.stop_stream()
            audio_stream.close()
        if p:
            p.terminate()

    # Calculate and display metrics
    total_time = time.time() - start_time
    audio_duration = len(audio_bytes) / (sample_rate * channels * sample_width)
    
    print(f"\n✅ Received {chunk_count} audio chunks ({len(audio_bytes)} bytes total)")
    print(f"\n📊 Performance Metrics:")
    if first_chunk_time:
        print(f"   ⚡ Time to first audio: {(first_chunk_time - request_sent_time) * 1000:.0f}ms")
    if last_chunk_time:
        print(f"   ⏱️  Time to last byte: {(last_chunk_time - request_sent_time) * 1000:.0f}ms")
    print(f"   📏 Audio duration: {audio_duration:.2f}s")
    print(f"   🎯 Total time: {total_time:.2f}s")
    if last_chunk_time and audio_duration > 0:
        streaming_ratio = ((last_chunk_time - request_sent_time) / audio_duration) * 100
        print(f"   💡 Streaming efficiency: Generated in {streaming_ratio:.0f}% of playback time")
        if streaming_ratio < 100:
            print(f"   🚀 Audio finished playing BEFORE generation completed (streaming advantage!)")

    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)

        print(f"💾 Saved audio to {output_file}")

    return audio_bytes


def main():
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Stream text-to-speech using XAI API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default voice (Ara)
  python streaming-tts.py "Hello, how are you today?"

  # Specify voice
  python streaming-tts.py "Hello!" --voice rex

  # Save to file
  python streaming-tts.py "Hello!" --output output.wav

  # Disable playback (only save to file)
  python streaming-tts.py "Hello!" --output output.wav --no-play

Available voices:
  ara - Female voice (default)
  rex - Male voice
  sal - Voice (likely Salathiel)
  eve - Female voice
  una - Female voice
  leo - Male voice
        """,
    )

    parser.add_argument("text", help="Text to convert to speech")
    parser.add_argument(
        "--voice",
        default="ara",
        choices=["ara", "rex", "sal", "eve", "una", "leo"],
        help="Voice to use (default: ara)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (e.g., output.wav)",
    )
    parser.add_argument(
        "--no-play",
        action="store_true",
        help="Don't play audio (only save to file)",
    )

    args = parser.parse_args()

    # Validate
    if args.no_play and not args.output:
        print("❌ Error: --no-play requires --output to be specified")
        sys.exit(1)

    try:
        asyncio.run(
            streaming_tts(
                text=args.text,
                voice=args.voice,
                output_file=args.output,
                play_audio=not args.no_play,
            )
        )
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

