// ApplyLuma extension popup script (Phase 7)

const API_BASE = 'https://applyluma-production.up.railway.app';
const EXTENSION_AUTH_URL = 'https://applyluma.com/extension-auth';

// ── DOM references ──────────────────────────────────────────────────────────

const views = {
  noJob: document.getElementById('view-no-job'),
  connected: document.getElementById('view-connected'),
  connect: document.getElementById('view-connect'),
  save: document.getElementById('view-save'),
};

const connectedCount = document.getElementById('connected-count');
const linkSavedJobs = document.getElementById('link-saved-jobs');
const linkApp = document.getElementById('link-app');

const connectError = document.getElementById('connect-error');
const tokenInput = document.getElementById('token-input');
const btnLogin = document.getElementById('btn-login');
const btnConnect = document.getElementById('btn-connect');

const fieldTitle = document.getElementById('field-title');
const fieldCompany = document.getElementById('field-company');
const fieldUrl = document.getElementById('field-url');
const fieldDescription = document.getElementById('field-description');
const toggleNotes = document.getElementById('toggle-notes');
const notesField = document.getElementById('notes-field');
const fieldNotes = document.getElementById('field-notes');

const btnSave = document.getElementById('btn-save');
const btnSaveLabel = document.getElementById('btn-save-label');
const btnSaveSpinner = document.getElementById('btn-save-spinner');
const saveStatus = document.getElementById('save-status');

const scoreSection = document.getElementById('score-section');
const scoreValue = document.getElementById('score-value');
const scoreBar = document.getElementById('score-bar');
const scoreHint = document.getElementById('score-hint');

const btnTrack = document.getElementById('btn-track');
const trackStatus = document.getElementById('track-status');

const btnDisconnect = document.getElementById('btn-disconnect');

const tailorSection = document.getElementById('tailor-section');
const tailorUsage = document.getElementById('tailor-usage');
const tailorCvSelect = document.getElementById('tailor-cv-select');
const btnTailor = document.getElementById('btn-tailor');
const tailorStatus = document.getElementById('tailor-status');

// ── State ────────────────────────────────────────────────────────────────────

let savedRawJobPostingId = null;
let tailorPollTimer = null;

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

const normalizeUrl = (url) => ApplyLumaUrl.jobUrlKey(url);

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
  return { token: data.applyluma_token || null, refreshToken: data.applyluma_refresh_token || null };
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

// Forget the sign-in and say why the connect screen is back.
async function sessionEnded() {
  await clearTokens();
  connectError.textContent = 'Your session has expired. Log in again to continue.';
  connectError.classList.remove('hidden');
  showView('connect');
  throw new Error('Session expired. Please reconnect.');
}

async function fetchWithAuth(url, options = {}) {
  const { token, refreshToken } = await getTokens();

  const doFetch = (t) =>
    fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}), Authorization: `Bearer ${t}` },
    });

  if (!token) {
    showView('connect');
    throw new Error('Not connected. Please reconnect.');
  }

  let res = await doFetch(token);

  if (res.status === 401 && refreshToken) {
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
      await sessionEnded();
    }
  } else if (res.status === 401) {
    // A pasted token with nothing to renew it: the sign-in has run out.
    await sessionEnded();
  }

  return res;
}

// ── Initialise popup ────────────────────────────────────────────────────────

const JOB_TTL_MS = 15 * 60 * 1000; // 15 minutes
const SAVED_JOBS_URL = 'https://applyluma.com/discover?tab=saved';

// Ask the page in the active tab to read the job now. Reading on demand gets
// fields that had not rendered yet when the page first loaded, and always
// describes this tab rather than whichever tab was read last.
// The page script that reads each job board. A board's script is normally
// already in its tabs; it is loaded on demand into one that was open before
// the extension was installed or updated. Any other site gets the generic
// script, and only because the user opened the popup or used the shortcut
// there (activeTab).
const SITE_SCRIPTS = [
  [/(^|\.)linkedin\.com$/, 'content/linkedin.js'],
  [/(^|\.)indeed\.com$/, 'content/indeed.js'],
  [/(^|\.)arbetsformedlingen\.se$/, 'content/platsbanken.js'],
  [/(^|\.)glassdoor\.com$/, 'content/glassdoor.js'],
];

