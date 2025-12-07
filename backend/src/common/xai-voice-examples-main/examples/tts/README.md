# XAI Text-to-Speech (TTS)

Convert text to natural-sounding speech using XAI's audio API with 6 voice options.

## Quick Start

### Standard TTS (HTTP API)

```bash
# Python
cd python && ./start.sh

# Node.js
cd nodejs && ./start.sh
```

The script will:
- Create virtual environment (Python) or install dependencies (Node.js)
- Check for `.env` file
- Generate audio samples for all 6 voices
- Save files to `../audio/` directory

### Streaming TTS (WebSocket API)

Real-time text-to-speech with audio playback as it's generated:

```bash
# Python - stream and play audio
cd python
python streaming-tts.py "Hello, how are you today?" --voice ara

# Node.js - stream and play audio
cd nodejs
npx tsx streaming-tts.ts "Hello, how are you today?" --voice rex
```

## API Endpoints

### Standard TTS
```
POST https://api.x.ai/v1/audio/speech
```

### Streaming TTS
```
WSS wss://api.x.ai/v1/realtime/audio/speech
```

## curl Example (Standard API)

```bash
curl https://api.x.ai/v1/audio/speech \
    -H "Authorization: Bearer xai-xxx" \
    -H "Content-Type: application/json" \
    -d '{
          "input": "It is a good model, sir.",
          "voice": "Ara", 
          "response_format": "mp3"
    }' \
    --output speech.mp3
```

## Available Voices

| Voice | Type | Description |
|-------|------|-------------|
| `Ara` | Female | Default voice |
| `Rex` | Male | Male voice |
| `Sal` | Voice | Salathiel voice |
| `Eve` | Female | Female voice |
| `Una` | Female | Female voice |
| `Leo` | Male | Male voice |

## Configuration

All examples use environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `XAI_API_KEY` | Yes | - | Your XAI API key |
| `BASE_URL` | No | `https://api.x.ai/v1` | API base URL |

## Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `input` | string | Yes | Text to convert to speech |
| `voice` | string | Yes | Voice to use (Ara, Rex, Sal, Eve, Una, Leo) |
| `response_format` | string | No | Audio format: mp3, wav, opus, flac, pcm (default: mp3) |

## Response

Binary audio data in the requested format.

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
python tts.py
```

**Features:**
- Tests all 6 voices
- Saves audio to `../audio/` directory
- Supports all audio formats
- Error handling and logging

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
- Tests all 6 voices
- Saves audio to `../audio/` directory
- Async/await pattern
- Error handling and logging

**Dependencies:**
- Node.js 18+
- TypeScript
- dotenv

## Output

Generated audio files are saved to:
```
tts/audio/
├── ara_sample.mp3
├── rex_sample.mp3
├── sal_sample.mp3
├── eve_sample.mp3
├── una_sample.mp3
└── leo_sample.mp3
```

**Note:** The `audio/` directory is gitignored as files are generated.

## Usage in Your Application

### Python Example

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

response = requests.post(
    "https://api.x.ai/v1/audio/speech",
    headers={"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}"},
    json={
        "input": "Hello, how can I help you?",
        "voice": "Ara",
        "response_format": "mp3"
    }
)

with open("output.mp3", "wb") as f:
    f.write(response.content)
```

### Node.js Example

```typescript
import fs from 'fs';
import dotenv from 'dotenv';

dotenv.config();

const response = await fetch('https://api.x.ai/v1/audio/speech', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${process.env.XAI_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    input: 'Hello, how can I help you?',
    voice: 'Ara',
    response_format: 'mp3'
  })
});

const buffer = Buffer.from(await response.arrayBuffer());
fs.writeFileSync('output.mp3', buffer);
```

## Streaming API

For real-time text-to-speech with immediate playback:

### Python Streaming Example

```bash
# Play audio in real-time
python streaming-tts.py "Hello, how are you today?" --voice ara

# Save to file while playing
python streaming-tts.py "Hello!" --voice rex --output output.wav

# Save only (no playback)
python streaming-tts.py "Hello!" --output output.wav --no-play
```

### Node.js Streaming Example

```bash
# Play audio in real-time (requires ffplay)
npx tsx streaming-tts.ts "Hello, how are you today?" --voice ara

# Save to file while playing
npx tsx streaming-tts.ts "Hello!" --voice rex --output output.wav

# Save only (no playback)
npx tsx streaming-tts.ts "Hello!" --output output.wav --no-play
```

### When to Use Streaming

✅ **Use Streaming For:**
- Real-time voice agents
- Interactive applications
- Low-latency responses
- Immediate audio feedback

❌ **Use Standard API For:**
- Batch processing
- File generation
- Specific audio formats (MP3, AAC, etc.)
- Simpler integration

## Error Handling

Common errors and solutions:

**401 Unauthorized:**
- Check your API key is correct
- Ensure key is properly set in `.env`

**400 Bad Request:**
- Verify voice name is correct (case-sensitive)
- Check input text is not empty
- Ensure response_format is valid

**500 Internal Error:**
- Try again after a moment
- Check XAI API status

## Best Practices

1. **Cache audio files** - Don't regenerate the same text repeatedly
2. **Handle errors gracefully** - Implement retry logic
3. **Validate input** - Check text length and content
4. **Choose appropriate format** - MP3 for web, WAV for processing
5. **Monitor usage** - Track API calls and costs

## Supported Audio Formats

| Format | Use Case | File Size |
|--------|----------|-----------|
| **mp3** | Web streaming, mobile apps | Small |
| **wav** | High quality, audio processing | Large |
| **opus** | WebRTC, voice chat | Very small |
| **flac** | Lossless compression | Medium |
| **pcm** | Raw audio, DSP | Largest |

## Limitations

- Maximum input text length: Check API documentation
- Rate limits apply based on your plan
- Audio quality depends on format chosen

## Get API Key

Get your XAI API key at: [console.x.ai](https://console.x.ai/)

## API Documentation

Full API documentation: [x.ai/api](https://x.ai/api)

---

**Need help?** Check the example code in `python/tts.py` or `nodejs/tts.ts` for complete implementations.
