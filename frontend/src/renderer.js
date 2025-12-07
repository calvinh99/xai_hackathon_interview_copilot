/**
 * Renderer process - UI logic, backend API calls, and PDF rendering.
 */
const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');

const API_BASE = 'http://localhost:8000';
const TEST_MODE = true; // Set to false to use real API

// Store skills for click handler access
let currentSkills = [];

// PDF.js state
const pdfjsLib = window.pdfjsLib;
pdfjsLib.GlobalWorkerOptions.workerSrc = '';
let pdfDoc = null;
let pageTextItems = [];
let currentScale = 1.5; // Will be calculated based on container width

// Mock data for testing (reconstructed from session file)
function loadTestData() {
  const sessionPath = path.join(__dirname, '../../backend/outputs/session_20251207_021838.json');
  const session = JSON.parse(fs.readFileSync(sessionPath, 'utf8'));

  // Get skills from analyze_resume (index 0)
  const allSkills = JSON.parse(session.calls[0].response);
  const skillsMap = {};
  allSkills.forEach(s => { skillsMap[s.keyword] = s.resume_sources; });

  // Get top skills from filter_top_skills (index 1)
  const topSkills = JSON.parse(session.calls[1].response);

  // Get x_posts from search_x_profile calls
  const xPostsMap = {};
  session.calls.forEach(call => {
    if (call.step === 'search_x_profile') {
      // Extract skill from prompt
      const match = call.prompt.match(/related to: (.+?)\n/);
      if (match) {
        const skill = match[1];
        try {
          const data = JSON.parse(call.response);
          xPostsMap[skill] = data.posts || [];
        } catch (e) {
          xPostsMap[skill] = [];
        }
      }
    }
  });

  // Compute flag based on x_posts
  function computeFlag(resumeSources, xPosts) {
    if (!xPosts || xPosts.length === 0) return 'no_data';
    const labels = xPosts.map(p => p.label);
    const yes = labels.filter(l => l === 'yes').length;
    const no = labels.filter(l => l === 'no').length;
    const maybe = labels.filter(l => l === 'could_be').length;
    const strongClaim = resumeSources.length >= 2 || resumeSources.some(s => s.length > 100);
    if (no > 0 && yes === 0) return 'highly_suspect';
    if (strongClaim && yes === 0 && maybe > 0) return 'suspect';
    if (yes > 0) return 'verified';
    return 'no_data';
  }

  // Build mock results
  return topSkills.map((keyword, idx) => {
    const resumeSources = skillsMap[keyword] || [];
    const xPosts = xPostsMap[keyword] || [];
    return {
      keyword,
      priority_rank: idx + 1,
      resume_sources: resumeSources,
      x_posts: xPosts,
      flag: computeFlag(resumeSources, xPosts)
    };
  });
}

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

async function runAnalysis() {
  const fileInput = document.getElementById('resume-file');
  const xHandle = document.getElementById('x-handle').value.trim();
  const jobDesc = document.getElementById('job-description').value.trim();

  if (!fileInput.files[0]) { alert('Please select a resume PDF'); return; }
  if (!TEST_MODE && !xHandle) { alert('Please enter X handle'); return; }
  if (!TEST_MODE && !jobDesc) { alert('Please enter job description'); return; }

  // Load PDF into the left panel
  const file = fileInput.files[0];
  const arrayBuffer = await file.arrayBuffer();
  await loadPDF(arrayBuffer);

  // TEST MODE: Load mock data immediately
  if (TEST_MODE) {
    console.log('[TEST MODE] Loading mock data from session file');
    try {
      const skills = loadTestData();
      renderResults(skills);
    } catch (err) {
      console.error('Test data load error:', err);
      alert('Error loading test data: ' + err.message);
    }
    return;
  }

  // Show loading, hide form and results
  document.getElementById('analyze-form').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
  document.getElementById('results').style.display = 'none';
  document.getElementById('progress-log').innerHTML = '';
  document.getElementById('loading-text').textContent = 'Starting analysis...';

  try {
    const formData = new FormData();
    formData.append('resume', fileInput.files[0]);
    formData.append('x_handle', xHandle);
    formData.append('job_description', jobDesc);
    formData.append('top_n', '10');

    const res = await fetch(`${API_BASE}/offline/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Server error ${res.status}: ${errText}`);
    }

    // Read SSE stream
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let skills = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            handleSSEMessage(data);
            if (data.type === 'results') {
              skills = data.skills;
            } else if (data.type === 'error') {
              throw new Error(data.message);
            }
          } catch (e) {
            // Ignore JSON parse errors (e.g. heartbeats), only rethrow if it's our error
            if (e.message && !e.message.includes('JSON')) throw e;
          }
        }
      }
    }

    if (!skills || skills.length === 0) {
      throw new Error('No skills returned from analysis');
    }
    renderResults(skills);
  } catch (err) {
    console.error('Analysis error:', err);
    alert('Error: ' + err.message);
    document.getElementById('analyze-form').style.display = 'block';
  } finally {
    document.getElementById('loading').style.display = 'none';
  }
}

