/**
 * Cheat Alert Window - Renderer Process
 * Displays real-time inconsistencies and potential cheating indicators
 */

const { ipcRenderer } = require('electron');

const content = document.getElementById('content');
const alertCountEl = document.getElementById('alert-count');
let alerts = [];

/**
 * Listen for cheat alert updates from main process
 */
ipcRenderer.on('cheats-updated', (event, newAlerts) => {
  alerts = newAlerts;
  renderAlerts();
});

/**
 * Render alerts to the UI
 */
function renderAlerts() {
  alertCountEl.textContent = alerts.length;
  
  if (!alerts || alerts.length === 0) {
    content.innerHTML = `
      <div class="empty-state">
        <p>✅ No alerts detected</p>
        <p style="font-size: 12px; margin-top: 8px;">Monitoring for inconsistencies...</p>
      </div>
    `;
    return;
  }
  
  let html = '';
  
  // Sort by severity (critical first) and timestamp (newest first)
  const sortedAlerts = [...alerts].sort((a, b) => {
    if (a.severity === 'critical' && b.severity !== 'critical') return -1;
    if (a.severity !== 'critical' && b.severity === 'critical') return 1;
    return new Date(b.timestamp) - new Date(a.timestamp);
  });
  
  sortedAlerts.forEach(alert => {
    html += renderAlertCard(alert);
  });
  
  content.innerHTML = html;
  
  // Auto-scroll to top to show newest alert
  content.scrollTop = 0;
}

/**
 * Render a single alert card
 */
function renderAlertCard(alert) {
  const timestamp = new Date(alert.timestamp).toLocaleTimeString();
  const severityClass = alert.severity || 'warning';
  
  let detailsHtml = '';
  if (alert.details) {
    if (alert.details.contradiction) {
      detailsHtml += `
        <div class="alert-details">
          <strong>Contradiction Found:</strong>
          <div class="contradiction">
            <div class="contradiction-item">
              <strong>Said before:</strong> "${alert.details.contradiction.before}"
            </div>
            <div class="contradiction-item">
              <strong>Said now:</strong> "${alert.details.contradiction.now}"
            </div>
          </div>
        </div>
      `;
    }
    
    if (alert.details.resumeVsX) {
      detailsHtml += `
        <div class="alert-details">
          <strong>Resume vs X Profile:</strong><br>
          Claimed skill "${alert.details.skill}" but no evidence in X posts.
        </div>
      `;
    }
    
    if (alert.details.confidence) {
      detailsHtml += `
        <div class="alert-details">
          <strong>Confidence:</strong> ${(alert.details.confidence * 100).toFixed(0)}%
        </div>
      `;
    }
  }
  
  let baitingScoreHtml = '';
  if (alert.baitingScore !== undefined) {
    const scorePercent = (alert.baitingScore / 10) * 100;
    baitingScoreHtml = `
      <div class="baiting-score">
        <div>Baiting Success Score: ${alert.baitingScore}/10</div>
        <div class="score-bar">
          <div class="score-fill" style="width: ${scorePercent}%"></div>
        </div>
      </div>
    `;
  }
  
  return `
    <div class="alert-card ${severityClass}">
      <div class="alert-header">
        <div class="alert-type ${severityClass}">
          <span class="severity-indicator ${severityClass}"></span>
          ${alert.type || 'INCONSISTENCY'}
        </div>
        <div class="alert-timestamp">${timestamp}</div>
      </div>
      <div class="alert-message">${alert.message}</div>
      ${detailsHtml}
      ${baitingScoreHtml}
    </div>
  `;
}

/**
 * Clear all alerts
 */
function clearAlerts() {
  alerts = [];
  renderAlerts();
}

/**
 * Window controls
 */
function minimizeWindow() {
  ipcRenderer.send('toggle-cheat-window');
}

function closeWindow() {
  ipcRenderer.send('close-window', 'cheat');
}

/**
 * Example: Fetch alerts from backend API
 */
async function fetchAlertsFromBackend() {
  try {
    const response = await fetch('http://localhost:8000/api/check-inconsistencies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        transcript: 'Current interview transcript...',
        history: []
      })
    });
    const data = await response.json();
    if (data.alerts) {
      alerts = [...alerts, ...data.alerts];
      renderAlerts();
    }
  } catch (error) {
    console.error('Failed to fetch alerts:', error);
  }
}

/**
 * Add a new alert programmatically
 */
function addAlert(alert) {
  alerts.unshift({
    ...alert,
    timestamp: alert.timestamp || new Date().toISOString()
  });
  renderAlerts();
  
  // Play notification sound (optional)
  // new Audio('alert.mp3').play();
}

// Expose to window for testing
window.addAlert = addAlert;

// Poll backend for new alerts every 3 seconds during active interview
// setInterval(fetchAlertsFromBackend, 3000);

// Demo data for testing
setTimeout(() => {
  addAlert({
    type: 'CONTRADICTION',
    severity: 'critical',
    message: 'Candidate contradicted previous statement about CUDA experience',
    details: {
      contradiction: {
        before: 'I have 3 years of experience writing CUDA kernels',
        now: 'I\'ve never actually written production CUDA code'
      },
      confidence: 0.95
    }
  });
}, 3000);

setTimeout(() => {
  addAlert({
    type: 'RESUME MISMATCH',
    severity: 'warning',
    message: 'Listed "Triton" as a skill but no X posts mention it',
    details: {
      resumeVsX: true,
      skill: 'Triton',
      confidence: 0.78
    }
  });
}, 5000);

setTimeout(() => {
  addAlert({
    type: 'BAITING SUCCESS',
    severity: 'critical',
    message: 'Candidate exposed lack of knowledge through baiting question',
    baitingScore: 9,
    details: {
      confidence: 0.92
    }
  });
}, 8000);

