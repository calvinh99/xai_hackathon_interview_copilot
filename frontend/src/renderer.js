/**
 * Renderer process - UI logic and backend API calls.
 */
const API_BASE = 'http://localhost:8000';

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
  if (!xHandle) { alert('Please enter X handle'); return; }
  if (!jobDesc) { alert('Please enter job description'); return; }

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
  const details = document.getElementById(`skill-${idx}`);
  details.classList.toggle('open');
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