function handleSSEMessage(data) {
  const logDiv = document.getElementById('progress-log');
  const loadingText = document.getElementById('loading-text');

  if (data.type === 'log') {
    const msg = data.message;
    // Update loading text with key events
    if (msg.includes('Step 1')) loadingText.textContent = 'Extracting skills from resume...';
    else if (msg.includes('Step 2')) loadingText.textContent = 'Filtering top skills for job...';
    else if (msg.includes('Step 3')) loadingText.textContent = 'Searching X profile...';
    else if (msg.includes('Done:')) {
      const match = msg.match(/Done: (.+?) ->/);
      if (match) loadingText.textContent = `Checked: ${match[1]}`;
    }
    else if (msg.includes('Analysis complete')) loadingText.textContent = 'Finishing up...';

    // Add to log
    const line = document.createElement('div');
    line.textContent = msg;
    line.style.color = msg.includes('ERROR') ? '#ff3b30' : msg.includes('WARNING') ? '#ff9500' : '#888';
    logDiv.appendChild(line);
    logDiv.scrollTop = logDiv.scrollHeight;
  }
}

function renderResults(skills) {
  currentSkills = skills; // Store for click handler

  const container = document.getElementById('results');
  container.innerHTML = skills.map((skill, idx) => `
    <div class="skill-card">
      <div class="skill-header" onclick="toggleSkill(${idx})">
        <span class="skill-rank">#${skill.priority_rank}</span>
        <span class="skill-name">${escapeHtml(skill.keyword)}</span>
        <span class="skill-flag flag-${skill.flag}">${formatFlag(skill.flag)}</span>
      </div>
      <div class="skill-details" id="skill-${idx}">
        <div class="section-title">Resume Sources (${skill.resume_sources.length})</div>
        ${skill.resume_sources.map(s => `<div class="source-item">${escapeHtml(s)}</div>`).join('') || '<div class="source-item" style="color:#888;">No sources found</div>'}

        <div class="section-title">X Posts (${skill.x_posts.length})</div>
        ${skill.x_posts.map(p => `
          <div class="source-item x-post">
            <span class="x-post-label label-${p.label}">${p.label}</span>
            <div class="x-post-content">
              ${escapeHtml(p.content)}
              <br><a href="${escapeHtml(p.url)}" target="_blank">View on X</a>
            </div>
          </div>
        `).join('') || '<div class="source-item" style="color:#888;">No relevant posts found</div>'}
      </div>
    </div>
  `).join('');

  container.style.display = 'block';
  document.getElementById('analyze-form').style.display = 'block';
}

function toggleSkill(idx) {
  const clickedDetails = document.getElementById(`skill-${idx}`);
  const clickedCard = clickedDetails.closest('.skill-card');
  const isOpening = !clickedDetails.classList.contains('open');

  // Collapse all other skills and remove their highlights
  document.querySelectorAll('.skill-details.open').forEach(el => {
    if (el.id !== `skill-${idx}`) el.classList.remove('open');
  });
  document.querySelectorAll('.skill-card.selected').forEach(el => {
    el.classList.remove('selected');
  });

  // Toggle clicked skill
  clickedDetails.classList.toggle('open');
  if (isOpening) {
    clickedCard.classList.add('selected');
    // Highlight resume_sources in PDF
    const skill = currentSkills[idx];
    if (skill && skill.resume_sources && skill.resume_sources.length > 0) {
      highlightText(skill.resume_sources);
    }
  } else {
    clearHighlights();
  }
}

