// ApplyLuma extension background service worker (Phase 7)

const API_BASE = 'https://applyluma-production.up.railway.app';
const ALARM_NAME = 'al-saved-urls';
const REFRESH_MINUTES = 30;

// Patterns for all supported job sites — used to broadcast badge updates.
// Kept in sync with manifest host_permissions / content_scripts so tab queries
// reach exactly the pages where content scripts run.
const JOB_SITE_PATTERNS = [
  'https://www.linkedin.com/*',
  'https://www.indeed.com/*',
  'https://se.indeed.com/*',
  'https://www.glassdoor.com/*',
  'https://arbetsformedlingen.se/*',
  'https://www.arbetsformedlingen.se/*',
];

// Same helpers as popup/popup.js (the two run in separate contexts).
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
          files: ['content/common.js', script],
        });
        reply = await askTab(tab.id);
      } catch {
        // The page refused the script (a browser page, or a frame still loading).
      }
    }
  }
  return reply;
}

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

function updateBadge(savedUrls) {
  const count = savedUrls ? savedUrls.length : 0;
  const text = count > 0 ? String(count > 99 ? '99+' : count) : '';
  chrome.action.setBadgeText({ text });
  if (text) chrome.action.setBadgeBackgroundColor({ color: '#10b981' });
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
    updateBadge(savedUrls);

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

const JOB_TTL_MS = 15 * 60 * 1000; // 15 minutes — mirrors popup.js

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== 'quick-save') return;

  // Read the job from the active tab now (its details may have rendered after
  // the page's own snapshot); fall back to the snapshot if the tab can't answer.
  let job = null;
  let answered = false;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const reply = await readJobFromTab(tab);
    if (reply) { answered = true; job = reply.job || null; }
  } catch { /* no ApplyLuma script on this tab */ }
  if (!answered) {
    const { linkedinJob: rawJob } = await chrome.storage.local.get('linkedinJob');
    job = rawJob && rawJob.extractedAt && (Date.now() - rawJob.extractedAt) < JOB_TTL_MS
      ? rawJob : null;
  }

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

// ── Helpers ──────────────────────────────────────────────────────────────────

async function clearStaleJobData() {
  const { linkedinJob } = await chrome.storage.local.get('linkedinJob');
  if (linkedinJob && linkedinJob.extractedAt && (Date.now() - linkedinJob.extractedAt) >= JOB_TTL_MS) {
    await chrome.storage.local.remove('linkedinJob');
  }
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: REFRESH_MINUTES });
  void refreshSavedUrls();
});

chrome.runtime.onStartup.addListener(() => {
  void clearStaleJobData();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) void refreshSavedUrls();
});

// Refresh on token change: connect triggers a refresh; disconnect clears the
// badge and the cached account data (the privacy policy promises this).
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local') return;
  if (changes.applyluma_token?.newValue) {
    void refreshSavedUrls();
  } else if (changes.applyluma_token && !changes.applyluma_token.newValue) {
    updateBadge([]);
    void chrome.storage.local.remove(['savedUrls', 'appliedUrls']);
  }
});
