import sounddevice as sd
import soundfile as sf
import threading
import queue
import sys

from ..common.stt.python.stt import transcribe_audio

class SystemAudioRecorder:
    def __init__(self, sample_rate=44100, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.stream = None
        self.q = queue.Queue()
        self.recording = False
        self.writer_thread = None

    def list_devices(self):
        """Prints available devices to help you find IDs."""
        print("\n=== Available Audio Devices ===")
        print(sd.query_devices())
        print("===============================\n")

    def _callback(self, indata, frames, time, status):
        """Thread-safe callback for audio stream."""
        if status:
            print(f"Audio Status: {status}", file=sys.stderr)
        self.q.put(indata.copy())

    def _file_writer(self, filepath):
        """Writes audio data to file in a separate thread."""
        with sf.SoundFile(filepath, mode='x', samplerate=self.sample_rate, 
                          channels=self.channels) as file:
            while self.recording or not self.q.empty():
                try:
                    # If the queue is empty for >0.2s, this raises queue.Empty
                    data = self.q.get(timeout=0.2)
                    file.write(data)
                except queue.Empty:
                    # Catch the error and loop back to check 'self.recording'
                    continue

    def start(self, output_path, device_index=None):
        """
        Starts recording.
        
        Args:
            output_path: Where to save the .wav file.
            device_index: The integer ID of the device to record from.
                          If None, uses system default input.
        """
        if self.recording:
            print("⚠️  Error: Already recording.")
            return

        self.recording = True
        
        # Start file writer thread
        self.writer_thread = threading.Thread(target=self._file_writer, args=(output_path,))
        self.writer_thread.start()

        # Start audio stream
        self.stream = sd.InputStream(
            device=device_index, # <--- KEY: Selects Mic or Loopback
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._callback
        )
        self.stream.start()
        print(f"🎙️  Recording started on Device #{device_index if device_index else 'Default'} -> {output_path}")

    def stop(self):
        """Stops recording and saves file."""
        if not self.recording:
            return

        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        
        if self.writer_thread:
            self.writer_thread.join()
        
        print("⏹️  Recording stopped and saved.")

# --- API Wrappers ---

recorder = SystemAudioRecorder()

def list_audio_devices():
    """Helper to see what IDs to use"""
    recorder.list_devices()

def audio_capture(output_path, start=True, device_id=None):
    """
    Unified capture function.
    pass device_id to switch between Microphone and System Audio.
    """
    if start:
        recorder.start(output_path, device_index=device_id)
    else:
        recorder.stop()

def audio_to_text(input_path):
    """Mock of your existing transcription call"""
    return transcribe_audio(input_path).get('text')