function formatFlag(flag) {
  const labels = {
    'highly_suspect': 'Highly Suspect',
    'suspect': 'Suspect',
    'verified': 'Verified',
    'no_data': 'No Data',
  };
  return labels[flag] || flag;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// =============================================================================
// PDF Rendering and Highlighting (integrated from pdf-renderer.js)
// =============================================================================

function updatePdfStatus(msg) {
  const status = document.getElementById('pdf-status');
  if (status) status.textContent = msg;
}

async function loadPDF(arrayBuffer) {
  console.log('[pdf] Loading PDF, size:', arrayBuffer.byteLength);
  try {
    updatePdfStatus('Loading PDF...');
    const typedArray = new Uint8Array(arrayBuffer);

    pdfDoc = await pdfjsLib.getDocument({
      data: typedArray,
      useWorkerFetch: false,
      isEvalSupported: false,
      useSystemFonts: true,
    }).promise;

    console.log('[pdf] PDF loaded, pages:', pdfDoc.numPages);
    updatePdfStatus(`Loaded ${pdfDoc.numPages} page(s)`);

    // Show PDF panel (width will be set in renderAllPages)
    document.getElementById('pdf-panel').classList.add('open');

    await renderAllPages();
  } catch (err) {
    console.error('[pdf] Load error:', err);
    updatePdfStatus('Error: ' + err.message);
  }
}

async function renderAllPages() {
  const container = document.getElementById('pdf-container');
  container.innerHTML = '';
  pageTextItems = [];

  // Calculate scale to fit container height (window height - header - padding)
  const containerHeight = window.innerHeight - 80; // 40px header + 40px padding
  const firstPage = await pdfDoc.getPage(1);
  const unscaledViewport = firstPage.getViewport({ scale: 1 });
  currentScale = containerHeight / unscaledViewport.height;

  // Calculate scaled PDF width and resize panel accordingly
  const scaledWidth = unscaledViewport.width * currentScale;
  const panelWidth = scaledWidth + 30; // Add padding
  document.getElementById('pdf-panel').style.width = panelWidth + 'px';
  ipcRenderer.send('expand-window-for-pdf', { pdfWidth: panelWidth });

  for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale: currentScale });

    // Create page wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'page-wrapper';
    wrapper.style.width = viewport.width + 'px';
    wrapper.style.height = viewport.height + 'px';

    // Render canvas
    const canvas = document.createElement('canvas');
    canvas.className = 'page-canvas';
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext('2d');
    await page.render({ canvasContext: ctx, viewport }).promise;

    // Create highlight overlay layer
    const highlightLayer = document.createElement('div');
    highlightLayer.className = 'highlight-layer';
    highlightLayer.id = `highlights-${pageNum}`;
    highlightLayer.style.width = viewport.width + 'px';
    highlightLayer.style.height = viewport.height + 'px';

    wrapper.appendChild(canvas);
    wrapper.appendChild(highlightLayer);
    container.appendChild(wrapper);

    // Extract text with positions for highlighting
    const textContent = await page.getTextContent();
    pageTextItems[pageNum] = textContent.items.map(item => {
      const tx = item.transform[4];
      const ty = item.transform[5];
      const fontSize = Math.sqrt(item.transform[0] ** 2 + item.transform[1] ** 2);
      const height = fontSize * currentScale * 1.2;

      return {
        text: item.str,
        x: tx * currentScale,
        y: viewport.height - (ty * currentScale) - height + (fontSize * currentScale * 0.15),
        w: item.width * currentScale,
        h: height,
      };
    });
  }

  console.log('[pdf] All pages rendered');
}

