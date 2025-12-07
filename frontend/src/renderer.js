/**
 * Renderer process - UI logic and backend API calls.
 */
const { ipcRenderer } = require('electron');
const API_BASE = 'http://localhost:8000';

let isInterviewActive = false;

function showTab(tabName) {
  document.querySelectorAll('.content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(tabName).classList.add('active');
  event.target.classList.add('active');
}

async function callApi(endpoint, data) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

/**
 * Offline Analysis Functions
 */
async function runOfflineAnalysis() {
  const xProfileUrl = document.getElementById('xProfileUrl').value;
  const resumePath = document.getElementById('resumePath').value;
  const jobDescription = document.getElementById('jobDescription').value;
  
  const statusEl = document.getElementById('offlineStatus');
  statusEl.innerHTML = '<div class="status">Analyzing candidate profile...</div>';
  
  try {
    const result = await callApi('/api/offline-analysis', {
      xProfileUrl,
      resumePath,
      jobDescription
    });
    
    statusEl.innerHTML = `
      <div class="status">✅ Analysis complete!</div>
      <div style="margin-top: 12px; padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px; font-size: 12px;">
        <strong>Inconsistencies Found:</strong> ${result.inconsistencies?.length || 0}<br>
        <strong>Technical Skills:</strong> ${result.technicalSkills?.length || 0}<br>
        <strong>Confidence Score:</strong> ${result.confidenceScore || 'N/A'}
      </div>
    `;
  } catch (error) {
    statusEl.innerHTML = `<div class="status error">❌ Error: ${error.message}</div>`;
  }
}

/**
 * Online Interview Functions
 */
function startInterview() {
  isInterviewActive = true;
  document.getElementById('startBtn').style.display = 'none';
  document.getElementById('stopBtn').style.display = 'inline-block';
  document.getElementById('onlineStatus').innerHTML = '<div class="status">🔴 Recording...</div>';
  
  // Start audio capture and real-time analysis
  startAudioCapture();
  startRealTimeAnalysis();
}

function stopInterview() {
  isInterviewActive = false;
  document.getElementById('startBtn').style.display = 'inline-block';
  document.getElementById('stopBtn').style.display = 'none';
  document.getElementById('onlineStatus').innerHTML = '<div class="status">Interview stopped</div>';
  
  // Stop audio capture
  stopAudioCapture();
}

/**
 * Audio capture (to be implemented with Web Audio API or Electron's desktopCapturer)
 */
let audioStream = null;

async function startAudioCapture() {
  try {
    // This is a placeholder - actual implementation would use Electron's desktopCapturer
    // or integrate with system audio capture
    console.log('Starting audio capture...');
    
    // Example: Web Audio API
    // audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // const audioContext = new AudioContext();
    // const source = audioContext.createMediaStreamSource(audioStream);
    // ... send to speech-to-text service
    
  } catch (error) {
    console.error('Audio capture failed:', error);
  }
}

function stopAudioCapture() {
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop());
    audioStream = null;
  }
}

/**
 * Real-time analysis polling
 */
let analysisInterval = null;

function startRealTimeAnalysis() {
  analysisInterval = setInterval(async () => {
    if (!isInterviewActive) return;
    
    try {
      // Get latest transcript and analyze
      const transcript = getCurrentTranscript();
      
      // Generate questions
      const questions = await callApi('/api/generate-questions', {
        transcript,
        history: []
      });
      
      // Send to question window
      ipcRenderer.send('update-questions', questions.questions || []);
      
      // Check for inconsistencies
      const alerts = await callApi('/api/check-inconsistencies', {
        transcript,
        history: []
      });
      
      // Send to cheat alert window
      if (alerts.alerts && alerts.alerts.length > 0) {
        ipcRenderer.send('update-cheats', alerts.alerts);
      }
      
    } catch (error) {
      console.error('Real-time analysis error:', error);
    }
  }, 5000); // Poll every 5 seconds
}

function getCurrentTranscript() {
  // Placeholder - would return actual accumulated transcript
  return "Current interview transcript...";
}

/**
 * Window controls
 */
function toggleQuestionWindow() {
  ipcRenderer.send('toggle-question-window');
}

function toggleCheatWindow() {
  ipcRenderer.send('toggle-cheat-window');
}

function closeApp() {
  ipcRenderer.send('close-window', 'main');
}

