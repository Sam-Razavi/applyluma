// Content script: extracts job data from Arbetsförmedlingen (Platsbanken) job pages
// and injects "Saved ✓" / "Applied ✓" badges on job cards in search results.

(function () {
  'use strict';

  const TITLE_SELECTORS = [
    '[class*="JobAd_title"]',
    '[class*="job-title"]',
    'h1[class*="heading"]',
    'h1',
  ];

  const COMPANY_SELECTORS = [
    '[class*="JobAd_employer"]',
    '[class*="employer-name"]',
    '[class*="company-name"]',
    '[data-testid="employer-name"]',
  ];

  const DESCRIPTION_SELECTORS = [
    '[class*="JobAd_description"]',
    '[class*="job-description"]',
    '[class*="JobDescription"]',
    'article',
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
    return /\/platsbanken\/annonser\//.test(window.location.href);
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

    const links = document.querySelectorAll(
      'a[data-testid="job-link"], pb-feature-ad a, article a[href*="/platsbanken/annonser/"]'
    );

    links.forEach((link) => {
      const normalized = normalizeUrl(link.href);
      const isApplied = appliedSet.has(normalized);
      const isSaved = savedSet.has(normalized);
      if (!isApplied && !isSaved) return;

      const card = link.closest('pb-feature-ad, article[data-testid], li');
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

      const titleEl = card.querySelector('h2, h3, [class*="title"]');
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