// Text matching helpers
function normalizeText(text) {
  return text
    .toLowerCase()
    .replace(/[\u2022\u2023\u25E6\u2043\u2219•·]/g, ' ')  // Bullets
    .replace(/[^\w\s]/g, ' ')  // Punctuation -> space
    .replace(/\s+/g, ' ')
    .trim();
}

function levenshtein(a, b) {
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;

  const matrix = [];
  for (let i = 0; i <= b.length; i++) matrix[i] = [i];
  for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      matrix[i][j] = b[i-1] === a[j-1]
        ? matrix[i-1][j-1]
        : Math.min(matrix[i-1][j-1] + 1, matrix[i][j-1] + 1, matrix[i-1][j] + 1);
    }
  }
  return matrix[b.length][a.length];
}

function wordsMatch(word1, word2, threshold = 0.3) {
  if (word1 === word2) return { match: true, score: 0 };
  if (word1.length < 2 || word2.length < 2) return { match: word1 === word2, score: word1 === word2 ? 0 : 1 };

  const distance = levenshtein(word1, word2);
  const maxLen = Math.max(word1.length, word2.length);
  const score = distance / maxLen;

  return { match: score <= threshold, score };
}

function buildPageWords(items) {
  const words = [];
  for (let itemIdx = 0; itemIdx < items.length; itemIdx++) {
    const itemWords = normalizeText(items[itemIdx].text).split(' ').filter(w => w.length > 0);
    for (let localIdx = 0; localIdx < itemWords.length; localIdx++) {
      words.push({ word: itemWords[localIdx], itemIdx, localIdx });
    }
  }
  return words;
}

function findWordSequenceMatches(sourceWords, pageWords) {
  const matches = [];

  if (sourceWords.length === 0 || pageWords.length === 0) return matches;

  for (let startIdx = 0; startIdx <= pageWords.length - sourceWords.length; startIdx++) {
    let totalScore = 0;
    let allMatch = true;
    let endIdx = startIdx;

    for (let i = 0; i < sourceWords.length; i++) {
      const pageIdx = startIdx + i;
      if (pageIdx >= pageWords.length) {
        allMatch = false;
        break;
      }

      const result = wordsMatch(sourceWords[i], pageWords[pageIdx].word);
      if (!result.match) {
        allMatch = false;
        break;
      }
      totalScore += result.score;
      endIdx = pageIdx;
    }

    if (allMatch) {
      const avgScore = totalScore / sourceWords.length;
      const startItem = pageWords[startIdx].itemIdx;
      const endItem = pageWords[endIdx].itemIdx;

      matches.push({
        startIdx,
        endIdx,
        startItem,
        endItem,
        score: avgScore,
        text: pageWords.slice(startIdx, endIdx + 1).map(w => w.word).join(' ')
      });
    }
  }

  return matches;
}

function selectBestMatches(matches) {
  if (matches.length <= 1) return matches;
  matches.sort((a, b) => a.score - b.score);
  const best = matches[0];
  return matches.filter(m => m.text === best.text || m.score <= best.score + 0.1);
}

function highlightText(resumeSources) {
  console.log('[pdf] Highlighting sources:', resumeSources?.length);
  if (!pdfDoc) return;

  clearHighlights();
  let matchCount = 0;
  let firstMatch = null;

  for (const source of resumeSources) {
    const sourceWords = normalizeText(source).split(' ').filter(w => w.length > 0);
    if (sourceWords.length === 0) continue;

    console.log('[pdf] Looking for:', sourceWords.join(' ').substring(0, 50) + '...');

    for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
      const items = pageTextItems[pageNum] || [];
      if (items.length === 0) continue;

      const layer = document.getElementById(`highlights-${pageNum}`);
      const pageWords = buildPageWords(items);

      let matches = findWordSequenceMatches(sourceWords, pageWords);

      if (matches.length === 0) continue;

      matches = selectBestMatches(matches);
      console.log(`[pdf] Found ${matches.length} match(es) on page ${pageNum}`);

      for (const match of matches) {
        let minX = Infinity, minY = Infinity, maxX = 0, maxY = 0;

        for (let i = match.startItem; i <= match.endItem; i++) {
          const item = items[i];
          if (!item.text.trim()) continue;
          minX = Math.min(minX, item.x);
          minY = Math.min(minY, item.y);
          maxX = Math.max(maxX, item.x + item.w);
          maxY = Math.max(maxY, item.y + item.h);
        }

        if (minX < Infinity) {
          const highlight = document.createElement('div');
          highlight.className = 'highlight';
          highlight.style.left = minX + 'px';
          highlight.style.top = minY + 'px';
          highlight.style.width = (maxX - minX) + 'px';
          highlight.style.height = (maxY - minY) + 'px';
          layer.appendChild(highlight);
          matchCount++;

          if (!firstMatch) {
            firstMatch = { pageNum, element: highlight };
          }
        }
      }
    }
  }

  // Scroll to first match
  if (firstMatch) {
    firstMatch.element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  updatePdfStatus(`Highlighted ${matchCount} source(s)`);
}