const GENERIC_SCRIPT = 'content/generic.js';

function siteScriptFor(url) {
  try {
    const { protocol, hostname } = new URL(url);
    if (protocol !== 'https:' && protocol !== 'http:') return null;
    const match = SITE_SCRIPTS.find(([pattern]) => pattern.test(hostname));
    return match ? match[1] : GENERIC_SCRIPT;
  } catch {
    return null;
  }
}

// Ask the tab's page script for the job. Resolves to null if nothing answers.
async function askTab(tabId) {
  try {
    return await Promise.race([
      chrome.tabs.sendMessage(tabId, { type: 'EXTRACT_JOB' }),
      new Promise((resolve) => setTimeout(() => resolve(null), 1500)),
    ]);
  } catch {
    return null; // no ApplyLuma script on this tab
  }
}

// Ask the tab; if it has no page script yet, load the right one and ask again.
// The browser only allows this on the job boards in the manifest and on the
// tab the user just invoked the extension on.
async function readJobFromTab(tab) {
  if (!tab || tab.id === undefined) return null;
  let reply = await askTab(tab.id);
  if (!reply) {
    const script = siteScriptFor(tab.url || '');
    if (script) {
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['content/url.js', 'content/common.js', script],
        });
        reply = await askTab(tab.id);
      } catch {
        // The page refused the script (a browser page, or a frame still loading).
      }
    }
  }
  return reply;
}

async function extractFromActiveTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const reply = await readJobFromTab(tab);
    return reply ? { answered: true, job: reply.job || null } : { answered: false };
  } catch {
    return { answered: false };
  }
}

async function init() {
  const [live, { linkedinJob: rawJob }, { token }] = await Promise.all([
    extractFromActiveTab(),
    chrome.storage.local.get('linkedinJob'),
    getTokens().then((t) => ({ token: t.token })),
  ]);
  const snapshot = rawJob && rawJob.extractedAt && (Date.now() - rawJob.extractedAt) < JOB_TTL_MS
    ? rawJob : null;
  // The tab's own answer wins; the snapshot only covers a page that could not answer.
  const linkedinJob = live.answered ? live.job : snapshot;

  const hasJob = linkedinJob && (linkedinJob.title || linkedinJob.company || linkedinJob.url);

  if (!hasJob && !token) { showView('noJob'); return; }
  if (!hasJob && token) {
    const { savedUrls } = await chrome.storage.local.get('savedUrls');
    const count = (savedUrls || []).length;
    connectedCount.textContent = count > 0
      ? `${count} job${count !== 1 ? 's' : ''} saved to ApplyLuma`
      : 'Connected to ApplyLuma';
    linkSavedJobs.addEventListener('click', (e) => { e.preventDefault(); chrome.tabs.create({ url: SAVED_JOBS_URL }); });
    linkApp.addEventListener('click', (e) => { e.preventDefault(); chrome.tabs.create({ url: 'https://applyluma.com' }); });
    showView('connected');
    return;
  }
  if (!token) { showView('connect'); return; }

  fieldTitle.value = linkedinJob.title || '';
  fieldCompany.value = linkedinJob.company || '';
  fieldUrl.value = linkedinJob.url || '';
  fieldDescription.value = linkedinJob.description || '';

  showView('save');
}

// ── Notes toggle ────────────────────────────────────────────────────────────

toggleNotes.addEventListener('click', (e) => {
  e.preventDefault();
  const isHidden = notesField.classList.toggle('hidden');
  toggleNotes.textContent = isHidden ? '+ Add note' : '− Hide note';
});

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

  let accessToken = raw;
  let refreshToken = null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed.access_token) { accessToken = parsed.access_token; refreshToken = parsed.refresh_token || null; }
  } catch { /* treat as raw access token */ }

  await setTokens(accessToken, refreshToken);
  await init();
});

