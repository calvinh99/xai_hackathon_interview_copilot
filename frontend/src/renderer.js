/**
 * Renderer process - UI logic and backend API calls.
 */
const API_BASE = 'http://localhost:8000';

function showTab(tabName) {
  document.querySelectorAll('.content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(tabName).style.display = 'block';
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
