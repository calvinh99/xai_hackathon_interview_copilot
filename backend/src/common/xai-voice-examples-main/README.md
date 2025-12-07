# XAI Voice Examples

Examples for building voice applications with XAI's APIs. Includes web demos, phone integration, and standalone TTS/STT examples.

## XAI APIs

All examples use XAI's production APIs. Get your API key at [console.x.ai](https://console.x.ai/).

### API Endpoints

| API | Endpoint | Description |
|-----|----------|-------------|
| **Realtime Voice** | `wss://api.x.ai/v1/realtime` | WebSocket for real-time voice conversations |
| **Text-to-Speech** | `https://api.x.ai/v1/audio/speech` | Convert text to natural speech audio |
| **Speech-to-Text** | `https://api.x.ai/v1/audio/transcriptions` | Transcribe audio files to text |

### Base URL

```bash
# All HTTP APIs use this base URL
https://api.x.ai/v1

# WebSocket APIs use
wss://api.x.ai/v1/realtime
```

### Authentication

All APIs use Bearer token authentication:

```bash
# HTTP APIs
curl https://api.x.ai/v1/audio/speech \
  -H "Authorization: Bearer YOUR_XAI_API_KEY"

# WebSocket APIs
wss://api.x.ai/v1/realtime
# Send API key in first message
```

### Available Models

- **TTS Voices**: Ara, Rex, Sal, Eve, Una, Leo (TTS) Multilingual
- **Transcription** Multilingual 