// ── Save job ────────────────────────────────────────────────────────────────

btnSave.addEventListener('click', async () => {
  const { token } = await getTokens();
  if (!token) { showView('connect'); return; }

  const url = fieldUrl.value.trim();
  if (!url) { showStatus('Job URL is required.', 'error-msg'); return; }

  const notes = fieldNotes.value.trim();
  const body = {
    title: fieldTitle.value.trim() || 'Untitled',
    company: fieldCompany.value.trim() || 'Unknown',
    url,
    description: fieldDescription.value.trim(),
    source: detectSource(url),
    ...(notes ? { notes } : {}),
  };

  // Check local cache first to detect duplicates without waiting for the API.
  const { savedUrls: cachedUrls } = await chrome.storage.local.get('savedUrls');
  const alreadySaved = (cachedUrls || []).some((u) => normalizeUrl(u) === normalizeUrl(url));

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
    // The API calls it source_raw_job_posting_id; older servers only sent that.
    savedRawJobPostingId = saved.raw_job_posting_id || saved.source_raw_job_posting_id;
    showStatus(alreadySaved ? 'Already in your saved jobs ✓' : 'Saved to ApplyLuma!', 'success');
    btnSave.disabled = true;

    fetchAndRenderScore(savedRawJobPostingId);
    loadTailorSection(savedRawJobPostingId);
  } catch (err) {
    if (err.message && err.message.includes('reconnect')) return;
    showStatus('Network error — check your connection.', 'error-msg');
  } finally {
    setSaving(false);
  }
});

// ── Match score ─────────────────────────────────────────────────────────────

async function fetchAndRenderScore(rawJobPostingId) {
  try {
    const res = await fetchWithAuth(`${API_BASE}/api/v1/jobs/${rawJobPostingId}`);
    if (!res.ok) return;
    const job = await res.json();
    renderScore(job.match_score);
  } catch {
    renderScore(null);
  }
}

