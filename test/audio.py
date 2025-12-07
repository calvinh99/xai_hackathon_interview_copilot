import os
from backend.src.online.audio import audio_to_text
from backend.src.online.audio import audio_capture
from backend.src.online.audio import list_audio_devices

def list_dev():
    print("Available audio devices:")
    list_audio_devices()

def test_audio_to_text():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_audio_path = os.path.join(base_dir, "data", "mono.wav")
    transcription = audio_to_text(test_audio_path)
    return transcription

if __name__ == "__main__":
    list_dev()
    audio_capture("test_recording.wav", start=True, device_id=4)
    input("Recording... Press Enter to stop.")
    audio_capture("test_recording.wav", start=False, device_id=4)
    result = test_audio_to_text()
    print("Transcription Result:", result)