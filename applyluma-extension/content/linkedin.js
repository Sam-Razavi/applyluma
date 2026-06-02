// Content script: extracts job data from LinkedIn job pages and stores it in
// chrome.storage.session so the popup can read it without needing scripting
// permission on demand.

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

  function firstText(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) {
        return el.textContent.trim();
      }
    }
    return '';
  }

  function extractJobData() {
    const url = window.location.href;

    // Only extract on actual job posting pages.
    if (!/linkedin\.com\/jobs\/view\//.test(url) && !/linkedin\.com\/jobs\/collections\//.test(url)) {
      // Still clear stale data so popup doesn't show old job.
      chrome.storage.session.set({ linkedinJob: null });
      return;
    }

    const title = firstText(TITLE_SELECTORS);
    const company = firstText(COMPANY_SELECTORS);
    const description = firstText(DESCRIPTION_SELECTORS);

    const data = { title, company, url, description, extractedAt: Date.now() };
    chrome.storage.session.set({ linkedinJob: data });
  }

  // ── Initial extraction ──────────────────────────────────────────────────

  // Wait a tick to let React render the job details after navigation.
  setTimeout(extractJobData, 800);

  // ── SPA navigation observer ─────────────────────────────────────────────
  // LinkedIn is a React SPA; URL changes don't trigger full page reloads.

  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      // Wait for the new page to render before extracting.
      setTimeout(extractJobData, 800);
    }
  }).observe(document, { subtree: true, childList: true });
})();
