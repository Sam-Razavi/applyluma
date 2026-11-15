// Page script for career sites that have no script of their own. It is never
// listed in the manifest: the popup or the keyboard shortcut loads it into the
// active tab, and only when the user asks (activeTab), so it runs on no page
// the user has not pointed the extension at.

(function () {
  'use strict';
  if (ApplyLuma.siteLoaded) return;
  ApplyLuma.siteLoaded = true;

  const MAX_DESCRIPTION = 20000;

  // Applicant-tracking systems that host other companies' job pages.
  const JOB_HOSTS = /(^|\.)(teamtailor\.com|greenhouse\.io|lever\.co|myworkdayjobs\.com|smartrecruiters\.com|jobylon\.com|varbi\.com|recruitee\.com|ashbyhq\.com|workable\.com|reachmee\.com|jobvite\.com|bamboohr\.com|personio\.(com|de)|icims\.com)$/i;

  // Words that mark a job page in a path, in English and the Nordic languages.
  const JOB_PATH = /(^|[/_.-])(jobs?|jobb|careers?|karriar|karriere|vacanc(y|ies)|positions?|openings?|lediga-(jobb|tjanster)|annons(er)?|stilling(er)?|rekrytering|opportunit(y|ies))([/_.-]|$)/i;

  function meta(name) {
    const el = document.querySelector(`meta[property="${name}"], meta[name="${name}"]`);
    return ApplyLuma.clean(el && el.getAttribute('content'));
  }

  function looksLikeJobPage() {
    if (ApplyLuma.jsonLdJob()) return true;
    const { hostname, pathname, search } = window.location;
    return JOB_HOSTS.test(hostname) || JOB_PATH.test(pathname) || /[?&](gh_jid|jobid|job_id)=/i.test(search);
  }

  // Hosts where the employer is the first part of the path
  // (jobs.lever.co/<employer>/...) or of the host (<employer>.teamtailor.com).
  const TENANT_IN_PATH = /(^|\.)(greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|smartrecruiters\.com)$/i;
  const TENANT_IN_HOST = /(^|\.)(teamtailor\.com|recruitee\.com|bamboohr\.com|myworkdayjobs\.com|personio\.(com|de)|jobvite\.com)$/i;
  const NOT_A_TENANT = /^(www|jobs?|apply|careers?|boards?|job-boards|embed|app|ext|[a-z]{2})$/i;

  function tidyName(slug) {
    return decodeURIComponent(slug)
      .replace(/[-_+]+/g, ' ')
      .replace(/\b[a-z]/g, (c) => c.toUpperCase())
      .trim();
  }

  // On an applicant-tracking system the host names the system, not the
  // employer, so the employer is read from where that system puts it.
  function employerOnJobHost() {
    const { hostname, pathname } = window.location;
    let slug = '';
    if (TENANT_IN_PATH.test(hostname)) slug = pathname.split('/').filter(Boolean)[0] || '';
    else if (TENANT_IN_HOST.test(hostname)) slug = hostname.split('.')[0];
    return slug && !NOT_A_TENANT.test(slug) ? tidyName(slug) : '';
  }

  // The company's name as the page gives it; else, on a company's own site,
  // its domain without "www.". Never the name of a recruiting system: an
  // empty field the user fills in is better than a wrong employer.
  function siteName() {
    const named = meta('og:site_name');
    if (!JOB_HOSTS.test(window.location.hostname)) {
      return named || window.location.hostname.replace(/^www\./, '');
    }
    return employerOnJobHost() || (/greenhouse|lever|workday|teamtailor|reachmee|varbi|jobylon/i.test(named) ? '' : named);
  }

  const SITE = {
    isJobPage: looksLikeJobPage,
    // Structured data is written for exactly this purpose, so it is trusted
    // before anything guessed from an unknown page's layout.
    preferStructured: true,
    title: ['h1'],
    company: [],
    description: [
      '[itemprop="description"]',
      '[class*="job-description" i]',
      '[class*="jobDescription" i]',
      '[id*="job-description" i]',
      'main',
      'article',
      '[role="main"]',
    ],
    maxDescription: MAX_DESCRIPTION,
    fromDocumentTitle: () => ({
      title: meta('og:title') || ApplyLuma.clean(document.title),
      company: siteName(),
    }),
  };

  ApplyLuma.answerExtractRequests(SITE);
})();
