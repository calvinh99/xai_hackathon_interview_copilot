# XAI Speech-to-Text (STT)

Transcribe audio files to text using XAI's transcription API with high accuracy.

## Quick Start

### Standard STT (HTTP API)

```bash
# Python
cd python && ./start.sh

# Node.js
cd nodejs && ./start.sh
```

The script will:
- Create virtual environment (Python) or install dependencies (Node.js)
- Check for `.env` file and test audio files
- Transcribe all test audio files
- Display results with accuracy summary

### Streaming STT (WebSocket API)

Real-time speech-to-text from your microphone:

```bash
# Python - transcribe from microphone in real-time
cd python
python streaming-stt.py

# Node.js - transcribe from microphone in real-time
cd nodejs
npx tsx streaming-stt.ts
```

Press Ctrl+C to stop recording.

## API Endpoints

### Standard STT
```
POST https://api.x.ai/v1/audio/transcriptions
```

### Streaming STT
```
WSS wss://api.x.ai/v1/realtime/audio/transcriptions
```

## curl Example (Standard API)

```bash
curl --request POST \
    --url https://api.x.ai/v1/audio/transcriptions \
    -H "Authorization: Bearer xai-xxx" \
    -H 'Content-Type: multipart/form-data' \
    --form file=@./input.mp3
```

## Configuration

All examples use environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `XAI_API_KEY` | Yes | - | Your XAI API key |
| `BASE_URL` | No | `https://api.x.ai/v1` | API base URL |

## Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | file | Yes | Audio file to transcribe (MP3, WAV, etc.) |
| `model` | string | No | Model to use (default: whisper-1) |
| `language` | string | No | Input language (ISO-639-1 format) |
| `prompt` | string | No | Optional text to guide the model |

## Response

```json
{
  "text": "Transcribed text from the audio file."
}
```

## Test Audio Files

The `audio/` directory contains sample files for testing:

| File | Format | Channels | Use Case |
|------|--------|----------|----------|
| `mono.mp3` | MP3 | Mono | Most common format |
| `mono.wav` | WAV | Mono | Uncompressed audio |
| `stereo.mp3` | MP3 | Stereo | Multi-channel audio |
| `stereo.wav` | WAV | Stereo | Uncompressed stereo |

**Note:** Test audio files are committed to git for easy testing.

## Examples

### Python

**Quick Start:**
```bash
cd python
./start.sh
```

**Manual Setup:**
```bash
cd python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your XAI_API_KEY
python stt.py
```

**Features:**
- Transcribes all test audio files
- Displays results with summary
- Error handling and logging
- Supports MP3 and WAV formats

**Dependencies:**
- Python 3.13+
- requests
- python-dotenv

### Node.js

**Quick Start:**
```bash
cd nodejs
./start.sh
```

**Manual Setup:**
```bash
cd nodejs
npm install
cp .env.example .env
# Edit .env and add your XAI_API_KEY
npm start
```

**Features:**
- TypeScript support
- Async/await pattern
- Tests all audio formats
- Error handling and logging
- Uses axios for reliable multipart uploads

**Dependencies:**
- Node.js 18+
- TypeScript
- axios
- form-data
- dotenv

## Usage in Your Application

### Python Example

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

with open("audio.mp3", "rb") as audio_file:
    response = requests.post(
        "https://api.x.ai/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}"},
        files={"file": ("audio.mp3", audio_file, "audio/mpeg")}
    )

result = response.json()
print(f"Transcription: {result['text']}")
```

### Node.js Example

```typescript
import fs from 'fs';
import FormData from 'form-data';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const formData = new FormData();
formData.append('file', fs.createReadStream('audio.mp3'), {
  filename: 'audio.mp3',
  contentType: 'audio/mpeg'
});

const response = await axios.post(
  'https://api.x.ai/v1/audio/transcriptions',
  formData,
  {
    headers: {
      'Authorization': `Bearer ${process.env.XAI_API_KEY}`,
      ...formData.getHeaders()
    }
  }
);