**Full API Documentation:** [x.ai/api](https://x.ai/api)

## Quick Start

Choose your use case and get started in minutes:

### Web Voice Agent

Real-time voice chat in your browser with React frontend and Python/Node.js backends.

**WebSocket Version** (Simplest):
```bash
# Start backend (Python or Node.js)
cd examples/agent/web/xai/backend-python
./start.sh

# Start frontend (in another terminal)
cd examples/agent/web/client
./start.sh

# Open http://localhost:5173
```

**WebRTC Version** (Lower latency + connection stats):
```bash
# Start server (Node.js WebRTC relay)
cd examples/agent/webrtc/server
./start.sh

# Start client (in another terminal)
cd examples/agent/webrtc/client
./start.sh

# Open http://localhost:5173
```

### Phone Voice Agent

Voice agent accessible via phone call using Twilio integration.

```bash
cd examples/agent/telephony/xai
npm install
# Configure .env with XAI_API_KEY and Twilio credentials
npm run dev
```

### Text-to-Speech (TTS)

Convert text to speech with 6 different voices (Ara, Rex, Sal, Eve, Una, Leo).

```bash
# Python
cd examples/tts/python
./start.sh

# Node.js
cd examples/tts/nodejs
./start.sh
```

### Speech-to-Text (STT)

Transcribe audio files to text (supports MP3, WAV, mono/stereo).

```bash
# Python
cd examples/stt/python
./start.sh

# Node.js
cd examples/stt/nodejs
./start.sh
```

## What's Included

### Voice Agents

| Example | Type | Stack | Features |
|---------|------|-------|----------|
| **Web Voice Agent** | Browser | React + Python/Node.js | Real-time voice, WebSocket, Debug console |
| **WebRTC Voice Agent** | Browser | React + Node.js | Low-latency WebRTC, Connection stats, PCM16 audio |
| **Telephony Agent** | Phone | Node.js + Twilio | Phone calls, Real-time voice, Function calling |

### API Examples

| Example | Languages | Features |
|---------|-----------|----------|
| **TTS** | Python + Node.js | 6 voices, Multiple formats (MP3, WAV, etc.) |
| **STT** | Python + Node.js | MP3/WAV support, Batch processing |

## Use Cases

### Build a Web Voice Assistant

Perfect for customer support, virtual assistants, or voice-enabled web apps.

**Option 1: WebSocket (Simplest)**
```bash
# Backend options: Python or Node.js
cd examples/agent/web/xai/backend-python  # or backend-nodejs
./start.sh

# Frontend
cd examples/agent/web/client
./start.sh
```

**Features:**
- Real-time voice streaming
- Visual transcript display
- Debug console for development
- Interchangeable backends (Python/Node.js)

**Option 2: WebRTC (Advanced)**
```bash
# Server (Node.js only)
cd examples/agent/webrtc/server
./start.sh

# Client
cd examples/agent/webrtc/client
./start.sh
```

**Additional Features:**
- Lower latency (~50-100ms)
- Connection quality monitoring (bitrate, jitter, packet loss, RTT)
- STUN/TURN support for NAT traversal
- DataChannel-based communication

### Build a Phone Voice Agent

Create AI agents accessible via phone calls for IVR systems, voice surveys, or call centers.

```bash
cd examples/agent/telephony/xai
npm install
# Configure Twilio credentials in .env
npm run dev
```

**Features:**
- Phone call integration
- Real-time voice processing
- Function/tool calling support
- Production-ready architecture

### Add Voice Features to Your App

Use standalone TTS and STT APIs to add voice capabilities to existing applications.

**TTS - Convert Text to Natural Speech:**
- 6 voice options (male/female)
- Multiple audio formats
- Batch processing support

**STT - Transcribe Audio to Text:**
- Multiple audio formats
- High-accuracy transcription
- Batch processing support

## Environment Setup

Each example includes a `.env.example` file. Copy it and add your API keys:

```bash
# In any example directory
cp .env.example .env

# Edit .env and add your keys
XAI_API_KEY=your_xai_api_key_here
```

### Get API Keys

- **XAI API Key**: [console.x.ai](https://console.x.ai/)
- **Twilio Credentials**: [console.twilio.com](https://console.twilio.com/) (for telephony examples)

## Text-to-Speech (TTS)

Convert text to natural-sounding speech.

**Available Voices:**
- **Ara** (Female) - Default
- **Rex** (Male)
- **Sal** (Voice)
- **Eve** (Female)
- **Una** (Female)
- **Leo** (Male)

**Supported Formats:** MP3, WAV, Opus, FLAC, PCM

```bash
# Quick start
cd examples/tts/python && ./start.sh
# Generates audio files for all 6 voices
```

[Full TTS Documentation →](examples/tts/README.md)

## Speech-to-Text (STT)

Transcribe audio files to text with high accuracy.

**Supported Formats:** MP3, WAV (mono/stereo)

```bash
# Quick start
cd examples/stt/python && ./start.sh
# Transcribes all test audio files
```

[Full STT Documentation →](examples/stt/README.md)

## Web Agent Architecture

The web agent examples demonstrate production-ready architectures:

**WebSocket Architecture** (Simplest):
```
┌─────────────┐      WebSocket       ┌─────────────┐      WebSocket       ┌─────────┐
│   Browser   │ ←──────────────────→ │   Backend   │ ←──────────────────→ │   XAI   │
│  (React)    │   Audio + Messages   │  (Py/Node)  │   Audio + Messages   │   API   │
└─────────────┘                      └─────────────┘                      └─────────┘
```

**Backend Options:**
- Python (FastAPI) or Node.js (Express)
- Both expose identical API
- Swap backends without frontend changes

**WebRTC Architecture** (Advanced):
```
┌─────────────┐      WebRTC          ┌─────────────┐      WebSocket       ┌─────────┐
│   Browser   │ ←──────────────────→ │   Server    │ ←──────────────────→ │   XAI   │
│  (React)    │  DataChannel (PCM16) │  (Node.js)  │   Audio + Messages   │   API   │
└─────────────┘                      └─────────────┘                      └─────────┘
```

**WebRTC Features:**
- Lower latency (~50-100ms)
- Connection quality stats
- STUN/TURN NAT traversal
- DataChannel for all communication

**Frontend (Both):**
- React + TypeScript + Vite
- Real-time audio streaming
- Transcript display
- Debug console

## Telephony Architecture

Phone integration using Twilio:

```
┌─────────┐      SIP       ┌─────────┐   WebSocket    ┌──────────┐   WebSocket    ┌─────────┐
│  Phone  │ ←────────────→ │ Twilio  │ ←────────────→ │  Server  │ ←────────────→ │   XAI   │
│  Call   │                │         │                │ (Node.js)│                │   API   │
└─────────┘                └─────────┘                └──────────┘                └─────────┘
```

## 🛠️ Tech Stack

### Web Examples
- **Frontend**: React, TypeScript, Vite, Web Audio API
- **Backend**: FastAPI (Python) or Express (Node.js)
- **Communication**: WebSockets or WebRTC
- **WebRTC**: werift (pure JavaScript WebRTC for Node.js)

### Telephony Examples
- **Runtime**: Node.js + TypeScript
- **Integration**: Twilio Media Streams
- **Communication**: WebSockets

### TTS/STT Examples
- **Languages**: Python 3.13+ or Node.js 18+
- **HTTP Client**: requests (Python) or axios (Node.js)

**For production deployment:**
- Add authentication/authorization
- Implement rate limiting
- Use HTTPS/WSS
- Enable security headers
- Monitor API usage

## Troubleshooting

### Common Issues

**No API key:**
```bash
# Add to .env file
echo "XAI_API_KEY=your-key-here" >> .env
```

**Port already in use:**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill
```

**Module not found (Python):**
```bash
pip install -r requirements.txt
```

**Dependencies missing (Node.js):**
```bash
npm install
```

## Documentation

- **[Web Agent Guide](examples/agent/web/README.md)** - WebSocket-based voice agent
- **[WebRTC Agent Guide](examples/agent/webrtc/README.md)** - WebRTC-based voice agent (low latency)
- **[Telephony Agent Guide](examples/agent/telephony/xai/README.md)** - Phone integration examples
- **[TTS Guide](examples/tts/README.md)** - Text-to-Speech API
- **[STT Guide](examples/stt/README.md)** - Speech-to-Text API
- **[XAI API Docs](https://x.ai/api)** - Official API documentation

## Getting Started

1. **Choose your use case** (web agent, phone agent, TTS, or STT)
2. **Navigate to the example directory**
3. **Copy `.env.example` to `.env`** and add your API key
4. **Run `./start.sh`** (or follow README in that directory)
5. **Start building!**

## License

See [LICENSE](LICENSE) file for details.
