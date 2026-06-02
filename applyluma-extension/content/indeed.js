// Content script: extracts job data from Indeed job pages.

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

  function firstText(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) return el.textContent.trim();
    }
    return '';
  }

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

  setTimeout(extractJobData, 800);

  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(extractJobData, 800);
    }
  }).observe(document, { subtree: true, childList: true });
})();
