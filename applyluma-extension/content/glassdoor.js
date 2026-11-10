// Content script: extracts job data from Glassdoor job pages and injects
// "Saved ✓" / "Applied ✓" badges on job cards in search results.

(function () {
  'use strict';

  const TITLE_SELECTORS = [
    '[data-test="job-title"]',
    '.job-title',
    'h1[class*="title"]',
    'h1',
  ];

  const COMPANY_SELECTORS = [
    '[data-test="employer-name"]',
    '.employer-name',
    '[class*="EmployerProfile_employerName"]',
    '[class*="employer"]',
  ];

  const DESCRIPTION_SELECTORS = [
    '[data-test="jobDescriptionContent"]',
    '.jobDescriptionContent',
    '[class*="JobDetails_jobDescription"]',
    '#JobDescriptionContainer',
  ];

  // ── Helpers ──────────────────────────────────────────────────────────────

  function normalizeUrl(url) {
    try {
      const u = new URL(url);
      return u.origin + u.pathname.replace(/\/$/, '');
    } catch {
      return url;
    }
  }

  // ── Job detail extraction ────────────────────────────────────────────────

  function isJobPage() {
    return /\/job-listing\/|\/Jobs\/|\/partner\/jobListing/.test(window.location.href);
  }

  const SITE = {
    isJobPage,
    title: TITLE_SELECTORS,
    company: COMPANY_SELECTORS,
    description: DESCRIPTION_SELECTORS,
  };

  function extractJobData() {
    ApplyLuma.storeSnapshot(SITE);
  }

  // ── Badge injection ──────────────────────────────────────────────────────

  function injectBadgeStyles() {
    if (document.getElementById('al-badge-styles')) return;
    const style = document.createElement('style');
    style.id = 'al-badge-styles';
    style.textContent = `
      .al-saved-badge, .al-applied-badge {
        display: inline-flex;
        align-items: center;
        padding: 1px 7px;
        border-radius: 999px;
        color: #fff !important;
        font-size: 10px;
        font-weight: 700;
        margin-left: 6px;
        vertical-align: middle;
        white-space: nowrap;
        letter-spacing: 0.02em;
        flex-shrink: 0;
      }
      .al-saved-badge { background: #4f46e5; }
      .al-applied-badge { background: #10b981; }
    `;
    document.head.appendChild(style);
  }

  function injectBadges(savedUrls, appliedUrls = []) {
    const hasSaved = savedUrls && savedUrls.length > 0;
    const hasApplied = appliedUrls && appliedUrls.length > 0;
    if (!hasSaved && !hasApplied) return;

    injectBadgeStyles();
    const savedSet = new Set(savedUrls.map(normalizeUrl));
    const appliedSet = new Set(appliedUrls.map(normalizeUrl));

    const links = document.querySelectorAll('a[data-test="job-title"], a.jobLink, a[class*="jobTitle"]');

    links.forEach((link) => {
      const normalized = normalizeUrl(link.href);
      const isApplied = appliedSet.has(normalized);
      const isSaved = savedSet.has(normalized);
      if (!isApplied && !isSaved) return;

      const card = link.closest('li.react-job-listing, [data-test="jobListing"], article');
      if (!card) return;

      const wantClass = isApplied ? 'al-applied-badge' : 'al-saved-badge';
      const wantText = isApplied ? 'Applied ✓' : 'Saved ✓';

      const existing = card.querySelector('.al-saved-badge, .al-applied-badge');
      if (existing) {
        if (existing.className !== wantClass) {
          existing.className = wantClass;
          existing.textContent = wantText;
        }
        return;
      }

      const badge = document.createElement('span');
      badge.className = wantClass;
      badge.textContent = wantText;

      link.insertAdjacentElement('afterend', badge);
    });
  }

  async function refreshBadges() {
    const { savedUrls, appliedUrls } = await chrome.storage.local.get(['savedUrls', 'appliedUrls']);
    injectBadges(savedUrls || [], appliedUrls || []);
  }

  // ── SPA navigation + badge re-run ────────────────────────────────────────

  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(extractJobData, 1000);
    }
    void refreshBadges();
  }).observe(document, { subtree: true, childList: true });

  // ── Message listener (from background worker) ────────────────────────────

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'SAVED_URLS_UPDATED') {
      injectBadges(msg.urls || [], msg.appliedUrls || []);
    }
  });

  // ── Boot ─────────────────────────────────────────────────────────────────

  ApplyLuma.answerExtractRequests(SITE);
  setTimeout(extractJobData, 1000);
  // Job details often render after the first read; read again once they have.
  setTimeout(extractJobData, 3000);
  void refreshBadges();
})();
