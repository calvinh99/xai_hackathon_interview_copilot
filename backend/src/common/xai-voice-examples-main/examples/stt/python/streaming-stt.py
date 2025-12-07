#!/usr/bin/env python3
"""
Streaming Speech-to-Text Example

This example demonstrates how to use XAI's streaming STT API to transcribe speech
in real-time using WebSocket connections. Audio is captured from the microphone
and transcribed as you speak.

API: wss://api.x.ai/v1/realtime/audio/transcriptions
Audio format: PCM linear16, 16kHz, mono
"""

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

import websockets
from dotenv import load_dotenv

# PyAudio is optional - only needed for microphone input
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    pyaudio = None


class StreamingSTT:
    """Streaming Speech-to-Text handler."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        enable_interim: bool = True,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.enable_interim = enable_interim
        self.running = False
        self.final_transcript = ""
        self.current_interim = ""
        self.first_transcript_time = None
        self.stream_start_time = None
        self.transcript_count = 0

    async def stream_audio(self):
        """Stream audio from microphone to XAI API."""
        # Check if PyAudio is available
        if not PYAUDIO_AVAILABLE:
            print("❌ PyAudio is not installed")
            print("   Install with: pip install pyaudio")
            print("   Or use the Node.js version which uses ffmpeg")
            return

        # Get API key
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY not found in environment variables")

        # Get base URL
        base_url = os.getenv("BASE_URL", "https://api.x.ai/v1")
        ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
        uri = f"{ws_url}/realtime/audio/transcriptions"

        print(f"🎤 Connecting to {uri}")
        print(f"📊 Sample rate: {self.sample_rate} Hz")
        print(f"🎵 Channels: {self.channels}")
        print(f"📦 Chunk size: {self.chunk_size}")
        print(f"⏱️  Interim results: {'enabled' if self.enable_interim else 'disabled'}")

        # Set up headers
        headers = {"Authorization": f"Bearer {api_key}"}

        # Initialize PyAudio
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
        )

        print("✅ Microphone ready")

        try:
            async with websockets.connect(uri, additional_headers=headers) as websocket:
                print("✅ Connected to XAI streaming STT API")
                print("\n🎙️  Speak now... (Press Ctrl+C to stop)\n")

                # Send config message
                config_message = {
                    "type": "config",
                    "data": {
                        "encoding": "linear16",
                        "sample_rate_hertz": self.sample_rate,
                        "enable_interim_results": self.enable_interim,
                    },
                }
                await websocket.send(json.dumps(config_message))
                print(f"📤 Sent config")

                self.running = True
                self.stream_start_time = time.time()

                # Create tasks for sending and receiving
                send_task = asyncio.create_task(self._send_audio(websocket, stream))
                recv_task = asyncio.create_task(self._receive_transcripts(websocket))

                # Wait for both tasks
                await asyncio.gather(send_task, recv_task)

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise
        finally:
            self.running = False
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("\n✅ Microphone closed")

            if self.final_transcript:
                print(f"\n📝 Final transcript:\n{self.final_transcript}")
                
            # Display metrics
            if self.stream_start_time:
                total_time = time.time() - self.stream_start_time
                print(f"\n📊 Performance Metrics:")
                if self.first_transcript_time:
                    time_to_first = (self.first_transcript_time - self.stream_start_time) * 1000
                    print(f"   ⚡ Time to first transcript: {time_to_first:.0f}ms")
                print(f"   📏 Total transcripts: {self.transcript_count}")
                print(f"   ⏱️  Total recording time: {total_time:.1f}s")
                if self.transcript_count > 0:
                    print(f"   🎯 Real-time transcription: Transcripts received WHILE speaking")

    async def _send_audio(self, websocket, stream):
        """Send audio chunks to the WebSocket."""
        chunk_count = 0
        try:
            while self.running:
                # Read audio chunk
                audio_data = await asyncio.to_thread(stream.read, self.chunk_size, exception_on_overflow=False)

                # Convert to base64
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")

                # Send audio message
                audio_message = {
                    "type": "audio",
                    "data": {"audio": audio_b64},
                }
                await websocket.send(json.dumps(audio_message))

                chunk_count += 1
                if chunk_count % 50 == 0:  # Log every 50 chunks
                    print(f"  📤 Sent {chunk_count} audio chunks...", end="\r")

        except Exception as e:
            if self.running:
                print(f"\n❌ Error sending audio: {e}")
                self.running = False

    async def _receive_transcripts(self, websocket):
        """Receive and display transcripts from the WebSocket."""
        try:
            while self.running:
                response = await websocket.recv()
                data = json.loads(response)

                # Check if it's a transcript
                if data.get("data", {}).get("type") == "speech_recognized":
                    transcript_data = data["data"]["data"]
                    transcript = transcript_data.get("transcript", "")
                    is_final = transcript_data.get("is_final", False)
                    
                    # Track time to first transcript
                    if self.first_transcript_time is None and transcript:
                        self.first_transcript_time = time.time()
                        elapsed = (self.first_transcript_time - self.stream_start_time) * 1000
                        print(f"\r⚡ First transcript received in {elapsed:.0f}ms")

                    if is_final:
                        # Final transcript
                        self.final_transcript += transcript + " "
                        self.current_interim = ""
                        self.transcript_count += 1
                        elapsed = (time.time() - self.stream_start_time) * 1000
                        print(f"\r✅ [{elapsed:.0f}ms] {transcript}")
                    else:
                        # Interim transcript
                        self.current_interim = transcript
                        elapsed = (time.time() - self.stream_start_time) * 1000
                        print(f"\r💭 [{elapsed:.0f}ms] {transcript}", end="", flush=True)

        except websockets.exceptions.ConnectionClosedOK:
            print("\n✅ Connection closed normally")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"\n❌ Connection closed with error: {e}")
        except Exception as e:
            if self.running:
                print(f"\n❌ Error receiving transcripts: {e}")
                self.running = False


def main():
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Stream speech-to-text using XAI API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default settings
  python streaming-stt.py

  # Disable interim results (only show final transcripts)
  python streaming-stt.py --no-interim

  # Custom sample rate and chunk size
  python streaming-stt.py --sample-rate 24000 --chunk-size 2048

Notes:
  - Press Ctrl+C to stop recording
  - Interim results show partial transcripts in real-time
  - Final results are confirmed transcripts
        """,
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Audio sample rate in Hz (default: 16000)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=1,
        help="Number of audio channels (default: 1 for mono)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024,
        help="Audio chunk size in frames (default: 1024)",
    )
    parser.add_argument(
        "--no-interim",
        action="store_true",
        help="Disable interim results (only show final transcripts)",
    )

    args = parser.parse_args()

    stt = StreamingSTT(
        sample_rate=args.sample_rate,
        channels=args.channels,
        chunk_size=args.chunk_size,
        enable_interim=not args.no_interim,
    )

    try:
        asyncio.run(stt.stream_audio())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

