#!/usr/bin/env python3
"""
Complete Flask server for Interview Copilot
Serves frontend and provides API endpoints for real-time interview analysis
"""

from flask import Flask, jsonify, request, Response, send_file
import threading
import time
import json
import queue
import os
from datetime import datetime

# Import your existing strategies module
# Adjust the import path based on your project structure
try:
    import backend.src.online.strategies as strategies
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import backend.src.online.strategies as strategies

app = Flask(__name__)

# Flags controlled by API requests
trigger_checkpoint = threading.Event()
trigger_generate = threading.Event()
trigger_evaluate = threading.Event()
stop_program = threading.Event()

# Queue for Server-Sent Events
analysis_queue = queue.Queue()

# Seed conversation for testing
SEED_CONVERSATION = """
Interviewer: Hi, welcome to the interview. Can you tell me about your experience with distributed systems?

Candidate: Thank you for having me. I have about 5 years of experience working with distributed systems.
"""


def report_analysis(result, mode):
    """Callback to queue analysis results for SSE."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"\n{'='*60}")
    print(f"📊 ANALYSIS - {mode.upper()} @ {timestamp}")
    print(f"{'='*60}")
    print(result)
    print(f"{'='*60}\n")
    
    # Put result in queue for SSE
    analysis_queue.put({
        'mode': mode,
        'result': result,
        'timestamp': timestamp
    })


def if_checkpoint():
    if trigger_checkpoint.is_set():
        trigger_checkpoint.clear()
        return True
    return False


def if_generate():
    if trigger_generate.is_set():
        trigger_generate.clear()
        return True
    return False


def if_evaluate():
    if trigger_evaluate.is_set():
        trigger_evaluate.clear()
        return True
    return False


# ============================================================
# API Routes
# ============================================================

@app.route('/')
def index():
    """Serve the main frontend HTML."""
    frontend_path = os.path.join(os.path.dirname(__file__), 'interview_copilot_frontend.html')
    
    # If the HTML file doesn't exist locally, serve inline HTML
    if not os.path.exists(frontend_path):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Interview Copilot</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 50px auto; padding: 20px; }
                button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; }
                .transcript { background: #f5f5f5; padding: 20px; border-radius: 8px; height: 400px; overflow-y: auto; }
                .controls { margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <h1>🎯 Interview Copilot</h1>
            <div class="controls">
                <button onclick="triggerAnalysis('generate')">🧠 Generate Strategies</button>
                <button onclick="triggerAnalysis('evaluate')">📊 Evaluate Interview</button>
                <button onclick="checkpoint()">💾 Checkpoint</button>
            </div>
            <h2>Live Transcript</h2>
            <div class="transcript" id="transcript">Loading...</div>
            <h2>Analysis Results</h2>
            <div class="transcript" id="results">Click buttons above to analyze</div>
            
            <script>
                setInterval(async () => {
                    const res = await fetch('/api/transcript');
                    const data = await res.json();
                    document.getElementById('transcript').innerHTML = '<pre>' + data.transcript + '</pre>';
                }, 2000);
                
                async function triggerAnalysis(mode) {
                    await fetch('/api/analyze/' + mode, { method: 'POST' });
                }
                
                async function checkpoint() {
                    await fetch('/api/checkpoint', { method: 'POST' });
                }
                
                const eventSource = new EventSource('/api/events');
                eventSource.addEventListener('analysis', (event) => {
                    const data = JSON.parse(event.data);
                    document.getElementById('results').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                });
            </script>
        </body>
        </html>
        """
        # print("!!!!!!!!!!!!")
    return send_file(frontend_path)


@app.route('/api/transcript', methods=['GET'])
def get_transcript():
    """Get the current conversation transcript."""
    with strategies.log_lock:
        current_log = strategies.conversation_log
    
    return jsonify({
        'transcript': current_log,
        'session_dir': strategies.current_session_dir
    })


@app.route('/api/analyze/<mode>', methods=['POST'])
def trigger_analysis(mode):
    """Trigger analysis (generate or evaluate)."""
    if mode == 'generate':
        trigger_generate.set()
        return jsonify({'success': True, 'message': 'Generate triggered'})
    elif mode == 'evaluate':
        trigger_evaluate.set()
        return jsonify({'success': True, 'message': 'Evaluate triggered'})
    else:
        return jsonify({'success': False, 'message': 'Invalid mode'}), 400


@app.route('/api/checkpoint', methods=['POST'])
def save_checkpoint():
    """Trigger a checkpoint save."""
    trigger_checkpoint.set()
    return jsonify({'success': True, 'message': 'Checkpoint triggered'})


@app.route('/api/events')
def sse():
    """Server-Sent Events endpoint for real-time analysis updates."""
    def event_stream():
        while True:
            try:
                # Wait for analysis results
                result = analysis_queue.get(timeout=30)
                yield f"event: analysis\ndata: {json.dumps(result)}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f": heartbeat\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get server status."""
    return jsonify({
        'status': 'running',
        'session_dir': strategies.current_session_dir,
        'log_length': len(strategies.conversation_log),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """List all session directories."""
    logs_dir = 'logs'
    if os.path.exists(logs_dir):
        sessions = [d for d in os.listdir(logs_dir) if d.startswith('session_')]
        return jsonify({'sessions': sessions})
    return jsonify({'sessions': []})


# ============================================================
# Server Initialization
# ============================================================

def main():
    print("\n" + "="*60)
    print("🚀 INTERVIEW COPILOT SERVER")
    print("="*60)
    
    # Seed conversation
    with strategies.log_lock:
        strategies.conversation_log = SEED_CONVERSATION
    print("✅ Conversation seeded")
    
    # Launch backend threads
    stop_event = strategies.launch_threads(
        if_checkpoint=if_checkpoint,
        if_generate=if_generate,
        if_evaluate=if_evaluate,
        report_analysis=report_analysis
    )
    print("✅ Backend threads launched")
    
    print(f"✅ Starting server at http://localhost:5001")
    print("="*60)
    
    # Start Flask server
    try:
        app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        stop_event.set()
        stop_program.set()
    except Exception as e:
        print(f"❌ Server error: {e}")
        stop_event.set()
        stop_program.set()


if __name__ == "__main__":
    main()