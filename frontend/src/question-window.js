/**
 * Question Hints Window - Renderer Process
 * Displays AI-generated interview questions and baiting strategies
 */

const { ipcRenderer } = require('electron');

const content = document.getElementById('content');
let currentQuestions = [];

/**
 * Listen for question updates from main process
 */
ipcRenderer.on('questions-updated', (event, questions) => {
  currentQuestions = questions;
  renderQuestions();
});

/**
 * Render questions to the UI
 */
function renderQuestions() {
  if (!currentQuestions || currentQuestions.length === 0) {
    content.innerHTML = `
      <div class="empty-state pulse">
        <p>🎯 Waiting for interview to start...</p>
        <p style="font-size: 12px; margin-top: 8px;">AI-generated questions will appear here</p>
      </div>
    `;
    return;
  }
  
  let html = '';
  
  // Group questions by type
  const hintQuestions = currentQuestions.filter(q => q.type === 'hint');
  const baitingQuestions = currentQuestions.filter(q => q.type === 'baiting');
  const technicalQuestions = currentQuestions.filter(q => q.type === 'technical');
  
  // Render Hint Questions
  if (hintQuestions.length > 0) {
    html += `
      <div class="section">
        <div class="section-title">💡 Suggested Questions</div>
    `;
    hintQuestions.forEach(q => {
      html += renderQuestionCard(q);
    });
    html += `</div>`;
  }
  
  // Render Baiting Questions
  if (baitingQuestions.length > 0) {
    html += `
      <div class="section">
        <div class="section-title">🎣 Baiting Strategies</div>
    `;
    baitingQuestions.forEach(q => {
      html += renderQuestionCard(q);
    });
    html += `</div>`;
  }
  
  // Render Technical Deep-Dive Questions
  if (technicalQuestions.length > 0) {
    html += `
      <div class="section">
        <div class="section-title">🔬 Technical Deep-Dive</div>
    `;
    technicalQuestions.forEach(q => {
      html += renderQuestionCard(q);
    });
    html += `</div>`;
  }
  
  content.innerHTML = html;
}

/**
 * Render a single question card
 */
function renderQuestionCard(question) {
  const tags = [];
  if (question.type) tags.push(`<span class="tag ${question.type}">${question.type}</span>`);
  if (question.skill) tags.push(`<span class="tag">${question.skill}</span>`);
  if (question.baitingScore) {
    tags.push(`<span class="tag baiting">Baiting: ${question.baitingScore}/10</span>`);
  }
  
  let followUps = '';
  if (question.followUps && question.followUps.length > 0) {
    followUps = '<div class="suggested-questions"><div style="font-size: 11px; color: #94a3b8; margin-bottom: 4px;">Follow-ups:</div>';
    question.followUps.forEach(f => {
      followUps += `<div class="suggested-item">${f}</div>`;
    });
    followUps += '</div>';
  }
  
  return `
    <div class="question-card" onclick='copyQuestion(${JSON.stringify(question.text).replace(/'/g, "&apos;")})'>
      <div class="question-text">${question.text}</div>
      <div class="question-meta">
        ${tags.join('')}
      </div>
      ${followUps}
    </div>
  `;
}

/**
 * Copy question to clipboard when clicked
 */
function copyQuestion(text) {
  navigator.clipboard.writeText(text).then(() => {
    console.log('Question copied to clipboard');
  });
}

/**
 * Window controls
 */
function minimizeWindow() {
  // Hide the window (Electron doesn't support true minimize for frameless windows)
  ipcRenderer.send('toggle-question-window');
}

function closeWindow() {
  ipcRenderer.send('close-window', 'question');
}

/**
 * Example: Fetch questions from backend API
 */
async function fetchQuestionsFromBackend() {
  try {
    const response = await fetch('http://localhost:8000/api/generate-questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        transcript: 'Current interview transcript...',
        candidateProfile: {}
      })
    });
    const data = await response.json();
    currentQuestions = data.questions;
    renderQuestions();
  } catch (error) {
    console.error('Failed to fetch questions:', error);
  }
}

// Poll backend for new questions every 5 seconds during active interview
// setInterval(fetchQuestionsFromBackend, 5000);

// Demo data for testing
setTimeout(() => {
  currentQuestions = [
    {
      type: 'hint',
      text: 'Can you walk me through your experience with CUDA kernel optimization?',
      skill: 'CUDA',
      followUps: [
        'What memory coalescing strategies did you use?',
        'How did you profile the kernel performance?'
      ]
    },
    {
      type: 'baiting',
      text: 'I noticed you mentioned working with Triton. How does it compare to writing raw CUDA?',
      skill: 'Triton',
      baitingScore: 8,
      followUps: [
        'Can you explain how Triton\'s block-level programming model works?',
        'What are the limitations of Triton compared to CUDA?'
      ]
    },
    {
      type: 'technical',
      text: 'Describe the architecture of the LLM training pipeline you built.',
      skill: 'LLM Training',
      followUps: [
        'How did you handle distributed training?',
        'What optimization techniques did you use?'
      ]
    }
  ];
  renderQuestions();
}, 2000);

