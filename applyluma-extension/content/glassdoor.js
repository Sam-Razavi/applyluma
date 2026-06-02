// Content script: extracts job data from Glassdoor job pages.

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

  function firstText(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) return el.textContent.trim();
    }
    return '';
  }

  function isJobPage() {
    return /\/job-listing\/|\/Jobs\/|\/partner\/jobListing/.test(window.location.href);
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
