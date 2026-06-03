// ApplyLuma extension background service worker (Phase 4)

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

// ── Saved / applied URL refresh ──────────────────────────────────────────────

async function refreshSavedUrls() {
  const { applyluma_token: token } = await chrome.storage.local.get('applyluma_token');
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

function normalizeUrl(url) {
  try {
    const u = new URL(url);
    return u.origin + u.pathname.replace(/\/$/, '');
  } catch {
    return url;
  }
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: REFRESH_MINUTES });
  void refreshSavedUrls();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) void refreshSavedUrls();
});

// Also refresh when the user stores a new token (extension just connected).
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.applyluma_token?.newValue) {
    void refreshSavedUrls();
  }
});
