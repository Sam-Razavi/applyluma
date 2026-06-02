// Content script: extracts job data from Arbetsförmedlingen (Platsbanken) job pages.

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

  function firstText(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) return el.textContent.trim();
    }
    return '';
  }

  function isJobPage() {
    return /\/platsbanken\/annonser\//.test(window.location.href);
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

  setTimeout(extractJobData, 1000);

  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(extractJobData, 1000);
    }
  }).observe(document, { subtree: true, childList: true });
})();
