# XAI Voice Examples

Examples for building voice applications with XAI's APIs. Includes web agents, phone integration, and standalone TTS/STT APIs.

## Examples Overview

### Voice Agents

Build complete voice applications with web or phone interfaces.

| Example | Description | Stack |
|---------|-------------|-------|
| **[Web Voice Agent](agent/web/)** | Browser-based voice chat | React + Python/Node.js backends |
| **[Telephony Agent](agent/telephony/xai/)** | Phone call integration | Node.js + Twilio |

### API Examples

Standalone examples for specific XAI APIs.

| Example | Description | Languages |
|---------|-------------|-----------|
| **[TTS](tts/)** | Text-to-Speech with 6 voices | Python + Node.js |
| **[STT](stt/)** | Speech-to-Text transcription | Python + Node.js |

## Quick Start

Each example includes a `start.sh` script for easy setup:

```bash
# Web Voice Agent
cd examples/agent/web/xai/backend-python
./start.sh

# Phone Agent
cd examples/agent/telephony/xai
npm install && npm run dev

# TTS
cd examples/tts/python
./start.sh

# STT
cd examples/stt/python
./start.sh
```

## Environment Setup

All examples use `.env` files for configuration:

```bash
# In any example directory
cp .env.example .env

# Edit .env and add your API key
XAI_API_KEY=your_xai_api_key_here
```

### Get API Keys

- **XAI API Key**: [console.x.ai](https://console.x.ai/)
- **Twilio** (for telephony): [console.twilio.com](https://console.twilio.com/)

## XAI APIs Used

| API | Endpoint | Used By |
|-----|----------|---------|
| **Realtime Voice** | `wss://api.x.ai/v1/realtime` | Web Agent, Telephony |
| **Text-to-Speech** | `https://api.x.ai/v1/audio/speech` | TTS Examples |
| **Speech-to-Text** | `https://api.x.ai/v1/audio/transcriptions` | STT Examples |

## Documentation

- **[Web Agent Guide](agent/web/README.md)** - Complete web demo documentation
- **[Telephony Guide](agent/telephony/xai/README.md)** - Phone integration guide
- **[TTS Guide](tts/README.md)** - Text-to-Speech API examples
- **[STT Guide](stt/README.md)** - Speech-to-Text API examples

## Tech Stack

### Web Agents
- **Frontend**: React, TypeScript, Vite, Web Audio API
- **Backend**: FastAPI (Python) or Express (Node.js)
- **Communication**: WebSockets

### Telephony Agents
- **Runtime**: Node.js + TypeScript
- **Integration**: Twilio Media Streams
- **Communication**: WebSockets

### TTS/STT
- **Languages**: Python 3.13+ or Node.js 18+
- **HTTP Clients**: requests (Python) or axios (Node.js)

## Example Features

### Web Voice Agent
- Real-time voice streaming
- Visual transcript
- Debug console
- Interchangeable backends (Python/Node.js)

### Telephony Agent
- Phone call integration
- Real-time voice processing
- Function/tool calling
- Production-ready architecture

### TTS Examples
- 6 voice options (Ara, Rex, Sal, Eve, Una, Leo)
- Multiple formats (MP3, WAV, Opus, FLAC, PCM)
- Batch processing
- Error handling

### STT Examples
- MP3 and WAV support
- Mono and stereo audio
- Test audio files included
- Batch processing

## Architecture

### Web Agent Flow
```
┌─────────────┐   WebSocket   ┌─────────────┐   WebSocket   ┌─────────┐
│   Browser   │ ←───────────→ │   Backend   │ ←───────────→ │   XAI   │
│  (React)    │  Audio+Text   │  (Py/Node)  │  Audio+Text   │   API   │
└─────────────┘               └─────────────┘               └─────────┘
```

### Telephony Flow
```
┌─────────┐    SIP    ┌─────────┐  WebSocket  ┌──────────┐  WebSocket  ┌─────────┐
│  Phone  │ ←────────→│ Twilio  │ ←──────────→│  Server  │ ←──────────→│   XAI   │
│  Call   │           │         │             │ (Node.js)│             │   API   │
└─────────┘           └─────────┘             └──────────┘             └─────────┘
```

## Development

### Start Scripts

All examples include automated start scripts:

```bash
# Creates venv, installs deps, runs example
./start.sh
```

### Manual Setup

**Python:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py  # or: python tts.py / stt.py
```

**Node.js:**
```bash
npm install
npm start       # or: npm run dev
```

## Common Issues

### API Key Missing
```bash
# Make sure .env exists with your key
echo "XAI_API_KEY=your_key_here" > .env
```

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill
```

### Dependencies Missing
```bash
# Python
pip install -r requirements.txt

# Node.js
npm install
```

## Security

All examples follow security best practices:
- API keys in `.env` files (gitignored)
- No hardcoded credentials
- Environment variable validation

For production:
- Add authentication/authorization
- Implement rate limiting
- Use HTTPS/WSS
- Enable security headers
- Monitor API usage

**Need help?** Check the specific example's README for detailed instructions.