console.log(`Transcription: ${response.data.text}`);
```

## Streaming API

For real-time transcription from microphone:

### Python Streaming Example

```bash
# Start streaming transcription
python streaming-stt.py

# With custom settings
python streaming-stt.py --sample-rate 24000 --no-interim

# Options:
#   --sample-rate: Audio sample rate (default: 16000)
#   --channels: Number of channels (default: 1)
#   --chunk-size: Audio chunk size (default: 1024)
#   --no-interim: Disable interim results
```

### Node.js Streaming Example

```bash
# Start streaming transcription (requires ffmpeg)
npx tsx streaming-stt.ts

# With custom settings
npx tsx streaming-stt.ts --sample-rate 24000 --no-interim

# Options:
#   --sample-rate: Audio sample rate (default: 16000)
#   --channels: Number of channels (default: 1)
#   --no-interim: Disable interim results
```

**Note:** Node.js streaming requires ffmpeg for microphone access:
- macOS: `brew install ffmpeg`
- Linux: `apt install ffmpeg`
- Windows: Download from ffmpeg.org

### Streaming Features

**Interim Results:**
- Shows partial transcripts in real-time (prefixed with 💭)
- Final transcripts confirmed (prefixed with ✅)

**When to Use Streaming:**
- ✅ Live voice input
- ✅ Real-time transcription
- ✅ Voice assistants
- ✅ Interactive applications

**When to Use Standard API:**
- ✅ Pre-recorded audio files
- ✅ Batch transcription
- ✅ Offline processing
- ✅ Simpler integration

## Supported Audio Formats

| Format | Extension | MIME Type | Notes |
|--------|-----------|-----------|-------|
| **MP3** | .mp3 | audio/mpeg | Most common, good compression |
| **WAV** | .wav | audio/wav | Uncompressed, high quality |
| **M4A** | .m4a | audio/m4a | Apple format |
| **OGG** | .ogg | audio/ogg | Open format |
| **FLAC** | .flac | audio/flac | Lossless compression |

**Supported channels:** Mono and Stereo

## Error Handling

Common errors and solutions:

**401 Unauthorized:**
- Check your API key is correct
- Ensure key is properly set in `.env`

**400 Bad Request:**
- Verify audio file format is supported
- Check file is not corrupted
- Ensure file size is within limits

**500 Internal Error:**
- Try again after a moment
- Try converting audio to a different format
- Check XAI API status

## Best Practices

1. **Audio quality matters** - Use clear, noise-free audio
2. **Format selection** - MP3 or WAV are most reliable
3. **File size** - Keep files under 25MB for best performance
4. **Sample rate** - 16kHz or higher recommended
5. **Error handling** - Implement retry logic
6. **Batch processing** - Process multiple files efficiently

## Audio Preprocessing Tips

For best transcription results:

- **Remove background noise** - Clean audio transcribes better
- **Normalize audio levels** - Consistent volume helps accuracy
- **Use mono audio** - Unless stereo is required
- **Sample rate** - 16kHz minimum, 44.1kHz optimal
- **Format** - Use MP3 or WAV for compatibility

## Limitations

- Maximum file size: Check API documentation
- Supported languages: Multiple (check API docs)
- Rate limits apply based on your plan
- Processing time depends on file length

## Transcription Accuracy

The examples test multiple audio formats to demonstrate:
- Consistent results across formats
- Handling of mono vs stereo
- Compressed vs uncompressed audio

Expected transcription:
> "This is Peter, this is Johnny, Kenny, and Josh. We just wanted to take a minute to thank you."

(Actual test audio transcription)

## Get API Key

Get your XAI API key at: [console.x.ai](https://console.x.ai/)

## API Documentation

Full API documentation: [x.ai/api](https://x.ai/api)

---

**Need help?** Check the example code in `python/stt.py` or `nodejs/stt.ts` for complete implementations.
