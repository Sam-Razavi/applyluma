// ApplyLuma extension popup script (Phase 2)

const API_BASE = 'https://applyluma-production.up.railway.app';
const EXTENSION_AUTH_URL = 'https://applyluma.com/extension-auth';

// ── DOM references ──────────────────────────────────────────────────────────

const views = {
  noJob: document.getElementById('view-no-job'),
  connect: document.getElementById('view-connect'),
  save: document.getElementById('view-save'),
};

const connectError = document.getElementById('connect-error');
const tokenInput = document.getElementById('token-input');
const btnLogin = document.getElementById('btn-login');
const btnConnect = document.getElementById('btn-connect');

const fieldTitle = document.getElementById('field-title');
const fieldCompany = document.getElementById('field-company');
const fieldUrl = document.getElementById('field-url');
const fieldDescription = document.getElementById('field-description');

const btnSave = document.getElementById('btn-save');
const btnSaveLabel = document.getElementById('btn-save-label');
const btnSaveSpinner = document.getElementById('btn-save-spinner');
const saveStatus = document.getElementById('save-status');

const scoreSection = document.getElementById('score-section');
const scoreValue = document.getElementById('score-value');
const scoreBar = document.getElementById('score-bar');
const scoreHint = document.getElementById('score-hint');

const btnDisconnect = document.getElementById('btn-disconnect');

// ── Helpers ─────────────────────────────────────────────────────────────────

function showView(name) {
  Object.values(views).forEach((el) => el.classList.add('hidden'));
  views[name].classList.remove('hidden');
}

function showStatus(message, type) {
  saveStatus.textContent = message;
  saveStatus.className = `status ${type}`;
  saveStatus.classList.remove('hidden');
}

function setSaving(active) {
  btnSave.disabled = active;
  btnSaveLabel.classList.toggle('hidden', active);
  btnSaveSpinner.classList.toggle('hidden', !active);
}

function detectSource(url) {
  if (url.includes('linkedin.com')) return 'linkedin';
  if (url.includes('indeed.')) return 'indeed';
  if (url.includes('arbetsformedlingen.se')) return 'platsbanken';
  if (url.includes('glassdoor.com')) return 'glassdoor';
  return 'extension';
}

// ── Auth / token storage ─────────────────────────────────────────────────────

async function getTokens() {
  const data = await chrome.storage.local.get(['applyluma_token', 'applyluma_refresh_token']);
  return {
    token: data.applyluma_token || null,
    refreshToken: data.applyluma_refresh_token || null,
  };
}

async function setTokens(token, refreshToken) {
  await chrome.storage.local.set({
    applyluma_token: token,
    ...(refreshToken ? { applyluma_refresh_token: refreshToken } : {}),
  });
}

async function clearTokens() {
  await chrome.storage.local.remove(['applyluma_token', 'applyluma_refresh_token']);
}

// ── Authenticated fetch with auto-refresh ────────────────────────────────────

async function fetchWithAuth(url, options = {}) {
  const { token, refreshToken } = await getTokens();

  const doFetch = (t) =>
    fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
        Authorization: `Bearer ${t}`,
      },
    });

  let res = await doFetch(token);

  if (res.status === 401 && refreshToken) {
    // Try to refresh the access token.
    const refreshRes = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (refreshRes.ok) {
      const { access_token: newToken } = await refreshRes.json();
      await setTokens(newToken, refreshToken);
      res = await doFetch(newToken);
    } else {
      // Refresh failed — clear tokens and show connect view.
      await clearTokens();
      showView('connect');
      throw new Error('Session expired. Please reconnect.');
    }
  }

  return res;
}

// ── Initialise popup ────────────────────────────────────────────────────────

async function init() {
  const [{ linkedinJob }, { token }] = await Promise.all([
    chrome.storage.session.get('linkedinJob'),
    getTokens().then((t) => ({ token: t.token })),
  ]);

  const hasJob = linkedinJob && (linkedinJob.title || linkedinJob.company || linkedinJob.url);

  if (!hasJob) {
    showView('noJob');
    return;
  }

  if (!token) {
    showView('connect');
    return;
  }

  fieldTitle.value = linkedinJob.title || '';
  fieldCompany.value = linkedinJob.company || '';
  fieldUrl.value = linkedinJob.url || '';
  fieldDescription.value = linkedinJob.description || '';

  showView('save');
}

