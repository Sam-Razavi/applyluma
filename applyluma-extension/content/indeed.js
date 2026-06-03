// Content script: extracts job data from Indeed job pages and injects
// "Saved ✓" / "Applied ✓" badges on job cards in search results.

(function () {
  'use strict';

  const TITLE_SELECTORS = [
    '[data-testid="jobsearch-JobInfoHeader-title"]',
    'h1.jobsearch-JobInfoHeader-title',
    'h1[class*="JobInfoHeader"]',
    'h1',
  ];

  const COMPANY_SELECTORS = [
    '[data-testid="inlineHeader-companyName"]',
    '.jobsearch-InlineCompanyRating-companyHeader',
    '[data-company-name="true"]',
    '.icl-u-lg-mr--sm.icl-u-xs-mr--xs',
  ];

  const DESCRIPTION_SELECTORS = [
    '#jobDescriptionText',
    '[data-testid="jobDescriptionText"]',
    '.jobsearch-jobDescriptionText',
  ];

  // ── Helpers ──────────────────────────────────────────────────────────────

  function firstText(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) return el.textContent.trim();
    }
    return '';
  }

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
    return /\/viewjob|\/rc\/clk/.test(window.location.href);
  }

  function extractJobData() {
    if (!isJobPage()) {
      chrome.storage.session.set({ linkedinJob: null });
      return;
    }
    const data = {
      title: firstText(TITLE_SELECTORS),
      company: firstText(COMPANY_SELECTORS),
      url: window.location.href,
      description: firstText(DESCRIPTION_SELECTORS),
      extractedAt: Date.now(),
    };
    chrome.storage.session.set({ linkedinJob: data });
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

    // Indeed job cards — find all job-view links (strip tracking params).
    const links = document.querySelectorAll('a[data-jk], a.jcs-JobTitle, a[id^="job_"]');

    links.forEach((link) => {
      const normalized = normalizeUrl(link.href);
      const isApplied = appliedSet.has(normalized);
      const isSaved = savedSet.has(normalized);
      if (!isApplied && !isSaved) return;

      const card = link.closest('.job_seen_beacon, .tapItem, [data-testid="job-result"]');
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

      const titleEl = card.querySelector('h2, .jobTitle, [data-testid="job-title"]');
      if (titleEl) {
        titleEl.insertAdjacentElement('afterend', badge);
      } else {
        card.prepend(badge);
      }
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
      setTimeout(extractJobData, 800);
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

  setTimeout(extractJobData, 800);
  void refreshBadges();
})();
