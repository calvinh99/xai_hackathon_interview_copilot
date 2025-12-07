"""Streaming STT using xAI WebSocket API for real-time transcription."""

import asyncio
import base64
import json
import os
import subprocess
import sys
import threading
import queue
import wave
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import websockets

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
DTYPE = 'int16'

# SystemAudioDump outputs 24kHz stereo
SYS_AUDIO_SAMPLE_RATE = 24000
SYS_AUDIO_CHANNELS = 2
SYS_AUDIO_CHUNK_DURATION = 0.1  # 100ms chunks

# Path to SystemAudioDump binary
SYSTEM_AUDIO_DUMP_PATH = Path(__file__).parent.parent.parent / "assets" / "SystemAudioDump"


class StreamingSTT:
    """Streams audio from a sounddevice input to xAI's WebSocket STT API."""

    def __init__(self, device_id: int, speaker_label: str,
                 on_transcript: Callable[[str, str, bool], None],
                 api_key: Optional[str] = None,
                 save_audio_path: Optional[str] = None):
        self.device_id = device_id
        self.speaker_label = speaker_label
        self.on_transcript = on_transcript
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.save_audio_path = save_audio_path
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._audio_buffer: list = []  # Buffer for saving audio

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self._save_audio()

    def _save_audio(self):
        if not self.save_audio_path or not self._audio_buffer:
            return
        try:
            audio_data = np.concatenate(self._audio_buffer)
            with wave.open(self.save_audio_path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data.tobytes())
            print(f"[{self.speaker_label}] Saved audio to {self.save_audio_path}")
        except Exception as e:
            print(f"[{self.speaker_label}] Failed to save audio: {e}")

    def _run_async_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._stream_audio())
        except Exception as e:
            print(f"[{self.speaker_label}] StreamingSTT error: {e}")
        finally:
            self._loop.close()
            self._loop = None

    async def _stream_audio(self):
        if not self.api_key:
            raise ValueError("XAI_API_KEY not set")

        ws_url = "wss://api.x.ai/v1/realtime/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        print(f"[{self.speaker_label}] Connecting to xAI STT (device={self.device_id})")

        audio_task = asyncio.create_task(self._capture_audio())
        try:
            async with websockets.connect(ws_url, additional_headers=headers) as ws:
                print(f"[{self.speaker_label}] Connected")
                await ws.send(json.dumps({
                    "type": "config",
                    "data": {
                        "encoding": "linear16",
                        "sample_rate_hertz": SAMPLE_RATE,
                        "enable_interim_results": True,
                    },
                }))
                await asyncio.gather(
                    self._send_audio(ws),
                    self._receive_transcripts(ws)
                )
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"[{self.speaker_label}] WebSocket closed: {e}")
        except Exception as e:
            print(f"[{self.speaker_label}] WebSocket error: {e}")
        finally:
            audio_task.cancel()
            try:
                await audio_task
            except asyncio.CancelledError:
                pass

    async def _capture_audio(self):
        def callback(indata, frames, time_info, status):
            if status:
                print(f"[{self.speaker_label}] Audio status: {status}")
            if self._running:
                chunk = indata.copy()
                self._audio_queue.put(chunk)
                if self.save_audio_path:
                    self._audio_buffer.append(chunk)

        try:
            with sd.InputStream(device=self.device_id, samplerate=SAMPLE_RATE,
                               channels=CHANNELS, dtype=DTYPE,
                               blocksize=CHUNK_SIZE, callback=callback):
                print(f"[{self.speaker_label}] Audio capture started")
                while self._running:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[{self.speaker_label}] Audio capture error: {e}")
            self._running = False

    async def _send_audio(self, ws):
        while self._running:
            try:
                audio_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._audio_queue.get(timeout=0.1)
                )
            except queue.Empty:
                continue
            except Exception as e:
                if self._running:
                    print(f"[{self.speaker_label}] Send error: {e}")
                break

            audio_b64 = base64.b64encode(audio_data.tobytes()).decode("utf-8")
            await ws.send(json.dumps({"type": "audio", "data": {"audio": audio_b64}}))

    async def _receive_transcripts(self, ws):
        while self._running:
            try:
                data = json.loads(await ws.recv())
                if data.get("data", {}).get("type") == "speech_recognized":
                    transcript_data = data["data"]["data"]
                    text = transcript_data.get("transcript", "")
                    if text.strip():
                        self.on_transcript(self.speaker_label, text, transcript_data.get("is_final", False))
            except websockets.exceptions.ConnectionClosedOK:
                break
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"[{self.speaker_label}] WebSocket closed: {e}")
                break
            except Exception as e:
                if self._running:
                    print(f"[{self.speaker_label}] Receive error: {e}")
                break
        self._running = False


