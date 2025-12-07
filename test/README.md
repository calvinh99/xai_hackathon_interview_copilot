# usage


**API Tests**
testing grok test APIs
```
python -m test.text
```
testing grok audio APIs and system audio input and output devices
```
python -m test.audio
```

**test online**

The online mode now uses **streaming STT via xAI WebSocket** for real-time transcription.

### Using the UI:
1. Start backend: `cd backend && uv run uvicorn src.app:app --reload --port 8000`
2. Start frontend: `cd frontend && bun start`
3. Click "Online" tab
4. Select audio devices (interviewer mic + candidate/system audio)
5. Click "Start Interview"
6. See live transcripts (interim updates in italics, final in normal text)
7. Click "Generate Strategies" for AI analysis

### Audio device setup:
```
python -m test.audio
```

This lists available devices. You need:
- **Interviewer device**: Your microphone
- **Candidate device**: System audio loopback (e.g., BlackHole on macOS)