function renderScore(score) {
  scoreSection.classList.remove('hidden');
  btnTrack.classList.remove('hidden');

  if (score === null || score === undefined) {
    scoreValue.textContent = '—';
    scoreBar.style.width = '0%';
    scoreBar.style.background = '#d1d5db';
    scoreHint.textContent = 'Score computing… check Saved Jobs in a moment.';
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

// ── Track Application ────────────────────────────────────────────────────────

btnTrack.addEventListener('click', async () => {
  if (!savedRawJobPostingId) return;

  btnTrack.disabled = true;
  trackStatus.classList.add('hidden');

  try {
    const res = await fetchWithAuth(`${API_BASE}/api/v1/applications`, {
      method: 'POST',
      body: JSON.stringify({ raw_job_posting_id: savedRawJobPostingId, status: 'wishlist' }),
    });

    if (res.status === 201 || res.status === 200) {
      btnTrack.textContent = 'Tracked ✓';
      btnTrack.classList.add('btn-track--done');
    } else {
      const err = await res.json().catch(() => ({}));
      trackStatus.textContent = err.detail || `Error ${res.status}`;
      trackStatus.className = 'track-status error-msg';
      trackStatus.classList.remove('hidden');
      btnTrack.disabled = false;
    }
  } catch {
    trackStatus.textContent = 'Network error.';
    trackStatus.className = 'track-status error-msg';
    trackStatus.classList.remove('hidden');
    btnTrack.disabled = false;
  }
});

// ── AI Tailor ────────────────────────────────────────────────────────────────

async function loadTailorSection(rawJobPostingId) {
  try {
    const [cvsRes, usageRes] = await Promise.all([
      fetchWithAuth(`${API_BASE}/api/v1/cvs`),
      fetchWithAuth(`${API_BASE}/api/v1/tailor/usage`),
    ]);

    if (!cvsRes.ok || !usageRes.ok) return;

    const cvs = await cvsRes.json();
    const usage = await usageRes.json();

    // Populate CV dropdown — skip tailored CVs, put default first.
    const baseCvs = cvs.filter((c) => !c.is_tailored);
    if (baseCvs.length === 0) return;

    baseCvs.sort((a, b) => (b.is_default ? 1 : 0) - (a.is_default ? 1 : 0));
    // Built with DOM nodes, not innerHTML: CV titles and file names are
    // user-provided text and must never be parsed as markup.
    tailorCvSelect.replaceChildren(
      ...baseCvs.map((c) => {
        const option = document.createElement('option');
        option.value = c.id;
        option.textContent = `${c.title || c.filename}${c.is_default ? ' (default)' : ''}`;
        return option;
      }),
    );

    // Usage display.
    const { used_today: used, daily_limit: limit } = usage;
    if (limit !== null && limit !== undefined) {
      const remaining = Math.max(0, limit - used);
      tailorUsage.textContent = remaining > 0
        ? `${remaining} tailor${remaining !== 1 ? 's' : ''} remaining today`
        : 'Daily tailoring limit reached — upgrade for more';
      if (remaining === 0) {
        tailorUsage.classList.add('limit-reached');
        btnTailor.disabled = true;
      }
    } else {
      tailorUsage.textContent = `${used} tailor${used !== 1 ? 's' : ''} used today`;
    }

    tailorSection.classList.remove('hidden');
  } catch {
    // Fail silently — tailor section stays hidden.
  }
}

function setTailorStatus(text, type = '') {
  tailorStatus.textContent = text;
  tailorStatus.className = `tailor-status${type ? ` ${type}` : ''}`;
  tailorStatus.classList.remove('hidden');
}

btnTailor.addEventListener('click', async () => {
  if (!savedRawJobPostingId) return;

  const cvId = tailorCvSelect.value;
  if (!cvId) return;

  const intensity = document.querySelector('input[name="intensity"]:checked')?.value || 'medium';

  btnTailor.disabled = true;
  tailorStatus.classList.add('hidden');
  if (tailorPollTimer) { clearInterval(tailorPollTimer); tailorPollTimer = null; }

  try {
    const res = await fetchWithAuth(`${API_BASE}/api/v1/tailor/submit`, {
      method: 'POST',
      body: JSON.stringify({ cv_id: cvId, raw_job_posting_id: savedRawJobPostingId, intensity }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setTailorStatus(err.detail || `Error ${res.status}`, 'error-msg');
      btnTailor.disabled = false;
      return;
    }

    const { id: tailorJobId } = await res.json();
    setTailorStatus('Tailoring in progress…');

    tailorPollTimer = setInterval(async () => {
      try {
        const statusRes = await fetchWithAuth(`${API_BASE}/api/v1/tailor/${tailorJobId}/status`);
        if (!statusRes.ok) return;
        const { status } = await statusRes.json();

        if (status === 'complete') {
          clearInterval(tailorPollTimer);
          tailorPollTimer = null;
          const resultLink = document.createElement('a');
          resultLink.href = 'https://applyluma.com/ai-tailor';
          resultLink.target = '_blank';
          resultLink.textContent = 'View result in ApplyLuma →';
          tailorStatus.replaceChildren('Done! ', resultLink);
          tailorStatus.className = 'tailor-status';
          tailorStatus.classList.remove('hidden');
        } else if (status === 'failed') {
          clearInterval(tailorPollTimer);
          tailorPollTimer = null;
          setTailorStatus('Tailoring failed — try again in ApplyLuma.', 'error-msg');
          btnTailor.disabled = false;
        }
      } catch { /* keep polling */ }
    }, 3000);
  } catch (err) {
    if (err.message && err.message.includes('reconnect')) return;
    setTailorStatus('Network error — check your connection.', 'error-msg');
    btnTailor.disabled = false;
  }
});

// ── Disconnect ──────────────────────────────────────────────────────────────

btnDisconnect.addEventListener('click', async () => {
  if (tailorPollTimer) { clearInterval(tailorPollTimer); tailorPollTimer = null; }
  await clearTokens();
  showView('connect');
});

// ── Boot ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => void init());
