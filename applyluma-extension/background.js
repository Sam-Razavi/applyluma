// ApplyLuma extension background service worker (Phase 3)

const API_BASE = 'https://applyluma-production.up.railway.app';
const ALARM_NAME = 'al-saved-urls';
const REFRESH_MINUTES = 30;

// ── Saved URL refresh ────────────────────────────────────────────────────────

async function refreshSavedUrls() {
  const { applyluma_token: token } = await chrome.storage.local.get('applyluma_token');
  if (!token) return;

  try {
    const res = await fetch(`${API_BASE}/api/v1/jobs/bookmark/saved-urls`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;

    const { urls } = await res.json();
    // Normalize: strip query params and trailing slashes for reliable badge matching.
    const normalized = urls.map(normalizeUrl);
    await chrome.storage.local.set({ savedUrls: normalized });

    // Notify active LinkedIn tabs so badges update immediately.
    const tabs = await chrome.tabs.query({ url: 'https://www.linkedin.com/*' });
    for (const tab of tabs) {
      chrome.tabs.sendMessage(tab.id, { type: 'SAVED_URLS_UPDATED', urls: normalized }).catch(() => {});
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