// ── Login with ApplyLuma ────────────────────────────────────────────────────

btnLogin.addEventListener('click', () => {
  chrome.tabs.create({ url: EXTENSION_AUTH_URL });
});

// ── Connect (token paste) ───────────────────────────────────────────────────

btnConnect.addEventListener('click', async () => {
  const raw = tokenInput.value.trim();
  if (!raw) {
    connectError.textContent = 'Please paste your access token.';
    connectError.classList.remove('hidden');
    return;
  }
  connectError.classList.add('hidden');

  // Accept either a JSON blob {"access_token":"...","refresh_token":"..."} (from
  // /extension-auth) or a plain access token string (backward compat with Settings).
  let accessToken = raw;
  let refreshToken = null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed.access_token) {
      accessToken = parsed.access_token;
      refreshToken = parsed.refresh_token || null;
    }
  } catch {
    // Not JSON — treat as a raw access token.
  }

  await setTokens(accessToken, refreshToken);
  await init();
});

// ── Save job ────────────────────────────────────────────────────────────────

btnSave.addEventListener('click', async () => {
  const { token } = await getTokens();
  if (!token) {
    showView('connect');
    return;
  }

  const url = fieldUrl.value.trim();
  if (!url) {
    showStatus('Job URL is required.', 'error-msg');
    return;
  }

  const body = {
    title: fieldTitle.value.trim() || 'Untitled',
    company: fieldCompany.value.trim() || 'Unknown',
    url,
    description: fieldDescription.value.trim(),
    source: detectSource(url),
  };

  setSaving(true);
  saveStatus.classList.add('hidden');
  scoreSection.classList.add('hidden');

  try {
    const res = await fetchWithAuth(`${API_BASE}/api/v1/jobs/bookmark`, {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showStatus(err.detail || `Error ${res.status}`, 'error-msg');
      return;
    }

    const saved = await res.json();
    showStatus('Saved to ApplyLuma!', 'success');
    btnSave.disabled = true;

    // Feature D: fetch and show match score.
    if (saved.raw_job_posting_id) {
      fetchMatchScore(saved.raw_job_posting_id);
    }
  } catch (err) {
    if (err.message && err.message.includes('reconnect')) return; // handled in fetchWithAuth
    showStatus('Network error — check your connection.', 'error-msg');
  } finally {
    setSaving(false);
  }
});

// ── Match score ─────────────────────────────────────────────────────────────

async function fetchMatchScore(rawJobPostingId) {
  try {
    const res = await fetchWithAuth(`${API_BASE}/api/v1/jobs/${rawJobPostingId}`);
    if (!res.ok) return;
    const job = await res.json();
    renderScore(job.match_score);
  } catch {
    // Score is best-effort; ignore errors silently.
  }
}

function renderScore(score) {
  scoreSection.classList.remove('hidden');

  if (score === null || score === undefined) {
    scoreValue.textContent = '—';
    scoreBar.style.width = '0%';
    scoreBar.style.background = '#d1d5db';
    scoreHint.textContent = 'Scoring pending — check back in Saved Jobs.';
    return;
  }

  const pct = Math.round(score);
  scoreValue.textContent = `${pct}%`;
  scoreBar.style.width = `${pct}%`;

  if (pct >= 80) {
    scoreBar.style.background = 'linear-gradient(90deg, #4f46e5, #7c3aed)';
    scoreHint.textContent = 'Strong match!';
  } else if (pct >= 60) {
    scoreBar.style.background = '#f59e0b';
    scoreHint.textContent = 'Good match.';
  } else {
    scoreBar.style.background = '#ef4444';
    scoreHint.textContent = 'Partial match — consider tailoring your CV.';
  }
}

// ── Disconnect ──────────────────────────────────────────────────────────────

btnDisconnect.addEventListener('click', async () => {
  await clearTokens();
  showView('connect');
});

// ── Boot ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => void init());