class SystemAudioSTT:
    """Captures system audio via SystemAudioDump binary (macOS only)."""

    def __init__(self, speaker_label: str,
                 on_transcript: Callable[[str, str, bool], None],
                 api_key: Optional[str] = None,
                 save_audio_path: Optional[str] = None):
        self.speaker_label = speaker_label
        self.on_transcript = on_transcript
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.save_audio_path = save_audio_path
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._audio_buffer: list = []

    @staticmethod
    def is_available() -> bool:
        return sys.platform == "darwin" and SYSTEM_AUDIO_DUMP_PATH.exists()

    def start(self):
        if self._running:
            return
        if not self.is_available():
            print(f"[{self.speaker_label}] SystemAudioDump not available")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self._save_audio()

    def _save_audio(self):
        if not self.save_audio_path or not self._audio_buffer:
            return
        try:
            audio_data = np.concatenate(self._audio_buffer)
            with wave.open(self.save_audio_path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data.tobytes())
            print(f"[{self.speaker_label}] Saved audio to {self.save_audio_path}")
        except Exception as e:
            print(f"[{self.speaker_label}] Failed to save audio: {e}")

    def _run_async_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._stream_audio())
        except Exception as e:
            print(f"[{self.speaker_label}] SystemAudioSTT error: {e}")
        finally:
            self._loop.close()
            self._loop = None

    def _stereo_to_mono_resample(self, stereo_data: bytes) -> np.ndarray:
        """Convert 24kHz stereo to 16kHz mono."""
        # Parse stereo int16 samples
        stereo = np.frombuffer(stereo_data, dtype=np.int16)
        # Take left channel only (every other sample)
        mono_24k = stereo[::2].copy()
        # Resample 24kHz -> 16kHz (ratio 2:3)
        num_samples_16k = int(len(mono_24k) * SAMPLE_RATE / SYS_AUDIO_SAMPLE_RATE)
        indices = np.linspace(0, len(mono_24k) - 1, num_samples_16k).astype(int)
        mono_16k = mono_24k[indices]
        return mono_16k

    async def _capture_system_audio(self):
        """Spawn SystemAudioDump and read PCM data from stdout."""
        chunk_bytes = int(SYS_AUDIO_SAMPLE_RATE * 2 * SYS_AUDIO_CHANNELS * SYS_AUDIO_CHUNK_DURATION)

        self._process = subprocess.Popen(
            [str(SYSTEM_AUDIO_DUMP_PATH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=chunk_bytes,
        )
        print(f"[{self.speaker_label}] SystemAudioDump started (PID={self._process.pid})")

        buffer = b""
        while self._running and self._process.poll() is None:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._process.stdout.read(chunk_bytes)
                )
                if not data:
                    await asyncio.sleep(0.01)
                    continue
                buffer += data
                while len(buffer) >= chunk_bytes:
                    chunk = buffer[:chunk_bytes]
                    buffer = buffer[chunk_bytes:]
                    mono_16k = self._stereo_to_mono_resample(chunk)
                    self._audio_queue.put(mono_16k)
                    if self.save_audio_path:
                        self._audio_buffer.append(mono_16k)
            except Exception as e:
                if self._running:
                    print(f"[{self.speaker_label}] Capture error: {e}")
                break

    async def _stream_audio(self):
        if not self.api_key:
            raise ValueError("XAI_API_KEY not set")

        ws_url = "wss://api.x.ai/v1/realtime/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        print(f"[{self.speaker_label}] Connecting to xAI STT (system audio)")

        audio_task = asyncio.create_task(self._capture_system_audio())
        try:
            async with websockets.connect(ws_url, additional_headers=headers) as ws:
                print(f"[{self.speaker_label}] Connected")
                await ws.send(json.dumps({
                    "type": "config",
                    "data": {
                        "encoding": "linear16",
                        "sample_rate_hertz": SAMPLE_RATE,
                        "enable_interim_results": True,
                    },
                }))
                await asyncio.gather(
                    self._send_audio(ws),
                    self._receive_transcripts(ws)
                )
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"[{self.speaker_label}] WebSocket closed: {e}")
        except Exception as e:
            print(f"[{self.speaker_label}] WebSocket error: {e}")
        finally:
            audio_task.cancel()
            try:
                await audio_task
            except asyncio.CancelledError:
                pass

    async def _send_audio(self, ws):
        while self._running:
            try:
                audio_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._audio_queue.get(timeout=0.1)
                )
            except queue.Empty:
                continue
            except Exception as e:
                if self._running:
                    print(f"[{self.speaker_label}] Send error: {e}")
                break
            audio_b64 = base64.b64encode(audio_data.tobytes()).decode("utf-8")
            await ws.send(json.dumps({"type": "audio", "data": {"audio": audio_b64}}))

    async def _receive_transcripts(self, ws):
        while self._running:
            try:
                data = json.loads(await ws.recv())
                if data.get("data", {}).get("type") == "speech_recognized":
                    transcript_data = data["data"]["data"]
                    text = transcript_data.get("transcript", "")
                    if text.strip():
                        self.on_transcript(self.speaker_label, text, transcript_data.get("is_final", False))
            except websockets.exceptions.ConnectionClosedOK:
                break
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"[{self.speaker_label}] WebSocket closed: {e}")
                break
            except Exception as e:
                if self._running:
                    print(f"[{self.speaker_label}] Receive error: {e}")
                break
        self._running = False


