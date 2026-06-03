// Content script: extracts job data from LinkedIn job pages and injects
// "Saved ✓" badges on job cards in search results.

(function () {
  'use strict';

  // ── Selector sets — primary then fallbacks ──────────────────────────────

  const TITLE_SELECTORS = [
    'h1.t-24',
    'h1[class*="job-title"]',
    '.job-details-jobs-unified-top-card__job-title h1',
    '.jobs-unified-top-card__job-title',
  ];

  const COMPANY_SELECTORS = [
    '.job-details-jobs-unified-top-card__company-name a',
    '.job-details-jobs-unified-top-card__company-name',
    '.jobs-unified-top-card__company-name a',
    '.jobs-unified-top-card__company-name',
    '[data-test-id="job-detail-company-name"]',
  ];

  const DESCRIPTION_SELECTORS = [
    '.jobs-description__content',
    '#job-details',
    '.jobs-box__html-content',
    '.description__text',
  ];

  // ── Helpers ─────────────────────────────────────────────────────────────

  function firstText(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) {
        return el.textContent.trim();
      }
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

  function extractJobData() {
    const url = window.location.href;

    if (!/linkedin\.com\/jobs\/view\//.test(url) && !/linkedin\.com\/jobs\/collections\//.test(url)) {
      chrome.storage.session.set({ linkedinJob: null });
      return;
    }

    const data = {
      title: firstText(TITLE_SELECTORS),
      company: firstText(COMPANY_SELECTORS),
      url,
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
      .al-saved-badge {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        padding: 1px 7px;
        border-radius: 999px;
        background: #4f46e5;
        color: #fff !important;
        font-size: 10px;
        font-weight: 700;
        margin-left: 6px;
        vertical-align: middle;
        white-space: nowrap;
        letter-spacing: 0.02em;
        flex-shrink: 0;
      }
    `;
    document.head.appendChild(style);
  }

  function injectBadges(savedUrls) {
    if (!savedUrls || savedUrls.length === 0) return;

    injectBadgeStyles();
    const savedSet = new Set(savedUrls.map(normalizeUrl));

    // LinkedIn job cards in list view — find all job-view links.
    const links = document.querySelectorAll(
      'a[href*="/jobs/view/"], a.job-card-list__title, a.job-card-container__link'
    );

    links.forEach((link) => {
      const normalized = normalizeUrl(link.href);
      if (!savedSet.has(normalized)) return;

      // Find the nearest card container — don't double-badge.
      const card = link.closest(
        '.job-card-container, .base-card, .scaffold-layout__list-item, .jobs-search-results__list-item'
      );
      if (!card) return;
      if (card.querySelector('.al-saved-badge')) return;

      const badge = document.createElement('span');
      badge.className = 'al-saved-badge';
      badge.textContent = 'Saved ✓';

      // Try to append after the job title link; fall back to appending to the card.
      const titleEl = card.querySelector('.job-card-list__title, .base-card__full-link, h3');
      if (titleEl) {
        titleEl.insertAdjacentElement('afterend', badge);
      } else {
        card.prepend(badge);
      }
    });
  }

  async function refreshBadges() {
    const { savedUrls } = await chrome.storage.local.get('savedUrls');
    injectBadges(savedUrls || []);
  }

  // ── SPA navigation + badge re-run ────────────────────────────────────────

  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(extractJobData, 800);
    }
    // Re-inject badges as new cards load (infinite scroll / SPA pagination).
    void refreshBadges();
  }).observe(document, { subtree: true, childList: true });

  // ── Message listener (from background worker) ────────────────────────────

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'SAVED_URLS_UPDATED') {
      injectBadges(msg.urls || []);
    }
  });

  // ── Boot ─────────────────────────────────────────────────────────────────

  setTimeout(extractJobData, 800);
  void refreshBadges();
})();
