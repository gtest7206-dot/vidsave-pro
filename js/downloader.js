/* ============================
   VidSave Pro - Downloader (Real API)
   Calls /api/info and /api/download on the Flask backend.
   ============================ */

// ── API Base Configuration ──────────────────────────────────────────────────
// When running locally, this uses the local server.
// For production hosting (e.g., ProFreeHost frontend + Render backend),
// change the URL below to your deployed Python backend URL (e.g. on Render).
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? ''
  : 'https://vidsave-backend1.onrender.com';

let currentVideoUrl = '';

// ── Detect platform from URL ────────────────────────────────────────────────
function detectPlatform(url) {
  const u = url.toLowerCase();
  if (u.includes('youtube.com') || u.includes('youtu.be'))  return 'youtube';
  if (u.includes('facebook.com') || u.includes('fb.watch')) return 'facebook';
  if (u.includes('instagram.com'))                           return 'instagram';
  if (u.includes('tiktok.com') || u.includes('vm.tiktok'))  return 'tiktok';
  if (u.includes('twitter.com') || u.includes('x.com'))     return 'twitter';
  if (u.includes('vimeo.com'))                               return 'vimeo';
  if (u.includes('reddit.com') || u.includes('v.redd.it'))  return 'reddit';
  if (u.includes('dailymotion.com'))                         return 'dailymotion';
  return 'other';
}

// ── Validate URL ────────────────────────────────────────────────────────────
function isValidUrl(str) {
  try { new URL(str); return true; } catch { return false; }
}

// ── Main form handler ───────────────────────────────────────────────────────
async function handleDownload(e) {
  e.preventDefault();

  const input  = document.getElementById('video-url-input');
  const url    = input ? input.value.trim() : '';

  if (!url) {
    showToast('⚠️ Please paste a video URL first');
    input && input.focus();
    return;
  }
  if (!isValidUrl(url)) {
    showToast('❌ Please enter a valid URL (starting with https://)');
    input && input.focus();
    return;
  }

  currentVideoUrl = url;

  const loadingArea  = document.getElementById('loading-area');
  const resultsArea  = document.getElementById('results-area');
  const submitBtn    = document.getElementById('download-submit-btn');

  if (loadingArea)  loadingArea.style.display  = 'block';
  if (resultsArea)  resultsArea.style.display  = 'none';
  if (submitBtn)    submitBtn.disabled          = true;

  try {
    const res  = await fetch(`${API_BASE}/api/info?url=${encodeURIComponent(url)}`);
    const data = await res.json();

    if (!res.ok || data.error) {
      showToast(`❌ ${data.error || 'Could not fetch video info'}`);
      if (loadingArea) loadingArea.style.display = 'none';
      if (submitBtn)   submitBtn.disabled         = false;
      return;
    }

    if (loadingArea) loadingArea.style.display = 'none';
    if (submitBtn)   submitBtn.disabled         = false;
    showResults(data);

  } catch (err) {
    showToast('❌ Cannot reach server — make sure Python server.py is running!');
    if (loadingArea) loadingArea.style.display = 'none';
    if (submitBtn)   submitBtn.disabled         = false;
  }
}

