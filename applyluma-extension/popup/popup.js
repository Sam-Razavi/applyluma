// ApplyLuma extension popup script (Phase 1)

const API_BASE = 'https://applyluma-production.up.railway.app';
const BOOKMARK_ENDPOINT = `${API_BASE}/api/v1/jobs/bookmark`;

// ── DOM references ──────────────────────────────────────────────────────────

const views = {
  noJob: document.getElementById('view-no-job'),
  connect: document.getElementById('view-connect'),
  save: document.getElementById('view-save'),
};

const connectError = document.getElementById('connect-error');
const tokenInput = document.getElementById('token-input');
const btnConnect = document.getElementById('btn-connect');

const fieldTitle = document.getElementById('field-title');
const fieldCompany = document.getElementById('field-company');
const fieldUrl = document.getElementById('field-url');
const fieldDescription = document.getElementById('field-description');

const btnSave = document.getElementById('btn-save');
const btnSaveLabel = document.getElementById('btn-save-label');
const btnSaveSpinner = document.getElementById('btn-save-spinner');
const saveStatus = document.getElementById('save-status');

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

// ── Initialise popup ────────────────────────────────────────────────────────

async function init() {
  const [{ linkedinJob }, { applyluma_token: token }] = await Promise.all([
    chrome.storage.session.get('linkedinJob'),
    chrome.storage.local.get('applyluma_token'),
  ]);

  const hasJob = linkedinJob && linkedinJob.title;

  if (!hasJob) {
    showView('noJob');
    return;
  }

  if (!token) {
    showView('connect');
    return;
  }

  // Populate fields with extracted (and editable) data.
  fieldTitle.value = linkedinJob.title || '';
  fieldCompany.value = linkedinJob.company || '';
  fieldUrl.value = linkedinJob.url || '';
  fieldDescription.value = linkedinJob.description || '';

  showView('save');
}

// ── Connect (token save) ────────────────────────────────────────────────────

btnConnect.addEventListener('click', async () => {
  const token = tokenInput.value.trim();
  if (!token) {
    connectError.textContent = 'Please paste your access token.';
    connectError.classList.remove('hidden');
    return;
  }
  connectError.classList.add('hidden');
  await chrome.storage.local.set({ applyluma_token: token });
  await init();
});

// ── Save job ────────────────────────────────────────────────────────────────

btnSave.addEventListener('click', async () => {
  const { applyluma_token: token } = await chrome.storage.local.get('applyluma_token');
  if (!token) {
    showView('connect');
    return;
  }

  const body = {
    title: fieldTitle.value.trim() || 'Untitled',
    company: fieldCompany.value.trim() || 'Unknown',
    url: fieldUrl.value.trim(),
    description: fieldDescription.value.trim(),
    source: 'linkedin',
  };

  if (!body.url) {
    showStatus('Job URL is required.', 'error-msg');
    return;
  }

  setSaving(true);
  saveStatus.classList.add('hidden');

  try {
    const res = await fetch(BOOKMARK_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    if (res.status === 401) {
      await chrome.storage.local.remove('applyluma_token');
      showView('connect');
      return;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showStatus(err.detail || `Error ${res.status}`, 'error-msg');
      return;
    }

    showStatus('Saved to ApplyLuma!', 'success');
    btnSave.disabled = true;
  } catch (err) {
    showStatus('Network error — check your connection.', 'error-msg');
  } finally {
    setSaving(false);
  }
});

// ── Disconnect ──────────────────────────────────────────────────────────────

btnDisconnect.addEventListener('click', async () => {
  await chrome.storage.local.remove('applyluma_token');
  showView('connect');
});

// ── Boot ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => void init());
