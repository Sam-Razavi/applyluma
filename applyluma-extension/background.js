// ApplyLuma extension background service worker (Phase 5)

const API_BASE = 'https://applyluma-production.up.railway.app';
const ALARM_NAME = 'al-saved-urls';
const REFRESH_MINUTES = 30;

// Patterns for all supported job sites — used to broadcast badge updates.
const JOB_SITE_PATTERNS = [
  'https://www.linkedin.com/*',
  'https://www.indeed.com/*',
  'https://uk.indeed.com/*',
  'https://www.glassdoor.com/*',
  'https://www.arbetsformedlingen.se/*',
];

// ── Auth helpers ─────────────────────────────────────────────────────────────

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

async function authedFetch(url, options = {}) {
  const { token, refreshToken } = await getTokens();
  if (!token) throw new Error('not_connected');

  const doFetch = (t) =>
    fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}), Authorization: `Bearer ${t}` },
    });

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
      await clearTokens();
      throw new Error('session_expired');
    }
  }

  return res;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function normalizeUrl(url) {
  try {
    const u = new URL(url);
    return u.origin + u.pathname.replace(/\/$/, '');
  } catch {
    return url;
  }
}

function detectSource(url) {
  if (url.includes('linkedin.com')) return 'linkedin';
  if (url.includes('indeed.')) return 'indeed';
  if (url.includes('arbetsformedlingen.se')) return 'platsbanken';
  if (url.includes('glassdoor.com')) return 'glassdoor';
  return 'extension';
}

function notify(title, message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title,
    message,
  });
}

// ── Saved / applied URL refresh ──────────────────────────────────────────────

async function refreshSavedUrls() {
  const { token } = await getTokens();
  if (!token) return;

  const headers = { Authorization: `Bearer ${token}` };

  try {
    const [savedRes, appliedRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/jobs/bookmark/saved-urls`, { headers }),
      fetch(`${API_BASE}/api/v1/applications/applied-urls`, { headers }),
    ]);

    const savedUrls = savedRes.ok ? (await savedRes.json()).urls.map(normalizeUrl) : [];
    const appliedUrls = appliedRes.ok ? (await appliedRes.json()).urls.map(normalizeUrl) : [];

    await chrome.storage.local.set({ savedUrls, appliedUrls });

    // Notify all active job-site tabs so badges update immediately.
    const tabs = await chrome.tabs.query({ url: JOB_SITE_PATTERNS });
    for (const tab of tabs) {
      chrome.tabs.sendMessage(tab.id, {
        type: 'SAVED_URLS_UPDATED',
        urls: savedUrls,
        appliedUrls,
      }).catch(() => {});
    }
  } catch {
    // Fail silently — next alarm will retry.
  }
}

// ── Keyboard shortcut — quick save ───────────────────────────────────────────

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== 'quick-save') return;

  // Read job data written by the content script.
  const { linkedinJob } = await chrome.storage.session.get('linkedinJob');
  const job = linkedinJob;

  if (!job || (!job.title && !job.company && !job.url)) {
    notify('ApplyLuma', 'No job detected on this page. Navigate to a job posting first.');
    return;
  }

  try {
    const body = {
      title: job.title || 'Untitled',
      company: job.company || 'Unknown',
      url: job.url || '',
      description: job.description || '',
      source: detectSource(job.url || ''),
    };

    const res = await authedFetch(`${API_BASE}/api/v1/jobs/bookmark`, {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (res.ok) {
      notify('Saved ✓', `${body.title} at ${body.company} saved to ApplyLuma.`);
      void refreshSavedUrls();
    } else {
      const err = await res.json().catch(() => ({}));
      notify('ApplyLuma — Save failed', err.detail || `Error ${res.status}`);
    }
  } catch (err) {
    if (err.message === 'not_connected') {
      notify('ApplyLuma', 'Not connected. Open the extension popup to log in.');
    } else if (err.message === 'session_expired') {
      notify('ApplyLuma', 'Session expired. Open the extension popup to reconnect.');
    } else {
      notify('ApplyLuma — Save failed', 'Network error. Check your connection.');
    }
  }
});

// ── Lifecycle ────────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: REFRESH_MINUTES });
  void refreshSavedUrls();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) void refreshSavedUrls();
});

// Refresh when the user stores a new token (extension just connected).
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.applyluma_token?.newValue) {
    void refreshSavedUrls();
  }
});
