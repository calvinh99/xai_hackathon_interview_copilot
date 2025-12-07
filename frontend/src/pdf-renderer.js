/**
 * PDF renderer with text highlighting using PDF.js (loaded via CDN)
 */
const { ipcRenderer } = require('electron');

// PDF.js is loaded via CDN script tag, access via window.pdfjsLib
const pdfjsLib = window.pdfjsLib;

// Disable worker (use fake worker for simplicity)
pdfjsLib.GlobalWorkerOptions.workerSrc = '';

let pdfDoc = null;
let pageTextItems = []; // Store text items with positions per page
const scale = 1.5; // Fixed scale for good readability

console.log('[pdf-renderer] Script loaded, PDF.js version:', pdfjsLib.version);

// Load and render PDF when received from main window
ipcRenderer.on('load-pdf', async (event, pdfData) => {
  console.log('[pdf-renderer] Received load-pdf event, data length:', pdfData?.length);
  try {
    updateStatus('Loading PDF...');
    const typedArray = new Uint8Array(pdfData);

    pdfDoc = await pdfjsLib.getDocument({
      data: typedArray,
      useWorkerFetch: false,
      isEvalSupported: false,
      useSystemFonts: true,
    }).promise;

    console.log('[pdf-renderer] PDF loaded, pages:', pdfDoc.numPages);
    updateStatus(`Loaded ${pdfDoc.numPages} page(s)`);
    await renderAllPages();
  } catch (err) {
    console.error('[pdf-renderer] PDF load error:', err);
    updateStatus('Error: ' + err.message);
  }
});

// Render all pages of the PDF
async function renderAllPages() {
  const container = document.getElementById('pdf-container');
  container.innerHTML = '';
  pageTextItems = [];

  let maxWidth = 0;
  let firstPageHeight = 0;

  for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale });

    maxWidth = Math.max(maxWidth, viewport.width);
    if (pageNum === 1) firstPageHeight = viewport.height;

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
      const height = fontSize * scale * 1.2;

      return {
        text: item.str,
        x: tx * scale,
        // PDF coords: ty is baseline. Move up by font height to get top of text
        y: viewport.height - (ty * scale) - height + (fontSize * scale * 0.15),
        w: item.width * scale,
        h: height,
      };
    });
  }

  // Resize window to fit PDF width and first page height
  ipcRenderer.send('resize-pdf-window', { width: maxWidth, height: firstPageHeight });
  console.log('[pdf-renderer] All pages rendered, resize to:', maxWidth, 'x', firstPageHeight);
}

/**
 * WORD SEQUENCE MATCHING
 *
 * Approach:
 * 1. Split source text into words
 * 2. Build a flat list of {word, itemIdx} from all PDF text items
 * 3. For each occurrence of the first source word, try to match the full sequence
 * 4. Use fuzzy matching for individual words (handles typos, OCR errors)
 * 5. Return contiguous item ranges that match the source
 */

// Normalize text for matching
function normalizeText(text) {
  return text
    .toLowerCase()
    .replace(/[\u2022\u2023\u25E6\u2043\u2219•·]/g, ' ')  // Bullets
    .replace(/[^\w\s]/g, ' ')  // Punctuation -> space
    .replace(/\s+/g, ' ')
    .trim();
}

// Levenshtein distance for fuzzy word matching
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

// Check if two words match (exact or fuzzy)
function wordsMatch(word1, word2, threshold = 0.3) {
  if (word1 === word2) return { match: true, score: 0 };
  if (word1.length < 2 || word2.length < 2) return { match: word1 === word2, score: word1 === word2 ? 0 : 1 };

  const distance = levenshtein(word1, word2);
  const maxLen = Math.max(word1.length, word2.length);
  const score = distance / maxLen;

  return { match: score <= threshold, score };
}

// Build word list from page items: [{word, itemIdx, localIdx}]
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

// Find all word sequence matches for a source in page words
function findWordSequenceMatches(sourceWords, pageWords) {
  const matches = [];

  if (sourceWords.length === 0 || pageWords.length === 0) return matches;

  // For each potential starting position in pageWords
  for (let startIdx = 0; startIdx <= pageWords.length - sourceWords.length; startIdx++) {
    let totalScore = 0;
    let allMatch = true;
    let endIdx = startIdx;

    // Try to match all source words sequentially
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

// Select best matches - if identical, keep all; otherwise keep best
function selectBestMatches(matches) {
  if (matches.length <= 1) return matches;

  // Sort by score (lower is better)
  matches.sort((a, b) => a.score - b.score);

  const best = matches[0];

  // Keep all matches with same text as best, or very close score
  return matches.filter(m => m.text === best.text || m.score <= best.score + 0.1);
}

// Handle highlight request from main window
ipcRenderer.on('highlight-text', (event, resumeSources) => {
  console.log('[pdf-renderer] Received highlight-text, sources:', resumeSources?.length);
  if (!pdfDoc) return;

  clearHighlights();
  let matchCount = 0;
  let firstMatch = null;

  for (const source of resumeSources) {
    const sourceWords = normalizeText(source).split(' ').filter(w => w.length > 0);
    if (sourceWords.length === 0) continue;

    console.log('[pdf-renderer] Looking for:', sourceWords.join(' '));

    for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
      const items = pageTextItems[pageNum] || [];
      if (items.length === 0) continue;

      const layer = document.getElementById(`highlights-${pageNum}`);
      const pageWords = buildPageWords(items);

      // Find all matching sequences
      let matches = findWordSequenceMatches(sourceWords, pageWords);

      if (matches.length === 0) continue;

      // Select best matches
      matches = selectBestMatches(matches);
      console.log(`[pdf-renderer] Found ${matches.length} match(es) on page ${pageNum}:`, matches.map(m => m.text));

      // Create highlight for each match
      for (const match of matches) {
        // Calculate bounding box for all items in match range
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

  updateStatus(`Highlighted ${matchCount} source(s)`);
});

// Clear all highlights
ipcRenderer.on('clear-highlights', clearHighlights);

function clearHighlights() {
  document.querySelectorAll('.highlight-layer').forEach(layer => {
    layer.innerHTML = '';
  });
}

function updateStatus(msg) {
  const status = document.getElementById('status');
  if (status) status.textContent = msg;
}