function clearHighlights() {
  document.querySelectorAll('.highlight-layer').forEach(layer => {
    layer.innerHTML = '';
  });
}

// =============================================================================
// Online Mode - Live Interview
// =============================================================================

let onlineEventSource = null;
let isInterviewRunning = false;

// Fetch and populate audio devices
async function refreshDevices() {
  try {
    const res = await fetch(`${API_BASE}/online/devices`);
    const data = await res.json();

    const interviewerSelect = document.getElementById('interviewer-device');
    const candidateSelect = document.getElementById('candidate-device');

    interviewerSelect.innerHTML = '';
    candidateSelect.innerHTML = '';

    data.devices.forEach(d => {
      const opt1 = document.createElement('option');
      opt1.value = d.id;
      opt1.textContent = `${d.id}: ${d.name}`;
      if (d.is_default) opt1.textContent += ' (default)';
      interviewerSelect.appendChild(opt1);

      const opt2 = opt1.cloneNode(true);
      candidateSelect.appendChild(opt2);
    });

    console.log('[online] Devices loaded:', data.devices.length);
  } catch (err) {
    console.error('[online] Failed to load devices:', err);
    alert('Failed to load audio devices. Is the backend running?');
  }
}

// Start interview session
async function startInterview() {
  const interviewerId = parseInt(document.getElementById('interviewer-device').value);
  const candidateId = parseInt(document.getElementById('candidate-device').value);

  if (isNaN(interviewerId) || isNaN(candidateId)) {
    alert('Please select audio devices first');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/online/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        interviewer_device_id: interviewerId,
        candidate_device_id: candidateId
      })
    });

    const data = await res.json();
    if (!data.success) {
      alert('Failed to start: ' + (data.error || 'Unknown error'));
      return;
    }

    isInterviewRunning = true;
    updateOnlineUI(true);
    connectToEventStream();
    console.log('[online] Interview started, session:', data.session_dir);
  } catch (err) {
    console.error('[online] Failed to start interview:', err);
    alert('Failed to start interview: ' + err.message);
  }
}

// Stop interview session
async function stopInterview() {
  try {
    await fetch(`${API_BASE}/online/stop`, { method: 'POST' });
  } catch (err) {
    console.error('[online] Error stopping:', err);
  }

  isInterviewRunning = false;
  if (onlineEventSource) {
    onlineEventSource.close();
    onlineEventSource = null;
  }
  updateOnlineUI(false);
  console.log('[online] Interview stopped');
}

// Update UI state for online mode
function updateOnlineUI(running) {
  document.getElementById('online-setup').style.display = running ? 'none' : 'block';
  document.getElementById('online-controls').style.display = running ? 'block' : 'none';
  document.getElementById('generate-btn').disabled = !running;
  document.getElementById('evaluate-btn').disabled = !running;
  document.getElementById('generate-btn').style.background = running ? '#0066ff' : '#444';
  document.getElementById('evaluate-btn').style.background = running ? '#0066ff' : '#444';

  if (!running) {
    // Reset transcript display but keep content for review
    const content = document.getElementById('transcript-content');
    if (content.innerHTML === '' || content.innerHTML.includes('Waiting to start')) {
      content.innerHTML = '<span style="color: #888;">Waiting to start...</span>';
    }
  }
}