// ── Render results from real API data ──────────────────────────────────────
function showResults(data) {
  const resultsArea    = document.getElementById('results-area');
  const videoInfo      = document.getElementById('video-info');
  const qualityOptions = document.getElementById('quality-options');
  if (!resultsArea || !videoInfo || !qualityOptions) return;

  // ── Video info panel ─────────────────────────────────────────────────────
  const thumbSrc = data.thumbnail || '';
  const meta = [data.channel, data.duration, data.views].filter(Boolean).join(' &nbsp;•&nbsp; ');

  videoInfo.innerHTML = `
    <img
      src="${thumbSrc}"
      alt="${escHtml(data.title)}"
      class="video-thumb"
      onerror="this.style.display='none'"
    >
    <div class="video-meta">
      <h3>${escHtml(data.title)}</h3>
      <p>${meta}</p>
      <p style="margin-top:8px;font-size:0.78rem;color:var(--text-muted);word-break:break-all">
        ${currentVideoUrl.length > 72 ? currentVideoUrl.substring(0, 72) + '…' : currentVideoUrl}
      </p>
    </div>
  `;

  // ── Quality buttons ──────────────────────────────────────────────────────
  window._currentFormats = data.formats || [];

  qualityOptions.innerHTML = window._currentFormats.map((fmt, i) => {
    const unavailable = fmt.available === false;
    const tooltip     = unavailable
      ? 'Requires ffmpeg — see README'
      : `Download ${fmt.label} (${fmt.size || ''})`;

    return `
      <button
        class="quality-btn ${unavailable ? 'quality-btn-disabled' : ''}"
        onclick="${unavailable ? 'showToast(\"⚠️ This quality requires ffmpeg. See README.\")' : `startDownload(${i})`}"
        id="qbtn-${i}"
        title="${tooltip}"
        ${unavailable ? 'style="opacity:0.45;cursor:not-allowed"' : ''}
      >
        <span>
          <div style="font-weight:700;font-size:0.95rem">${escHtml(fmt.label)}</div>
          <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px">
            ${fmt.ext} &nbsp;•&nbsp; ${fmt.size || 'Unknown'}
            ${unavailable ? '&nbsp; ⚠️ needs ffmpeg' : ''}
          </div>
        </span>
        <span class="quality-badge ${fmt.is_audio ? 'mp3' : ''}">${fmt.badge}</span>
      </button>
    `;
  }).join('');

  resultsArea.style.display = 'block';
  resultsArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Trigger real download via backend ───────────────────────────────────────
async function startDownload(index) {
  const fmt = window._currentFormats && window._currentFormats[index];
  if (!fmt) return;

  const btn = document.getElementById(`qbtn-${index}`);
  if (!btn) return;

  const origHtml = btn.innerHTML;

  // Disable all quality buttons during download to prevent double downloads
  const allBtns = document.querySelectorAll('.quality-btn');
  allBtns.forEach(b => {
    b.disabled = true;
    if (b !== btn) {
      b.style.opacity = '0.3';
    }
  });

  btn.style.borderColor = 'var(--primary)';
  btn.innerHTML = `
    <span>
      <div style="font-weight:700" class="dl-status-title">Starting download…</div>
      <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px" class="dl-status-subtitle">Contacting backend...</div>
    </span>
    <span class="quality-badge ${fmt.is_audio ? 'mp3' : ''}" style="animation:spin 1s linear infinite">⟳</span>
  `;

  showToast(`⬇️ Initializing download: ${fmt.label}`);

  try {
    const startRes = await fetch(`${API_BASE}/api/download/start?url=${encodeURIComponent(currentVideoUrl)}&format_id=${encodeURIComponent(fmt.format_id)}&audio=${fmt.is_audio ? 'true' : 'false'}`);
    const startData = await startRes.json();

    if (!startRes.ok || startData.error) {
      throw new Error(startData.error || 'Failed to start download');
    }

    const taskId = startData.task_id;

    // Poll for status
    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await fetch(`${API_BASE}/api/download/status?task_id=${taskId}`);
        if (!statusRes.ok) return;
        const task = await statusRes.json();

        if (task.status === 'downloading') {
          btn.innerHTML = `
            <span>
              <div style="font-weight:700">Downloading: ${task.progress}%</div>
              <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px">${task.speed} &nbsp;•&nbsp; ETA: ${task.eta}</div>
            </span>
            <span class="quality-badge ${fmt.is_audio ? 'mp3' : ''}" style="background:var(--primary);color:#000;font-weight:bold">${task.progress}%</span>
          `;
        } else if (task.status === 'processing') {
          btn.innerHTML = `
            <span>
              <div style="font-weight:700">Finalizing file…</div>
              <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px">Merging streams or converting to MP3...</div>
            </span>
            <span class="quality-badge ${fmt.is_audio ? 'mp3' : ''}" style="animation:spin 1s linear infinite">⟳</span>
          `;
        } else if (task.status === 'completed') {
          clearInterval(pollInterval);
          btn.innerHTML = `
            <span>
              <div style="font-weight:700;color:var(--primary)">Download Complete!</div>
              <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px">Saving to your computer...</div>
            </span>
            <span class="quality-badge ${fmt.is_audio ? 'mp3' : ''}">✓</span>
          `;

          // Trigger browser file download
          const downloadUrl = `${API_BASE}/api/download/file?task_id=${taskId}`;
          let frame = document.getElementById('dl-frame');
          if (!frame) {
            frame = document.createElement('iframe');
            frame.id = 'dl-frame';
            frame.style.display = 'none';
            document.body.appendChild(frame);
          }
          frame.src = downloadUrl;

          // Reset UI after 4 seconds
          setTimeout(() => {
            resetButtons();
          }, 4000);

        } else if (task.status === 'failed') {
          clearInterval(pollInterval);
          showToast(`❌ Download failed: ${task.error}`);
          resetButtons();
        }
      } catch (err) {
        // Ignore parsing/network errors during polling, just let it retry
      }
    }, 1500);

  } catch (err) {
    showToast(`❌ ${err.message}`);
    resetButtons();
  }

  function resetButtons() {
    allBtns.forEach(b => {
      b.disabled = false;
      b.style.opacity = '';
      b.style.borderColor = '';
    });
    btn.innerHTML = origHtml;
  }
}

// ── Auto-detect platform on paste ──────────────────────────────────────────
const urlInput = document.getElementById('video-url-input');
if (urlInput) {
  urlInput.addEventListener('paste', () => {
    setTimeout(() => {
      const v = urlInput.value.trim();
      if (!v) return;
      const platform = detectPlatform(v);
      const nice     = platform.charAt(0).toUpperCase() + platform.slice(1);
      document.querySelectorAll('.ptab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.platform === platform);
      });
      showToast(`🔍 Detected: ${nice}`);
    }, 80);
  });

  urlInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); handleDownload(e); }
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