class DualStreamingSTT:
    """Manages two STT sessions for interviewer and candidate."""

    # Special device ID to indicate system audio capture
    SYSTEM_AUDIO_DEVICE = -1

    def __init__(self, interviewer_device_id: int, candidate_device_id: int,
                 on_transcript: Callable[[str, str, bool], None],
                 session_dir: Optional[str] = None):
        interviewer_audio = os.path.join(session_dir, "interviewer.wav") if session_dir else None
        candidate_audio = os.path.join(session_dir, "candidate.wav") if session_dir else None

        # Interviewer always uses mic input
        self.interviewer_stt = StreamingSTT(
            interviewer_device_id, "Interviewer", on_transcript, save_audio_path=interviewer_audio)

        # Candidate: use system audio if device_id is -1 and available, else mic
        if candidate_device_id == self.SYSTEM_AUDIO_DEVICE and SystemAudioSTT.is_available():
            print("[DualStreamingSTT] Using SystemAudioDump for candidate")
            self.candidate_stt = SystemAudioSTT(
                "Candidate", on_transcript, save_audio_path=candidate_audio)
        else:
            self.candidate_stt = StreamingSTT(
                candidate_device_id, "Candidate", on_transcript, save_audio_path=candidate_audio)

    def start(self):
        self.interviewer_stt.start()
        self.candidate_stt.start()

    def stop(self):
        self.interviewer_stt.stop()
        self.candidate_stt.stop()