// Connect to SSE event stream
function connectToEventStream() {
  if (onlineEventSource) {
    onlineEventSource.close();
  }

  // Reset interim elements
  interimElements = { Interviewer: null, Candidate: null };

  // Clear transcript for new session
  document.getElementById('transcript-content').innerHTML = '';
  document.getElementById('strategies-content').innerHTML = '<div style="color: #666; font-size: 12px;">Click "Generate Strategies" to get baiting questions and hints.</div>';
  document.getElementById('evaluation-panel').style.display = 'none';

  onlineEventSource = new EventSource(`${API_BASE}/online/events`);

  onlineEventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleOnlineEvent(data);
    } catch (err) {
      console.error('[online] Failed to parse event:', err);
    }
  };

  onlineEventSource.onerror = (err) => {
    console.error('[online] EventSource error:', err);
    if (isInterviewRunning) {
      // Try to reconnect after a delay
      setTimeout(() => {
        if (isInterviewRunning) connectToEventStream();
      }, 2000);
    }
  };
}

// Track interim transcript elements for updating
let interimElements = {
  Interviewer: null,
  Candidate: null
};

// Handle incoming SSE events
function handleOnlineEvent(data) {
  if (data.type === 'transcript') {
    appendTranscript(data.speaker, data.text, data.is_final);
  } else if (data.type === 'analysis') {
    displayAnalysis(data.mode, data.result);
  } else if (data.type === 'stopped') {
    isInterviewRunning = false;
    updateOnlineUI(false);
  }
  // Ignore heartbeats
}

// Append transcript content (handles interim and final)
function appendTranscript(speaker, text, isFinal) {
  const container = document.getElementById('transcript-content');
  const label = speaker === 'Interviewer' ? 'You' : 'Candidate';
  const cssClass = speaker === 'Interviewer' ? 'interviewer' : 'candidate';

  if (isFinal) {
    if (interimElements[speaker]) {
      interimElements[speaker].remove();
      interimElements[speaker] = null;
    }
    const div = document.createElement('div');
    div.className = `transcript-line ${cssClass}`;
    div.innerHTML = `<strong>${label}:</strong> ${escapeHtml(text)}`;
    container.appendChild(div);
  } else {
    if (!interimElements[speaker]) {
      const div = document.createElement('div');
      div.className = `transcript-line ${cssClass} interim`;
      div.style.opacity = '0.6';
      div.style.fontStyle = 'italic';
      container.appendChild(div);
      interimElements[speaker] = div;
    }
    interimElements[speaker].innerHTML = `<strong>${label}:</strong> ${escapeHtml(text)}...`;
  }

  document.getElementById('transcript-container').scrollTop =
    document.getElementById('transcript-container').scrollHeight;
}

// Display analysis results
function displayAnalysis(mode, result) {
  const container = document.getElementById('strategies-content');

  // Clear placeholder if first result
  if (container.querySelector('div[style*="color: #666"]')) {
    container.innerHTML = '';
  }

  const card = document.createElement('div');
  card.className = `strategy-card ${mode}`;

  let label = mode.toUpperCase();
  if (mode === 'bait') label = 'BAITING STRATEGY';
  else if (mode === 'hint') label = 'TECHNICAL HINTS';
  else if (mode === 'evaluate') label = 'EVALUATION';

  card.innerHTML = `
    <div class="strategy-label">${label}</div>
    <div class="strategy-content">${escapeHtml(result)}</div>
  `;

  // For evaluation, also show in evaluation panel
  if (mode === 'evaluate') {
    document.getElementById('evaluation-panel').style.display = 'block';
    document.getElementById('evaluation-content').innerHTML = `<pre style="white-space: pre-wrap; font-size: 12px; margin: 0;">${escapeHtml(result)}</pre>`;
  }

  container.insertBefore(card, container.firstChild);
  container.scrollTop = 0;
}

// Trigger strategy generation
async function triggerGenerate() {
  if (!isInterviewRunning) return;

  const btn = document.getElementById('generate-btn');
  btn.disabled = true;
  btn.textContent = 'Generating...';

  try {
    await fetch(`${API_BASE}/online/trigger/generate`, { method: 'POST' });
  } catch (err) {
    console.error('[online] Failed to trigger generate:', err);
  }

  // Re-enable after delay (results come via SSE)
  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = 'Generate Strategies';
  }, 2000);
}

// Trigger interview evaluation
async function triggerEvaluate() {
  if (!isInterviewRunning) return;

  const btn = document.getElementById('evaluate-btn');
  btn.disabled = true;
  btn.textContent = 'Evaluating...';

  try {
    await fetch(`${API_BASE}/online/trigger/evaluate`, { method: 'POST' });
  } catch (err) {
    console.error('[online] Failed to trigger evaluate:', err);
  }

  // Re-enable after delay
  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = 'Evaluate Interview';
  }, 2000);
}

// Load devices when switching to online tab
const originalShowTab = showTab;
showTab = function(tabName) {
  originalShowTab(tabName);
  if (tabName === 'online') {
    refreshDevices();
  }
};

// Initial device load if starting on online tab
if (document.getElementById('online').classList.contains('active')) {
  refreshDevices();
}

// =============================================================================
// Online RL - Prompt Tuning
// =============================================================================

let rlPanelOpen = false;

async function launchOnlineRL() {
  const btn = document.getElementById('launch-rl-btn');
  btn.disabled = true;
  btn.textContent = 'Loading...';

  try {
    const res = await fetch(`${API_BASE}/online/rl/questions`);
    const data = await res.json();

    if (data.error && !data.questions?.length) {
      alert('Error: ' + data.error);
      return;
    }

    // Show panel
    const panel = document.getElementById('rl-panel');
    panel.style.width = '400px';
    rlPanelOpen = true;
    ipcRenderer.send('expand-window-for-rl', { rlWidth: 400 });

    // Update session info
    document.getElementById('rl-session-info').textContent =
      data.session ? `Session: ${data.session}` : 'No session loaded';

    // Render questions
    renderRLQuestions(data.questions || []);

    // Reset tune result
    document.getElementById('tune-result').style.display = 'none';
  } catch (err) {
    console.error('[rl] Failed to load questions:', err);
    alert('Failed to load questions: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Launch Online RL';
  }
}

function closeRLPanel() {
  const panel = document.getElementById('rl-panel');
  panel.style.width = '0';
  rlPanelOpen = false;
  ipcRenderer.send('collapse-window-for-rl');
}

function renderRLQuestions(questions) {
  const container = document.getElementById('rl-questions');

  if (!questions.length) {
    container.innerHTML = '<div style="color: #666;">No bait questions found</div>';
    return;
  }

  container.innerHTML = questions.map((q, i) => {
    const statusClass = q.accepted ? 'accepted' : 'rejected';
    const statusLabel = q.accepted ? 'ACCEPTED' : 'NOT USED';
    return `
      <div class="rl-question-item ${statusClass}">
        <div class="rl-question-label ${statusClass}">${statusLabel}</div>
        <div>${escapeHtml(q.question)}</div>
      </div>
    `;
  }).join('');
}

async function tunePrompt() {
  const btn = document.getElementById('tune-btn');
  btn.disabled = true;
  btn.textContent = 'Tuning...';

  try {
    const res = await fetch(`${API_BASE}/online/rl/tune`, { method: 'POST' });
    const data = await res.json();

    if (data.error) {
      alert('Tuning failed: ' + data.error);
      return;
    }

    // Show result
    document.getElementById('tune-result').style.display = 'block';
    document.getElementById('prev-prompt').textContent = data.prev_prompt || '';
    document.getElementById('new-prompt').textContent = data.new_prompt || '';
    document.getElementById('diff-summary').textContent = data.diff_summary || '';

    console.log('[rl] Tuning complete, new version:', data.new_version_id);
  } catch (err) {
    console.error('[rl] Tuning failed:', err);
    alert('Tuning failed: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Tune Prompt';
  }
}
